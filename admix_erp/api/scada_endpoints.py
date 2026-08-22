"""SCADA ↔ ADMIX-ERP entegrasyon endpoint'leri.

Üç endpoint:

  1. POST /api/v1/production/batches/from-scada/
     Node-RED batch tamamlandığında POST atar.
     Idempotent: aynı batch_number iki kez gönderilirse 200 warning döner.

  2. GET  /api/v1/production/active-recipe/
     Node-RED aktif reçeteyi ERP'den çeker (Modbus'a yazılacak).
     Sadece is_active=True olan reçete döner.

  3. GET  /api/v1/production/scada/status/
     ERP'nin son 10 SCADA batch'ini + istatistikleri döner.
     Node-RED health check + ERP tarafında dashboard için.
"""
from __future__ import annotations

import datetime as dt
import logging
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from formulation.models import Recipe
from masterdata.models import RawMaterial
from production.models import (
    MaterialConsumption,
    ProductionBatch,
    ProductionOrder,
)
from quality.models import QCParameter, QCTestResult


log = logging.getLogger(__name__)


VERDICT_MAP = {
    "PASS": QCTestResult.Verdict.PASS,
    "FAIL": QCTestResult.Verdict.FAIL,
    "NA": QCTestResult.Verdict.NA,
}


# ---------------------------------------------------------------------------
# 1) POST — SCADA'dan tamamlanan batch verisi geldi
# ---------------------------------------------------------------------------

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def batch_from_scada(request):
    """SCADA batch tamamlanma verisini kaydeder.

    Beklenen JSON:
    ```
    {
        "batch_number": "BATCH-20260915-042",
        "recipe_code": "ADX-100-v3",
        "target_kg": 1000.0,
        "actual_kg": 999.7,
        "started_at": "2026-09-15T14:23:07Z",
        "completed_at": "2026-09-15T15:03:12Z",
        "operator": "Mohamed Belaidi",
        "consumptions": [
            {"code": "W",  "target": 600.0, "actual": 600.2}
        ],
        "qc_results": [
            {"parameter": "PH", "value": 5.8, "verdict": "PASS"}
        ]
    }
    ```

    Yanıt:
      201 Created — yeni batch
      200 OK       — daha önce POST edildi (idempotent), duplicate warning
      400 Bad Req  — validation hatası
      404 Not Found — reçete/hammadde/parametre kod eşleşmiyor
    """
    data = request.data or {}

    # Zorunlu alan kontrolü
    missing = [k for k in ("batch_number", "recipe_code", "target_kg", "actual_kg",
                           "started_at") if k not in data]
    if missing:
        return Response(
            {"error": f"Zorunlu alan eksik: {', '.join(missing)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    batch_number = str(data["batch_number"]).strip()

    # ── Idempotency: aynı batch geldi mi? ──
    existing = ProductionBatch.objects.filter(batch_number=batch_number).first()
    if existing is not None:
        log.info("SCADA duplicate batch %s (source=%s)", batch_number,
                 request.user.username)
        return Response({
            "batch_id": existing.pk,
            "batch_number": existing.batch_number,
            "duplicate": True,
            "message": "Bu batch daha önce ERP'ye kaydedilmişti.",
        }, status=status.HTTP_200_OK)

    # ── Sayısal alanlar ──
    try:
        target_kg = Decimal(str(data["target_kg"]))
        actual_kg = Decimal(str(data["actual_kg"]))
    except (InvalidOperation, ValueError) as e:
        return Response(
            {"error": f"target_kg / actual_kg geçersiz: {e}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ── Reçete ──
    recipe_code = str(data["recipe_code"]).strip()
    recipe = (
        Recipe.objects
        .filter(product__code=_recipe_code_to_product(recipe_code))
        .order_by("-version")
        .first()
    )
    if recipe is None:
        log.warning("SCADA: recipe not found for %s", recipe_code)
        return Response(
            {"error": f"Reçete bulunamadı: {recipe_code}"},
            status=status.HTTP_404_NOT_FOUND,
        )

    # ── Reaktör ──
    reactor = _default_reactor()
    if reactor is None:
        return Response(
            {"error": "Sistem konfigürasyon hatası: reaktör tanımlı değil."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # ── Transaction başlat ──
    try:
        with transaction.atomic():
            # ProductionOrder — hafif kayıt
            order, _ = ProductionOrder.objects.get_or_create(
                order_number=f"SCADA-{batch_number}",
                defaults={
                    "product": recipe.product,
                    "recipe": recipe,
                    "target_qty": target_kg,
                    "unit": recipe.unit,
                    "reactor": reactor,
                    "status": ProductionOrder.Status.COMPLETED,
                },
            )

            # ProductionBatch — asıl kayıt
            batch = ProductionBatch.objects.create(
                batch_number=batch_number,
                production_order=order,
                recipe=recipe,
                reactor=reactor,
                target_qty=target_kg,
                actual_qty=actual_kg,
                status=ProductionBatch.Status.COMPLETED,
                started_at=_parse_time(data["started_at"]),
                completed_at=_parse_time(data.get("completed_at")),
                operator=str(data.get("operator", "SCADA-AUTO"))[:120],
            )

            # Malzeme tüketimleri
            consumption_ids = []
            missing_codes = []
            for c in data.get("consumptions", []):
                rm = RawMaterial.objects.filter(code=c.get("code")).first()
                if rm is None:
                    missing_codes.append(c.get("code"))
                    continue
                cons = MaterialConsumption.objects.create(
                    batch=batch,
                    raw_material=rm,
                    target_weight=Decimal(str(c["target"])),
                    actual_weight=Decimal(str(c["actual"])),
                    source=MaterialConsumption.Source.SCADA,
                    dosed_at=batch.completed_at or timezone.now(),
                )
                consumption_ids.append(cons.pk)

            # QC test sonuçları
            qc_ids = []
            missing_params = []
            for qc in data.get("qc_results", []):
                param = QCParameter.objects.filter(code=qc.get("parameter")).first()
                if param is None:
                    missing_params.append(qc.get("parameter"))
                    continue
                result = QCTestResult.objects.create(
                    parameter=param,
                    batch=batch,
                    value=Decimal(str(qc["value"])),
                    verdict=VERDICT_MAP.get(qc.get("verdict", "NA"),
                                            QCTestResult.Verdict.NA),
                    tester="SCADA-AUTO",
                )
                qc_ids.append(result.pk)

    except (ValidationError, InvalidOperation, ValueError) as e:
        log.error("SCADA batch kaydı hatası: %s", e)
        return Response(
            {"error": f"Kayıt hatası: {e}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    warnings = {}
    if missing_codes:
        warnings["missing_raw_material_codes"] = missing_codes
    if missing_params:
        warnings["missing_qc_parameters"] = missing_params

    log.info("SCADA batch %s kaydedildi (kullanıcı=%s)",
             batch_number, request.user.username)

    return Response({
        "batch_id": batch.pk,
        "batch_number": batch.batch_number,
        "consumption_ids": consumption_ids,
        "qc_result_ids": qc_ids,
        "warnings": warnings or None,
        "message": f"Batch {batch.batch_number} SCADA'dan alındı.",
    }, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# 2) GET — Aktif reçete (SCADA/Node-RED PLC'ye yazar)
# ---------------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def active_recipe_for_scada(request):
    """SCADA aktif reçeteyi çeker.

    Query param:
      product_code (opsiyonel)  — belirtilirse o ürünün aktif reçetesi
                                  yoksa sistemdeki tek aktif reçete

    Yanıt (200):
    ```
    {
        "product_code": "ADX-100",
        "product_name": "Superplasticizer PCE",
        "recipe_code": "ADX-100-v3",
        "version": 3,
        "base_batch_size": 1000.0,
        "unit": "kg",
        "lines": [
            {"code": "W",  "quantity": 600.0, "tolerance_pct": 0.5, "is_complement": true},
            {"code": "M1", "quantity": 250.0, "tolerance_pct": 0.5, "is_complement": false}
        ],
        "quality_targets": {
            "ph_min": 4.5, "ph_max": 7.0,
            "temp_max_c": 45.0, "chloride_max_ppm": 800.0
        }
    }
    ```

    Yanıt (404): aktif reçete yok
    """
    product_code = request.query_params.get("product_code")
    qs = Recipe.objects.filter(is_active=True).select_related("product", "unit")

    if product_code:
        qs = qs.filter(product__code=product_code)

    recipe = qs.first()
    if recipe is None:
        return Response(
            {"error": f"Aktif reçete bulunamadı"
                      f"{' (product_code=' + product_code + ')' if product_code else ''}."},
            status=status.HTTP_404_NOT_FOUND,
        )

    lines = []
    for line in recipe.lines.select_related("raw_material").order_by("sequence"):
        lines.append({
            "sequence": line.sequence,
            "code": line.raw_material.code,
            "name": line.raw_material.name,
            "quantity": float(line.quantity),
            "tolerance_pct": float(line.tolerance_pct),
            "is_complement": line.is_complement,
        })

    # Kalite hedefleri — QCSpec'ten türet (varsa)
    quality_targets = _quality_targets_for_product(recipe.product)

    return Response({
        "product_code": recipe.product.code,
        "product_name": recipe.product.name,
        "recipe_code": f"{recipe.product.code}-v{recipe.version}",
        "version": recipe.version,
        "base_batch_size": float(recipe.base_batch_size),
        "unit": recipe.unit.code,
        "lines": lines,
        "quality_targets": quality_targets,
        "fetched_at": timezone.now().isoformat(),
    }, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# 3) GET — SCADA entegrasyon durumu (sağlık kontrol + son batchler)
# ---------------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def scada_status(request):
    """Node-RED health check + ADMIX-ERP'nin gördüğü son SCADA batch listesi.

    Yanıt (200):
    ```
    {
        "erp_status": "OK",
        "server_time": "2026-09-15T15:04:12Z",
        "authenticated_as": "scada_bridge",
        "stats": {
            "scada_batches_today": 8,
            "scada_batches_week": 41,
            "last_batch_at": "2026-09-15T15:03:12Z"
        },
        "recent_batches": [
            {"batch_number": "BATCH-20260915-042", "recipe": "ADX-100-v3",
             "actual_kg": 999.7, "completed_at": "2026-09-15T15:03:12Z"}
        ]
    }
    ```
    """
    now = timezone.now()
    today = now.date()
    week_ago = today - dt.timedelta(days=7)

    scada_batches = ProductionBatch.objects.filter(
        production_order__order_number__startswith="SCADA-"
    ).select_related("recipe__product").order_by("-created_at")

    today_count = scada_batches.filter(created_at__date=today).count()
    week_count = scada_batches.filter(created_at__date__gte=week_ago).count()

    last_batch = scada_batches.first()
    last_batch_at = last_batch.completed_at.isoformat() if (
        last_batch and last_batch.completed_at
    ) else None

    recent = []
    for b in scada_batches[:10]:
        recent.append({
            "batch_number": b.batch_number,
            "recipe": f"{b.recipe.product.code}-v{b.recipe.version}",
            "target_kg": float(b.target_qty),
            "actual_kg": float(b.actual_qty) if b.actual_qty else None,
            "operator": b.operator,
            "started_at": b.started_at.isoformat() if b.started_at else None,
            "completed_at": b.completed_at.isoformat() if b.completed_at else None,
        })

    return Response({
        "erp_status": "OK",
        "server_time": now.isoformat(),
        "authenticated_as": request.user.username,
        "stats": {
            "scada_batches_today": today_count,
            "scada_batches_week": week_count,
            "last_batch_at": last_batch_at,
        },
        "recent_batches": recent,
    }, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Yardımcı fonksiyonlar
# ---------------------------------------------------------------------------

def _recipe_code_to_product(recipe_code: str) -> str:
    """'ADX-100-v3' → 'ADX-100'."""
    parts = recipe_code.split("-v")
    return parts[0] if len(parts) == 2 else recipe_code


def _default_reactor():
    from masterdata.models import Container
    return Container.objects.filter(
        container_type=Container.ContainerType.REACTOR
    ).first()


def _parse_time(value):
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return value
    return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _quality_targets_for_product(product) -> dict:
    """Ürün için aktif QCSpec'lerden kalite hedefleri çıkar."""
    from quality.models import QCSpec

    targets = {}
    specs = QCSpec.objects.filter(product=product, is_active=True).select_related("parameter")
    for spec in specs:
        code = spec.parameter.code.upper()
        if code in ("PH", "AT_R01_PH"):
            targets["ph_min"] = float(spec.min_value or 0)
            targets["ph_max"] = float(spec.max_value or 14)
        elif code in ("TEMP", "TT_R01_TEMP", "TEMPERATURE"):
            targets["temp_max_c"] = float(spec.max_value or 60)
        elif code in ("CHLORIDE", "CL", "AT_R01_CL"):
            targets["chloride_max_ppm"] = float(spec.max_value or 1000)
    return targets

"""SCADA servisleri: reçete indirme + tartım ingest (tag → consumption eşleşmesi)."""
from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from production.models import MaterialConsumption, ProductionBatch, ProductionOrder
from production.services import create_batch_from_order, record_dosing

from .adapters import PLCAdapter, WeighmentSample, build_adapter
from .models import PLCEndpoint, RecipeDownload, WeighmentEvent


# ---------------------------------------------------------------------------
# Reçete indirme
# ---------------------------------------------------------------------------

def build_recipe_payload(order: ProductionOrder, batch: ProductionBatch | None) -> dict:
    """PLC'ye gönderilecek reçete payload'unu üretir.

    Sabitlenmiş versiyondan ölçeklenmiş satırlar dahil edilir.
    """
    recipe = order.recipe
    lines = [
        {
            "sequence": s["sequence"],
            "material_code": s["raw_material"].code,
            "target_weight": str(s["quantity"]),
            "tolerance_pct": str(s["tolerance_pct"]),
        }
        for s in recipe.scaled_lines(order.target_qty)
    ]
    return {
        "order_number": order.order_number,
        "batch_number": batch.batch_number if batch else None,
        "product_code": recipe.product.code,
        "recipe_version": recipe.version,
        "target_qty": str(order.target_qty),
        "reactor": order.reactor.code,
        "lines": lines,
    }


@transaction.atomic
def download_recipe(
    endpoint: PLCEndpoint,
    order: ProductionOrder,
    *,
    batch: ProductionBatch | None = None,
    auto_create_batch: bool = True,
    adapter: PLCAdapter | None = None,
) -> RecipeDownload:
    """Emirden reçete payload'u üretip PLC'ye gönderir; RecipeDownload audit kaydı yazar.

    Batch verilmediyse ve `auto_create_batch` doğruysa, order için otomatik parti
    oluşturulur (batch_number `AUTO-<order_number>-<n>`).
    """
    if batch is None and auto_create_batch:
        n = order.batches.count() + 1
        batch = create_batch_from_order(
            order, batch_number=f"AUTO-{order.order_number}-{n}"
        )

    payload = build_recipe_payload(order, batch)
    download = RecipeDownload.objects.create(
        endpoint=endpoint,
        production_order=order,
        batch=batch,
        payload=payload,
        status=RecipeDownload.Status.PENDING,
    )

    adapter = adapter or build_adapter(endpoint)
    try:
        response = adapter.send_recipe(payload)
    except Exception as exc:  # pragma: no cover
        download.status = RecipeDownload.Status.FAILED
        download.response = f"{type(exc).__name__}: {exc}"
        download.save(update_fields=["status", "response", "updated_at"])
        raise

    download.status = (
        RecipeDownload.Status.SIMULATED
        if response == "MOCK_ACK"
        else RecipeDownload.Status.SENT
    )
    download.sent_at = timezone.now()
    download.response = response
    download.save(update_fields=["status", "sent_at", "response", "updated_at"])
    return download


# ---------------------------------------------------------------------------
# Tartım ingest
# ---------------------------------------------------------------------------

def _parse_tag(tag: str) -> tuple[str, str]:
    """Tag formatı: `<batch_number>.<material_code>`."""
    if "." not in tag:
        raise ValueError(f"Geçersiz tag formatı (nokta bekleniyor): {tag}")
    batch_number, material_code = tag.rsplit(".", 1)
    return batch_number, material_code


def _find_consumption(batch_number: str, material_code: str) -> MaterialConsumption | None:
    return (
        MaterialConsumption.objects
        .select_related("batch", "raw_material")
        .filter(batch__batch_number=batch_number,
                raw_material__code=material_code,
                actual_weight__isnull=True)
        .order_by("sequence")
        .first()
    )


@transaction.atomic
def ingest_weighment(
    endpoint: PLCEndpoint,
    sample: WeighmentSample,
) -> WeighmentEvent:
    """Bir tartım örneğini işler:

    1. WeighmentEvent kaydı açar (RECEIVED)
    2. Tag'i (batch, material) olarak çözer
    3. `actual_weight=null` olan ilgili MaterialConsumption'ı bulur
    4. `record_dosing(..., source=SCADA)` çağırır → FEFO lot + stok hareketi + tolerans
    5. Event'i MATCHED / UNMATCHED / FAILED olarak kapatır
    """
    event = WeighmentEvent.objects.create(
        endpoint=endpoint,
        tag=sample.tag,
        weight=Decimal(sample.weight),
        plc_timestamp=sample.plc_timestamp,
        raw_payload=sample.raw or {},
        status=WeighmentEvent.Status.RECEIVED,
    )

    try:
        batch_number, material_code = _parse_tag(sample.tag)
    except ValueError as exc:
        event.status = WeighmentEvent.Status.FAILED
        event.error_message = str(exc)
        event.save(update_fields=["status", "error_message", "updated_at"])
        return event

    consumption = _find_consumption(batch_number, material_code)
    if consumption is None:
        event.status = WeighmentEvent.Status.UNMATCHED
        event.error_message = (
            f"Bekleyen tüketim bulunamadı: {batch_number}.{material_code}"
        )
        event.save(update_fields=["status", "error_message", "updated_at"])
        return event

    try:
        record_dosing(
            consumption,
            actual_weight=Decimal(sample.weight),
            source=MaterialConsumption.Source.SCADA,
        )
    except ValidationError as exc:
        event.status = WeighmentEvent.Status.FAILED
        event.error_message = "; ".join(exc.messages)
        event.save(update_fields=["status", "error_message", "updated_at"])
        return event

    event.consumption = consumption
    event.status = WeighmentEvent.Status.MATCHED
    event.save(update_fields=["consumption", "status", "updated_at"])
    return event


def poll_and_ingest(
    endpoint: PLCEndpoint,
    *,
    adapter: PLCAdapter | None = None,
    limit: int | None = None,
) -> list[WeighmentEvent]:
    """Endpoint'ten tartımları çek ve ingest et. Adapter test için enjekte edilebilir."""
    adapter = adapter or build_adapter(endpoint)
    samples = list(adapter.poll_weighments())
    if limit is not None:
        samples = samples[:limit]
    return [ingest_weighment(endpoint, s) for s in samples]

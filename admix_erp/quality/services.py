"""Kalite servisleri: test kaydı, otomatik değerlendirme, karantina/serbest bırakma, COA üretimi."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from inventory.models import RawMaterialLot
from production.models import ProductionBatch

from .models import CertificateOfAnalysis, QCParameter, QCSpec, QCTestResult


# ---------------------------------------------------------------------------
# Spec çözümleme
# ---------------------------------------------------------------------------

def _spec_for(parameter: QCParameter, *, lot: RawMaterialLot | None = None,
              batch: ProductionBatch | None = None) -> QCSpec | None:
    if lot is not None:
        return QCSpec.objects.filter(parameter=parameter, raw_material=lot.raw_material).first()
    if batch is not None:
        return QCSpec.objects.filter(parameter=parameter, product=batch.recipe.product).first()
    return None


# ---------------------------------------------------------------------------
# Test kaydı
# ---------------------------------------------------------------------------

@transaction.atomic
def record_test(
    parameter: QCParameter,
    value: Decimal | None,
    *,
    lot: RawMaterialLot | None = None,
    batch: ProductionBatch | None = None,
    tester: str = "",
    notes: str = "",
) -> QCTestResult:
    """QC ölçüm kaydeder ve spec'e göre verdict verir."""
    if (lot is None) == (batch is None):
        raise ValidationError("Ya lot ya da batch verilmeli (yalnızca biri).")

    spec = _spec_for(parameter, lot=lot, batch=batch)
    verdict = spec.evaluate(value) if spec else QCTestResult.Verdict.NA

    return QCTestResult.objects.create(
        parameter=parameter, lot=lot, batch=batch,
        value=value, verdict=verdict, tester=tester, notes=notes,
    )


# ---------------------------------------------------------------------------
# Lot iş akışı
# ---------------------------------------------------------------------------

@dataclass
class QCEvaluation:
    all_mandatory_present: bool
    all_pass: bool
    fails: list[str]
    missing: list[str]


def evaluate_lot(lot: RawMaterialLot) -> QCEvaluation:
    """Hammadde lotu için tüm zorunlu spec'ler test edilmiş mi ve geçti mi?"""
    specs = QCSpec.objects.filter(raw_material=lot.raw_material)
    results = {r.parameter_id: r for r in lot.qc_results.all()}
    fails: list[str] = []
    missing: list[str] = []
    for spec in specs:
        r = results.get(spec.parameter_id)
        if r is None:
            if spec.is_mandatory:
                missing.append(spec.parameter.code)
            continue
        if r.verdict == QCTestResult.Verdict.FAIL:
            fails.append(spec.parameter.code)
    return QCEvaluation(
        all_mandatory_present=not missing,
        all_pass=not fails,
        fails=fails,
        missing=missing,
    )


@transaction.atomic
def release_lot(lot: RawMaterialLot) -> RawMaterialLot:
    """Zorunlu testler eksiksiz ve PASS ise lotu RELEASED yap."""
    ev = evaluate_lot(lot)
    if not ev.all_mandatory_present:
        raise ValidationError(f"Eksik zorunlu testler: {', '.join(ev.missing)}")
    if not ev.all_pass:
        raise ValidationError(f"FAIL testler var: {', '.join(ev.fails)}")
    lot.qc_status = RawMaterialLot.QCStatus.RELEASED
    lot.save(update_fields=["qc_status", "updated_at"])
    return lot


@transaction.atomic
def quarantine_lot(lot: RawMaterialLot, reason: str = "") -> RawMaterialLot:
    lot.qc_status = RawMaterialLot.QCStatus.QUARANTINE
    lot.save(update_fields=["qc_status", "updated_at"])
    return lot


@transaction.atomic
def reject_lot(lot: RawMaterialLot, reason: str = "") -> RawMaterialLot:
    lot.qc_status = RawMaterialLot.QCStatus.REJECTED
    lot.save(update_fields=["qc_status", "updated_at"])
    return lot


# ---------------------------------------------------------------------------
# Parti iş akışı
# ---------------------------------------------------------------------------

def evaluate_batch(batch: ProductionBatch) -> QCEvaluation:
    """Mamul partisi için tüm zorunlu spec'ler test edilmiş mi ve geçti mi?"""
    specs = QCSpec.objects.filter(product=batch.recipe.product)
    results = {r.parameter_id: r for r in batch.qc_results.all()}
    fails: list[str] = []
    missing: list[str] = []
    for spec in specs:
        r = results.get(spec.parameter_id)
        if r is None:
            if spec.is_mandatory:
                missing.append(spec.parameter.code)
            continue
        if r.verdict == QCTestResult.Verdict.FAIL:
            fails.append(spec.parameter.code)
    return QCEvaluation(
        all_mandatory_present=not missing,
        all_pass=not fails,
        fails=fails,
        missing=missing,
    )


@transaction.atomic
def release_batch(batch: ProductionBatch) -> ProductionBatch:
    """Parti QC'yi geçtiyse RELEASED yap. State machine üzerinden."""
    ev = evaluate_batch(batch)
    if not ev.all_mandatory_present:
        raise ValidationError(f"Eksik zorunlu testler: {', '.join(ev.missing)}")
    if not ev.all_pass:
        raise ValidationError(f"FAIL testler var: {', '.join(ev.fails)}")
    batch.qc_status = ProductionBatch.QCStatus.RELEASED
    batch.save(update_fields=["qc_status", "updated_at"])
    # Durum makinesi: COMPLETED veya QC_HOLD'dan RELEASED'a geçebilir
    if batch.status in {ProductionBatch.Status.COMPLETED, ProductionBatch.Status.QC_HOLD}:
        batch.transition_to(ProductionBatch.Status.RELEASED)
    return batch


@transaction.atomic
def reject_batch(batch: ProductionBatch, reason: str = "") -> ProductionBatch:
    batch.qc_status = ProductionBatch.QCStatus.REJECTED
    batch.qc_notes = (batch.qc_notes + "\n" + reason).strip()
    batch.save(update_fields=["qc_status", "qc_notes", "updated_at"])
    if batch.status in {ProductionBatch.Status.COMPLETED, ProductionBatch.Status.QC_HOLD}:
        batch.transition_to(ProductionBatch.Status.REJECTED)
    return batch


# ---------------------------------------------------------------------------
# COA
# ---------------------------------------------------------------------------

@transaction.atomic
def generate_coa(
    batch: ProductionBatch,
    coa_number: str | None = None,
    issued_by: str = "",
    summary: str = "",
) -> CertificateOfAnalysis:
    """Parti için COA üretir. Yalnız RELEASED partiler için yayımlanabilir.

    Zaten mevcut COA varsa döner; DRAFT ise ISSUED'a çevirmez, çağıran karar verir.
    """
    coa = CertificateOfAnalysis.objects.filter(batch=batch).first()
    if coa is None:
        coa = CertificateOfAnalysis.objects.create(
            batch=batch,
            coa_number=coa_number or f"COA-{batch.batch_number}",
            summary=summary,
        )

    if batch.qc_status != ProductionBatch.QCStatus.RELEASED:
        raise ValidationError("Yalnızca QC-RELEASED parti için COA yayımlanabilir.")

    coa.status = CertificateOfAnalysis.Status.ISSUED
    coa.issued_at = timezone.now()
    coa.issued_by = issued_by or coa.issued_by
    if summary:
        coa.summary = summary
    coa.save(update_fields=["status", "issued_at", "issued_by", "summary", "updated_at"])
    return coa


def coa_payload(coa: CertificateOfAnalysis) -> dict:
    """COA gövdesi: parti + reçete + tüm QC sonuçları + tüketilen lotların COA ref'leri."""
    batch = coa.batch
    results = [
        {
            "parameter": r.parameter.code,
            "name": r.parameter.name,
            "unit": r.parameter.unit,
            "method": r.parameter.get_method_display(),
            "value": r.value,
            "verdict": r.verdict,
            "tested_at": r.tested_at,
        }
        for r in batch.qc_results.select_related("parameter").all()
    ]
    consumed_lots = [
        {
            "raw_material": c.raw_material.code,
            "lot_number": c.lot.lot_number if c.lot else None,
            "coa_reference": c.lot.coa_reference if c.lot else None,
            "supplier": c.lot.supplier.name if (c.lot and c.lot.supplier) else None,
        }
        for c in batch.consumptions.select_related("raw_material", "lot", "lot__supplier").all()
    ]
    return {
        "coa_number": coa.coa_number,
        "status": coa.status,
        "issued_at": coa.issued_at,
        "issued_by": coa.issued_by,
        "batch_number": batch.batch_number,
        "product": batch.recipe.product.code,
        "product_name": batch.recipe.product.name,
        "recipe_version": batch.recipe.version,
        "target_qty": batch.target_qty,
        "actual_qty": batch.actual_qty,
        "results": results,
        "consumed_lots": consumed_lots,
        "summary": coa.summary,
    }

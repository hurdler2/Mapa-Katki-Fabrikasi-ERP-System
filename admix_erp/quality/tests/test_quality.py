"""Kalite akışı testleri: spec değerlendirme, lot/parti release/reject, COA."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from inventory.models import RawMaterialLot
from production.models import ProductionBatch
from production.services import create_batch_from_order, record_dosing
from quality.models import CertificateOfAnalysis, QCParameter, QCSpec, QCTestResult
from quality.services import (
    coa_payload,
    evaluate_batch,
    evaluate_lot,
    generate_coa,
    quarantine_lot,
    record_test,
    reject_batch,
    release_batch,
    release_lot,
)


pytestmark = pytest.mark.django_db


# --- fixtures ---------------------------------------------------------------

@pytest.fixture
def qc_params(db):
    ph = QCParameter.objects.create(code="PH", name="pH", unit="")
    density = QCParameter.objects.create(code="DENSITY", name="Yoğunluk", unit="g/cm³")
    solids = QCParameter.objects.create(code="SOLIDS", name="Katı %", unit="%")
    return {"PH": ph, "DENSITY": density, "SOLIDS": solids}


@pytest.fixture
def product_specs(product, qc_params):
    QCSpec.objects.create(parameter=qc_params["PH"], product=product,
                          min_value=Decimal("4.0"), max_value=Decimal("7.0"))
    QCSpec.objects.create(parameter=qc_params["DENSITY"], product=product,
                          min_value=Decimal("1.05"), max_value=Decimal("1.15"))
    QCSpec.objects.create(parameter=qc_params["SOLIDS"], product=product,
                          min_value=Decimal("35"), max_value=Decimal("42"))
    return True


@pytest.fixture
def raw_specs(raws, qc_params):
    QCSpec.objects.create(parameter=qc_params["DENSITY"], raw_material=raws["SP"],
                          min_value=Decimal("1.05"), max_value=Decimal("1.12"))
    return True


@pytest.fixture
def pending_sp_lot(raws, supplier):
    return RawMaterialLot.objects.create(
        lot_number="LOT-SP-PEND", raw_material=raws["SP"], supplier=supplier,
        received_date=dt.date.today(),
        expiry_date=dt.date.today() + dt.timedelta(days=180),
        received_qty=Decimal("500"), remaining_qty=Decimal("500"),
        qc_status=RawMaterialLot.QCStatus.PENDING,
    )


# --- QCSpec.evaluate --------------------------------------------------------

def test_spec_evaluate_pass_fail_na(qc_params, product):
    spec = QCSpec.objects.create(parameter=qc_params["PH"], product=product,
                                 min_value=Decimal("4"), max_value=Decimal("7"))
    assert spec.evaluate(Decimal("5.5")) == QCTestResult.Verdict.PASS
    assert spec.evaluate(Decimal("3.9")) == QCTestResult.Verdict.FAIL
    assert spec.evaluate(Decimal("7.1")) == QCTestResult.Verdict.FAIL
    assert spec.evaluate(None) == QCTestResult.Verdict.NA


# --- Lot iş akışı -----------------------------------------------------------

def test_record_test_for_lot_sets_verdict(pending_sp_lot, raw_specs, qc_params):
    r = record_test(qc_params["DENSITY"], Decimal("1.08"), lot=pending_sp_lot, tester="QA1")
    assert r.verdict == QCTestResult.Verdict.PASS
    r2 = record_test(qc_params["DENSITY"], Decimal("1.20"), lot=pending_sp_lot, tester="QA1")
    assert r2.verdict == QCTestResult.Verdict.FAIL


def test_release_lot_requires_all_mandatory_tests(pending_sp_lot, raw_specs):
    ev = evaluate_lot(pending_sp_lot)
    assert not ev.all_mandatory_present
    with pytest.raises(ValidationError):
        release_lot(pending_sp_lot)


def test_release_lot_success(pending_sp_lot, raw_specs, qc_params):
    record_test(qc_params["DENSITY"], Decimal("1.08"), lot=pending_sp_lot)
    release_lot(pending_sp_lot)
    pending_sp_lot.refresh_from_db()
    assert pending_sp_lot.qc_status == RawMaterialLot.QCStatus.RELEASED


def test_release_lot_blocks_on_fail(pending_sp_lot, raw_specs, qc_params):
    record_test(qc_params["DENSITY"], Decimal("1.20"), lot=pending_sp_lot)
    with pytest.raises(ValidationError):
        release_lot(pending_sp_lot)
    quarantine_lot(pending_sp_lot)
    pending_sp_lot.refresh_from_db()
    assert pending_sp_lot.qc_status == RawMaterialLot.QCStatus.QUARANTINE


# --- Parti iş akışı ---------------------------------------------------------

def _prep_completed_batch(order, released_lots, ibc, qc_params):
    batch = create_batch_from_order(order, batch_number="BATCH-QC-001")
    batch.transition_to(ProductionBatch.Status.IN_PROGRESS)
    for code, w in [("W", Decimal("300")), ("G", Decimal("7.5")),
                    ("SP", Decimal("175")), ("HD", Decimal("17.5"))]:
        c = batch.consumptions.get(raw_material__code=code)
        record_dosing(c, actual_weight=w)
    batch.transition_to(ProductionBatch.Status.COMPLETED)
    return batch


def test_release_batch_requires_all_tests(order, released_lots, ibc, product_specs, qc_params):
    batch = _prep_completed_batch(order, released_lots, ibc, qc_params)
    with pytest.raises(ValidationError):
        release_batch(batch)


def test_release_batch_success_and_state(order, released_lots, ibc, product_specs, qc_params):
    batch = _prep_completed_batch(order, released_lots, ibc, qc_params)
    record_test(qc_params["PH"], Decimal("5.5"), batch=batch)
    record_test(qc_params["DENSITY"], Decimal("1.10"), batch=batch)
    record_test(qc_params["SOLIDS"], Decimal("38"), batch=batch)
    release_batch(batch)
    batch.refresh_from_db()
    assert batch.qc_status == ProductionBatch.QCStatus.RELEASED
    assert batch.status == ProductionBatch.Status.RELEASED


def test_reject_batch_transitions_state(order, released_lots, ibc, product_specs, qc_params):
    batch = _prep_completed_batch(order, released_lots, ibc, qc_params)
    record_test(qc_params["PH"], Decimal("8.0"), batch=batch)  # FAIL
    reject_batch(batch, reason="pH aralık dışı")
    batch.refresh_from_db()
    assert batch.qc_status == ProductionBatch.QCStatus.REJECTED
    assert batch.status == ProductionBatch.Status.REJECTED


# --- COA --------------------------------------------------------------------

def test_generate_coa_requires_released_batch(order, released_lots, ibc, product_specs, qc_params):
    batch = _prep_completed_batch(order, released_lots, ibc, qc_params)
    with pytest.raises(ValidationError):
        generate_coa(batch, issued_by="qa@example.com")


def test_generate_coa_success_and_payload(order, released_lots, ibc, product_specs, qc_params):
    batch = _prep_completed_batch(order, released_lots, ibc, qc_params)
    record_test(qc_params["PH"], Decimal("5.5"), batch=batch, tester="QA1")
    record_test(qc_params["DENSITY"], Decimal("1.10"), batch=batch, tester="QA1")
    record_test(qc_params["SOLIDS"], Decimal("38"), batch=batch, tester="QA1")
    release_batch(batch)

    coa = generate_coa(batch, issued_by="qa@example.com", summary="Uygun.")
    assert coa.status == CertificateOfAnalysis.Status.ISSUED
    assert coa.issued_at is not None

    payload = coa_payload(coa)
    assert payload["batch_number"] == "BATCH-QC-001"
    assert payload["product"] == "ADX-100"
    params_in_payload = {r["parameter"] for r in payload["results"]}
    assert {"PH", "DENSITY", "SOLIDS"} <= params_in_payload
    lots = {lot["raw_material"] for lot in payload["consumed_lots"]}
    assert {"W", "G", "SP", "HD"} == lots


def test_coa_number_default_when_missing(order, released_lots, ibc, product_specs, qc_params):
    batch = _prep_completed_batch(order, released_lots, ibc, qc_params)
    record_test(qc_params["PH"], Decimal("5.5"), batch=batch)
    record_test(qc_params["DENSITY"], Decimal("1.10"), batch=batch)
    record_test(qc_params["SOLIDS"], Decimal("38"), batch=batch)
    release_batch(batch)
    coa = generate_coa(batch)
    assert coa.coa_number == "COA-BATCH-QC-001"

"""Chemicals testleri: SDS onay + PDF, retention, raf ömrü tarama."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import call_command

from chemicals.models import (
    ChemicalProfile,
    HazardClass,
    HazardStatement,
    Pictogram,
    RetentionSample,
    SafetyDataSheet,
    ShelfLifeAlert,
)
from chemicals.services import (
    approve_sds,
    dispose_retention_sample,
    render_sds_pdf,
    scan_shelf_life,
    take_retention_sample,
)
from inventory.models import RawMaterialLot
from production.services import create_batch_from_order


pytestmark = pytest.mark.django_db


@pytest.fixture
def ghs_seeded(db):
    call_command("seed_ghs")
    return True


def test_seed_ghs_creates_reference_data(ghs_seeded):
    assert Pictogram.objects.count() >= 9
    assert HazardStatement.objects.filter(code="H315").exists()


def test_chemical_profile_requires_target(raws):
    with pytest.raises(Exception):
        # ne raw ne product → constraint hatası
        ChemicalProfile.objects.create()


def test_sds_approve_workflow_and_supersedes(raws):
    profile = ChemicalProfile.objects.create(
        raw_material=raws["SP"], hazard_class=HazardClass.CORROSIVE,
    )
    author = User.objects.create_user("author2", password="pw")
    approver = User.objects.create_user("approver2", password="pw")

    v1 = SafetyDataSheet.objects.create(
        sds_number="SDS-SP-001", profile=profile, version="1.0",
        language="tr", prepared_by=author,
    )
    # Hazırlayan onaylayamaz
    with pytest.raises(ValidationError):
        approve_sds(v1, approver=author)
    approve_sds(v1, approver=approver)
    v1.refresh_from_db()
    assert v1.status == SafetyDataSheet.Status.APPROVED

    # Yeni versiyon geldiğinde eskisi SUPERSEDED
    v2 = SafetyDataSheet.objects.create(
        sds_number="SDS-SP-002", profile=profile, version="2.0",
        language="tr", prepared_by=author,
    )
    approve_sds(v2, approver=approver)
    v1.refresh_from_db()
    assert v1.status == SafetyDataSheet.Status.SUPERSEDED
    assert v2.status == SafetyDataSheet.Status.APPROVED


def test_sds_pdf_bytes(raws, ghs_seeded):
    profile = ChemicalProfile.objects.create(
        raw_material=raws["SP"], hazard_class=HazardClass.CORROSIVE,
        cas_no="9003-04-7", un_number="1830", adr_class="8",
    )
    profile.hazard_statements.set(HazardStatement.objects.filter(code__in=["H315", "H319"]))
    author = User.objects.create_user("prep", password="pw")
    sds = SafetyDataSheet.objects.create(
        sds_number="SDS-SP-100", profile=profile, prepared_by=author,
        section_1_identification="ADX-100 hammadde tanımı",
        section_2_hazards="Cilt tahrişi, göz irritasyonu",
        section_7_handling="Havalandırılan alanda kullanın",
    )
    pdf = render_sds_pdf(sds)
    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 1000  # anlamlı bir belge boyutu


def test_retention_sample_take_and_dispose(order, released_lots):
    batch = create_batch_from_order(order, batch_number="BATCH-RS-1")
    admin_u = User.objects.create_user("admin_ret", password="pw", is_staff=True)
    sample = take_retention_sample(
        batch=batch, sample_number="RS-001",
        quantity=Decimal("0.5"), storage_location="Rack A-3",
        keep_days=30,
    )
    assert sample.status == RetentionSample.Status.STORED
    assert sample.keep_until == sample.sampled_at + dt.timedelta(days=30)

    # Süresi dolmadan imha edilemez
    with pytest.raises(ValidationError):
        dispose_retention_sample(sample, disposed_by=admin_u)

    # Süresi geçmiş kılıp imha et
    sample.keep_until = dt.date.today() - dt.timedelta(days=1)
    sample.save()
    dispose_retention_sample(sample, disposed_by=admin_u, note="Süresi doldu")
    sample.refresh_from_db()
    assert sample.status == RetentionSample.Status.DISPOSED
    assert sample.disposed_by == admin_u


def test_shelf_life_scan_severities(raws, supplier):
    today = dt.date.today()
    plans = [
        ("EXP-1", today - dt.timedelta(days=5), "EXPIRED"),
        ("CRIT-1", today + dt.timedelta(days=3), "CRITICAL"),
        ("WARN-1", today + dt.timedelta(days=20), "WARNING"),
        ("INFO-1", today + dt.timedelta(days=60), "INFO"),
        ("SAFE-1", today + dt.timedelta(days=200), None),
    ]
    for i, (lot_no, exp, expected) in enumerate(plans):
        RawMaterialLot.objects.create(
            lot_number=lot_no, raw_material=raws["SP"], supplier=supplier,
            received_date=today, expiry_date=exp,
            received_qty=Decimal("100"), remaining_qty=Decimal("100"),
            qc_status=RawMaterialLot.QCStatus.RELEASED,
        )

    alerts = scan_shelf_life(as_of=today)
    # SAFE-1 hariç 4 alert oluşmalı
    assert len(alerts) == 4
    by_lot = {a.lot.lot_number: a.severity for a in alerts}
    assert by_lot["EXP-1"] == ShelfLifeAlert.Severity.EXPIRED
    assert by_lot["CRIT-1"] == ShelfLifeAlert.Severity.CRITICAL
    assert by_lot["WARN-1"] == ShelfLifeAlert.Severity.WARNING
    assert by_lot["INFO-1"] == ShelfLifeAlert.Severity.INFO


def test_shelf_life_scan_idempotent_same_day(raws, supplier):
    RawMaterialLot.objects.create(
        lot_number="IDEM-1", raw_material=raws["SP"], supplier=supplier,
        received_date=dt.date.today(),
        expiry_date=dt.date.today() + dt.timedelta(days=5),
        received_qty=Decimal("50"), remaining_qty=Decimal("50"),
        qc_status=RawMaterialLot.QCStatus.RELEASED,
    )
    first = scan_shelf_life()
    second = scan_shelf_life()
    assert len(first) == 1
    assert len(second) == 0  # aynı gün mükerrer yok

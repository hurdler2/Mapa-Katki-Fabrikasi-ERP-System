"""Analytics testleri: fire trendi, QC istatistiği, NCR aging, ISO paket, dashboard erişim."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from analytics.services import (
    iso_audit_package,
    ncr_capa_aging,
    qc_pass_fail_stats,
    supplier_scorecard,
    waste_trend,
)
from production.services import create_batch_from_order, record_dosing
from qms.models import Nonconformance
from qms.services import open_ncr
from quality.models import QCParameter, QCTestResult


pytestmark = pytest.mark.django_db


@pytest.fixture
def staff_client(client):
    User.objects.create_user("bi_admin", password="pw", is_staff=True)
    client.login(username="bi_admin", password="pw")
    return client


def test_waste_trend_returns_last_n_months():
    trend = waste_trend(6)
    assert len(trend) == 6
    assert all("month" in r for r in trend)


def test_oee_by_equipment_handles_reactor_equipment(db):
    """Regression: Equipment (REACTOR) → Container FK üzerinden batches filtresi.

    Bug: `reactor=eq` (Equipment) verdiğinde Container FK bekleyen sorgu ValueError atardı.
    """
    from cmms.models import Equipment
    from masterdata.models import Container, UnitOfMeasure
    from analytics.services import oee_by_equipment

    unit = UnitOfMeasure.objects.create(code="L", name="Litre")
    c = Container.objects.create(
        code="R-X", name="Reactor X",
        container_type=Container.ContainerType.REACTOR,
        capacity=1000, unit=unit,
    )
    Equipment.objects.create(
        equipment_number="EQ-X", name="Reactor X",
        category=Equipment.Category.REACTOR, container=c,
    )
    # container'sız reaktör de olabilir — sorgu patlamamalı
    Equipment.objects.create(
        equipment_number="EQ-Y", name="Reactor Y",
        category=Equipment.Category.REACTOR,
    )
    out = oee_by_equipment()
    codes = [r["equipment"] for r in out]
    assert "EQ-X" in codes and "EQ-Y" in codes


def test_qc_stats_counts_pass_fail(order, released_lots):
    from quality.models import QCSpec
    param = QCParameter.objects.create(code="TP", name="Test param")
    from masterdata.models import Product
    prod = Product.objects.first()
    QCSpec.objects.create(parameter=param, product=prod,
                           min_value=Decimal("1"), max_value=Decimal("10"))
    batch = create_batch_from_order(order, batch_number="BATCH-STATS-1")
    QCTestResult.objects.create(parameter=param, batch=batch, value=Decimal("5"),
                                  verdict=QCTestResult.Verdict.PASS)
    QCTestResult.objects.create(parameter=param, batch=batch, value=Decimal("15"),
                                  verdict=QCTestResult.Verdict.FAIL)
    stats = qc_pass_fail_stats()
    assert stats["total"] >= 2
    assert stats["pass_count"] >= 1
    assert stats["fail_count"] >= 1


def test_aging_buckets_ncr():
    user = User.objects.create_user("qa_x", password="pw")
    # Bugün açılmış → 0-7
    ncr = open_ncr(
        ncr_number="NCR-AG-1", source=Nonconformance.Source.QC_TEST,
        detected_by=user, title="Test", description="X",
    )
    # Backdated ncr for >90 bucket
    old = open_ncr(
        ncr_number="NCR-AG-2", source=Nonconformance.Source.QC_TEST,
        detected_by=user, title="Old", description="Y",
    )
    old.detected_at = timezone.now() - dt.timedelta(days=120)
    old.save()

    aging = ncr_capa_aging()
    assert aging["ncr_open"] >= 2
    assert aging["ncr_by_age"]["0-7"] >= 1
    assert aging["ncr_by_age"][">90"] >= 1


def test_iso_audit_package_returns_expected_keys():
    pkg = iso_audit_package()
    for key in ("period", "documents", "qms", "calibration",
                "internal_audit", "management_review", "legal_compliance",
                "ehs", "quality", "risk"):
        assert key in pkg


def test_bi_dashboard_renders(staff_client):
    resp = staff_client.get(reverse("analytics:bi_dashboard"))
    assert resp.status_code == 200
    assert b"BI Dashboard" in resp.content or b"OEE" in resp.content


def test_iso_audit_view_renders(staff_client):
    resp = staff_client.get(reverse("analytics:iso_audit"))
    assert resp.status_code == 200


def test_iso_audit_pdf_returns_pdf(staff_client):
    resp = staff_client.get(reverse("analytics:iso_audit_pdf"))
    assert resp.status_code == 200
    assert resp["Content-Type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF-")


def test_iso_audit_json_returns_json(staff_client):
    resp = staff_client.get(reverse("analytics:iso_audit_json"))
    assert resp.status_code == 200
    assert "application/json" in resp["Content-Type"]


def test_iso_audit_zip_returns_zip(staff_client):
    resp = staff_client.get(reverse("analytics:iso_audit_zip"))
    assert resp.status_code == 200
    assert resp["Content-Type"] == "application/zip"
    # ZIP magic
    assert resp.content[:2] == b"PK"

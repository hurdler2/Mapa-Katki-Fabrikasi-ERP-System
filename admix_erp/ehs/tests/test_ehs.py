"""EHS testleri: olay + otomatik NCR, PPE stok, iş izni yaşam döngüsü."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.utils import timezone

from ehs.models import (
    Incident,
    JobSafetyAnalysis,
    JSAStep,
    PPEIssuance,
    PPEItem,
    WorkPermit,
)
from ehs.services import (
    close_incident,
    close_permit,
    expire_stale_permits,
    find_overdue_ppe,
    issue_permit,
    issue_ppe,
    report_incident,
    return_ppe,
    start_investigation,
)


pytestmark = pytest.mark.django_db


@pytest.fixture
def reporter(db):
    return User.objects.create_user("reporter", password="pw")


@pytest.fixture
def investigator(db):
    return User.objects.create_user("investigator", password="pw")


@pytest.fixture
def worker(db):
    return User.objects.create_user("worker", password="pw")


@pytest.fixture
def ehs_seeded(db):
    call_command("seed_ehs")
    return True


def test_seed_ehs_populates_ppe_and_legal(ehs_seeded):
    assert PPEItem.objects.filter(code="KKD-EYE-01").exists()
    from ehs.models import LegalRequirement
    assert LegalRequirement.objects.filter(code="DZ-OHS-01").exists()


def test_report_incident_serious_creates_ncr(reporter):
    inc = report_incident(
        incident_number="INC-001",
        type=Incident.Type.INJURY,
        occurred_at=timezone.now(),
        location="Reaktör 1",
        description="Elde asit teması",
        reported_by=reporter,
        severity=Incident.Severity.SERIOUS,
        body_parts="Sağ el",
    )
    assert inc.ncr is not None
    assert inc.ncr.source == "EHS"


def test_report_near_miss_no_ncr(reporter):
    inc = report_incident(
        incident_number="INC-NM-1",
        type=Incident.Type.NEAR_MISS,
        occurred_at=timezone.now(),
        location="Depo",
        description="Vinç yükü sallandı, düşmedi",
        reported_by=reporter,
    )
    assert inc.ncr is None
    assert inc.severity == Incident.Severity.MINOR


def test_close_incident_requires_root_cause(reporter, investigator):
    inc = report_incident(
        incident_number="INC-002",
        type=Incident.Type.INJURY,
        occurred_at=timezone.now(),
        location="X",
        description="Y",
        reported_by=reporter,
    )
    start_investigation(inc, investigator=investigator)
    with pytest.raises(ValidationError):
        close_incident(inc)
    inc.root_cause_analysis = "İnsan hatası + KKD kullanılmadı"
    inc.save()
    close_incident(inc, closure_note="Aksiyonlar tamamlandı")
    inc.refresh_from_db()
    assert inc.status == Incident.Status.CLOSED
    assert inc.closed_at is not None


def test_close_near_miss_without_root_cause_ok(reporter):
    inc = report_incident(
        incident_number="INC-NM-2", type=Incident.Type.NEAR_MISS,
        occurred_at=timezone.now(), location="Depo",
        description="Kimyasal dökülmedi", reported_by=reporter,
    )
    close_incident(inc)
    inc.refresh_from_db()
    assert inc.status == Incident.Status.CLOSED


def test_issue_ppe_reduces_stock(worker):
    item = PPEItem.objects.create(
        code="TEST-GLOVE", name="Test eldiven",
        category=PPEItem.Category.HAND, stock_quantity=10, replacement_days=30,
    )
    issue_ppe(user=worker, item=item, quantity=2)
    item.refresh_from_db()
    assert item.stock_quantity == 8


def test_issue_ppe_insufficient_stock(worker):
    item = PPEItem.objects.create(
        code="TEST-MASK", name="Maske", category=PPEItem.Category.RESPIRATORY,
        stock_quantity=1,
    )
    with pytest.raises(ValidationError):
        issue_ppe(user=worker, item=item, quantity=5)


def test_return_ppe_restores_stock(worker):
    item = PPEItem.objects.create(
        code="R-1", name="Ayakkabı", category=PPEItem.Category.FOOT,
        stock_quantity=5,
    )
    iss = issue_ppe(user=worker, item=item, quantity=1)
    return_ppe(iss)
    item.refresh_from_db()
    assert item.stock_quantity == 5


def test_find_overdue_ppe(worker):
    item = PPEItem.objects.create(
        code="OVR-1", name="Test",
        category=PPEItem.Category.HAND, stock_quantity=10, replacement_days=1,
    )
    iss = issue_ppe(user=worker, item=item, issued_at=dt.date.today() - dt.timedelta(days=10))
    overdue = find_overdue_ppe()
    assert iss in overdue


def test_issue_permit_requires_gas_test_for_confined_space(reporter, investigator, worker):
    permit = WorkPermit.objects.create(
        permit_number="WP-001", type=WorkPermit.Type.CONFINED_SPACE,
        work_description="Reaktör içi temizlik",
        location="REACTOR-1",
        valid_from=timezone.now(),
        valid_until=timezone.now() + dt.timedelta(hours=8),
        requested_by=reporter, permit_holder=worker,
    )
    with pytest.raises(ValidationError):
        issue_permit(permit, issuer=investigator)

    permit.gas_test_result = "O2=20.9%, LEL=0%, H2S=0ppm"
    permit.save()
    issue_permit(permit, issuer=investigator)
    permit.refresh_from_db()
    assert permit.status == WorkPermit.Status.ISSUED


def test_permit_segregation_of_duties(reporter, worker):
    permit = WorkPermit.objects.create(
        permit_number="WP-002", type=WorkPermit.Type.WORK_AT_HEIGHT,
        work_description="Çatı bakım", location="Çatı",
        valid_from=timezone.now(),
        valid_until=timezone.now() + dt.timedelta(hours=8),
        requested_by=reporter, permit_holder=worker,
    )
    with pytest.raises(ValidationError):
        issue_permit(permit, issuer=reporter)


def test_expire_stale_permits(reporter, investigator, worker):
    old = WorkPermit.objects.create(
        permit_number="WP-OLD", type=WorkPermit.Type.HOT_WORK,
        work_description="Kaynak", location="Atölye",
        valid_from=timezone.now() - dt.timedelta(hours=10),
        valid_until=timezone.now() - dt.timedelta(hours=1),
        requested_by=reporter, permit_holder=worker,
        gas_test_result="LEL=0", status=WorkPermit.Status.ISSUED,
        issued_by=investigator, issued_at=timezone.now() - dt.timedelta(hours=9),
    )
    count = expire_stale_permits()
    assert count == 1
    old.refresh_from_db()
    assert old.status == WorkPermit.Status.EXPIRED


def test_close_permit_flow(reporter, investigator, worker):
    permit = WorkPermit.objects.create(
        permit_number="WP-003", type=WorkPermit.Type.WORK_AT_HEIGHT,
        work_description="Çatı bakım", location="Çatı",
        valid_from=timezone.now(),
        valid_until=timezone.now() + dt.timedelta(hours=8),
        requested_by=reporter, permit_holder=worker,
    )
    issue_permit(permit, issuer=investigator)
    close_permit(permit, closed_by=investigator, note="İş tamamlandı, alan temiz")
    permit.refresh_from_db()
    assert permit.status == WorkPermit.Status.CLOSED
    assert permit.closed_at is not None


def test_jsa_with_steps(worker):
    jsa = JobSafetyAnalysis.objects.create(
        jsa_number="JSA-001", task_name="SP hammadde IBC değişimi",
        prepared_by=worker,
    )
    JSAStep.objects.create(
        jsa=jsa, sequence=1, step_description="Boş IBC'yi vinçle çıkar",
        hazards="Ezilme, düşme", controls="Vinç sertifikalı, sinyal",
        residual_risk=JSAStep.RiskLevel.MEDIUM,
    )
    JSAStep.objects.create(
        jsa=jsa, sequence=2, step_description="Yeni IBC'yi konumlandır",
        hazards="Kimyasal sıçrama", controls="KKD + drip tray",
        residual_risk=JSAStep.RiskLevel.LOW,
    )
    assert jsa.steps.count() == 2

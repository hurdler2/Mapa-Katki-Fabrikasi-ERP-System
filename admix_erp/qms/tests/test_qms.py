"""QMS testleri: NCR açma/kapatma, CAPA yaşam döngüsü, şikayet eskalasyonu."""
from __future__ import annotations

import datetime as dt

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from masterdata.models import Customer
from qms.models import CAPA, CAPAAction, CustomerComplaint, Nonconformance
from qms.services import (
    close_capa,
    close_ncr,
    disposition_ncr,
    escalate_complaint_to_ncr,
    log_complaint,
    open_capa,
    open_ncr,
    resolve_complaint,
    start_capa,
    verify_capa,
)


pytestmark = pytest.mark.django_db


@pytest.fixture
def qa_user(db):
    return User.objects.create_user("qa1", password="pw")


@pytest.fixture
def owner_user(db):
    return User.objects.create_user("owner1", password="pw")


@pytest.fixture
def customer(db):
    return Customer.objects.create(code="CUS-Q", name="Test Müşteri")


def test_open_ncr(qa_user, product):
    ncr = open_ncr(
        ncr_number="NCR-001",
        source=Nonconformance.Source.QC_TEST,
        detected_by=qa_user,
        title="Yoğunluk aralık dışı",
        description="Test 3 lotu spec dışı geldi.",
        severity="HIGH",
        target=product,
    )
    assert ncr.status == Nonconformance.Status.OPEN
    assert ncr.target == product


def test_cannot_close_ncr_without_disposition(qa_user):
    ncr = open_ncr(
        ncr_number="NCR-002", source=Nonconformance.Source.PRODUCTION,
        detected_by=qa_user, title="X", description="Y",
    )
    with pytest.raises(ValidationError):
        close_ncr(ncr, user=qa_user)


def test_close_ncr_after_disposition(qa_user):
    ncr = open_ncr(
        ncr_number="NCR-003", source=Nonconformance.Source.PRODUCTION,
        detected_by=qa_user, title="X", description="Y",
    )
    disposition_ncr(ncr, disposition=Nonconformance.Disposition.REWORK,
                    reason="Reworked", user=qa_user)
    close_ncr(ncr, user=qa_user)
    assert ncr.status == Nonconformance.Status.CLOSED
    assert ncr.closed_at is not None


def test_capa_lifecycle(owner_user, qa_user):
    capa = open_capa(
        capa_number="CAPA-001", type=CAPA.Type.CORRECTIVE,
        title="Kalibrasyon eksik", description="Terazi kalibre değildi",
        owner=owner_user, action_plan="Aylık kalibrasyon planı",
        target_date=dt.date.today(),
    )
    assert capa.status == CAPA.Status.PLANNED

    start_capa(capa)
    capa.refresh_from_db()
    assert capa.status == CAPA.Status.IN_PROGRESS

    # Açık aksiyon varken doğrulama başarısız
    action = CAPAAction.objects.create(
        capa=capa, sequence=1, description="Kalibrasyon yap",
        assignee=owner_user, status=CAPAAction.Status.OPEN,
    )
    with pytest.raises(ValidationError):
        verify_capa(capa, verified_by=qa_user, notes="")

    # Aksiyonu kapat, doğrula
    action.status = CAPAAction.Status.COMPLETED
    action.save()
    verify_capa(capa, verified_by=qa_user, notes="Etkin buldum.")
    capa.refresh_from_db()
    assert capa.status == CAPA.Status.VERIFICATION

    close_capa(capa)
    capa.refresh_from_db()
    assert capa.status == CAPA.Status.CLOSED
    assert capa.closed_at is not None


def test_complaint_escalation_to_ncr(customer, qa_user):
    c = log_complaint(
        complaint_number="COMP-001", customer=customer,
        description="Malzeme çok akışkan", severity="HIGH",
    )
    escalate_complaint_to_ncr(c, ncr_number="NCR-COMP-1", detected_by=qa_user)
    c.refresh_from_db()
    assert c.ncr is not None
    assert c.status == CustomerComplaint.Status.UNDER_REVIEW
    assert c.ncr.source == Nonconformance.Source.CUSTOMER_COMPLAINT


def test_complaint_resolve(customer, qa_user):
    c = log_complaint(
        complaint_number="COMP-002", customer=customer,
        description="Ambalaj hasarlı", severity="LOW",
    )
    resolve_complaint(c, resolution="İade edildi", customer_satisfied=True)
    c.refresh_from_db()
    assert c.status == CustomerComplaint.Status.RESOLVED
    assert c.customer_satisfied is True


def test_batch_history_recorded_via_simple_history(order, released_lots):
    """django-simple-history entegrasyonu: parti değişiklikleri iz bırakır."""
    from production.services import create_batch_from_order
    from production.models import ProductionBatch

    batch = create_batch_from_order(order, batch_number="BATCH-HIST-1")
    initial = batch.history.count()
    batch.transition_to(ProductionBatch.Status.IN_PROGRESS)
    batch.transition_to(ProductionBatch.Status.COMPLETED)
    assert batch.history.count() >= initial + 2
    # En eski önce, en yeni sonra? default ordering: -history_date
    statuses = list(batch.history.all().order_by("history_date").values_list("status", flat=True))
    assert "PLANNED" in statuses
    assert "IN_PROGRESS" in statuses
    assert "COMPLETED" in statuses

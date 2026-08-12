"""HR testleri: vardiya, eğitim → yetkinlik, izin akışı."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from hr.models import (
    LeaveRequest,
    Shift,
    ShiftAssignment,
    TrainingCourse,
    TrainingRecord,
    TrainingSession,
)
from hr.services import (
    approve_leave,
    complete_training,
    find_expiring_competencies,
    reject_leave,
)
from iam.models import Competency, UserCompetency


pytestmark = pytest.mark.django_db


def test_shift_assignment_unique():
    u = User.objects.create_user("op1", password="pw")
    sh = Shift.objects.create(code="A", name="Sabah",
                                start_time=dt.time(8), end_time=dt.time(16))
    ShiftAssignment.objects.create(user=u, shift=sh, date=dt.date(2026, 8, 10))
    with pytest.raises(Exception):
        ShiftAssignment.objects.create(user=u, shift=sh, date=dt.date(2026, 8, 10))


def test_complete_training_grants_competency():
    u = User.objects.create_user("trainee", password="pw")
    comp = Competency.objects.create(code="ISG-BASIC", name="Temel İSG",
                                      valid_days=365)
    course = TrainingCourse.objects.create(
        code="CRS-ISG", name="Temel İSG Eğitimi",
        category=TrainingCourse.Category.HSE,
        validity_days=365, grants_competency=comp,
    )
    session = TrainingSession.objects.create(
        course=course, session_number="SES-1",
        date=dt.date(2026, 6, 1),
    )
    rec = TrainingRecord.objects.create(
        session=session, user=u, result=TrainingRecord.Result.ATTENDED,
    )
    complete_training(rec, certificate_number="CERT-001")
    rec.refresh_from_db()
    assert rec.result == TrainingRecord.Result.PASSED
    assert rec.valid_until == dt.date(2027, 6, 1)

    uc = UserCompetency.objects.get(user=u, competency=comp)
    assert uc.obtained_on == dt.date(2026, 6, 1)
    assert uc.expires_on == dt.date(2027, 6, 1)
    assert uc.evidence == "CERT-001"


def test_leave_flow():
    emp = User.objects.create_user("emp1", password="pw")
    mgr = User.objects.create_user("mgr1", password="pw")
    req = LeaveRequest.objects.create(
        request_number="LV-1", user=emp, type=LeaveRequest.Type.ANNUAL,
        start_date=dt.date(2026, 8, 10), end_date=dt.date(2026, 8, 12),
    )
    assert req.days == 3

    with pytest.raises(ValidationError):
        approve_leave(req, approver=emp)  # kişi kendi onayı

    approve_leave(req, approver=mgr)
    req.refresh_from_db()
    assert req.status == LeaveRequest.Status.APPROVED

    r2 = LeaveRequest.objects.create(
        request_number="LV-2", user=emp, type=LeaveRequest.Type.SICK,
        start_date=dt.date(2026, 9, 1), end_date=dt.date(2026, 9, 2),
    )
    reject_leave(r2, approver=mgr, reason="Belge eksik")
    r2.refresh_from_db()
    assert r2.status == LeaveRequest.Status.REJECTED
    assert r2.rejection_reason == "Belge eksik"


def test_find_expiring_competencies():
    u = User.objects.create_user("u_comp", password="pw")
    comp = Competency.objects.create(code="C-1", name="Test")
    UserCompetency.objects.create(
        user=u, competency=comp,
        obtained_on=dt.date.today() - dt.timedelta(days=350),
        expires_on=dt.date.today() + dt.timedelta(days=15),
    )
    UserCompetency.objects.create(
        user=u, competency=Competency.objects.create(code="C-2", name="Uzun"),
        obtained_on=dt.date.today(),
        expires_on=dt.date.today() + dt.timedelta(days=200),
    )
    expiring = find_expiring_competencies(within_days=30)
    assert len(expiring) == 1
    assert expiring[0].competency.code == "C-1"

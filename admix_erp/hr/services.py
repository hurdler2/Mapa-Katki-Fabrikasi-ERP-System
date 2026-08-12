"""HR servisleri: eğitim tamamlama → yetkinlik atama, izin onay."""
from __future__ import annotations

import datetime as dt

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from iam.models import UserCompetency

from .models import LeaveRequest, TrainingRecord, TrainingSession


@transaction.atomic
def complete_training(
    record: TrainingRecord, *, valid_until: dt.date | None = None,
    certificate_number: str = "",
) -> TrainingRecord:
    """Eğitim kaydını PASSED olarak işaretle; kurs bir yetkinlik kazandırıyorsa
    kullanıcıya `UserCompetency` ata (varsa güncelle)."""
    if record.result != TrainingRecord.Result.PASSED:
        record.result = TrainingRecord.Result.PASSED
    if certificate_number:
        record.certificate_number = certificate_number
    if valid_until:
        record.valid_until = valid_until
    elif record.session.course.validity_days:
        record.valid_until = record.session.date + dt.timedelta(
            days=record.session.course.validity_days)
    record.save(update_fields=[
        "result", "certificate_number", "valid_until", "updated_at",
    ])

    course = record.session.course
    if course.grants_competency:
        UserCompetency.objects.update_or_create(
            user=record.user, competency=course.grants_competency,
            defaults={
                "obtained_on": record.session.date,
                "expires_on": record.valid_until,
                "evidence": record.certificate_number,
            },
        )
    return record


@transaction.atomic
def approve_leave(req: LeaveRequest, *, approver) -> LeaveRequest:
    if req.status != LeaveRequest.Status.REQUESTED:
        raise ValidationError("Yalnız REQUESTED talep onaylanabilir.")
    if approver.pk == req.user_id:
        raise ValidationError("Kişi kendi izin talebini onaylayamaz.")
    req.status = LeaveRequest.Status.APPROVED
    req.approved_by = approver
    req.approved_at = timezone.now()
    req.save(update_fields=[
        "status", "approved_by", "approved_at", "updated_at",
    ])
    return req


@transaction.atomic
def reject_leave(req: LeaveRequest, *, approver, reason: str) -> LeaveRequest:
    if req.status != LeaveRequest.Status.REQUESTED:
        raise ValidationError("Yalnız REQUESTED talep reddedilebilir.")
    req.status = LeaveRequest.Status.REJECTED
    req.approved_by = approver
    req.rejection_reason = reason
    req.save(update_fields=[
        "status", "approved_by", "rejection_reason", "updated_at",
    ])
    return req


def find_expiring_competencies(
    *, within_days: int = 30, as_of: dt.date | None = None
) -> list[UserCompetency]:
    """Süresi `within_days` içinde dolacak yetkinlikler."""
    as_of = as_of or dt.date.today()
    cutoff = as_of + dt.timedelta(days=within_days)
    return list(UserCompetency.objects.filter(
        expires_on__isnull=False,
        expires_on__gte=as_of,
        expires_on__lte=cutoff,
    ).select_related("user", "competency"))

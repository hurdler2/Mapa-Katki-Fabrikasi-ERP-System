"""Doküman kontrol servisleri: onay zinciri, yürürlüğe alma, geri çekme."""
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import ControlledDocument, DocumentAcknowledgement, DocumentRevision


@transaction.atomic
def submit_for_review(rev: DocumentRevision) -> DocumentRevision:
    if rev.status != DocumentRevision.Status.DRAFT:
        raise ValidationError("Yalnız DRAFT revizyonlar incelemeye gönderilebilir.")
    rev.status = DocumentRevision.Status.REVIEW
    rev.save(update_fields=["status", "updated_at"])
    return rev


@transaction.atomic
def review_revision(rev: DocumentRevision, *, reviewer, note: str = "") -> DocumentRevision:
    if rev.status != DocumentRevision.Status.REVIEW:
        raise ValidationError("Yalnız REVIEW aşamasındaki revizyon incelenebilir.")
    if reviewer.pk == rev.prepared_by_id:
        raise ValidationError("Hazırlayan revizyonu inceleyemez (görev ayrımı).")
    rev.reviewed_by = reviewer
    rev.reviewed_at = timezone.now()
    rev.save(update_fields=["reviewed_by", "reviewed_at", "updated_at"])
    return rev


@transaction.atomic
def approve_revision(rev: DocumentRevision, *, approver) -> DocumentRevision:
    if rev.reviewed_at is None:
        raise ValidationError("Onaydan önce inceleme tamamlanmalıdır.")
    if approver.pk in {rev.prepared_by_id, rev.reviewed_by_id}:
        raise ValidationError("Hazırlayan/inceleyen aynı zamanda onaylayan olamaz.")
    rev.approved_by = approver
    rev.approved_at = timezone.now()
    rev.status = DocumentRevision.Status.APPROVED
    rev.save(update_fields=["approved_by", "approved_at", "status", "updated_at"])
    return rev


@transaction.atomic
def make_effective(rev: DocumentRevision, *, effective_date=None) -> DocumentRevision:
    """Yeni revizyonu yürürlüğe al; önceki EFFECTIVE'i SUPERSEDED'a çek."""
    if rev.status != DocumentRevision.Status.APPROVED:
        raise ValidationError("Yürürlüğe alma için önce onay gerekir.")

    prev = rev.document.revisions.filter(
        status=DocumentRevision.Status.EFFECTIVE
    ).exclude(pk=rev.pk)
    prev.update(status=DocumentRevision.Status.SUPERSEDED)

    rev.effective_date = effective_date or timezone.now().date()
    rev.status = DocumentRevision.Status.EFFECTIVE
    rev.save(update_fields=["effective_date", "status", "updated_at"])
    return rev


@transaction.atomic
def withdraw(rev: DocumentRevision, *, reason: str = "") -> DocumentRevision:
    rev.status = DocumentRevision.Status.WITHDRAWN
    rev.save(update_fields=["status", "updated_at"])
    return rev


@transaction.atomic
def acknowledge(rev: DocumentRevision, *, user, note: str = "") -> DocumentAcknowledgement:
    """Personel dokümanı okuduğunu ve anladığını onaylar."""
    if rev.status != DocumentRevision.Status.EFFECTIVE:
        raise ValidationError("Yalnız yürürlükteki revizyon onaylanabilir.")
    ack, _ = DocumentAcknowledgement.objects.get_or_create(
        revision=rev, user=user, defaults={"note": note},
    )
    return ack

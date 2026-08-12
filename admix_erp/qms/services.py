"""QMS servisleri: NCR/CAPA/Deviation/Complaint iş akışları."""
from __future__ import annotations

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import CAPA, CAPAAction, CustomerComplaint, Deviation, Nonconformance


# ---------------------------------------------------------------------------
# NCR
# ---------------------------------------------------------------------------

@transaction.atomic
def open_ncr(
    *,
    ncr_number: str,
    source: str,
    detected_by,
    title: str,
    description: str,
    severity: str = "MEDIUM",
    target=None,
    detected_at=None,
    quantity_affected=None,
) -> Nonconformance:
    """Yeni bir uygunsuzluk aç. target: herhangi bir model instance'ı olabilir."""
    ct = ContentType.objects.get_for_model(target) if target else None
    return Nonconformance.objects.create(
        ncr_number=ncr_number,
        source=source,
        severity=severity,
        detected_at=detected_at or timezone.now(),
        detected_by=detected_by,
        title=title,
        description=description,
        content_type=ct,
        object_id=target.pk if target else None,
        quantity_affected=quantity_affected,
    )


@transaction.atomic
def disposition_ncr(
    ncr: Nonconformance,
    *,
    disposition: str,
    reason: str,
    user,
) -> Nonconformance:
    ncr.disposition = disposition
    ncr.disposition_reason = reason
    ncr.status = Nonconformance.Status.DISPOSITIONED
    ncr.save(update_fields=["disposition", "disposition_reason", "status", "updated_at"])
    return ncr


@transaction.atomic
def close_ncr(ncr: Nonconformance, *, user, note: str = "") -> Nonconformance:
    if ncr.disposition == Nonconformance.Disposition.PENDING:
        raise ValidationError("Karar (disposition) verilmeden NCR kapatılamaz.")
    ncr.status = Nonconformance.Status.CLOSED
    ncr.closed_at = timezone.now()
    ncr.closed_by = user
    if note:
        ncr.disposition_reason = (ncr.disposition_reason + "\n" + note).strip()
    ncr.save(update_fields=[
        "status", "closed_at", "closed_by", "disposition_reason", "updated_at",
    ])
    return ncr


# ---------------------------------------------------------------------------
# CAPA
# ---------------------------------------------------------------------------

@transaction.atomic
def open_capa(
    *,
    capa_number: str,
    type: str,
    title: str,
    description: str,
    owner,
    action_plan: str,
    severity: str = "MEDIUM",
    ncrs: list[Nonconformance] | None = None,
    deviations: list[Deviation] | None = None,
    target_date=None,
    root_cause_method: str = "5WHY",
    root_cause_analysis: str = "",
) -> CAPA:
    capa = CAPA.objects.create(
        capa_number=capa_number,
        type=type,
        title=title,
        description=description,
        severity=severity,
        owner=owner,
        action_plan=action_plan,
        target_date=target_date,
        root_cause_method=root_cause_method,
        root_cause_analysis=root_cause_analysis,
        status=CAPA.Status.PLANNED,
    )
    if ncrs:
        capa.ncrs.set(ncrs)
    if deviations:
        capa.deviations.set(deviations)
    return capa


@transaction.atomic
def start_capa(capa: CAPA) -> CAPA:
    if capa.status not in {CAPA.Status.DRAFT, CAPA.Status.PLANNED}:
        raise ValidationError(f"CAPA başlatılamaz: mevcut durum {capa.status}")
    capa.status = CAPA.Status.IN_PROGRESS
    capa.save(update_fields=["status", "updated_at"])
    return capa


@transaction.atomic
def verify_capa(capa: CAPA, *, verified_by, notes: str) -> CAPA:
    if capa.status != CAPA.Status.IN_PROGRESS:
        raise ValidationError("Yalnız IN_PROGRESS CAPA doğrulanabilir.")
    open_actions = capa.actions.exclude(status=CAPAAction.Status.COMPLETED).exists()
    if open_actions:
        raise ValidationError("Kapatılmamış aksiyonlar var; önce onları tamamlayın.")
    capa.status = CAPA.Status.VERIFICATION
    capa.verified_by = verified_by
    capa.verified_at = timezone.now()
    capa.verification_notes = notes
    capa.save(update_fields=[
        "status", "verified_by", "verified_at", "verification_notes", "updated_at",
    ])
    return capa


@transaction.atomic
def close_capa(capa: CAPA) -> CAPA:
    if capa.status != CAPA.Status.VERIFICATION:
        raise ValidationError("Yalnız VERIFICATION aşamasındaki CAPA kapatılabilir.")
    capa.status = CAPA.Status.CLOSED
    capa.closed_at = timezone.now()
    capa.save(update_fields=["status", "closed_at", "updated_at"])
    return capa


# ---------------------------------------------------------------------------
# Deviation
# ---------------------------------------------------------------------------

@transaction.atomic
def open_deviation(
    *,
    deviation_number: str,
    detected_by,
    title: str,
    description: str,
    severity: str = "LOW",
    target=None,
    impact_assessment: str = "",
) -> Deviation:
    ct = ContentType.objects.get_for_model(target) if target else None
    return Deviation.objects.create(
        deviation_number=deviation_number,
        detected_at=timezone.now(),
        detected_by=detected_by,
        title=title,
        description=description,
        severity=severity,
        content_type=ct,
        object_id=target.pk if target else None,
        impact_assessment=impact_assessment,
    )


# ---------------------------------------------------------------------------
# Customer Complaint
# ---------------------------------------------------------------------------

@transaction.atomic
def log_complaint(
    *,
    complaint_number: str,
    customer,
    description: str,
    severity: str = "MEDIUM",
    received_via: str = "",
    reference_batch: str = "",
    reference_shipment: str = "",
    received_at=None,
) -> CustomerComplaint:
    return CustomerComplaint.objects.create(
        complaint_number=complaint_number,
        customer=customer,
        received_at=received_at or timezone.now(),
        received_via=received_via,
        reference_batch=reference_batch,
        reference_shipment=reference_shipment,
        severity=severity,
        description=description,
    )


@transaction.atomic
def escalate_complaint_to_ncr(
    complaint: CustomerComplaint,
    *,
    ncr_number: str,
    detected_by,
    severity: str | None = None,
) -> CustomerComplaint:
    """Şikayeti bir NCR'a bağla (kalite sürecine sok)."""
    ncr = open_ncr(
        ncr_number=ncr_number,
        source=Nonconformance.Source.CUSTOMER_COMPLAINT,
        detected_by=detected_by,
        title=f"Müşteri şikayeti: {complaint.complaint_number}",
        description=complaint.description,
        severity=severity or complaint.severity,
        target=complaint,
    )
    complaint.ncr = ncr
    complaint.status = CustomerComplaint.Status.UNDER_REVIEW
    complaint.save(update_fields=["ncr", "status", "updated_at"])
    return complaint


@transaction.atomic
def resolve_complaint(
    complaint: CustomerComplaint,
    *,
    resolution: str,
    customer_satisfied: bool | None = None,
) -> CustomerComplaint:
    complaint.resolution = resolution
    complaint.resolved_at = timezone.now()
    complaint.customer_satisfied = customer_satisfied
    complaint.status = CustomerComplaint.Status.RESOLVED
    complaint.save(update_fields=[
        "resolution", "resolved_at", "customer_satisfied", "status", "updated_at",
    ])
    return complaint

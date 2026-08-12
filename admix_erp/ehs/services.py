"""EHS servisleri: olay iş akışı, PPE, iş izni yaşam döngüsü."""
from __future__ import annotations

import datetime as dt

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from qms.services import open_ncr

from .models import (
    ExposureMeasurement,
    Incident,
    JSAStep,
    JobSafetyAnalysis,
    PPEIssuance,
    PPEItem,
    WorkPermit,
)


# ---------------------------------------------------------------------------
# İSG olay
# ---------------------------------------------------------------------------

@transaction.atomic
def report_incident(
    *,
    incident_number: str,
    type: str,
    occurred_at,
    location: str,
    description: str,
    reported_by,
    severity: str = "MINOR",
    affected_persons=None,
    body_parts: str = "",
    environmental_medium: str = "",
    spilled_material: str = "",
    spilled_quantity_kg=None,
) -> Incident:
    incident = Incident.objects.create(
        incident_number=incident_number,
        type=type,
        severity=severity,
        occurred_at=occurred_at,
        location=location,
        reported_by=reported_by,
        description=description,
        body_parts=body_parts,
        environmental_medium=environmental_medium,
        spilled_material=spilled_material,
        spilled_quantity_kg=spilled_quantity_kg,
    )
    if affected_persons:
        incident.affected_persons.set(affected_persons)

    # Ciddi olaylar otomatik olarak NCR açar (kalite/uyum takibi için)
    if severity in {Incident.Severity.SERIOUS, Incident.Severity.FATAL,
                    Incident.Severity.LOST_TIME, Incident.Severity.MAJOR,
                    Incident.Severity.SIGNIFICANT}:
        from qms.models import Nonconformance
        ncr = open_ncr(
            ncr_number=f"NCR-INC-{incident_number}",
            source=Nonconformance.Source.EHS,
            detected_by=reported_by,
            title=f"Olay {incident_number} · {incident.get_type_display()}",
            description=description,
            severity="HIGH" if severity in {Incident.Severity.SERIOUS,
                                            Incident.Severity.FATAL} else "MEDIUM",
            target=incident,
        )
        incident.ncr = ncr
        incident.save(update_fields=["ncr", "updated_at"])

    return incident


@transaction.atomic
def start_investigation(
    incident: Incident, *, investigator, root_cause: str = ""
) -> Incident:
    if incident.status not in {Incident.Status.REPORTED, Incident.Status.INVESTIGATING}:
        raise ValidationError("Yalnız REPORTED / INVESTIGATING olay incelenebilir.")
    incident.investigator = investigator
    incident.status = Incident.Status.INVESTIGATING
    if root_cause:
        incident.root_cause_analysis = root_cause
    incident.save(update_fields=[
        "investigator", "status", "root_cause_analysis", "updated_at",
    ])
    return incident


@transaction.atomic
def close_incident(incident: Incident, *, closure_note: str = "") -> Incident:
    if incident.type != Incident.Type.NEAR_MISS and not incident.root_cause_analysis:
        raise ValidationError("Kök neden analizi olmadan olay kapatılamaz.")
    incident.status = Incident.Status.CLOSED
    incident.closed_at = timezone.now()
    if closure_note:
        incident.immediate_actions = (
            (incident.immediate_actions or "") + "\n" + closure_note
        ).strip()
    incident.save(update_fields=[
        "status", "closed_at", "immediate_actions", "updated_at",
    ])
    return incident


# ---------------------------------------------------------------------------
# PPE
# ---------------------------------------------------------------------------

@transaction.atomic
def issue_ppe(
    *,
    user,
    item: PPEItem,
    quantity: int = 1,
    issued_at: dt.date | None = None,
    notes: str = "",
) -> PPEIssuance:
    if item.stock_quantity < quantity:
        raise ValidationError(
            f"KKD stoğu yetersiz: {item.code} istenen={quantity} stok={item.stock_quantity}"
        )
    issued_at = issued_at or dt.date.today()
    replace_by = (
        issued_at + dt.timedelta(days=item.replacement_days)
        if item.replacement_days else None
    )
    issuance = PPEIssuance.objects.create(
        user=user, item=item, quantity=quantity,
        issued_at=issued_at, replace_by=replace_by, notes=notes,
    )
    item.stock_quantity -= quantity
    item.save(update_fields=["stock_quantity", "updated_at"])
    return issuance


@transaction.atomic
def return_ppe(issuance: PPEIssuance, *, status: str = "RETURNED") -> PPEIssuance:
    if issuance.status != PPEIssuance.Status.ISSUED:
        raise ValidationError("Yalnız ISSUED kayıt iade edilebilir.")
    issuance.status = status
    issuance.returned_at = dt.date.today()
    issuance.save(update_fields=["status", "returned_at", "updated_at"])
    if status == PPEIssuance.Status.RETURNED:
        issuance.item.stock_quantity += issuance.quantity
        issuance.item.save(update_fields=["stock_quantity", "updated_at"])
    return issuance


def find_overdue_ppe(*, as_of: dt.date | None = None) -> list[PPEIssuance]:
    """Değişim tarihi geçmiş ama iade edilmemiş KKD teslimlerini döner."""
    as_of = as_of or dt.date.today()
    return list(PPEIssuance.objects.filter(
        status=PPEIssuance.Status.ISSUED,
        replace_by__isnull=False,
        replace_by__lt=as_of,
    ).select_related("user", "item"))


# ---------------------------------------------------------------------------
# İş izni
# ---------------------------------------------------------------------------

@transaction.atomic
def issue_permit(
    permit: WorkPermit, *, issuer, safety_officer=None
) -> WorkPermit:
    if permit.status not in {WorkPermit.Status.DRAFT, WorkPermit.Status.REQUESTED}:
        raise ValidationError("Yalnız DRAFT/REQUESTED izin verilebilir.")
    if permit.valid_from >= permit.valid_until:
        raise ValidationError("Geçerlilik başlangıcı bitişten önce olmalı.")
    if issuer.pk == permit.requested_by_id:
        raise ValidationError("Talep eden aynı zamanda veren olamaz (görev ayrımı).")
    if permit.type in {WorkPermit.Type.CONFINED_SPACE, WorkPermit.Type.HOT_WORK}:
        if not permit.gas_test_result:
            raise ValidationError(
                "Kapalı alan / sıcak çalışma izni için gaz ölçüm sonucu zorunlu."
            )
    permit.issued_by = issuer
    permit.issued_at = timezone.now()
    permit.safety_officer = safety_officer
    permit.status = WorkPermit.Status.ISSUED
    permit.save(update_fields=[
        "issued_by", "issued_at", "safety_officer", "status", "updated_at",
    ])
    return permit


@transaction.atomic
def close_permit(
    permit: WorkPermit, *, closed_by, note: str = ""
) -> WorkPermit:
    if permit.status not in {WorkPermit.Status.ISSUED, WorkPermit.Status.SUSPENDED,
                              WorkPermit.Status.EXPIRED}:
        raise ValidationError("Yalnız aktif/askı/expired izin kapatılabilir.")
    permit.status = WorkPermit.Status.CLOSED
    permit.closed_at = timezone.now()
    permit.closed_by = closed_by
    if note:
        permit.closure_notes = (permit.closure_notes + "\n" + note).strip()
    permit.save(update_fields=[
        "status", "closed_at", "closed_by", "closure_notes", "updated_at",
    ])
    return permit


def expire_stale_permits(*, as_of=None) -> int:
    """Geçerlilik süresi geçen aktif izinleri EXPIRED yap. Cron ile çalıştırılır."""
    as_of = as_of or timezone.now()
    qs = WorkPermit.objects.filter(
        status=WorkPermit.Status.ISSUED,
        valid_until__lt=as_of,
    )
    count = qs.count()
    qs.update(status=WorkPermit.Status.EXPIRED, updated_at=timezone.now())
    return count

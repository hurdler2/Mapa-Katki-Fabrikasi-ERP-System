"""records/services.py — Case → Record → Evidence → Decision → Sign akış API'si.

Bu servisler ORM'i sarmalar ve MCOS kural setini zorlar:
    - Case/Record ID yeniden kullanılmaz
    - RecordInstance SoD (preparer≠reviewer≠approver)
    - Decision self-approval yasak
    - Decision e-imzası parola doğrulaması gerektirir
    - Evidence SHA-256 hash otomatik
    - Record RECORD_COPY olduktan sonra immutable (SUPERSEDED gerekli)
"""
from __future__ import annotations

import hashlib
from typing import IO, Iterable

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from businessline.models import BusinessLine
from registry.models import ControlledCode

from .models import (
    Case,
    Decision,
    DecisionSignature,
    Evidence,
    RecordInstance,
)


# ---------------------------------------------------------------------------
# Case
# ---------------------------------------------------------------------------

@transaction.atomic
def open_case(
    *,
    case_id: str,
    family: str,
    title: str,
    description: str,
    detected_by: User,
    detected_at=None,
    severity: str = Case.Severity.SEV3,
    business_line: BusinessLine | None = None,
    gate: str = "",
) -> Case:
    """Yeni bir Case açar. case_id yeniden kullanılamaz — unique violation raise."""
    if Case.objects.filter(case_id=case_id).exists():
        raise ValidationError(
            f"Case ID '{case_id}' zaten kullanılmış — yeniden kullanılamaz."
        )
    return Case.objects.create(
        case_id=case_id,
        family=family,
        title=title,
        description=description,
        detected_by=detected_by,
        detected_at=detected_at or timezone.now(),
        severity=severity,
        business_line=business_line,
        gate=gate,
    )


def mark_case_phase(case: Case, phase: str, when=None) -> Case:
    """T-faz zaman damgasını işaretler (T1..T6, closed)."""
    when = when or timezone.now()
    mapping = {
        "T1": "contained_at",
        "T2": "scope_frozen_at",
        "T3": "classified_at",
        "T4": "recovery_at",
        "T5": "reconciled_at",
        "T6": "capa_opened_at",
        "CLOSED": "closed_at",
    }
    field = mapping.get(phase.upper())
    if not field:
        raise ValidationError(f"Geçersiz T-faz: {phase}")
    setattr(case, field, when)
    if phase.upper() == "CLOSED":
        case.status = Case.Status.CLOSED
    elif case.status == Case.Status.OPEN:
        case.status = Case.Status.INVESTIGATING
    case.save()
    return case


# ---------------------------------------------------------------------------
# RecordInstance
# ---------------------------------------------------------------------------

@transaction.atomic
def create_record(
    *,
    record_id: str,
    controlled_code: ControlledCode,
    case: Case,
    preparer: User,
    business_line: BusinessLine | None = None,
    payload: dict | None = None,
) -> RecordInstance:
    """Case × ControlledCode için WORKING durumda yeni kayıt açar."""
    if RecordInstance.objects.filter(record_id=record_id).exists():
        raise ValidationError(
            f"Record ID '{record_id}' zaten kullanılmış — yeniden kullanılamaz."
        )
    bl = business_line or case.business_line
    return RecordInstance.objects.create(
        record_id=record_id,
        controlled_code=controlled_code,
        case=case,
        preparer=preparer,
        business_line=bl,
        payload=payload or {},
        status=RecordInstance.Status.WORKING,
    )


def _guard_mutable(record: RecordInstance) -> None:
    if record.status in (
        RecordInstance.Status.RECORD_COPY,
        RecordInstance.Status.SUPERSEDED,
    ):
        raise ValidationError(
            f"Record '{record.record_id}' RECORD_COPY/SUPERSEDED — "
            "immutable, düzenlenemez."
        )


@transaction.atomic
def submit_for_review(record: RecordInstance, *, reviewer: User) -> RecordInstance:
    _guard_mutable(record)
    if reviewer == record.preparer:
        raise ValidationError({"reviewer": "SoD: Hazırlayan aynı zamanda inceleyen olamaz."})
    record.reviewer = reviewer
    record.review_started_at = timezone.now()
    record.status = RecordInstance.Status.REVIEW
    record.full_clean()
    record.save()
    return record


@transaction.atomic
def approve_record(record: RecordInstance, *, approver: User) -> RecordInstance:
    _guard_mutable(record)
    if approver == record.preparer:
        raise ValidationError({"approver": "SoD: Hazırlayan aynı zamanda onaylayan olamaz."})
    if record.reviewer and approver == record.reviewer:
        raise ValidationError({"approver": "SoD: İnceleyen aynı zamanda onaylayan olamaz."})
    if record.status != RecordInstance.Status.REVIEW:
        raise ValidationError("Onay için önce REVIEW durumuna geçilmeli.")
    record.approver = approver
    record.approved_at = timezone.now()
    record.status = RecordInstance.Status.APPROVED
    record.full_clean()
    record.save()
    return record


@transaction.atomic
def finalize_record_copy(record: RecordInstance, *, path: str = "") -> RecordInstance:
    """Approved → RECORD_COPY (immutable arşiv)."""
    if record.status != RecordInstance.Status.APPROVED:
        raise ValidationError("Sadece APPROVED kayıtlar record copy'ye alınabilir.")
    record.record_copy_at = timezone.now()
    record.record_copy_path = path or record.working_path
    record.status = RecordInstance.Status.RECORD_COPY
    record.save()
    return record


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------

def _hash_file(f: IO[bytes]) -> str:
    h = hashlib.sha256()
    for chunk in iter(lambda: f.read(65536), b""):
        h.update(chunk)
    f.seek(0)
    return h.hexdigest()


@transaction.atomic
def add_evidence(
    *,
    evidence_id: str,
    case: Case,
    kind: str,
    title: str,
    collected_by: User,
    record_instance: RecordInstance | None = None,
    file=None,
    external_url: str = "",
    description: str = "",
    is_contemporaneous: bool = True,
    is_original: bool = True,
    derivative_note: str = "",
) -> Evidence:
    """Dosya varsa SHA-256 hash otomatik hesaplanır. ALCOA+ metadata zorunlu."""
    if Evidence.objects.filter(evidence_id=evidence_id).exists():
        raise ValidationError(f"Evidence ID '{evidence_id}' zaten kullanılmış.")

    sha = ""
    if file is not None:
        sha = _hash_file(file)

    return Evidence.objects.create(
        evidence_id=evidence_id,
        case=case,
        record_instance=record_instance,
        kind=kind,
        title=title,
        description=description,
        collected_by=collected_by,
        file=file,
        external_url=external_url,
        sha256=sha,
        is_contemporaneous=is_contemporaneous,
        is_original=is_original,
        derivative_note=derivative_note,
    )


# ---------------------------------------------------------------------------
# Decision + Signature
# ---------------------------------------------------------------------------

@transaction.atomic
def record_decision(
    *,
    decision_id: str,
    case: Case,
    level: str,
    status: str,
    decision_maker: User,
    options_considered: str,
    rationale: str,
    record_instance: RecordInstance | None = None,
    delegated_authority: str = "",
    evidence_reviewed: Iterable[Evidence] | None = None,
    independent_reviewers: Iterable[User] | None = None,
    assumptions: str = "",
    dissent_or_veto: str = "",
    conditions: str = "",
    action_owner: User | None = None,
    due_date=None,
    acceptance_evidence: str = "",
    escalation_trigger: str = "",
    reopen_trigger: str = "",
    veto_holder_role: str = "",
    decision_date=None,
) -> Decision:
    """Yetkili karar kaydı — NAV-002 §4 zorunlu alanların hepsi doldurulur.

    Self-approval yasak: decision_maker independent_reviewers arasında olamaz.
    """
    if Decision.objects.filter(decision_id=decision_id).exists():
        raise ValidationError(f"Decision ID '{decision_id}' zaten kullanılmış.")

    reviewers = list(independent_reviewers or [])
    if decision_maker in reviewers:
        raise ValidationError(
            "Self-approval yasak: karar veren aynı zamanda bağımsız inceleyen olamaz."
        )

    d = Decision.objects.create(
        decision_id=decision_id,
        case=case,
        record_instance=record_instance,
        level=level,
        status=status,
        decision_date=decision_date or timezone.now(),
        decision_maker=decision_maker,
        delegated_authority=delegated_authority,
        options_considered=options_considered,
        rationale=rationale,
        assumptions=assumptions,
        dissent_or_veto=dissent_or_veto,
        conditions=conditions,
        action_owner=action_owner,
        due_date=due_date,
        acceptance_evidence=acceptance_evidence,
        escalation_trigger=escalation_trigger,
        reopen_trigger=reopen_trigger,
        veto_holder_role=veto_holder_role,
    )

    if reviewers:
        d.independent_reviewers.set(reviewers)
    if evidence_reviewed:
        d.evidence_reviewed.set(list(evidence_reviewed))

    return d


@transaction.atomic
def sign_decision(
    decision: Decision,
    *,
    signer: User,
    password: str,
    meaning: str,
    reason: str,
    ip_address: str | None = None,
) -> DecisionSignature:
    """21 CFR Part 11 tarzı e-imza — parola doğrulaması + kayıt.

    Parola geçersizse PermissionDenied.
    """
    if not signer.check_password(password):
        raise PermissionDenied("Parola doğrulanamadı — e-imza reddedildi.")
    if meaning not in DecisionSignature.Meaning.values:
        raise ValidationError(f"Geçersiz imza anlamı: {meaning}")

    return DecisionSignature.objects.create(
        decision=decision,
        signer=signer,
        meaning=meaning,
        reason=reason,
        ip_address=ip_address,
    )

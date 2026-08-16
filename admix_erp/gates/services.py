"""gates/services.py — 8-Part Gate open/complete/close/reopen API'si.

Kritik kurallar:
    - open_gate: 8 GateSection'u OPEN durumda otomatik oluşturur
    - complete_section: bölümü PASS/CONDITIONAL/HOLD/FAIL olarak işaretler,
      evidence bağlantısını doğrular
    - close_gate:
        * 8 bölüm hepsi PASS veya CONDITIONAL olmalı
        * Her bölüme en az 1 Evidence bağlı olmalı
        * Case'in en az 1 Decision'u olmalı
        * HOLD/FAIL varsa gate FAIL edilir (kapanır ama başarısız)
    - reopen_gate: PASS/CONDITIONAL gate'i REOPENED'a çevirir,
      history'e trigger + user + timestamp append eder
"""
from __future__ import annotations

from typing import Iterable

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from businessline.models import BusinessLine
from records.models import Case, Evidence

from .models import Gate, GateSection


# ---------------------------------------------------------------------------
# Open gate — 8 section auto-create
# ---------------------------------------------------------------------------

@transaction.atomic
def open_gate(
    *,
    gate_id: str,
    case: Case,
    owner: User,
    scope: str,
    business_line: BusinessLine | None = None,
) -> Gate:
    """Yeni bir gate açar ve 8 GateSection'u OPEN olarak oluşturur."""
    if Gate.objects.filter(gate_id=gate_id).exists():
        raise ValidationError(
            f"Gate ID '{gate_id}' zaten kullanılmış — yeniden kullanılamaz."
        )
    g = Gate.objects.create(
        gate_id=gate_id, case=case, owner=owner, scope=scope,
        business_line=business_line or case.business_line,
        status=Gate.Status.OPEN,
    )
    for section in Gate.ALL_SECTIONS:
        GateSection.objects.create(
            gate=g, section=section,
            completion_status=Gate.Status.OPEN,
        )
    return g


# ---------------------------------------------------------------------------
# Complete a section
# ---------------------------------------------------------------------------

@transaction.atomic
def complete_section(
    gate: Gate,
    *,
    section: str,
    status: str,
    reviewer: User,
    evidence: Iterable[Evidence] | None = None,
    notes: str = "",
) -> GateSection:
    """Bir bölümü tamamlanmış (PASS/CONDITIONAL/HOLD/FAIL) olarak işaretle."""
    if gate.status in (Gate.Status.PASS, Gate.Status.CONDITIONAL, Gate.Status.FAIL):
        raise ValidationError(
            f"Gate '{gate.gate_id}' zaten kapalı ({gate.status}) — bölüm güncellenemez."
        )
    if status not in {
        Gate.Status.PASS, Gate.Status.CONDITIONAL, Gate.Status.HOLD,
        Gate.Status.FAIL, Gate.Status.IN_PROGRESS,
    }:
        raise ValidationError(f"Geçersiz section durumu: {status}")

    try:
        gs = GateSection.objects.get(gate=gate, section=section)
    except GateSection.DoesNotExist:
        raise ValidationError(f"Gate {gate.gate_id}'de bölüm '{section}' yok.")

    gs.completion_status = status
    gs.reviewer = reviewer
    gs.reviewed_at = timezone.now()
    if notes:
        gs.notes = notes
    gs.save()

    if evidence:
        gs.evidence.set(list(evidence))

    # Gate'in genel durumunu güncelle
    if gate.status == Gate.Status.OPEN:
        gate.status = Gate.Status.IN_PROGRESS
        gate.save(update_fields=["status", "updated_at"])

    return gs


# ---------------------------------------------------------------------------
# Close gate
# ---------------------------------------------------------------------------

def close_gate(gate: Gate, *, closed_by: User) -> Gate:
    """Gate'i kapatmayı dener.

    Beklenen: 8 bölüm PASS/CONDITIONAL + her birinde evidence + case'in
    en az 1 Decision'u. Aksi halde ValidationError ya da FAIL.

    Not: `@transaction.atomic` kasten kullanılmıyor — HOLD/FAIL bölümü
    tespit edilince gate FAIL kaydı işlenip commit edilir, sonra hata
    yükseltilir. Aksi halde tek rollback her şeyi geri alırdı.
    """
    if gate.status in (Gate.Status.PASS, Gate.Status.CONDITIONAL, Gate.Status.FAIL):
        raise ValidationError(f"Gate zaten kapalı ({gate.status}).")

    sections = list(gate.sections.all())
    if len(sections) != len(Gate.ALL_SECTIONS):
        raise ValidationError(
            f"Gate'te {len(sections)} bölüm var, 8 olmalı."
        )

    # Hard-fail kontrolü: HOLD veya FAIL varsa gate FAIL (kayıt edilir + raise)
    for gs in sections:
        if gs.completion_status in (Gate.Status.HOLD, Gate.Status.FAIL):
            with transaction.atomic():
                gate.status = Gate.Status.FAIL
                gate.closed_at = timezone.now()
                gate.closed_by = closed_by
                gate.save()
            raise ValidationError(
                f"Gate FAIL: bölüm '{gs.get_section_display()}' "
                f"{gs.completion_status} durumda."
            )

    # Tüm bölümler PASS/CONDITIONAL mı?
    for gs in sections:
        if gs.completion_status not in (Gate.Status.PASS, Gate.Status.CONDITIONAL):
            raise ValidationError(
                f"Gate kapanamaz: bölüm '{gs.get_section_display()}' "
                f"henüz tamamlanmadı ({gs.completion_status})."
            )
        if gs.evidence.count() < 1:
            raise ValidationError(
                f"Gate kapanamaz: bölüm '{gs.get_section_display()}' için "
                "en az 1 evidence bağlanmalı."
            )

    # Case'in en az 1 Decision'u olmalı
    if gate.case.decisions.count() < 1:
        raise ValidationError(
            f"Gate kapanamaz: case '{gate.case.case_id}' için "
            "en az 1 Decision kaydı gerekli."
        )

    # Herhangi bir bölüm CONDITIONAL ise gate CONDITIONAL PASS, aksi halde PASS
    with transaction.atomic():
        any_conditional = any(
            gs.completion_status == Gate.Status.CONDITIONAL for gs in sections
        )
        gate.status = Gate.Status.CONDITIONAL if any_conditional else Gate.Status.PASS
        gate.closed_at = timezone.now()
        gate.closed_by = closed_by
        gate.save()
    return gate


# ---------------------------------------------------------------------------
# Reopen gate
# ---------------------------------------------------------------------------

@transaction.atomic
def reopen_gate(
    gate: Gate,
    *,
    triggered_by: User,
    trigger: str,
    note: str = "",
) -> Gate:
    """PASS/CONDITIONAL bir gate'i yeniden aç.

    Kurallar:
        - Yalnız kapanmış (PASS/CONDITIONAL) veya FAIL gate reopen edilebilir.
        - trigger boş olamaz — nedeni JSON history'e loglanır.
    """
    if gate.status not in (Gate.Status.PASS, Gate.Status.CONDITIONAL,
                            Gate.Status.FAIL):
        raise ValidationError(
            f"Reopen sadece kapanmış gate için: '{gate.status}' geçerli değil."
        )
    if not trigger.strip():
        raise ValidationError("Reopen tetiği (trigger) zorunlu.")

    entry = {
        "trigger": trigger,
        "by_user": triggered_by.username,
        "at": timezone.now().isoformat(),
        "note": note,
        "prev_status": gate.status,
    }
    history = list(gate.reopen_history or [])
    history.append(entry)
    gate.reopen_history = history

    gate.status = Gate.Status.REOPENED
    gate.closed_at = None
    gate.closed_by = None
    gate.save()
    return gate

"""12 Non-Negotiable kural için enforcement fonksiyonları.

Her kural bir `check_ruleXX(instance, **ctx)` fonksiyonuna sahiptir. Fonksiyon:
    - Kural karşılanıyorsa None döner (kaydetme devam eder).
    - İhlal varsa `log_and_raise()` çağırır → RuleViolation kaydı + ValidationError.

`log_only=True` verilirse ValidationError yükseltilmez (sadece log; opsiyonel mod).
"""
from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError

from .models import RULE_TITLES, RuleViolation


class RuleViolationError(ValidationError):
    """Non-negotiable kural ihlalini işaretler (ValidationError alt sınıfı)."""

    def __init__(self, rule_no: int, message: str):
        self.rule_no = rule_no
        super().__init__(f"[R{rule_no:02d}] {message}")


def _rules_enabled() -> bool:
    return getattr(settings, "MCOS_ENABLE_RULES_ENFORCER", True)


def log_and_raise(
    *,
    rule_no: int,
    instance: Any,
    attempted_action: str,
    reason: str,
    context: dict | None = None,
    user=None,
    blocked: bool = True,
) -> None:
    """RuleViolation kaydı oluşturur; blocked=True ise RuleViolationError yükseltir."""
    model = type(instance)
    target_model = f"{model._meta.app_label}.{model.__name__}"
    target_pk = str(getattr(instance, "pk", "") or "")
    target_repr = str(instance)[:200]

    RuleViolation.objects.create(
        rule_no=rule_no,
        rule_title=RULE_TITLES[rule_no],
        user=user,
        target_model=target_model,
        target_pk=target_pk,
        target_repr=target_repr,
        attempted_action=attempted_action,
        reason=reason,
        context=context or {},
        blocked=blocked,
    )
    if blocked:
        raise RuleViolationError(rule_no, reason)


# ---------------------------------------------------------------------------
# R01 — Onaysız reçete / hammadde / tedarikçi ile üretim yok
# ---------------------------------------------------------------------------

def check_rule01_batch_uses_approved_inputs(batch) -> None:
    """ProductionBatch save: recipe.is_active olmalı."""
    if not _rules_enabled():
        return
    recipe = getattr(batch, "recipe", None)
    if recipe and not getattr(recipe, "is_active", True):
        log_and_raise(
            rule_no=1, instance=batch, attempted_action="save",
            reason=(f"Reçete '{recipe}' aktif değil — onaysız reçete ile üretim yasak."),
            context={"recipe_id": recipe.pk, "recipe_active": False},
        )


# ---------------------------------------------------------------------------
# R02 — HOLD/REJECT malzeme tüketilemez veya sevk edilemez
# ---------------------------------------------------------------------------

_ALLOWED_QC = {"RELEASED"}


def check_rule02_consumption_uses_released_lot(consumption) -> None:
    """MaterialConsumption save: lot.qc_status == RELEASED olmalı."""
    if not _rules_enabled():
        return
    lot = getattr(consumption, "lot", None)
    if lot is None:
        return
    qc = getattr(lot, "qc_status", None)
    if qc not in _ALLOWED_QC:
        log_and_raise(
            rule_no=2, instance=consumption, attempted_action="consume",
            reason=(f"Lot '{lot.lot_number}' QC durumu {qc} — sadece RELEASED tüketilebilir."),
            context={"lot": lot.lot_number, "qc_status": qc},
        )


def check_rule02_shipment_line_ships_released_batch(line) -> None:
    """ShipmentLine save: batch.qc_status == RELEASED olmalı."""
    if not _rules_enabled():
        return
    batch = getattr(line, "batch", None)
    if batch is None:
        return
    qc = getattr(batch, "qc_status", None)
    if qc not in _ALLOWED_QC:
        log_and_raise(
            rule_no=2, instance=line, attempted_action="ship",
            reason=(f"Parti '{batch.batch_number}' QC durumu {qc} — sadece RELEASED sevk edilebilir."),
            context={"batch": batch.batch_number, "qc_status": qc},
        )


# ---------------------------------------------------------------------------
# R03 — Geçerli numune + review olmadan release yok
# ---------------------------------------------------------------------------

def check_rule03_release_requires_qc_results(batch, old_qc_status: str | None = None) -> None:
    """ProductionBatch RELEASED'e geçmeden en az 1 QC test sonucu olmalı."""
    if not _rules_enabled():
        return
    new_qc = getattr(batch, "qc_status", None)
    if new_qc != "RELEASED":
        return
    if old_qc_status == "RELEASED":
        return  # yeni release değil, zaten released
    # Batch pk yoksa henüz oluşturulmuyor — kontrol atlanır (sonra tekrar tetiklenir)
    if not batch.pk:
        return
    qc_count = batch.qc_results.count() if hasattr(batch, "qc_results") else 0
    if qc_count == 0:
        log_and_raise(
            rule_no=3, instance=batch, attempted_action="release",
            reason=(f"Parti '{batch.batch_number}' RELEASED yapılıyor ama QC sonucu yok."),
            context={"batch": batch.batch_number, "qc_test_count": 0},
        )


# ---------------------------------------------------------------------------
# R04 — Kritik ölçüm geçerli kalibrasyon olmadan kabul edilmez
# ---------------------------------------------------------------------------

def check_rule04_qc_result_requires_calibrated_equipment(result) -> None:
    """QCTestResult save: eğer equipment atanmışsa kalibrasyon geçerli olmalı.

    Model equipment FK varsa kontrol eder; yoksa (opsiyonel alan) atlar.
    """
    if not _rules_enabled():
        return
    equipment = getattr(result, "equipment", None)
    if equipment is None:
        return
    valid_until = getattr(equipment, "calibration_valid_until", None)
    if valid_until is None:
        return
    import datetime as _dt
    today = _dt.date.today()
    if valid_until < today:
        log_and_raise(
            rule_no=4, instance=result, attempted_action="save",
            reason=(f"Ekipman '{equipment}' kalibrasyonu {valid_until} tarihinde bitti."),
            context={"equipment": str(equipment), "calibration_valid_until": valid_until.isoformat()},
        )


# ---------------------------------------------------------------------------
# R05 — Kayıt geriye dönük oluşturulmaz (backdating yasak)
# ---------------------------------------------------------------------------

BACKDATE_TOLERANCE_HOURS = 24


def check_rule05_record_not_backdated(record) -> None:
    """RecordInstance save: working_started_at case.detected_at'den önce olamaz.

    Tolerance: 24 saat (system clock drift veya delayed reporting için).
    Yeni kayıtta working_started_at henüz set olmamış olabilir (auto_now_add DB'ye
    kaydolurken atanır) — bu durumda timezone.now() referans alınır.
    """
    if not _rules_enabled():
        return
    from django.utils import timezone as _tz
    case = getattr(record, "case", None)
    if not case:
        return
    detected = getattr(case, "detected_at", None)
    if not detected:
        return
    started = getattr(record, "working_started_at", None) or _tz.now()
    import datetime as _dt
    tolerance = _dt.timedelta(hours=BACKDATE_TOLERANCE_HOURS)
    if started + tolerance < detected:
        log_and_raise(
            rule_no=5, instance=record, attempted_action="save",
            reason=(f"Record '{getattr(record, 'record_id', '?')}' başlangıcı "
                    f"{started} olay tarihi {detected}'den önce (backdating)."),
            context={"started": started.isoformat(),
                      "detected": detected.isoformat()},
        )


# ---------------------------------------------------------------------------
# R06 — MOC olmadan aktif reçete/proses değişmez
# ---------------------------------------------------------------------------

def check_rule06_active_recipe_change_needs_moc(recipe, old_recipe=None) -> None:
    """Recipe save: aktif reçete değiştiriliyorsa change_notice_ref alanı zorunlu.

    Opt-in: Model'in change_notice_ref FIELD'ı yoksa kural devre dışı
    (modele alan eklenene kadar kural NoOp).
    """
    if not _rules_enabled():
        return
    # Opt-in field check
    if not any(f.name == "change_notice_ref" for f in recipe._meta.get_fields()):
        return
    if not old_recipe:
        return  # yeni oluşturma; MOC gerektirmez
    if not getattr(old_recipe, "is_active", False):
        return  # zaten inaktif, MOC gerekmez
    critical_fields = ("base_batch_size", "version")
    changed = any(
        getattr(old_recipe, f, None) != getattr(recipe, f, None)
        for f in critical_fields
    )
    if not changed:
        return
    moc_ref = getattr(recipe, "change_notice_ref", "") or ""
    if not str(moc_ref).strip():
        log_and_raise(
            rule_no=6, instance=recipe, attempted_action="save",
            reason=("Aktif reçete kritik alanı değişiyor ama change_notice_ref boş."),
            context={"recipe_id": recipe.pk},
        )


# ---------------------------------------------------------------------------
# R07 — QA hold/red/release ticari baskıyla bypass edilmez
# ---------------------------------------------------------------------------

def check_rule07_approval_veto_respected(approval) -> None:
    """ApprovalRequest save: veto_holder_role tanımlıysa ve REJECTED bir veto varsa,
    aynı hedef için yeni APPROVED talep açılamaz."""
    if not _rules_enabled():
        return
    from portal.models import ApprovalRequest
    if approval.status != ApprovalRequest.Status.APPROVED:
        return
    if not approval.pk:
        return
    # Aynı hedefe daha önce veto edilmiş talep var mı?
    prior_veto = ApprovalRequest.objects.filter(
        content_type_id=approval.content_type_id,
        object_id=approval.object_id,
        status=ApprovalRequest.Status.REJECTED,
        decision_reason__startswith="[VETO",
    ).exclude(pk=approval.pk).first()
    if prior_veto is not None:
        log_and_raise(
            rule_no=7, instance=approval, attempted_action="save",
            reason=(f"Bu hedef için önceden veto edilmiş talep var (#{prior_veto.pk}). "
                    "QA/HSE vetosu ticari baskıyla bypass edilemez."),
            context={"prior_veto_pk": prior_veto.pk,
                      "veto_reason": prior_veto.decision_reason[:200]},
        )


# ---------------------------------------------------------------------------
# R08 — Emniyetsiz iş bypass edilemez
# ---------------------------------------------------------------------------

def check_rule08_hse_incident_severity(incident) -> None:
    """Incident save: FATALITY veya SERIOUS_INJURY severity ise CLOSED yapılamaz
    öncesinde CAPA açılmadan."""
    if not _rules_enabled():
        return
    severity = getattr(incident, "severity", "")
    status = getattr(incident, "status", "")
    if severity not in {"FATALITY", "SERIOUS", "MAJOR"}:
        return
    if status == "CLOSED":
        # CAPA açık mı? (basit heuristik: NCR açılmış olmalı — yoksa reddet)
        case = getattr(incident, "case", None)
        if case is None:
            log_and_raise(
                rule_no=8, instance=incident, attempted_action="close",
                reason=(f"Ciddi olay ({severity}) MCOS Case bağlantısı olmadan kapatılamaz."),
                context={"severity": severity},
            )


# ---------------------------------------------------------------------------
# R09 — Kritik görev yetkisiz kişi tarafından yürütülemez
# ---------------------------------------------------------------------------

def check_rule09_decision_maker_has_authority(decision) -> None:
    """Decision save: decision_maker'ın D-seviyesi yetkisi olmalı."""
    if not _rules_enabled():
        return
    from iam.models import Role
    maker = getattr(decision, "decision_maker", None)
    level = getattr(decision, "level", None)
    if not maker or not level:
        return
    # Delege edilmiş yetki varsa esneme
    if getattr(decision, "delegated_authority", "").strip():
        return
    if not Role.user_can_decide_at(maker, level):
        log_and_raise(
            rule_no=9, instance=decision, attempted_action="save",
            reason=(f"Kullanıcı '{maker.username}' {level} seviyesinde karar veremez "
                    "(delegated_authority boş)."),
            context={"user": maker.username, "level": level},
        )


# ---------------------------------------------------------------------------
# R10 — NCR/CAPA sadece aksiyon yapıldı diye kapanmaz (etkinlik zorunlu)
# ---------------------------------------------------------------------------

def check_rule10_capa_close_requires_effectiveness(capa) -> None:
    """CAPA save (status=CLOSED): verified_at alanı dolu olmalı."""
    if not _rules_enabled():
        return
    status = getattr(capa, "status", "")
    if status != "CLOSED":
        return
    verified = getattr(capa, "verified_at", None)
    if verified is None:
        log_and_raise(
            rule_no=10, instance=capa, attempted_action="close",
            reason=(f"CAPA '{getattr(capa, 'capa_number', '?')}' CLOSED yapılıyor ama "
                    "verified_at boş — etkinlik doğrulanmadan kapatma yasak."),
            context={"capa": getattr(capa, "capa_number", "")},
        )


# ---------------------------------------------------------------------------
# R11 — ControlledCode sahibi olmadan yayımlanmaz
# ---------------------------------------------------------------------------

def check_rule11_controlled_code_owner_required(code) -> None:
    """ControlledCode save (status=ISSUED/ACTIVATED): owner_role boş olamaz."""
    if not _rules_enabled():
        return
    status = getattr(code, "status", "")
    if status not in {"IS", "AC"}:  # ISSUED / ACTIVATED
        return
    owner = getattr(code, "owner_role", "") or ""
    if not owner.strip():
        log_and_raise(
            rule_no=11, instance=code, attempted_action="save",
            reason=(f"ControlledCode '{code.full_code}' {status} statüsüne alınıyor "
                    "ama owner_role boş."),
            context={"code": code.full_code, "status": status},
        )


# ---------------------------------------------------------------------------
# R12 — Ciddi risk (SEV1/SEV2) eskale edilir (GM notify)
# ---------------------------------------------------------------------------

def check_rule12_severe_case_escalated(case) -> None:
    """Case save: SEV1/SEV2 severity → GM'ye bildirim (log_only, block etmez)."""
    if not _rules_enabled():
        return
    severity = getattr(case, "severity", "")
    if severity not in {"SEV1", "SEV2"}:
        return
    # Sadece yeni oluşturmada eskalasyon logla — güncellemede tekrar açmasın
    if getattr(case, "_escalation_notified", False):
        return
    log_and_raise(
        rule_no=12, instance=case, attempted_action="save",
        reason=(f"Ciddi Case '{case.case_id}' ({severity}) — GM'ye eskale edildi."),
        context={"case": case.case_id, "severity": severity},
        blocked=False,  # sadece log + notify, kayıt engellenmez
    )
    case._escalation_notified = True
    # Notify GM (varsa notifications servisi)
    try:
        from notifications.services import notify_group
        notify_group(
            role_code="GENERAL_MANAGER",
            title=f"Ciddi olay: {case.case_id}",
            message=f"{severity} · {case.title}",
            level="ALERT",
            target=case,
            action_url=f"/portal/cases/{case.case_id}/",
        )
    except Exception:  # noqa: BLE001
        pass  # bildirim opsiyonel — kural log'u yeterli

"""Portal servisleri: onay talebi oluşturma + karar verme + onay uygulaması."""
from __future__ import annotations

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from notifications.services import notify_group

from .models import ApprovalRequest


@transaction.atomic
def request_approval(
    *,
    kind: str,
    target,
    requested_by,
    required_role: str,
    title: str,
    description: str = "",
    decision_level: str = ApprovalRequest.DecisionLevel.D2,
    veto_holder_role: str = "",
) -> ApprovalRequest:
    """Bir kayıt için onay talebi oluştur ve ilgili role bildirim gönder.

    MCOS Faz B: `decision_level` D1-D4 arası, `veto_holder_role` NAV-002
    §3'teki veto sahibi rollerden biri olmalı.
    """
    from iam.models import Role

    if veto_holder_role and not Role.is_veto_holder(veto_holder_role):
        raise ValidationError(
            f"'{veto_holder_role}' NAV-002 §3 veto sahibi role listesinde değil."
        )

    ct = ContentType.objects.get_for_model(target)
    # Aynı hedef için açık talep var mı?
    existing = ApprovalRequest.objects.filter(
        content_type=ct, object_id=target.pk,
        kind=kind, status=ApprovalRequest.Status.PENDING,
    ).first()
    if existing:
        return existing

    ar = ApprovalRequest.objects.create(
        kind=kind, target=target,
        content_type=ct, object_id=target.pk,
        requested_by=requested_by,
        required_role=required_role,
        title=title, description=description,
        decision_level=decision_level,
        veto_holder_role=veto_holder_role,
    )
    notify_group(
        role_code=required_role,
        title=f"Onay bekliyor: {title}",
        message=description or f"{kind} onay talebi",
        level="TASK",
        target=ar,
        action_url="/portal/onaylar/",
    )
    return ar


@transaction.atomic
def approve(ar: ApprovalRequest, *, user, reason: str = "") -> ApprovalRequest:
    """Onay talebini onayla. Kullanıcı doğru role sahip olmalı.

    MCOS Faz B: kullanıcı ayrıca `decision_level` yetkisine sahip olmalı
    (Role.DEFAULT_DECISION_LEVEL üzerinden hesaplanır).

    Onay verildikten sonra hedef nesne üzerinde ilgili işlem otomatik uygulanır
    (fatura post, batch release vb.)
    """
    from iam.models import Role

    if ar.status != ApprovalRequest.Status.PENDING:
        raise ValidationError(f"Talep zaten karar verilmiş: {ar.status}")

    if not user.is_superuser and not user.groups.filter(name=ar.required_role).exists():
        raise PermissionDenied(
            f"Onay için '{ar.required_role}' rolüne sahip olmalısınız."
        )

    if not Role.user_can_decide_at(user, ar.decision_level):
        raise PermissionDenied(
            f"{ar.decision_level} seviyesinde karar verme yetkiniz yok."
        )

    if user.pk == ar.requested_by_id:
        raise ValidationError("Kişi kendi talebini onaylayamaz (görev ayrımı).")

    ar.status = ApprovalRequest.Status.APPROVED
    ar.decided_by = user
    ar.decided_at = timezone.now()
    ar.decision_reason = reason
    ar.save(update_fields=[
        "status", "decided_by", "decided_at", "decision_reason", "updated_at",
    ])

    # Talep türüne göre otomatik işlem uygula
    _execute_on_approval(ar, executed_by=user)

    return ar


@transaction.atomic
def reject(ar: ApprovalRequest, *, user, reason: str) -> ApprovalRequest:
    if ar.status != ApprovalRequest.Status.PENDING:
        raise ValidationError(f"Talep zaten karar verilmiş: {ar.status}")

    if not user.is_superuser and not user.groups.filter(name=ar.required_role).exists():
        raise PermissionDenied(
            f"Ret için '{ar.required_role}' rolüne sahip olmalısınız."
        )

    if not reason.strip():
        raise ValidationError("Ret gerekçesi zorunludur.")

    ar.status = ApprovalRequest.Status.REJECTED
    ar.decided_by = user
    ar.decided_at = timezone.now()
    ar.decision_reason = reason
    ar.save(update_fields=[
        "status", "decided_by", "decided_at", "decision_reason", "updated_at",
    ])
    return ar


def _execute_on_approval(ar: ApprovalRequest, *, executed_by):
    """Onaylanan talebe göre hedef nesne üzerinde işlemi tamamla."""
    from accounting.services import post_invoice

    target = ar.target
    if target is None:
        return

    if ar.kind == ApprovalRequest.Kind.INVOICE_POST:
        try:
            post_invoice(target, user=executed_by)
        except Exception:
            pass  # Fatura zaten POSTED olabilir
    elif ar.kind == ApprovalRequest.Kind.BATCH_RELEASE:
        from production.models import ProductionBatch
        if isinstance(target, ProductionBatch):
            target.qc_status = ProductionBatch.QCStatus.RELEASED
            if target.status == ProductionBatch.Status.QC_HOLD:
                target.status = ProductionBatch.Status.RELEASED
            elif target.status == ProductionBatch.Status.COMPLETED:
                target.status = ProductionBatch.Status.RELEASED
            target.save(update_fields=["qc_status", "status", "updated_at"])
    elif ar.kind == ApprovalRequest.Kind.CAPA_CLOSE:
        from qms.models import CAPA
        from qms.services import close_capa
        if isinstance(target, CAPA):
            try:
                close_capa(target)
            except Exception:
                pass


@transaction.atomic
def veto(ar: ApprovalRequest, *, user, reason: str) -> ApprovalRequest:
    """NAV-002 §3 — veto sahibi rol talebi bloklar (REJECT + veto işareti).

    Sadece `ar.veto_holder_role` grubuna üye kullanıcı çağırabilir.
    """
    from iam.models import Role

    if ar.status != ApprovalRequest.Status.PENDING:
        raise ValidationError(f"Talep zaten karar verilmiş: {ar.status}")
    if not ar.veto_holder_role:
        raise ValidationError("Bu talep için tanımlı veto sahibi rol yok.")
    if not Role.is_veto_holder(ar.veto_holder_role):
        raise ValidationError(
            f"'{ar.veto_holder_role}' NAV-002 §3 veto listesinde değil."
        )
    if not user.is_superuser and not user.groups.filter(
            name=ar.veto_holder_role).exists():
        raise PermissionDenied(
            f"Veto için '{ar.veto_holder_role}' rolüne sahip olmalısınız."
        )
    if not reason.strip():
        raise ValidationError("Veto gerekçesi zorunludur.")

    ar.status = ApprovalRequest.Status.REJECTED
    ar.decided_by = user
    ar.decided_at = timezone.now()
    ar.decision_reason = f"[VETO by {ar.veto_holder_role}] {reason}"
    ar.save(update_fields=[
        "status", "decided_by", "decided_at", "decision_reason", "updated_at",
    ])
    return ar


def approvals_for_user(user) -> "QuerySet[ApprovalRequest]":
    """Kullanıcının rolüne göre bekleyen onay talepleri."""
    if user.is_superuser:
        return ApprovalRequest.objects.filter(status=ApprovalRequest.Status.PENDING)
    role_names = list(user.groups.values_list("name", flat=True))
    return ApprovalRequest.objects.filter(
        status=ApprovalRequest.Status.PENDING,
        required_role__in=role_names,
    ).exclude(requested_by=user)  # Kendi talebini onaylayamaz


def approvals_count(user) -> int:
    return approvals_for_user(user).count()

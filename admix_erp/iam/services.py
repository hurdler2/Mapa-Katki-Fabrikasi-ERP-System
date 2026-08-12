"""IAM servisleri: e-imza doğrulama, yetkilendirme yardımcıları."""
from __future__ import annotations

from django.contrib.auth import authenticate
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from .models import ESignature


@transaction.atomic
def sign(
    *,
    user,
    target,
    meaning: str,
    reason: str,
    password: str | None = None,
    ip_address: str | None = None,
    verify_password: bool = True,
) -> ESignature:
    """E-imza oluşturur.

    Kullanıcı parolasını yeniden doğrular (verify_password=True), aksi halde
    ValidationError. Parola doğru değilse veya kullanıcı aktif değilse
    PermissionDenied yükseltilir.
    """
    if not reason.strip():
        raise ValidationError("E-imza için gerekçe zorunludur (21 CFR 11).")

    if verify_password:
        if password is None:
            raise ValidationError("E-imza için parola gereklidir.")
        u = authenticate(username=user.get_username(), password=password)
        if u is None or u.pk != user.pk:
            raise PermissionDenied("E-imza parola doğrulaması başarısız.")

    ct = ContentType.objects.get_for_model(target)
    return ESignature.objects.create(
        user=user,
        content_type=ct,
        object_id=target.pk,
        meaning=meaning,
        reason=reason.strip(),
        ip_address=ip_address,
    )


def signatures_for(target) -> "QuerySet[ESignature]":
    """Bir hedef nesne için tüm e-imzaları getirir (kronolojik)."""
    ct = ContentType.objects.get_for_model(target)
    return ESignature.objects.filter(
        content_type=ct, object_id=target.pk
    ).select_related("user").order_by("signed_at")


def user_has_role(user, *role_codes: str) -> bool:
    """Kullanıcının verilen role kodlarından herhangi birine sahip olup olmadığını döndürür."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=role_codes).exists()


def require_role(*role_codes: str):
    """View decoratörü: kullanıcının rolü uygun değilse PermissionDenied."""
    from functools import wraps

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not user_has_role(request.user, *role_codes):
                raise PermissionDenied(
                    f"Bu işlem için gerekli rol yok: {', '.join(role_codes)}"
                )
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator

"""BusinessLine yardımcı servisler: rol × BL scope, current-BL yönetimi."""
from __future__ import annotations

from django.contrib.auth.models import User

from .models import BusinessLine, RoleBusinessLineScope


def business_lines_for(user: User):
    """Kullanıcının erişebildiği BL'lerin queryset'i.

    - Superuser → tüm aktif BL'ler
    - Hiç rol scope kaydı yok → tüm aktif BL'ler (backward-compat)
    - Kayıt var → sadece scope'daki BL'ler
    """
    active = BusinessLine.objects.filter(is_active=True)
    if not user.is_authenticated:
        return active.none()
    if user.is_superuser:
        return active

    scopes = RoleBusinessLineScope.objects.filter(
        group__in=user.groups.all()
    ).values_list("business_line_id", flat=True)

    # Hiç scope yok → hepsine erişim (geçiş dönemi için)
    if not scopes:
        return active

    return active.filter(pk__in=set(scopes))


def user_has_bl_access(user: User, business_line: BusinessLine) -> bool:
    """Kullanıcı belirli BL'ye erişebilir mi?"""
    if business_line is None:
        return True  # BL bağlantısı yok (geçiş dönemi, backward-compat)
    if user.is_superuser:
        return True
    scopes = RoleBusinessLineScope.objects.filter(
        group__in=user.groups.all(),
        business_line=business_line,
    )
    if not RoleBusinessLineScope.objects.filter(
        group__in=user.groups.all()
    ).exists():
        return True  # Hiç scope tanımlı değil → geçiş dönemi
    return scopes.exists()


def get_active_bl_code(request):
    """Session'daki aktif BL kodunu döner. Yoksa None (Tümü)."""
    return request.session.get("active_bl_code")


def set_active_bl_code(request, code: str | None):
    """Session'a aktif BL yaz. code=None → temizle."""
    if code:
        request.session["active_bl_code"] = code
    else:
        request.session.pop("active_bl_code", None)


def get_active_bl(request):
    """Aktif BusinessLine instance'ı (yoksa None)."""
    code = get_active_bl_code(request)
    if not code:
        return None
    return BusinessLine.objects.filter(code=code, is_active=True).first()

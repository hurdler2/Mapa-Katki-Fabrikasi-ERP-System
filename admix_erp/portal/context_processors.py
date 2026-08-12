"""Portal context — sidebar menu, badges ve aktif BL her sayfada mevcut."""
from __future__ import annotations

from .menu import filter_menu_for


def portal_context(request):
    if not request.user.is_authenticated:
        return {}
    from iam.models import Role
    from notifications.models import Notification
    from .services import approvals_count

    role_labels = []
    for g in request.user.groups.all():
        role_labels.append(Role.LABELS.get(g.name, g.name))

    ctx = {
        "sidebar_menu": filter_menu_for(request.user),
        "unread_count": Notification.objects.filter(
            recipient=request.user, is_read=False).count(),
        "approvals_count": approvals_count(request.user),
        "user_roles_display": ", ".join(role_labels) if role_labels else "Rol yok",
    }

    # MCOS Faz A — BusinessLine context
    from django.conf import settings
    if getattr(settings, "MCOS_ENABLE_BUSINESSLINE", False):
        from businessline.services import (
            business_lines_for, get_active_bl,
        )
        ctx["available_business_lines"] = business_lines_for(request.user)
        ctx["active_business_line"] = get_active_bl(request)
    return ctx

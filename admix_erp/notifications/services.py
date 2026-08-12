"""Bildirim servisleri: notify + broadcast + kullanıcı görev sayacı."""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

from .models import Notification


User = get_user_model()


@transaction.atomic
def notify(
    *,
    recipient,
    title: str,
    message: str = "",
    level: str = Notification.Level.INFO,
    target=None,
    action_url: str = "",
) -> Notification:
    ct = ContentType.objects.get_for_model(target) if target else None
    return Notification.objects.create(
        recipient=recipient, title=title, message=message,
        level=level, content_type=ct,
        object_id=target.pk if target else None,
        action_url=action_url,
    )


@transaction.atomic
def notify_group(
    *,
    role_code: str,
    title: str,
    message: str = "",
    level: str = Notification.Level.INFO,
    target=None,
    action_url: str = "",
) -> int:
    """Bir role (Group) dahil tüm aktif kullanıcılara bildirim gönder. Sayı döner."""
    try:
        group = Group.objects.get(name=role_code)
    except Group.DoesNotExist:
        return 0
    count = 0
    ct = ContentType.objects.get_for_model(target) if target else None
    for user in group.user_set.filter(is_active=True):
        Notification.objects.create(
            recipient=user, title=title, message=message,
            level=level, content_type=ct,
            object_id=target.pk if target else None,
            action_url=action_url,
        )
        count += 1
    return count


@transaction.atomic
def mark_read(notification: Notification) -> Notification:
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=["is_read", "read_at", "updated_at"])
    return notification


def unread_count(user) -> int:
    return Notification.objects.filter(recipient=user, is_read=False).count()

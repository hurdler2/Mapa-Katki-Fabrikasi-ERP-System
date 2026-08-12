"""Notification testleri: notify + inbox + role broadcast."""
from __future__ import annotations

import pytest
from django.contrib.auth.models import Group, User
from django.urls import reverse

from notifications.models import Notification
from notifications.services import mark_read, notify, notify_group, unread_count


pytestmark = pytest.mark.django_db


def test_notify_and_unread_count(product):
    u = User.objects.create_user("nuser", password="pw")
    n = notify(recipient=u, title="Yeni ürün", message="ADX-100 kaydı açıldı.",
               target=product, action_url="/admin/masterdata/product/")
    assert n.pk is not None
    assert n.target == product
    assert unread_count(u) == 1
    mark_read(n)
    assert unread_count(u) == 0


def test_notify_group_broadcast():
    g = Group.objects.create(name="QA_TEAM")
    u1 = User.objects.create_user("qa1", password="pw")
    u2 = User.objects.create_user("qa2", password="pw")
    u1.groups.add(g)
    u2.groups.add(g)
    count = notify_group(role_code="QA_TEAM", title="COA hazır",
                          message="Onay bekliyor.",
                          level=Notification.Level.TASK)
    assert count == 2
    assert Notification.objects.filter(recipient__in=[u1, u2]).count() == 2


def test_notify_group_missing_role_returns_zero():
    assert notify_group(role_code="NONEXISTENT", title="X") == 0


def test_inbox_view(client):
    u = User.objects.create_user("inbox_user", password="pw")
    client.login(username="inbox_user", password="pw")
    notify(recipient=u, title="Test bildirim")
    resp = client.get(reverse("notifications:inbox"))
    assert resp.status_code == 200
    assert b"Test bildirim" in resp.content


def test_mark_read_view_marks_and_redirects(client):
    u = User.objects.create_user("mr_user", password="pw")
    client.login(username="mr_user", password="pw")
    n = notify(recipient=u, title="X")
    resp = client.post(reverse("notifications:mark_read", args=[n.pk]))
    assert resp.status_code in (301, 302)
    n.refresh_from_db()
    assert n.is_read is True


def test_cannot_mark_others_notification_read(client):
    owner = User.objects.create_user("owner", password="pw")
    other = User.objects.create_user("other", password="pw")
    n = notify(recipient=owner, title="Gizli")
    client.login(username="other", password="pw")
    resp = client.post(reverse("notifications:mark_read", args=[n.pk]))
    assert resp.status_code == 404

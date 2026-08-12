"""Inbox sayfası — kullanıcının okunmamış + tüm bildirimleri."""
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Notification
from .services import mark_read


@login_required
def inbox(request: HttpRequest) -> HttpResponse:
    only_unread = request.GET.get("filter") == "unread"
    qs = Notification.objects.filter(recipient=request.user)
    if only_unread:
        qs = qs.filter(is_read=False)
    qs = qs[:200]
    return render(request, "notifications/inbox.html", {
        "notifications": qs,
        "only_unread": only_unread,
        "unread_count": Notification.objects.filter(
            recipient=request.user, is_read=False).count(),
    })


@login_required
@require_POST
def mark_read_view(request: HttpRequest, pk: int) -> HttpResponse:
    n = get_object_or_404(Notification, pk=pk, recipient=request.user)
    mark_read(n)
    if n.action_url:
        return redirect(n.action_url)
    return redirect("notifications:inbox")

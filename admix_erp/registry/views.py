"""Registry portal views — 271 kontrollü kod listesi + detay."""
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from .models import ControlledCode


def _has_registry_perm(request):
    if request.user.is_superuser:
        return
    if not request.user.has_perm("registry.view_controlledcode"):
        raise PermissionDenied("Registry görme yetkiniz yok.")


@login_required
def registry_list(request: HttpRequest) -> HttpResponse:
    _has_registry_perm(request)

    qs = ControlledCode.objects.filter(is_active=True).order_by(
        "function", "type", "full_code")

    q = request.GET.get("q", "").strip()
    fn = request.GET.get("function", "")
    tp = request.GET.get("type", "")
    lv = request.GET.get("level", "")
    st = request.GET.get("status", "")

    if q:
        qs = qs.filter(
            Q(full_code__icontains=q) | Q(short_alias__icontains=q) |
            Q(title__icontains=q) | Q(owner_role__icontains=q)
        )
    if fn:
        qs = qs.filter(function=fn)
    if tp:
        qs = qs.filter(type=tp)
    if lv:
        qs = qs.filter(level=lv)
    if st:
        qs = qs.filter(status=st)

    page = Paginator(qs, 50).get_page(request.GET.get("page"))

    # Filtre seçenekleri (dinamik — sadece mevcut değerler)
    functions = ControlledCode.objects.values_list(
        "function", flat=True).distinct().order_by("function")
    types = ControlledCode.objects.values_list(
        "type", flat=True).distinct().order_by("type")
    levels = ControlledCode.objects.values_list(
        "level", flat=True).distinct().order_by("level")

    return render(request, "registry/list.html", {
        "page": page,
        "q": q, "fn": fn, "tp": tp, "lv": lv, "st": st,
        "functions": functions,
        "types": types,
        "levels": levels,
        "function_labels": dict(ControlledCode.Function.choices),
        "type_labels": dict(ControlledCode.Type.choices),
        "level_labels": dict(ControlledCode.Level.choices),
        "status_labels": dict(ControlledCode.Status.choices),
        "total_codes": ControlledCode.objects.count(),
        "filtered_count": qs.count(),
        "current": "portal:registry_list",
    })


@login_required
def registry_detail(request: HttpRequest, pk: int) -> HttpResponse:
    _has_registry_perm(request)
    code = get_object_or_404(ControlledCode.objects.prefetch_related(
        "revisions", "business_lines"), pk=pk)
    return render(request, "registry/detail.html", {
        "code": code,
        "current": "portal:registry_list",
    })

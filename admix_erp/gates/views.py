"""Gates portal views — 8-Part Gate liste + detay (renkli kart)."""
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from .models import Gate


def _perm_or_403(request, perm: str) -> None:
    if request.user.is_superuser:
        return
    if not request.user.has_perm(perm):
        raise PermissionDenied(f"Bu sayfa için '{perm}' izni gerekli.")


@login_required
def gate_list(request: HttpRequest) -> HttpResponse:
    _perm_or_403(request, "gates.view_gate")

    qs = Gate.objects.select_related("case", "owner", "business_line",
                                       "closed_by").order_by("-opened_at")
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    if q:
        qs = qs.filter(Q(gate_id__icontains=q) | Q(scope__icontains=q) |
                       Q(case__case_id__icontains=q))
    if status:
        qs = qs.filter(status=status)

    page = Paginator(qs, 30).get_page(request.GET.get("page"))
    return render(request, "gates/list.html", {
        "page": page, "q": q, "status": status,
        "statuses": Gate.Status.choices,
        "total": Gate.objects.count(),
        "filtered": qs.count(),
        "current": "portal:gate_list",
    })


@login_required
def gate_detail(request: HttpRequest, gate_id: str) -> HttpResponse:
    _perm_or_403(request, "gates.view_gate")
    gate = get_object_or_404(
        Gate.objects.select_related("case", "owner", "business_line",
                                      "closed_by")
                    .prefetch_related("sections__evidence",
                                       "sections__reviewer"),
        gate_id=gate_id,
    )
    # 8 bölümü sırayla göster (enum sırası ile)
    section_order = {s: i for i, s in enumerate(Gate.ALL_SECTIONS)}
    sections = sorted(gate.sections.all(),
                       key=lambda s: section_order.get(s.section, 99))
    return render(request, "gates/detail.html", {
        "gate": gate,
        "sections": sections,
        "current": "portal:gate_list",
    })

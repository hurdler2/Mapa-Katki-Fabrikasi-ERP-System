"""Rules portal views — 12 kural + ihlal listesi + resolution."""
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import RULE_TITLES, RuleViolation


def _perm_or_403(request, perm: str) -> None:
    if request.user.is_superuser:
        return
    if not request.user.has_perm(perm):
        raise PermissionDenied(f"Bu sayfa için '{perm}' izni gerekli.")


@login_required
def violation_list(request: HttpRequest) -> HttpResponse:
    _perm_or_403(request, "rules.view_ruleviolation")

    qs = RuleViolation.objects.select_related("user").order_by("-created_at")

    q = request.GET.get("q", "").strip()
    rule = request.GET.get("rule", "")
    blocked = request.GET.get("blocked", "")
    resolved = request.GET.get("resolved", "")

    if q:
        qs = qs.filter(Q(reason__icontains=q) | Q(target_repr__icontains=q) |
                       Q(target_model__icontains=q))
    if rule:
        qs = qs.filter(rule_no=int(rule))
    if blocked in ("1", "0"):
        qs = qs.filter(blocked=blocked == "1")
    if resolved in ("1", "0"):
        qs = qs.filter(resolved=resolved == "1")

    # KPI özet
    all_v = RuleViolation.objects.all()
    kpi_total = all_v.count()
    kpi_blocked = all_v.filter(blocked=True, resolved=False).count()
    kpi_last_7d = all_v.filter(
        created_at__gte=timezone.now() - timezone.timedelta(days=7)).count()
    by_rule = list(all_v.values("rule_no").annotate(n=Count("id")).order_by("rule_no"))

    page = Paginator(qs, 30).get_page(request.GET.get("page"))
    return render(request, "rules/violation_list.html", {
        "page": page, "q": q, "rule": rule, "blocked": blocked, "resolved": resolved,
        "rule_titles": RULE_TITLES,
        "kpi_total": kpi_total,
        "kpi_blocked": kpi_blocked,
        "kpi_last_7d": kpi_last_7d,
        "by_rule": by_rule,
        "current": "portal:violation_list",
    })


@login_required
def violation_resolve(request: HttpRequest, pk: int) -> HttpResponse:
    _perm_or_403(request, "rules.change_ruleviolation")
    v = get_object_or_404(RuleViolation, pk=pk)
    if request.method == "POST":
        note = request.POST.get("note", "").strip()
        v.resolved = True
        v.resolution_note = note
        v.save(update_fields=["resolved", "resolution_note", "updated_at"])
    return redirect("portal:violation_list")


@login_required
def rules_catalog(request: HttpRequest) -> HttpResponse:
    """12 kuralı bir referans sayfada gösterir."""
    _perm_or_403(request, "rules.view_ruleviolation")
    counts = {r["rule_no"]: r["n"] for r in
              RuleViolation.objects.values("rule_no").annotate(n=Count("id"))}
    rules = [(k, RULE_TITLES[k], counts.get(k, 0))
             for k in sorted(RULE_TITLES)]
    return render(request, "rules/catalog.html", {
        "rules": rules,
        "current": "portal:rules_catalog",
    })

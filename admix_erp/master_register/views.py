"""Master Register portal views — KPI + integrated + security listeleri."""
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from .models import IntegratedEventRegister, SecurityEventRegister
from .services import snapshot_chain_integrated


def _perm_or_403(request, perm: str) -> None:
    if request.user.is_superuser:
        return
    if not request.user.has_perm(perm):
        raise PermissionDenied(f"Bu sayfa için '{perm}' izni gerekli.")


@login_required
def integrated_list(request: HttpRequest) -> HttpResponse:
    _perm_or_403(request, "master_register.view_integratedeventregister")

    qs = (IntegratedEventRegister.objects
          .filter(is_snapshot=False)
          .select_related("case", "owner")
          .order_by("-detection_date"))

    q = request.GET.get("q", "").strip()
    family = request.GET.get("family", "")
    status = request.GET.get("status", "")
    hold = request.GET.get("hold", "")

    if q:
        qs = qs.filter(Q(event_id__icontains=q) | Q(site_process__icontains=q) |
                       Q(scope_summary__icontains=q))
    if family:
        qs = qs.filter(family=family)
    if status:
        qs = qs.filter(status=status)
    if hold == "1":
        qs = qs.filter(hold_flag=True)

    # KPI'lar (üst yönetim özeti)
    all_active = IntegratedEventRegister.objects.filter(is_snapshot=False)
    kpi_open = all_active.exclude(status=IntegratedEventRegister.Status.CLOSED).count()
    kpi_hold = all_active.filter(hold_flag=True).count()
    kpi_closed_30d = all_active.filter(
        status=IntegratedEventRegister.Status.CLOSED).count()
    kpi_repeat = all_active.exclude(recurrence_code__in=("", "R0")).count()

    page = Paginator(qs, 30).get_page(request.GET.get("page"))
    return render(request, "master_register/integrated_list.html", {
        "page": page, "q": q, "family": family, "status": status, "hold": hold,
        "families": IntegratedEventRegister.Family.choices,
        "statuses": IntegratedEventRegister.Status.choices,
        "kpi_open": kpi_open,
        "kpi_hold": kpi_hold,
        "kpi_closed": kpi_closed_30d,
        "kpi_repeat": kpi_repeat,
        "current": "portal:master_integrated_list",
    })


@login_required
def integrated_detail(request: HttpRequest, event_id: str) -> HttpResponse:
    _perm_or_403(request, "master_register.view_integratedeventregister")
    active = get_object_or_404(
        IntegratedEventRegister,
        event_id=event_id, is_snapshot=False,
    )
    chain = snapshot_chain_integrated(active)
    return render(request, "master_register/integrated_detail.html", {
        "entry": active,
        "chain": chain,
        "chain_count": len(chain),
        "current": "portal:master_integrated_list",
    })


@login_required
def security_list(request: HttpRequest) -> HttpResponse:
    _perm_or_403(request, "master_register.view_securityeventregister")

    qs = (SecurityEventRegister.objects
          .filter(is_snapshot=False)
          .select_related("case", "owner")
          .order_by("-detection_datetime"))

    q = request.GET.get("q", "").strip()
    severity = request.GET.get("severity", "")
    current_status = request.GET.get("status", "")
    escalation = request.GET.get("escalation", "")

    if q:
        qs = qs.filter(Q(incident_id__icontains=q) |
                       Q(affected_asset__icontains=q) |
                       Q(scope_impact_summary__icontains=q))
    if severity:
        qs = qs.filter(severity=severity)
    if current_status:
        qs = qs.filter(current_status=current_status)
    if escalation:
        qs = qs.filter(escalation_status=escalation)

    active = SecurityEventRegister.objects.filter(is_snapshot=False)
    kpi_open = active.exclude(current_status=SecurityEventRegister.CurrentStatus.CLOSED).count()
    kpi_sev1 = active.filter(severity=SecurityEventRegister.Severity.SEV1).count()
    kpi_breach = active.filter(escalation_status=SecurityEventRegister.EscalationStatus.BREACH).count()

    page = Paginator(qs, 30).get_page(request.GET.get("page"))
    return render(request, "master_register/security_list.html", {
        "page": page, "q": q, "severity": severity,
        "current_status": current_status, "escalation": escalation,
        "severities": SecurityEventRegister.Severity.choices,
        "statuses": SecurityEventRegister.CurrentStatus.choices,
        "escalations": SecurityEventRegister.EscalationStatus.choices,
        "kpi_open": kpi_open,
        "kpi_sev1": kpi_sev1,
        "kpi_breach": kpi_breach,
        "current": "portal:master_security_list",
    })

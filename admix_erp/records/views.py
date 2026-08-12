"""Records portal views — Case / RecordInstance / Decision liste + detay."""
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from .models import Case, Decision, RecordInstance


def _perm_or_403(request, perm: str) -> None:
    if request.user.is_superuser:
        return
    if not request.user.has_perm(perm):
        raise PermissionDenied(f"Bu sayfa için '{perm}' izni gerekli.")


# ---------------------------------------------------------------------------
# Case
# ---------------------------------------------------------------------------

@login_required
def case_list(request: HttpRequest) -> HttpResponse:
    _perm_or_403(request, "records.view_case")

    qs = Case.objects.select_related("business_line", "detected_by").annotate(
        n_records=Count("records", distinct=True),
        n_decisions=Count("decisions", distinct=True),
    ).order_by("-detected_at")

    q = request.GET.get("q", "").strip()
    family = request.GET.get("family", "")
    status = request.GET.get("status", "")
    severity = request.GET.get("severity", "")

    if q:
        qs = qs.filter(Q(case_id__icontains=q) | Q(title__icontains=q) |
                       Q(description__icontains=q))
    if family:
        qs = qs.filter(family=family)
    if status:
        qs = qs.filter(status=status)
    if severity:
        qs = qs.filter(severity=severity)

    page = Paginator(qs, 30).get_page(request.GET.get("page"))
    return render(request, "records/case_list.html", {
        "page": page, "q": q, "family": family, "status": status, "severity": severity,
        "families": Case.Family.choices,
        "statuses": Case.Status.choices,
        "severities": Case.Severity.choices,
        "total": Case.objects.count(),
        "filtered": qs.count(),
        "current": "portal:case_list",
    })


@login_required
def case_detail(request: HttpRequest, case_id: str) -> HttpResponse:
    _perm_or_403(request, "records.view_case")
    case = get_object_or_404(
        Case.objects.select_related("business_line", "detected_by")
                    .prefetch_related("records__controlled_code",
                                       "evidence_set",
                                       "decisions__decision_maker",
                                       "decisions__signatures"),
        case_id=case_id,
    )
    return render(request, "records/case_detail.html", {
        "case": case,
        "records": case.records.all(),
        "evidence_list": case.evidence_set.all(),
        "decisions": case.decisions.all(),
        "current": "portal:case_list",
    })


# ---------------------------------------------------------------------------
# RecordInstance
# ---------------------------------------------------------------------------

@login_required
def record_detail(request: HttpRequest, record_id: str) -> HttpResponse:
    _perm_or_403(request, "records.view_recordinstance")
    rec = get_object_or_404(
        RecordInstance.objects.select_related(
            "controlled_code", "case", "preparer", "reviewer", "approver"),
        record_id=record_id,
    )
    return render(request, "records/record_detail.html", {
        "record": rec, "current": "portal:case_list",
    })


# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------

@login_required
def decision_detail(request: HttpRequest, decision_id: str) -> HttpResponse:
    _perm_or_403(request, "records.view_decision")
    d = get_object_or_404(
        Decision.objects.select_related("case", "decision_maker", "record_instance")
                        .prefetch_related("independent_reviewers",
                                           "evidence_reviewed", "signatures"),
        decision_id=decision_id,
    )
    return render(request, "records/decision_detail.html", {
        "decision": d, "current": "portal:case_list",
    })

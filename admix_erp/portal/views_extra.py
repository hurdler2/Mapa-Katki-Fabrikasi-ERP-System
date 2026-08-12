"""Onay bekleyenler + basit liste sayfaları (recipes, ncr, capa, coa, ...).

Bu sayfalar Django Admin'e link vermek yerine kendi UI'ı sunar.
Admin'e link vermek yerine kayda tıklandığında portal detay sayfası açar.
"""
from __future__ import annotations

import datetime as dt

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST


# Registry portal wrapper'ları — Faz C UI
@login_required
def registry_list_view(request: HttpRequest) -> HttpResponse:
    from registry.views import registry_list
    return registry_list(request)


@login_required
def registry_detail_view(request: HttpRequest, pk: int) -> HttpResponse:
    from registry.views import registry_detail
    return registry_detail(request, pk)


# Records portal wrapper'ları — Faz D UI (5-Katman ID Modeli)
@login_required
def case_list_view(request: HttpRequest) -> HttpResponse:
    from records.views import case_list
    return case_list(request)


@login_required
def case_detail_view(request: HttpRequest, case_id: str) -> HttpResponse:
    from records.views import case_detail
    return case_detail(request, case_id)


@login_required
def record_detail_view(request: HttpRequest, record_id: str) -> HttpResponse:
    from records.views import record_detail
    return record_detail(request, record_id)


@login_required
def decision_detail_view(request: HttpRequest, decision_id: str) -> HttpResponse:
    from records.views import decision_detail
    return decision_detail(request, decision_id)


@login_required
@require_POST
def switch_business_line(request: HttpRequest) -> HttpResponse:
    """Session'daki aktif BL'i değiştirir. POST body: bl_code=MCS/MPT/MFT/MLTS/''"""
    from businessline.services import (
        business_lines_for, set_active_bl_code,
    )
    code = (request.POST.get("bl_code") or "").strip().upper()
    if code == "":
        set_active_bl_code(request, None)
        messages.info(request, "İş kolu filtresi kaldırıldı (tümü).")
    else:
        allowed = business_lines_for(request.user).filter(code=code).first()
        if allowed is None:
            messages.error(request, f"{code} iş koluna erişim yetkiniz yok.")
        else:
            set_active_bl_code(request, code)
            messages.success(request, f"Aktif iş kolu: {allowed.name}")
    return redirect(request.META.get("HTTP_REFERER", "/portal/"))


def _has_perm(request, *perms):
    if request.user.is_superuser:
        return
    if not all(request.user.has_perm(p) for p in perms):
        raise PermissionDenied("Bu sayfa için gerekli izne sahip değilsiniz.")


# ---------------------------------------------------------------------------
# Onay bekleyenler
# ---------------------------------------------------------------------------

@login_required
def approvals_inbox(request: HttpRequest) -> HttpResponse:
    from .services import approvals_for_user
    qs = approvals_for_user(request.user).select_related("requested_by")

    my_requests = None
    if not request.user.is_superuser:
        from .models import ApprovalRequest
        my_requests = ApprovalRequest.objects.filter(
            requested_by=request.user
        ).order_by("-created_at")[:15]

    return render(request, "portal/approvals/inbox.html", {
        "pending": qs,
        "my_requests": my_requests,
    })


@login_required
def approval_decide(request: HttpRequest, pk: int) -> HttpResponse:
    from .models import ApprovalRequest
    from .services import approve, reject

    ar = get_object_or_404(ApprovalRequest, pk=pk)
    if request.method == "POST":
        action = request.POST.get("action")
        reason = request.POST.get("reason", "")
        try:
            if action == "approve":
                approve(ar, user=request.user, reason=reason)
                messages.success(request, f"Talep onaylandı: {ar.title}")
            elif action == "reject":
                reject(ar, user=request.user, reason=reason)
                messages.success(request, f"Talep reddedildi: {ar.title}")
        except Exception as e:
            messages.error(request, f"İşlem başarısız: {e}")
        return redirect("portal:approvals_inbox")

    return render(request, "portal/approvals/decide.html", {"ar": ar})


# ---------------------------------------------------------------------------
# Liste sayfaları (admin yerine portal içinde)
# ---------------------------------------------------------------------------

@login_required
def recipes_list(request: HttpRequest) -> HttpResponse:
    _has_perm(request, "formulation.view_recipe")
    from formulation.models import Recipe
    qs = Recipe.objects.select_related("product", "unit").order_by("product__code", "-version")
    return render(request, "portal/lists/recipes.html", {
        "recipes": qs, "current": "portal:recipes",
    })


@login_required
def qc_results_list(request: HttpRequest) -> HttpResponse:
    _has_perm(request, "quality.view_qctestresult")
    from quality.models import QCTestResult
    qs = QCTestResult.objects.select_related("parameter", "lot", "batch").order_by("-tested_at")
    page = Paginator(qs, 30).get_page(request.GET.get("page"))
    return render(request, "portal/lists/qc_results.html", {
        "page": page, "current": "portal:qc_results",
    })


@login_required
def coa_list(request: HttpRequest) -> HttpResponse:
    _has_perm(request, "quality.view_certificateofanalysis")
    from quality.models import CertificateOfAnalysis
    qs = CertificateOfAnalysis.objects.select_related("batch__recipe__product").order_by("-created_at")
    return render(request, "portal/lists/coas.html", {
        "coas": qs, "current": "portal:coa_list",
    })


@login_required
def ncr_list(request: HttpRequest) -> HttpResponse:
    _has_perm(request, "qms.view_nonconformance")
    from qms.models import Nonconformance
    qs = Nonconformance.objects.select_related("detected_by", "closed_by").order_by("-detected_at")
    page = Paginator(qs, 30).get_page(request.GET.get("page"))
    return render(request, "portal/lists/ncr.html", {
        "page": page, "current": "portal:ncr_list",
    })


@login_required
def capa_list(request: HttpRequest) -> HttpResponse:
    _has_perm(request, "qms.view_capa")
    from qms.models import CAPA
    qs = CAPA.objects.select_related("owner").order_by("-opened_at")
    page = Paginator(qs, 30).get_page(request.GET.get("page"))
    return render(request, "portal/lists/capa.html", {
        "page": page, "current": "portal:capa_list",
    })


@login_required
def documents_list(request: HttpRequest) -> HttpResponse:
    _has_perm(request, "docs.view_controlleddocument")
    from docs.models import ControlledDocument
    qs = ControlledDocument.objects.select_related("category", "process_owner").order_by("document_number")
    return render(request, "portal/lists/documents.html", {
        "docs": qs, "current": "portal:documents",
    })


@login_required
def internal_audits(request: HttpRequest) -> HttpResponse:
    _has_perm(request, "governance.view_internalaudit")
    from governance.models import InternalAudit
    qs = InternalAudit.objects.select_related("plan", "lead_auditor").order_by("-scheduled_date")
    return render(request, "portal/lists/audits.html", {
        "audits": qs, "current": "portal:internal_audits",
    })


@login_required
def mgmt_reviews(request: HttpRequest) -> HttpResponse:
    _has_perm(request, "governance.view_managementreview")
    from governance.models import ManagementReview
    qs = ManagementReview.objects.select_related("chairperson").order_by("-meeting_date")
    return render(request, "portal/lists/mgmt_reviews.html", {
        "reviews": qs, "current": "portal:mgmt_reviews",
    })


@login_required
def lots_list(request: HttpRequest) -> HttpResponse:
    _has_perm(request, "inventory.view_rawmateriallot")
    from inventory.models import RawMaterialLot
    qs = RawMaterialLot.objects.select_related("raw_material", "supplier").order_by("-received_date")
    status_f = request.GET.get("status", "")
    if status_f:
        qs = qs.filter(qc_status=status_f)
    page = Paginator(qs, 30).get_page(request.GET.get("page"))
    return render(request, "portal/lists/lots.html", {
        "page": page, "status_f": status_f, "current": "portal:lots_list",
    })


@login_required
def suppliers_list(request: HttpRequest) -> HttpResponse:
    _has_perm(request, "masterdata.view_supplier")
    from masterdata.models import Supplier
    qs = Supplier.objects.order_by("code")
    return render(request, "portal/lists/suppliers.html", {
        "suppliers": qs, "current": "portal:suppliers",
    })


@login_required
def equipment_list(request: HttpRequest) -> HttpResponse:
    _has_perm(request, "cmms.view_equipment")
    from cmms.models import Equipment
    qs = Equipment.objects.order_by("equipment_number")
    return render(request, "portal/lists/equipment.html", {
        "items": qs, "current": "portal:equipment_list",
    })


@login_required
def incident_new(request: HttpRequest) -> HttpResponse:
    _has_perm(request, "ehs.add_incident")
    from ehs.models import Incident
    from ehs.services import report_incident
    from django.utils import timezone

    if request.method == "POST":
        try:
            inc = report_incident(
                incident_number=request.POST["incident_number"].strip(),
                type=request.POST["type"],
                occurred_at=timezone.now(),
                location=request.POST["location"],
                description=request.POST["description"],
                reported_by=request.user,
                severity=request.POST.get("severity", "MINOR"),
            )
            messages.success(request, f"Olay {inc.incident_number} kaydedildi.")
            return redirect("portal:ehs")
        except Exception as e:
            messages.error(request, f"Kayıt başarısız: {e}")

    return render(request, "portal/lists/incident_new.html", {
        "current": "portal:incident_new",
        "types": Incident.Type.choices,
        "severities": Incident.Severity.choices,
    })


@login_required
def trial_balance_view(request: HttpRequest) -> HttpResponse:
    _has_perm(request, "accounting.view_account")
    return redirect("/accounting/balance/")


# ---------------------------------------------------------------------------
# Kullanıcı yönetimi (IT_ADMIN only)
# ---------------------------------------------------------------------------

def _is_it_admin(user):
    return user.is_superuser or user.groups.filter(name="IT_ADMIN").exists()


@login_required
@user_passes_test(_is_it_admin)
def user_admin(request: HttpRequest) -> HttpResponse:
    from iam.models import Role
    users = User.objects.prefetch_related("groups").order_by("-date_joined")
    return render(request, "portal/it_admin/users.html", {
        "users": users, "current": "portal:user_admin",
        "role_labels": Role.LABELS,
    })

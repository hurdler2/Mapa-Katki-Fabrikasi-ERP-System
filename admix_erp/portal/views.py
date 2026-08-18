"""Portal views — rol tabanlı dispatcher + rol başına dashboard."""
from __future__ import annotations

import datetime as dt
import json
from collections import defaultdict
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone


def _primary_role(user):
    groups = list(user.groups.values_list("name", flat=True))
    if user.is_superuser:
        return "IT_ADMIN"
    if not groups:
        return None
    priority = [
        "IT_ADMIN",
        "GENERAL_MANAGER", "TECHNICAL_MANAGER",
        "OPERATIONS_MANAGER", "IMS_QA_MANAGER", "ACCOUNTING_MANAGER",
        "LAB_QC", "OPERATIONS_SUPERVISOR",
        "WAREHOUSE", "PURCHASING",
    ]
    for r in priority:
        if r in groups:
            return r
    return groups[0]


@login_required
def home(request: HttpRequest) -> HttpResponse:
    """Kullanıcının rolüne göre uygun ana panoya yönlendir."""
    role = _primary_role(request.user)
    # Yeni org yapısı → route
    routes = {
        "IT_ADMIN":              "portal:user_admin",
        "GENERAL_MANAGER":       "portal:management",
        "TECHNICAL_MANAGER":     "portal:production",
        "OPERATIONS_MANAGER":    "portal:production",
        "IMS_QA_MANAGER":        "portal:quality",
        "ACCOUNTING_MANAGER":    "portal:accounting",
        "LAB_QC":                "portal:quality",
        "OPERATIONS_SUPERVISOR": "portal:production",
        "WAREHOUSE":             "portal:warehouse",
        "PURCHASING":            "portal:purchasing",
        # MCOS Faz B — 6 yeni rol landing
        "RDT_ENGINEER":          "portal:recipes",             # RDT ürün geliştirme
        "MLTS_ANALYST":          "portal:quality",             # Kalite lab (MLTS BL)
        "HSE_OFFICER":           "portal:ehs",                 # EHS panosu
        "INTERNAL_AUDITOR":      "portal:internal_audits",     # İç tetkik listesi
        "MAINTENANCE_TECH":      "portal:maintenance",         # CMMS
        "COMMERCIAL_ENG":        "portal:case_list",           # Şikayet/müşteri case'leri
    }
    if role and role in routes:
        return redirect(routes[role])
    return render(request, "portal/no_role.html")


def _require_role(user, *roles):
    """Sadece geriye uyumluluk için — yeni view'lar _has_perm kullanmalı."""
    if user.is_superuser:
        return
    if not user.groups.filter(name__in=roles).exists():
        raise PermissionDenied(
            f"Bu sayfaya erişim için şu rollerden birine sahip olmalısınız: {', '.join(roles)}"
        )


def _has_perm(request, *perms):
    """Django permission tabanlı erişim kontrolü (menu.py ile aynı kaynak)."""
    if request.user.is_superuser:
        return
    if not all(request.user.has_perm(p) for p in perms):
        raise PermissionDenied(
            "Bu sayfa için gerekli izne sahip değilsiniz."
        )


def _notif_ctx(user):
    from notifications.models import Notification
    return {"unread_count": Notification.objects.filter(recipient=user, is_read=False).count()}


# ---------------------------------------------------------------------------
# MUHASEBE PORTALI (grafikli, tam CRUD)
# ---------------------------------------------------------------------------

@login_required
def accounting_dashboard(request: HttpRequest) -> HttpResponse:
    _has_perm(request, "accounting.view_invoice")

    from accounting.models import Invoice, JournalEntry, Payment, TVADeclaration

    today = dt.date.today()
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    # ---- KPI'lar (bu ay) ----
    month_invoices = Invoice.objects.filter(date__gte=month_start)
    sales_this_month = month_invoices.filter(
        type=Invoice.Type.SALES
    ).aggregate(t=Sum("total_ttc"))["t"] or Decimal("0")
    purchases_this_month = month_invoices.filter(
        type=Invoice.Type.PURCHASE
    ).aggregate(t=Sum("total_ttc"))["t"] or Decimal("0")

    # Yıllık toplamlar (kar marjı için)
    sales_ytd = Invoice.objects.filter(
        type=Invoice.Type.SALES, date__gte=year_start
    ).aggregate(t=Sum("total_ttc"))["t"] or Decimal("0")
    purchases_ytd = Invoice.objects.filter(
        type=Invoice.Type.PURCHASE, date__gte=year_start
    ).aggregate(t=Sum("total_ttc"))["t"] or Decimal("0")
    margin_pct = 0
    if sales_ytd > 0:
        margin_pct = float(((sales_ytd - purchases_ytd) / sales_ytd) * 100)

    tva_collected = month_invoices.filter(
        type=Invoice.Type.SALES,
        status__in=[Invoice.Status.POSTED, Invoice.Status.PAID,
                    Invoice.Status.PARTIALLY_PAID],
    ).aggregate(t=Sum("total_tva"))["t"] or Decimal("0")
    tva_deductible = month_invoices.filter(
        type=Invoice.Type.PURCHASE,
        status__in=[Invoice.Status.POSTED, Invoice.Status.PAID,
                    Invoice.Status.PARTIALLY_PAID],
    ).aggregate(t=Sum("total_tva"))["t"] or Decimal("0")

    # Açık alacak/borç (net)
    ar_invs = Invoice.objects.filter(
        type=Invoice.Type.SALES,
        status__in=[Invoice.Status.POSTED, Invoice.Status.PARTIALLY_PAID],
    )
    open_ar = sum((i.amount_due for i in ar_invs), Decimal("0"))
    ap_invs = Invoice.objects.filter(
        type=Invoice.Type.PURCHASE,
        status__in=[Invoice.Status.POSTED, Invoice.Status.PARTIALLY_PAID],
    )
    open_ap = sum((i.amount_due for i in ap_invs), Decimal("0"))

    # ---- Aylık trend (son 12 ay, satış vs alım) ----
    trend = []
    for i in range(11, -1, -1):
        y, m = today.year, today.month - i
        while m <= 0:
            m += 12; y -= 1
        ms = dt.date(y, m, 1)
        me = (dt.date(y + (m // 12), (m % 12) + 1, 1) - dt.timedelta(days=1))
        sale = Invoice.objects.filter(
            type=Invoice.Type.SALES, date__gte=ms, date__lte=me
        ).aggregate(t=Sum("total_ttc"))["t"] or Decimal("0")
        buy = Invoice.objects.filter(
            type=Invoice.Type.PURCHASE, date__gte=ms, date__lte=me
        ).aggregate(t=Sum("total_ttc"))["t"] or Decimal("0")
        trend.append({
            "month": f"{y}-{m:02d}",
            "sales": float(sale),
            "purchases": float(buy),
            "net": float(sale - buy),
        })

    # ---- Ödeme yöntemi dağılımı (yıllık) ----
    payment_methods = list(
        Payment.objects.filter(date__gte=year_start)
        .values("method")
        .annotate(total=Sum("amount"), n=Count("id"))
        .order_by("-total")
    )
    method_labels = dict(Payment.Method.choices)
    payment_methods_chart = [{
        "label": method_labels.get(m["method"], m["method"]),
        "total": float(m["total"] or 0),
        "count": m["n"],
    } for m in payment_methods]

    # ---- Alacak yaşlanması (aging bucket) ----
    ar_open = list(Invoice.objects.filter(
        type=Invoice.Type.SALES,
        status__in=[Invoice.Status.POSTED, Invoice.Status.PARTIALLY_PAID],
    ).select_related("customer"))
    aging = {"0-30": 0.0, "31-60": 0.0, "61-90": 0.0, "90+": 0.0}
    for inv in ar_open:
        due = inv.due_date or inv.date
        days = (today - due).days
        amt = float(inv.amount_due)
        if days < 31:   aging["0-30"] += amt
        elif days < 61: aging["31-60"] += amt
        elif days < 91: aging["61-90"] += amt
        else:           aging["90+"] += amt

    # ---- Vadesi geçmiş faturalar (top 10) ----
    overdue = []
    for inv in ar_open:
        due = inv.due_date or inv.date
        if due < today:
            overdue.append({
                "invoice_number": inv.invoice_number,
                "pk": inv.pk,
                "customer": inv.customer.name if inv.customer else "—",
                "due": due,
                "days_overdue": (today - due).days,
                "amount_due": inv.amount_due,
            })
    overdue.sort(key=lambda x: -x["days_overdue"])
    overdue = overdue[:10]

    # ---- Vadesi yaklaşan çekler (30 gün içinde) ----
    upcoming_checks = list(Payment.objects.filter(
        method=Payment.Method.CHECK,
        check_status__in=[Payment.CheckStatus.ISSUED, Payment.CheckStatus.DEPOSITED],
        check_due_date__isnull=False,
        check_due_date__gte=today,
        check_due_date__lte=today + dt.timedelta(days=30),
    ).order_by("check_due_date")[:10])

    # ---- Top 5 müşteri (yıllık) ----
    top_customers = list(
        Invoice.objects.filter(
            type=Invoice.Type.SALES, date__gte=year_start,
            customer__isnull=False,
        )
        .values("customer__name")
        .annotate(total=Sum("total_ttc"), n=Count("id"))
        .order_by("-total")[:5]
    )

    # ---- TVA aylık trend (son 6 ay) ----
    tva_trend = []
    for i in range(5, -1, -1):
        y, m = today.year, today.month - i
        while m <= 0:
            m += 12; y -= 1
        ms = dt.date(y, m, 1)
        me = (dt.date(y + (m // 12), (m % 12) + 1, 1) - dt.timedelta(days=1))
        col = Invoice.objects.filter(
            type=Invoice.Type.SALES, date__gte=ms, date__lte=me,
            status__in=[Invoice.Status.POSTED, Invoice.Status.PAID, Invoice.Status.PARTIALLY_PAID],
        ).aggregate(t=Sum("total_tva"))["t"] or Decimal("0")
        ded = Invoice.objects.filter(
            type=Invoice.Type.PURCHASE, date__gte=ms, date__lte=me,
            status__in=[Invoice.Status.POSTED, Invoice.Status.PAID, Invoice.Status.PARTIALLY_PAID],
        ).aggregate(t=Sum("total_tva"))["t"] or Decimal("0")
        tva_trend.append({
            "month": f"{y}-{m:02d}",
            "collected": float(col),
            "deductible": float(ded),
            "net": float(col - ded),
        })

    # ---- Fatura durum dağılımı ----
    status_dist = list(
        Invoice.objects.values("status").annotate(n=Count("id")).order_by()
    )
    status_labels = dict(Invoice.Status.choices)
    status_dist_chart = [{
        "label": status_labels.get(s["status"], s["status"]),
        "count": s["n"],
    } for s in status_dist]

    # ---- Son 15 fatura ----
    recent = Invoice.objects.select_related("customer", "supplier").order_by("-date", "-id")[:15]

    ctx = {
        "current": "home",
        "today": today,
        "sales_this_month": sales_this_month,
        "purchases_this_month": purchases_this_month,
        "net_result": sales_this_month - purchases_this_month,
        "sales_ytd": sales_ytd,
        "purchases_ytd": purchases_ytd,
        "margin_pct": round(margin_pct, 1),
        "tva_collected": tva_collected,
        "tva_deductible": tva_deductible,
        "tva_net": tva_collected - tva_deductible,
        "open_ar": open_ar,
        "open_ap": open_ap,
        "working_capital": open_ar - open_ap,
        "trend_json": json.dumps(trend),
        "payment_methods_json": json.dumps(payment_methods_chart),
        "aging_json": json.dumps(aging),
        "tva_trend_json": json.dumps(tva_trend),
        "status_dist_json": json.dumps(status_dist_chart),
        "top_customers_json": json.dumps(top_customers, default=str),
        "overdue_invoices": overdue,
        "upcoming_checks": upcoming_checks,
        "recent_invoices": recent,
        **_notif_ctx(request.user),
    }
    return render(request, "portal/accounting/dashboard.html", ctx)


@login_required
def accounting_invoices(request: HttpRequest) -> HttpResponse:
    _has_perm(request, "accounting.view_invoice")
    from accounting.models import Invoice

    qs = Invoice.objects.select_related("customer", "supplier").order_by("-date", "-id")
    type_f = request.GET.get("type", "")
    status_f = request.GET.get("status", "")
    search = request.GET.get("q", "").strip()
    if type_f:
        qs = qs.filter(type=type_f)
    if status_f:
        qs = qs.filter(status=status_f)
    if search:
        qs = qs.filter(
            Q(invoice_number__icontains=search)
            | Q(customer__name__icontains=search)
            | Q(supplier__name__icontains=search)
        )
    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    return render(request, "portal/accounting/invoices.html", {
        "current": "invoices", "page": page,
        "type_f": type_f, "status_f": status_f, "search": search,
        "type_choices": Invoice.Type.choices,
        "status_choices": Invoice.Status.choices,
        **_notif_ctx(request.user),
    })


@login_required
def accounting_invoice_new(request: HttpRequest) -> HttpResponse:
    _has_perm(request, "accounting.add_invoice")
    from accounting.models import Invoice, InvoiceLine, TVARate
    from accounting.services import get_or_create_period, recompute_invoice
    from masterdata.models import Customer, Supplier

    if request.method == "POST":
        try:
            data = request.POST
            inv_type = data.get("type")
            date = dt.date.fromisoformat(data.get("date"))
            period = get_or_create_period(date)
            tva = TVARate.objects.get(code=data.get("tva_rate"))
            partner_kwargs = {}
            if inv_type in ("SALES", "CN_SALES"):
                partner_kwargs["customer"] = Customer.objects.get(pk=int(data.get("customer")))
            else:
                partner_kwargs["supplier"] = Supplier.objects.get(pk=int(data.get("supplier")))

            inv = Invoice.objects.create(
                invoice_number=data.get("invoice_number"),
                type=inv_type, date=date, period=period,
                due_date=(dt.date.fromisoformat(data["due_date"]) if data.get("due_date") else None),
                notes=data.get("notes", ""),
                attachment=request.FILES.get("attachment"),
                attachment_note=data.get("attachment_note", ""),
                **partner_kwargs,
            )
            # Satırlar (basit: tek satır)
            InvoiceLine.objects.create(
                invoice=inv, sequence=1,
                description=data.get("line_description", "Ürün / hizmet"),
                quantity=Decimal(data.get("quantity", "1") or "1"),
                unit_price=Decimal(data.get("unit_price", "0") or "0"),
                tva_rate=tva,
            )
            recompute_invoice(inv)
            messages.success(request, f"Fatura {inv.invoice_number} taslak olarak kaydedildi.")
            return redirect("portal:accounting_invoice_detail", pk=inv.pk)
        except Exception as e:
            messages.error(request, f"Fatura kaydedilemedi: {e}")

    ctx = {
        "current": "invoices",
        "customers": Customer.objects.filter(is_active=True).order_by("name"),
        "suppliers": Supplier.objects.filter(is_active=True).order_by("name"),
        "tva_rates": TVARate.objects.filter(is_active=True),
        "today": dt.date.today().isoformat(),
        **_notif_ctx(request.user),
    }
    return render(request, "portal/accounting/invoice_new.html", ctx)


@login_required
def accounting_invoice_detail(request: HttpRequest, pk: int) -> HttpResponse:
    _has_perm(request, "accounting.view_invoice")
    from accounting.models import Invoice
    from accounting.services import post_invoice
    from portal.models import ApprovalRequest
    from portal.services import request_approval

    inv = get_object_or_404(Invoice.objects.select_related("customer", "supplier"), pk=pk)

    # Onay durumunu bul
    pending_approval = ApprovalRequest.objects.filter(
        content_type__model="invoice",
        object_id=inv.pk,
        kind=ApprovalRequest.Kind.INVOICE_POST,
        status=ApprovalRequest.Status.PENDING,
    ).first()

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "request_approval":
                # Muhasebeci onay talebi açar (Genel Müdür veya kendi müdürü)
                request_approval(
                    kind=ApprovalRequest.Kind.INVOICE_POST,
                    target=inv,
                    requested_by=request.user,
                    required_role="GENERAL_MANAGER",
                    title=f"Fatura post onayı: {inv.invoice_number}",
                    description=f"{inv.get_type_display()} · Tutar: {inv.total_ttc} DZD",
                )
                messages.success(request, "Genel Müdür onayına gönderildi.")
            elif action == "post_directly" and request.user.is_superuser:
                post_invoice(inv, user=request.user)
                messages.success(request, f"Fatura {inv.invoice_number} muhasebeleştirildi.")
            elif action == "upload_attachment":
                f = request.FILES.get("attachment")
                if f:
                    inv.attachment = f
                    inv.save(update_fields=["attachment", "updated_at"])
                    messages.success(request, "Fatura eki yüklendi.")
                else:
                    messages.error(request, "Dosya seçilmedi.")
        except Exception as e:
            messages.error(request, f"İşlem başarısız: {e}")
        return redirect("portal:accounting_invoice_detail", pk=pk)

    return render(request, "portal/accounting/invoice_detail.html", {
        "current": "invoices", "inv": inv,
        "pending_approval": pending_approval,
        **_notif_ctx(request.user),
    })


# ---------------------------------------------------------------------------
# ÜRETİM PORTALI
# ---------------------------------------------------------------------------

@login_required
def production_dashboard(request: HttpRequest) -> HttpResponse:
    _has_perm(request, "production.view_productionbatch")

    from formulation.models import Recipe
    from masterdata.models import Container
    from production.models import ProductionBatch, ProductionOrder

    today = dt.date.today()
    since_30 = today - dt.timedelta(days=30)

    active_batches = ProductionBatch.objects.filter(
        status__in=[ProductionBatch.Status.PLANNED,
                    ProductionBatch.Status.IN_PROGRESS,
                    ProductionBatch.Status.COMPLETED,
                    ProductionBatch.Status.QC_HOLD],
    ).select_related("recipe__product", "reactor").order_by("-created_at")[:20]

    planned = ProductionOrder.objects.filter(
        status__in=[ProductionOrder.Status.PLANNED, ProductionOrder.Status.RELEASED],
    ).select_related("product", "reactor").order_by("scheduled_date")[:10]

    reactors = Container.objects.filter(
        container_type=Container.ContainerType.REACTOR, is_active=True,
    )
    reactor_states = []
    for r in reactors:
        active = ProductionBatch.objects.filter(
            reactor=r,
            status__in=[ProductionBatch.Status.IN_PROGRESS,
                        ProductionBatch.Status.COMPLETED],
        ).first()
        reactor_states.append({
            "container": r, "active_batch": active,
            "busy": active is not None,
        })

    total_30 = ProductionBatch.objects.filter(created_at__date__gte=since_30).count()
    released_30 = ProductionBatch.objects.filter(
        created_at__date__gte=since_30,
        qc_status=ProductionBatch.QCStatus.RELEASED,
    ).count()

    return render(request, "portal/production/dashboard.html", {
        "current": "home",
        "active_batches": active_batches,
        "planned_orders": planned,
        "reactor_states": reactor_states,
        "total_30": total_30, "released_30": released_30,
        "recipes_count": Recipe.objects.filter(is_active=True).count(),
        **_notif_ctx(request.user),
    })


@login_required
def production_start_batch(request: HttpRequest) -> HttpResponse:
    _has_perm(request, "production.add_productionbatch")
    from production.models import ProductionOrder
    from production.services import create_batch_from_order

    if request.method == "POST":
        try:
            order = ProductionOrder.objects.get(pk=int(request.POST["order_id"]))
            batch_number = request.POST["batch_number"].strip()
            batch = create_batch_from_order(order, batch_number=batch_number)
            messages.success(request, f"Parti {batch.batch_number} oluşturuldu, hedef ağırlıklar hazır.")
            return redirect("portal:production")
        except Exception as e:
            messages.error(request, f"Parti oluşturulamadı: {e}")

    orders = ProductionOrder.objects.filter(
        status__in=[ProductionOrder.Status.PLANNED, ProductionOrder.Status.RELEASED],
    ).select_related("product", "reactor")

    n = ProductionOrder.objects.count() + 1
    suggested = f"BATCH-{dt.date.today().strftime('%Y%m%d')}-{n:03d}"

    return render(request, "portal/production/start_batch.html", {
        "current": "home", "orders": orders, "suggested": suggested,
        **_notif_ctx(request.user),
    })


# ---------------------------------------------------------------------------
# STOK / DEPO
# ---------------------------------------------------------------------------

@login_required
def warehouse_dashboard(request: HttpRequest) -> HttpResponse:
    _has_perm(request, "inventory.view_rawmateriallot")

    from chemicals.models import ShelfLifeAlert
    from inventory.models import RawMaterialLot

    lots_by_status = dict(
        RawMaterialLot.objects.filter(remaining_qty__gt=0)
        .values("qc_status").annotate(n=Count("id")).values_list("qc_status", "n")
    )
    pending_lots = RawMaterialLot.objects.filter(
        qc_status=RawMaterialLot.QCStatus.PENDING, remaining_qty__gt=0
    ).select_related("raw_material", "supplier").order_by("-received_date")[:15]

    released_lots = RawMaterialLot.objects.filter(
        qc_status=RawMaterialLot.QCStatus.RELEASED, remaining_qty__gt=0
    ).select_related("raw_material").order_by("expiry_date")[:15]

    alerts = ShelfLifeAlert.objects.filter(
        status=ShelfLifeAlert.Status.OPEN
    ).select_related("lot", "lot__raw_material").order_by("days_to_expiry")[:10]

    return render(request, "portal/warehouse/dashboard.html", {
        "current": "home",
        "lots_by_status": lots_by_status,
        "pending_lots": pending_lots,
        "released_lots": released_lots,
        "alerts": alerts,
        **_notif_ctx(request.user),
    })


@login_required
def warehouse_receipt_new(request: HttpRequest) -> HttpResponse:
    _has_perm(request, "purchasing.add_goodsreceipt")
    from masterdata.models import Supplier, RawMaterial
    from purchasing.services import ReceiptLineSpec, receive_goods

    if request.method == "POST":
        try:
            supplier = Supplier.objects.get(pk=int(request.POST["supplier"]))
            rm = RawMaterial.objects.get(pk=int(request.POST["raw_material"]))
            spec = ReceiptLineSpec(
                raw_material=rm,
                quantity=Decimal(request.POST["quantity"]),
                lot_number=request.POST["lot_number"].strip(),
                expiry_date=(dt.date.fromisoformat(request.POST["expiry_date"])
                             if request.POST.get("expiry_date") else None),
                coa_reference=request.POST.get("coa_reference", ""),
            )
            receipt = receive_goods(
                receipt_number=request.POST["receipt_number"].strip(),
                supplier=supplier,
                received_date=dt.date.fromisoformat(request.POST["received_date"]),
                lines=[spec],
                receiver=request.user.get_full_name() or request.user.username,
                notes=request.POST.get("notes", ""),
            )
            messages.success(request, f"Mal kabul {receipt.receipt_number} kaydedildi (lot PENDING).")
            return redirect("portal:warehouse")
        except Exception as e:
            messages.error(request, f"Kayıt başarısız: {e}")

    return render(request, "portal/warehouse/receipt_new.html", {
        "current": "home",
        "suppliers": Supplier.objects.filter(is_active=True).order_by("name"),
        "raw_materials": RawMaterial.objects.filter(is_active=True).order_by("code"),
        "today": dt.date.today().isoformat(),
        **_notif_ctx(request.user),
    })


# ---------------------------------------------------------------------------
# KALİTE
# ---------------------------------------------------------------------------

@login_required
def quality_dashboard(request: HttpRequest) -> HttpResponse:
    _has_perm(request, "quality.view_qctestresult")

    from inventory.models import RawMaterialLot
    from production.models import ProductionBatch
    from quality.models import QCTestResult

    pending_lots = RawMaterialLot.objects.filter(
        qc_status=RawMaterialLot.QCStatus.PENDING, remaining_qty__gt=0
    ).select_related("raw_material", "supplier").order_by("-received_date")[:20]

    pending_batches = ProductionBatch.objects.filter(
        status__in=[ProductionBatch.Status.COMPLETED, ProductionBatch.Status.QC_HOLD],
        qc_status=ProductionBatch.QCStatus.PENDING,
    ).select_related("recipe__product", "reactor").order_by("-created_at")[:20]

    since = dt.date.today() - dt.timedelta(days=30)
    recent = QCTestResult.objects.filter(tested_at__date__gte=since)
    stats = {
        "total": recent.count(),
        "pass": recent.filter(verdict=QCTestResult.Verdict.PASS).count(),
        "fail": recent.filter(verdict=QCTestResult.Verdict.FAIL).count(),
        "na":   recent.filter(verdict=QCTestResult.Verdict.NA).count(),
    }
    stats["fail_pct"] = round(stats["fail"] / stats["total"] * 100, 1) if stats["total"] else 0

    return render(request, "portal/quality/dashboard.html", {
        "current": "home",
        "pending_lots": pending_lots,
        "pending_batches": pending_batches,
        "stats": stats,
        **_notif_ctx(request.user),
    })


# ---------------------------------------------------------------------------
# SATIŞ
# ---------------------------------------------------------------------------

@login_required
def sales_dashboard(request: HttpRequest) -> HttpResponse:
    _has_perm(request, "sales.view_salesorder")
    from sales.models import SalesOrder, Shipment

    open_orders = SalesOrder.objects.filter(
        status__in=[SalesOrder.Status.CONFIRMED, SalesOrder.Status.PARTIAL,
                    SalesOrder.Status.DRAFT],
    ).select_related("customer").order_by("-order_date")[:20]

    recent_shipments = Shipment.objects.select_related(
        "customer", "so"
    ).order_by("-shipped_date")[:10]

    return render(request, "portal/sales/dashboard.html", {
        "current": "home",
        "open_orders": open_orders,
        "recent_shipments": recent_shipments,
        **_notif_ctx(request.user),
    })


# ---------------------------------------------------------------------------
# SATIN ALMA
# ---------------------------------------------------------------------------

@login_required
def purchasing_dashboard(request: HttpRequest) -> HttpResponse:
    _has_perm(request, "purchasing.view_purchaseorder")
    from purchasing.models import GoodsReceipt, PurchaseOrder

    open_pos = PurchaseOrder.objects.filter(
        status__in=[PurchaseOrder.Status.DRAFT, PurchaseOrder.Status.OPEN,
                    PurchaseOrder.Status.PARTIAL],
    ).select_related("supplier").order_by("-order_date")[:20]

    recent_grs = GoodsReceipt.objects.select_related(
        "supplier", "po"
    ).order_by("-received_date")[:10]

    return render(request, "portal/purchasing/dashboard.html", {
        "current": "home",
        "open_pos": open_pos,
        "recent_grs": recent_grs,
        **_notif_ctx(request.user),
    })


# ---------------------------------------------------------------------------
# BAKIM & EHS & YÖNETİM & IT
# ---------------------------------------------------------------------------

@login_required
def maintenance_dashboard(request: HttpRequest) -> HttpResponse:
    _has_perm(request, "cmms.view_workorder")
    from cmms.models import CalibrationSchedule, WorkOrder

    open_wos = WorkOrder.objects.filter(
        status__in=[WorkOrder.Status.OPEN, WorkOrder.Status.ASSIGNED,
                    WorkOrder.Status.IN_PROGRESS, WorkOrder.Status.ON_HOLD],
    ).select_related("equipment").order_by("-priority", "-created_at")[:20]

    overdue_cal = CalibrationSchedule.objects.filter(
        is_active=True, next_due_date__isnull=False,
        next_due_date__lt=dt.date.today(),
    ).select_related("equipment").order_by("next_due_date")[:15]

    return render(request, "portal/maintenance/dashboard.html", {
        "current": "home",
        "open_wos": open_wos,
        "overdue_cal": overdue_cal,
        **_notif_ctx(request.user),
    })


@login_required
def ehs_dashboard(request: HttpRequest) -> HttpResponse:
    _has_perm(request, "ehs.view_incident")
    from ehs.models import Incident, WorkPermit

    open_incidents = Incident.objects.exclude(
        status=Incident.Status.CLOSED
    ).order_by("-occurred_at")[:20]

    active_permits = WorkPermit.objects.filter(
        status=WorkPermit.Status.ISSUED
    ).order_by("valid_until")[:15]

    return render(request, "portal/ehs/dashboard.html", {
        "current": "home",
        "open_incidents": open_incidents,
        "active_permits": active_permits,
        **_notif_ctx(request.user),
    })


@login_required
def management_dashboard(request: HttpRequest) -> HttpResponse:
    """Yönetim — BI, ISO paketi ve kritik operasyonel özet."""
    _require_role(request.user, "GENERAL_MANAGER", "TECHNICAL_MANAGER")
    from analytics.services import (
        complaint_trend, ncr_capa_aging, oee_by_equipment,
        qc_pass_fail_stats, waste_trend,
    )
    ctx = {
        "current": "home",
        "oee": oee_by_equipment(),
        "qc": qc_pass_fail_stats(),
        "aging": ncr_capa_aging(),
        "waste_json": json.dumps(waste_trend(6)),
        "complaints_json": json.dumps(complaint_trend(6)),
        **_notif_ctx(request.user),
    }
    return render(request, "portal/management/dashboard.html", ctx)


@login_required
def it_admin_home(request: HttpRequest) -> HttpResponse:
    """BT için: kullanıcı yönetimi ve Django Admin kısayolu."""
    if not (request.user.is_superuser or request.user.groups.filter(name="IT_ADMIN").exists()):
        raise PermissionDenied("BT yönetici yetkisi gerekli.")
    from django.contrib.auth.models import User
    return render(request, "portal/it_admin/dashboard.html", {
        "current": "home",
        "user_count": User.objects.count(),
        "active_user_count": User.objects.filter(is_active=True).count(),
        "group_count": Group.objects.count(),
        "recent_users": User.objects.order_by("-date_joined")[:10],
        **_notif_ctx(request.user),
    })

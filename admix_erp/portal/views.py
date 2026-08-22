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

            # İskonto — müşteri varsayılanı veya form'da override edilen
            try:
                discount_pct = Decimal(data.get("discount_pct", "0") or "0")
            except Exception:  # noqa: BLE001
                discount_pct = Decimal("0")
            if discount_pct < 0: discount_pct = Decimal("0")
            if discount_pct > 100: discount_pct = Decimal("100")

            inv = Invoice.objects.create(
                invoice_number=data.get("invoice_number"),
                type=inv_type, date=date, period=period,
                due_date=(dt.date.fromisoformat(data["due_date"]) if data.get("due_date") else None),
                notes=data.get("notes", ""),
                discount_pct=discount_pct,
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


@login_required
def formulation_new(request: HttpRequest) -> HttpResponse:
    """Nouvelle formulation — portal üzerinden reçete oluşturma.

    UsineERP paritesi (IMG_8303): Composition tablosu +
    MATIÈRE PREMIÈRE, QTÉ, UNITÉ, TOLÉRANCE, COMPLÉMENT.
    """
    _has_perm(request, "formulation.add_recipe")
    from decimal import Decimal
    from django.db import transaction
    from formulation.models import Recipe, RecipeLine
    from masterdata.models import Product, RawMaterial, UnitOfMeasure

    if request.method == "POST":
        try:
            with transaction.atomic():
                product = Product.objects.get(pk=int(request.POST["product"]))
                # Sıradaki versiyon
                last = Recipe.objects.filter(product=product).order_by("-version").first()
                next_version = (last.version if last else 0) + 1
                base_batch = Decimal(request.POST["base_batch_size"])
                unit = UnitOfMeasure.objects.get(pk=int(request.POST["unit"]))
                recipe = Recipe.objects.create(
                    product=product, version=next_version,
                    base_batch_size=base_batch, unit=unit,
                    is_active=(request.POST.get("is_active") == "on"),
                    notes=request.POST.get("notes", ""),
                )
                # Satırlar
                rm_ids = request.POST.getlist("rm_id")
                qtys = request.POST.getlist("quantity")
                tolerances = request.POST.getlist("tolerance_pct")
                complements = request.POST.getlist("is_complement")
                comp_set = set(complements)  # index string olarak
                seq = 1
                for i, (rm_pk, qty) in enumerate(zip(rm_ids, qtys)):
                    if not rm_pk or not qty:
                        continue
                    rm = RawMaterial.objects.get(pk=int(rm_pk))
                    tol = tolerances[i] if i < len(tolerances) else "1.00"
                    is_comp = str(i) in comp_set
                    RecipeLine.objects.create(
                        recipe=recipe, sequence=seq,
                        raw_material=rm, quantity=Decimal(qty),
                        tolerance_pct=Decimal(tol or "1.00"),
                        is_complement=is_comp,
                    )
                    seq += 1
                messages.success(
                    request,
                    f"Formulation {product.code} v{recipe.version} oluşturuldu."
                    f" {recipe.lines.count()} hammadde satırı."
                )
                return redirect("portal:recipes")
        except Exception as e:
            messages.error(request, f"Kaydedilemedi: {e}")

    return render(request, "portal/production/formulation_new.html", {
        "current": "recipes",
        "products": Product.objects.filter(is_active=True).order_by("code"),
        "raw_materials": RawMaterial.objects.filter(is_active=True).order_by("code"),
        "units": UnitOfMeasure.objects.all().order_by("code"),
        **_notif_ctx(request.user),
    })


@login_required
def production_order_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Üretim emri detayı — besoins théoriques + bilan massique (§22).

    ``scale`` query paramı verilirse target_qty yerine geçici bir hedefle
    tablo yeniden hesaplanır (kalıcı kayıt yok — sadece önizleme).
    """
    _has_perm(request, "production.view_productionorder")
    from decimal import Decimal
    from production.models import ProductionOrder

    order = ProductionOrder.objects.select_related(
        "product", "recipe__product", "reactor", "unit",
    ).get(pk=pk)

    scale_raw = request.GET.get("scale")
    if scale_raw:
        try:
            scale_preview = Decimal(scale_raw)
            target_preview = (order.recipe.base_batch_size * scale_preview).quantize(Decimal("0.0001"))
        except Exception:
            scale_preview = order.scale_factor
            target_preview = order.target_qty
    else:
        scale_preview = order.scale_factor
        target_preview = order.target_qty

    # Önizleme için geçici override — DB'ye yazmadan hesap:
    original = order.target_qty
    order.target_qty = target_preview
    needs = order.theoretical_needs()
    bilan = order.recipe.bilan_massique(target_preview)
    order.target_qty = original

    all_sufficient = all(r["sufficient"] for r in needs)

    return render(request, "portal/production/order_detail.html", {
        "current": "home",
        "order": order,
        "needs": needs,
        "bilan": bilan,
        "scale_preview": scale_preview,
        "target_preview": target_preview,
        "all_sufficient": all_sufficient,
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
def customer_statement(request: HttpRequest, customer_pk: int) -> HttpResponse:
    """Müşteri cari hesap özeti — faturalar, ödemeler, avanslar birleşik.

    Bir müşterinin net bakiyesi = faturalar (TTC toplamı)
                                − ödemeler (Payment.amount)
                                − avans tahsisleri (AdvanceAllocation.amount)
    """
    _has_perm(request, "accounting.view_invoice")
    from decimal import Decimal
    from accounting.models import Invoice, Payment, CustomerAdvance, AdvanceAllocation
    from masterdata.models import Customer

    customer = Customer.objects.get(pk=customer_pk)
    invoices = Invoice.objects.filter(
        customer=customer, type=Invoice.Type.SALES,
    ).order_by("-date")

    payments = Payment.objects.filter(
        invoice__customer=customer,
        direction=Payment.Direction.INCOMING,
    ).select_related("invoice").order_by("-date")

    advances = CustomerAdvance.objects.filter(customer=customer).order_by("-date")

    inv_total = invoices.aggregate(t=Sum("total_ttc"))["t"] or Decimal("0")
    inv_paid = invoices.aggregate(t=Sum("amount_paid"))["t"] or Decimal("0")
    payment_total = payments.aggregate(t=Sum("amount"))["t"] or Decimal("0")
    advance_total = advances.aggregate(t=Sum("amount"))["t"] or Decimal("0")
    advance_allocated = AdvanceAllocation.objects.filter(
        advance__customer=customer,
    ).aggregate(t=Sum("amount"))["t"] or Decimal("0")
    advance_remaining = advance_total - advance_allocated

    balance_due = inv_total - inv_paid

    return render(request, "portal/accounting/customer_statement.html", {
        "current": "cari",
        "customer": customer,
        "invoices": invoices,
        "payments": payments,
        "advances": advances,
        "inv_total": inv_total,
        "inv_paid": inv_paid,
        "payment_total": payment_total,
        "advance_total": advance_total,
        "advance_remaining": advance_remaining,
        "balance_due": balance_due,
        **_notif_ctx(request.user),
    })


@login_required
def report_aging_clients(request: HttpRequest) -> HttpResponse:
    """Échéancier clients — 0-30 / 31-60 / 61-90 / 90+ günlük alacak yaşlandırma."""
    _has_perm(request, "accounting.view_invoice")
    from decimal import Decimal
    from accounting.models import Invoice

    today = dt.date.today()
    invoices = Invoice.objects.filter(
        type=Invoice.Type.SALES,
        status__in=[Invoice.Status.POSTED, Invoice.Status.PARTIALLY_PAID, Invoice.Status.DRAFT],
    ).select_related("customer")

    buckets = {"current": Decimal("0"), "0_30": Decimal("0"), "31_60": Decimal("0"),
               "61_90": Decimal("0"), "90_plus": Decimal("0")}
    by_customer: dict = {}
    for inv in invoices:
        due = inv.amount_due
        if due <= 0:
            continue
        base = inv.due_date or inv.date
        days_overdue = (today - base).days if base else 0
        if days_overdue <= 0:
            bucket = "current"
        elif days_overdue <= 30:
            bucket = "0_30"
        elif days_overdue <= 60:
            bucket = "31_60"
        elif days_overdue <= 90:
            bucket = "61_90"
        else:
            bucket = "90_plus"
        buckets[bucket] += due

        cust = inv.customer
        row = by_customer.setdefault(cust.pk, {
            "customer": cust, "current": Decimal("0"), "0_30": Decimal("0"),
            "31_60": Decimal("0"), "61_90": Decimal("0"), "90_plus": Decimal("0"),
            "total": Decimal("0"),
        })
        row[bucket] += due
        row["total"] += due

    rows = sorted(by_customer.values(), key=lambda r: -r["total"])
    total = sum(buckets.values(), Decimal("0"))

    return render(request, "portal/reporting/aging_clients.html", {
        "current": "reports",
        "buckets": buckets,
        "rows": rows,
        "total": total,
        **_notif_ctx(request.user),
    })


@login_required
def report_stock_valuation(request: HttpRequest) -> HttpResponse:
    """Valorisation stocks — MP ve PF stok değerleri."""
    _has_perm(request, "masterdata.view_rawmaterial")
    from decimal import Decimal
    from masterdata.models import RawMaterial
    from inventory.models import RawMaterialLot

    rm_rows = []
    total_mp = Decimal("0")
    for rm in RawMaterial.objects.filter(is_active=True).order_by("code"):
        lots = RawMaterialLot.objects.filter(
            raw_material=rm, qc_status=RawMaterialLot.QCStatus.RELEASED,
        )
        qty = Decimal("0")
        val = Decimal("0")
        for lot in lots:
            if lot.remaining_qty > 0 and lot.unit_cost:
                qty += lot.remaining_qty
                val += lot.remaining_qty * lot.unit_cost
        if qty > 0 or val > 0:
            avg = (val / qty) if qty > 0 else Decimal("0")
            level = rm.stock_level()
            rm_rows.append({
                "rm": rm, "qty": qty, "value": val, "avg_cost": avg, "level": level,
            })
            total_mp += val

    return render(request, "portal/reporting/stock_valuation.html", {
        "current": "reports",
        "rm_rows": rm_rows,
        "total_mp": total_mp,
        **_notif_ctx(request.user),
    })


@login_required
def report_production_yields(request: HttpRequest) -> HttpResponse:
    """Rendements production — teorik vs gerçek verim analizi."""
    _has_perm(request, "production.view_productionbatch")
    from decimal import Decimal
    from production.models import ProductionBatch

    since = dt.date.today() - dt.timedelta(days=90)
    batches = ProductionBatch.objects.filter(
        status__in=[
            ProductionBatch.Status.COMPLETED, ProductionBatch.Status.RELEASED,
            ProductionBatch.Status.QC_HOLD,
        ],
        created_at__date__gte=since,
    ).select_related("recipe__product").order_by("-created_at")

    rows = []
    total_target = Decimal("0")
    total_actual = Decimal("0")
    for b in batches[:100]:
        actual = b.actual_qty or Decimal("0")
        target = b.target_qty or Decimal("0")
        yield_pct = ((actual / target) * 100) if target > 0 else None
        rows.append({
            "batch": b, "target": target, "actual": actual,
            "delta": actual - target,
            "yield_pct": yield_pct,
        })
        total_target += target
        total_actual += actual

    avg_yield = ((total_actual / total_target) * 100) if total_target > 0 else Decimal("0")

    return render(request, "portal/reporting/production_yields.html", {
        "current": "reports",
        "rows": rows,
        "total_target": total_target,
        "total_actual": total_actual,
        "avg_yield": avg_yield,
        **_notif_ctx(request.user),
    })


@login_required
def report_bl_invoice_matching(request: HttpRequest) -> HttpResponse:
    """BL Client ↔ Fatura eşleştirme raporu."""
    _has_perm(request, "sales.view_shipment")
    from sales.models import Shipment

    all_bl = Shipment.objects.select_related("customer", "invoice").order_by("-shipped_date")
    matched = all_bl.filter(invoice__isnull=False, status="INVOICED")
    pending = all_bl.filter(
        invoice__isnull=True,
        status__in=["DELIVERED", "DRAFT"],
    )
    cancelled = all_bl.filter(status="CANCELLED")

    total_pending_amount = sum(
        (b.total_amount for b in pending), __import__("decimal").Decimal("0"),
    )

    return render(request, "portal/reporting/bl_invoice_matching.html", {
        "current": "reports",
        "matched": matched[:50],
        "pending": pending[:100],
        "cancelled": cancelled[:20],
        "matched_count": matched.count(),
        "pending_count": pending.count(),
        "cancelled_count": cancelled.count(),
        "total_pending_amount": total_pending_amount,
        **_notif_ctx(request.user),
    })


@login_required
def stock_adjustment_new(request: HttpRequest) -> HttpResponse:
    """Yeni stok düzeltme formu."""
    _has_perm(request, "inventory.add_stockadjustment")
    from decimal import Decimal
    from inventory.models import RawMaterialLot, StockAdjustment
    from inventory.services import apply_stock_adjustment

    if request.method == "POST":
        try:
            lot = RawMaterialLot.objects.get(pk=int(request.POST["lot_id"]))
            new_qty = Decimal(request.POST["new_qty"])
            adj = apply_stock_adjustment(
                lot,
                adjustment_type=request.POST["adjustment_type"],
                reason=request.POST["reason"].strip(),
                new_qty=new_qty,
                performed_by=request.user,
                document_type=request.POST.get("document_type", "").strip(),
                document_ref=request.POST.get("document_ref", "").strip(),
                document=request.FILES.get("document"),
            )
            messages.success(request, f"{adj.adjustment_number} kaydedildi (Δ {adj.delta}).")
            return redirect("portal:raw_material_detail", pk=lot.raw_material_id)
        except Exception as e:
            messages.error(request, f"Düzeltme başarısız: {e}")

    lots = RawMaterialLot.objects.filter(
        qc_status=RawMaterialLot.QCStatus.RELEASED, remaining_qty__gt=0,
    ).select_related("raw_material").order_by("raw_material__code", "lot_number")[:200]

    return render(request, "portal/warehouse/stock_adjustment_new.html", {
        "current": "home",
        "lots": lots,
        "types": StockAdjustment.AdjustmentType.choices,
        **_notif_ctx(request.user),
    })


@login_required
def scada_dashboard(request: HttpRequest) -> HttpResponse:
    """SCADA entegrasyon panosu — Node-RED bağlantı sağlığı + son batch'ler."""
    _has_perm(request, "production.view_productionbatch")
    from decimal import Decimal
    from production.models import ProductionBatch
    from rest_framework.authtoken.models import Token
    from django.contrib.auth import get_user_model

    now = dt.datetime.now()
    today = now.date()
    week_ago = today - dt.timedelta(days=7)

    scada_batches = ProductionBatch.objects.filter(
        production_order__order_number__startswith="SCADA-"
    ).select_related("recipe__product", "reactor").order_by("-created_at")

    today_count = scada_batches.filter(created_at__date=today).count()
    week_count = scada_batches.filter(created_at__date__gte=week_ago).count()
    last_batch = scada_batches.first()

    # Bridge user + token durumu
    User = get_user_model()
    bridge_user = User.objects.filter(username="scada_bridge").first()
    token = None
    token_created = None
    if bridge_user:
        tok = Token.objects.filter(user=bridge_user).first()
        if tok:
            token = tok.key
            token_created = tok.created

    # Son 24 saat aktivite trend (saatlik batch sayısı)
    hourly_counts = []
    for i in range(23, -1, -1):
        hour_start = now - dt.timedelta(hours=i+1)
        hour_end = now - dt.timedelta(hours=i)
        count = scada_batches.filter(
            created_at__gte=hour_start, created_at__lt=hour_end,
        ).count()
        hourly_counts.append({"hour": hour_start.strftime("%H:00"), "count": count})

    return render(request, "portal/scada/dashboard.html", {
        "current": "scada",
        "today_count": today_count,
        "week_count": week_count,
        "total_count": scada_batches.count(),
        "last_batch": last_batch,
        "recent_batches": scada_batches[:20],
        "bridge_user": bridge_user,
        "token_last8": token[-8:] if token else None,
        "token_created": token_created,
        "hourly_counts": hourly_counts,
        **_notif_ctx(request.user),
    })


@login_required
def sds_list(request: HttpRequest) -> HttpResponse:
    """SDS listesi — 16 bölüm güvenlik bilgi formları."""
    _has_perm(request, "chemicals.view_safetydatasheet")
    from chemicals.models import SafetyDataSheet
    qs = SafetyDataSheet.objects.select_related("profile", "prepared_by", "approved_by").order_by("-revision_date")
    stats = {
        "total": qs.count(),
        "draft": qs.filter(status=SafetyDataSheet.Status.DRAFT).count(),
        "approved": qs.filter(status=SafetyDataSheet.Status.APPROVED).count(),
    }
    return render(request, "portal/compliance/sds_list.html", {
        "current": "sds", "sheets": qs[:200], "stats": stats,
        **_notif_ctx(request.user),
    })


@login_required
def sds_pdf(request: HttpRequest, pk: int):
    """SDS PDF üretimi — 16 bölüm."""
    _has_perm(request, "chemicals.view_safetydatasheet")
    from django.http import HttpResponse as _HR
    from chemicals.models import SafetyDataSheet
    from common.pdf import render_sds_pdf
    sds = SafetyDataSheet.objects.select_related("profile", "prepared_by", "approved_by").get(pk=pk)
    pdf = render_sds_pdf(sds)
    resp = _HR(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="SDS-{sds.sds_number}-v{sds.version}.pdf"'
    return resp


@login_required
def dop_list(request: HttpRequest) -> HttpResponse:
    """DoP listesi — Declaration of Performance (CE marking)."""
    _has_perm(request, "chemicals.view_declarationofperformance")
    from chemicals.models import DeclarationOfPerformance
    qs = DeclarationOfPerformance.objects.select_related("product", "coc__issuing_body").order_by("-issue_date")
    return render(request, "portal/compliance/dop_list.html", {
        "current": "dop", "dops": qs[:200],
        **_notif_ctx(request.user),
    })


@login_required
def dop_pdf(request: HttpRequest, pk: int):
    """DoP PDF üretimi — EN 305/2011 Annex III."""
    _has_perm(request, "chemicals.view_declarationofperformance")
    from django.http import HttpResponse as _HR
    from chemicals.models import DeclarationOfPerformance
    from common.pdf import render_dop_pdf
    dop = DeclarationOfPerformance.objects.select_related(
        "product", "coc__issuing_body", "coc__fpc_plan",
    ).get(pk=pk)
    pdf = render_dop_pdf(dop)
    resp = _HR(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="DoP-{dop.dop_number}.pdf"'
    return resp


@login_required
def fpc_audit_list(request: HttpRequest) -> HttpResponse:
    """FPC Audit listesi — Notified Body inspection kayıtları."""
    _has_perm(request, "chemicals.view_fpcaudit")
    from chemicals.models import FPCAudit
    qs = FPCAudit.objects.select_related("notified_body").order_by("-audit_date")
    return render(request, "portal/compliance/fpc_audit_list.html", {
        "current": "fpc", "audits": qs[:100],
        **_notif_ctx(request.user),
    })


@login_required
def reach_svhc_list(request: HttpRequest) -> HttpResponse:
    """REACH SVHC izleme — 0.1% üzeri bileşenler."""
    _has_perm(request, "masterdata.view_rawmaterial")
    from decimal import Decimal
    from masterdata.models import RawMaterial
    svhc = RawMaterial.objects.filter(svhc_flag=True).order_by("code")
    over_threshold = [r for r in svhc if (r.svhc_pct or Decimal("0")) > Decimal("0.1")]
    return render(request, "portal/compliance/reach_svhc.html", {
        "current": "reach", "svhc_items": svhc,
        "over_threshold": over_threshold,
        **_notif_ctx(request.user),
    })


@login_required
def expense_list(request: HttpRequest) -> HttpResponse:
    """Factures de dépense listesi."""
    _has_perm(request, "accounting.view_expenseinvoice")
    from decimal import Decimal
    from accounting.models import ExpenseInvoice

    status_filter = request.GET.get("status", "")
    category_filter = request.GET.get("category", "")
    qs = ExpenseInvoice.objects.select_related("supplier").order_by("-invoice_date")
    if status_filter:
        qs = qs.filter(status=status_filter)
    if category_filter:
        qs = qs.filter(category=category_filter)

    total_month = ExpenseInvoice.objects.filter(
        invoice_date__year=dt.date.today().year,
        invoice_date__month=dt.date.today().month,
    ).aggregate(t=Sum("amount_ttc"))["t"] or Decimal("0")

    draft_count = ExpenseInvoice.objects.filter(status=ExpenseInvoice.Status.DRAFT).count()
    approved_count = ExpenseInvoice.objects.filter(status=ExpenseInvoice.Status.APPROVED).count()

    return render(request, "portal/accounting/expense_list.html", {
        "current": "expenses",
        "expenses": qs[:200],
        "statuses": ExpenseInvoice.Status.choices,
        "categories": ExpenseInvoice.Category.choices,
        "status_filter": status_filter,
        "category_filter": category_filter,
        "total_month": total_month,
        "draft_count": draft_count,
        "approved_count": approved_count,
        **_notif_ctx(request.user),
    })


@login_required
def expense_new(request: HttpRequest) -> HttpResponse:
    """Yeni facture de dépense oluşturma."""
    _has_perm(request, "accounting.add_expenseinvoice")
    import datetime as _dt
    from decimal import Decimal
    from accounting.models import ExpenseInvoice, TVARate
    from accounting.services import get_or_create_period
    from masterdata.models import Supplier

    if request.method == "POST":
        try:
            invoice_date = _dt.date.fromisoformat(request.POST["invoice_date"])
            supplier = Supplier.objects.get(pk=int(request.POST["supplier"]))
            tva = TVARate.objects.get(pk=int(request.POST["tva_rate"]))
            period = get_or_create_period(invoice_date)

            n = ExpenseInvoice.objects.count() + 1
            expense_number = f"EXP-{invoice_date.strftime('%Y%m')}-{n:03d}"

            exp = ExpenseInvoice(
                expense_number=expense_number,
                supplier=supplier,
                category=request.POST["category"],
                invoice_date=invoice_date,
                due_date=_dt.date.fromisoformat(request.POST["due_date"])
                         if request.POST.get("due_date") else None,
                period=period,
                description=request.POST["description"],
                supplier_invoice_number=request.POST.get("supplier_invoice_number", ""),
                amount_ht=Decimal(request.POST["amount_ht"]),
                tva_rate=tva,
                equipment_reference=request.POST.get("equipment_reference", ""),
                proof_document=request.FILES.get("proof_document"),
                performed_by=request.user,
                notes=request.POST.get("notes", ""),
            )
            exp.recompute()
            exp.save()
            messages.success(
                request, f"{exp.expense_number} kaydedildi. TTC: {exp.amount_ttc} DZD."
            )
            return redirect("portal:expense_detail", pk=exp.pk)
        except Exception as e:
            messages.error(request, f"Kaydedilemedi: {e}")

    return render(request, "portal/accounting/expense_new.html", {
        "current": "expenses",
        "suppliers": Supplier.objects.filter(is_active=True).order_by("code"),
        "tva_rates": TVARate.objects.all(),
        "categories": ExpenseInvoice.Category.choices,
        "today": dt.date.today().isoformat(),
        **_notif_ctx(request.user),
    })


@login_required
def expense_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Facture de dépense detay + onay akışı."""
    _has_perm(request, "accounting.view_expenseinvoice")
    from accounting.models import ExpenseInvoice

    exp = ExpenseInvoice.objects.select_related(
        "supplier", "tva_rate", "performed_by", "approved_by",
    ).get(pk=pk)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "submit" and exp.status == ExpenseInvoice.Status.DRAFT:
            exp.status = ExpenseInvoice.Status.SUBMITTED
            exp.save()
            messages.info(request, f"{exp.expense_number} onaya sunuldu.")
        elif action == "approve" and exp.status == ExpenseInvoice.Status.SUBMITTED:
            _has_perm(request, "accounting.change_expenseinvoice")
            from django.utils import timezone
            exp.status = ExpenseInvoice.Status.APPROVED
            exp.approved_by = request.user
            exp.approved_at = timezone.now()
            exp.save()
            messages.success(request, f"{exp.expense_number} onaylandı.")
        elif action == "reject" and exp.status in [
            ExpenseInvoice.Status.SUBMITTED, ExpenseInvoice.Status.DRAFT,
        ]:
            exp.status = ExpenseInvoice.Status.REJECTED
            exp.save()
            messages.warning(request, f"{exp.expense_number} reddedildi.")
        elif action == "paid" and exp.status == ExpenseInvoice.Status.APPROVED:
            exp.status = ExpenseInvoice.Status.PAID
            exp.payment_reference = request.POST.get("payment_reference", "")
            exp.save()
            messages.success(request, f"{exp.expense_number} ödendi olarak işaretlendi.")
        return redirect("portal:expense_detail", pk=exp.pk)

    return render(request, "portal/accounting/expense_detail.html", {
        "current": "expenses",
        "exp": exp,
        **_notif_ctx(request.user),
    })


@login_required
def multi_line_adjustment_new(request: HttpRequest) -> HttpResponse:
    """Multi-line ajustement — bir belgede birden çok lot düzeltmesi."""
    _has_perm(request, "inventory.add_stockadjustment")
    from decimal import Decimal
    from inventory.models import RawMaterialLot, StockAdjustment
    from inventory.services import apply_multi_line_adjustment

    if request.method == "POST":
        try:
            lot_ids = request.POST.getlist("lot_id")
            new_qtys = request.POST.getlist("new_qty")
            line_reasons = request.POST.getlist("line_reason")
            lines = []
            for i, lot_pk in enumerate(lot_ids):
                if not lot_pk or not new_qtys[i]:
                    continue
                lot = RawMaterialLot.objects.get(pk=int(lot_pk))
                lines.append({
                    "lot": lot,
                    "new_qty": Decimal(new_qtys[i]),
                    "line_reason": line_reasons[i] if i < len(line_reasons) else "",
                })
            if not lines:
                messages.error(request, "En az bir satır doldurun.")
                return redirect("portal:multi_line_adjustment_new")

            adj = apply_multi_line_adjustment(
                adjustment_type=request.POST["adjustment_type"],
                reason=request.POST["reason"].strip(),
                lines=lines,
                performed_by=request.user,
                document_type=request.POST.get("document_type", ""),
                document_ref=request.POST.get("document_ref", ""),
                document=request.FILES.get("document"),
            )
            messages.success(
                request,
                f"{adj.adjustment_number} kaydedildi — {adj.lines.count()} satır, "
                f"toplam delta {adj.delta}.",
            )
            return redirect("portal:warehouse")
        except Exception as e:
            messages.error(request, f"Kaydedilemedi: {e}")

    lots = RawMaterialLot.objects.filter(
        qc_status=RawMaterialLot.QCStatus.RELEASED, remaining_qty__gt=0,
    ).select_related("raw_material").order_by("raw_material__code", "lot_number")[:200]

    return render(request, "portal/warehouse/multi_line_adjustment.html", {
        "current": "home",
        "lots": lots,
        "types": StockAdjustment.AdjustmentType.choices,
        **_notif_ctx(request.user),
    })


@login_required
def customer_advances_list(request: HttpRequest) -> HttpResponse:
    """Müşteri avansları listesi (§23)."""
    _has_perm(request, "accounting.view_customeradvance")
    from decimal import Decimal
    from accounting.models import CustomerAdvance

    status_filter = request.GET.get("status", "")
    qs = CustomerAdvance.objects.select_related("customer").order_by("-date")
    if status_filter:
        qs = qs.filter(status=status_filter)

    open_qs = CustomerAdvance.objects.filter(status=CustomerAdvance.Status.OPEN)
    open_remaining = sum(
        (a.remaining_amount for a in open_qs), Decimal("0")
    )

    return render(request, "portal/accounting/advances_list.html", {
        "current": "advances",
        "advances": qs[:200],
        "status_filter": status_filter,
        "statuses": CustomerAdvance.Status.choices,
        "open_count": open_qs.count(),
        "open_remaining": open_remaining,
        **_notif_ctx(request.user),
    })


@login_required
def advance_allocate(request: HttpRequest, pk: int) -> HttpResponse:
    """Avansı bir faturaya tahsis et (form + POST)."""
    _has_perm(request, "accounting.add_advanceallocation")
    from decimal import Decimal
    from accounting.models import CustomerAdvance, Invoice
    from accounting.services import allocate_advance_to_invoice

    advance = CustomerAdvance.objects.select_related("customer").get(pk=pk)

    if request.method == "POST":
        try:
            invoice = Invoice.objects.get(pk=int(request.POST["invoice_id"]))
            amount = Decimal(request.POST["amount"])
            allocate_advance_to_invoice(advance, invoice, amount)
            messages.success(
                request,
                f"{amount} DZD, {invoice.invoice_number} faturasına tahsis edildi.",
            )
            return redirect("portal:customer_advances")
        except Exception as e:
            messages.error(request, f"Tahsis başarısız: {e}")

    # Aynı müşterinin açık faturaları
    open_invoices = Invoice.objects.filter(
        customer=advance.customer,
        type=Invoice.Type.SALES,
        status__in=[Invoice.Status.POSTED, Invoice.Status.PARTIALLY_PAID, Invoice.Status.DRAFT],
    ).order_by("-date")[:50]

    return render(request, "portal/accounting/advance_allocate.html", {
        "current": "advances",
        "advance": advance,
        "open_invoices": open_invoices,
        **_notif_ctx(request.user),
    })


@login_required
def raw_material_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Hammadde detay sayfası — progress bar + alerte/rupture eşikleri
    + son 20 hareket + fiyat + valeur du stock."""
    _has_perm(request, "masterdata.view_rawmaterial")
    from decimal import Decimal
    from django.db.models import Sum, F, DecimalField, ExpressionWrapper
    from masterdata.models import RawMaterial
    from inventory.models import RawMaterialLot, StockMovement

    rm = RawMaterial.objects.select_related("unit").get(pk=pk)

    current = rm.current_stock
    level = rm.stock_level()

    # Ortalama birim maliyet: RELEASED lotların ağırlıklı ortalaması
    lots = RawMaterialLot.objects.filter(
        raw_material=rm, qc_status=RawMaterialLot.QCStatus.RELEASED,
    ).select_related("supplier")
    valid_lots = [l for l in lots if l.unit_cost and l.remaining_qty > 0]
    if valid_lots:
        total_qty = sum(l.remaining_qty for l in valid_lots)
        total_val = sum(l.remaining_qty * l.unit_cost for l in valid_lots)
        avg_cost = total_val / total_qty if total_qty > 0 else Decimal("0")
        stock_value = total_val
    else:
        avg_cost = Decimal("0")
        stock_value = Decimal("0")

    # Progress bar: 0 → alert → rupture arası pozisyon
    max_display = max(rm.alert_threshold * 2 if rm.alert_threshold else current, Decimal("1"))
    if max_display <= 0:
        percent = 0
    else:
        percent = min(100, int(current * 100 / max_display))

    movements = StockMovement.objects.filter(
        lot__raw_material=rm,
    ).select_related("lot").order_by("-created_at")[:20]

    return render(request, "portal/warehouse/raw_material_detail.html", {
        "current": "home",
        "rm": rm,
        "current_qty": current,
        "level": level,
        "avg_cost": avg_cost,
        "stock_value": stock_value,
        "percent": percent,
        "movements": movements,
        "lots": lots,
        **_notif_ctx(request.user),
    })


@login_required
def reporting_hub(request: HttpRequest) -> HttpResponse:
    """Reporting hub — 6 rapor kartı + son çalışmalar (UsineERP paritesi)."""
    from accounting.models import Invoice
    from decimal import Decimal
    import datetime as dt

    today = dt.date.today()
    month_start = today.replace(day=1)

    # Basit KPI'lar
    monthly_revenue = Invoice.objects.filter(
        type=Invoice.Type.SALES,
        date__gte=month_start,
    ).aggregate(t=Sum("total_ttc"))["t"] or Decimal("0")

    monthly_costs = Invoice.objects.filter(
        type=Invoice.Type.PURCHASE,
        date__gte=month_start,
    ).aggregate(t=Sum("total_ttc"))["t"] or Decimal("0")

    net = monthly_revenue - monthly_costs

    return render(request, "portal/reporting/hub.html", {
        "current": "reports",
        "monthly_revenue": monthly_revenue,
        "monthly_costs": monthly_costs,
        "net_result": net,
        "is_profit": net >= 0,
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


@login_required
def quality_specs_list(request: HttpRequest) -> HttpResponse:
    """Kalite şartname listesi — versiyon, QA onayı, per-Gate rozetleri."""
    _has_perm(request, "quality.view_qcspec")
    from quality.models import QCSpec

    only_active = request.GET.get("active") != "0"
    qs = QCSpec.objects.select_related(
        "parameter", "product", "raw_material", "approved_by", "created_by",
    ).order_by("-is_active", "product__code", "parameter__code", "-version")
    if only_active:
        qs = qs.filter(is_active=True)

    return render(request, "portal/quality/specs_list.html", {
        "current": "specs",
        "specs": qs[:200],
        "only_active": only_active,
        **_notif_ctx(request.user),
    })


@login_required
def quality_spec_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Şartname detay — versiyon geçmişi + Gate rozetleri."""
    _has_perm(request, "quality.view_qcspec")
    from quality.models import QCSpec

    spec = QCSpec.objects.select_related(
        "parameter", "product", "raw_material", "approved_by", "created_by",
    ).get(pk=pk)

    # Aynı hedef+parametrenin diğer versiyonları
    other_qs = QCSpec.objects.filter(parameter=spec.parameter).exclude(pk=spec.pk)
    if spec.product_id:
        other_qs = other_qs.filter(product=spec.product)
    else:
        other_qs = other_qs.filter(raw_material=spec.raw_material)
    versions = list(other_qs.order_by("-version"))

    return render(request, "portal/quality/spec_detail.html", {
        "current": "specs",
        "spec": spec,
        "versions": versions,
        **_notif_ctx(request.user),
    })


@login_required
def sampling_plans_list(request: HttpRequest) -> HttpResponse:
    """Örnekleme planları — Plan d'échantillonnage."""
    _has_perm(request, "quality.view_samplingplan")
    from quality.models import SamplingPlan

    plans = SamplingPlan.objects.select_related(
        "product", "raw_material",
    ).order_by("-is_active", "gate", "code")

    return render(request, "portal/quality/sampling_plans.html", {
        "current": "plans",
        "plans": plans,
        **_notif_ctx(request.user),
    })


@login_required
def quality_catalog(request: HttpRequest) -> HttpResponse:
    """Catalogue Propriétés / Tests — QCParameter kataloğu."""
    _has_perm(request, "quality.view_qcparameter")
    from quality.models import QCParameter

    params = QCParameter.objects.filter(is_active=True).order_by("code")

    return render(request, "portal/quality/catalog.html", {
        "current": "catalog",
        "params": params,
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


@login_required
def bl_client_list(request: HttpRequest) -> HttpResponse:
    """BL Client (İrsaliye) listesi + filtreleme."""
    _has_perm(request, "sales.view_shipment")
    from sales.models import Shipment

    status_filter = request.GET.get("status", "")
    qs = Shipment.objects.select_related("customer", "so", "invoice").order_by("-shipped_date")
    if status_filter:
        qs = qs.filter(status=status_filter)

    stats = {
        "draft": Shipment.objects.filter(status=Shipment.Status.DRAFT).count(),
        "delivered": Shipment.objects.filter(status=Shipment.Status.DELIVERED).count(),
        "invoiced": Shipment.objects.filter(status=Shipment.Status.INVOICED).count(),
        "cancelled": Shipment.objects.filter(status=Shipment.Status.CANCELLED).count(),
    }

    return render(request, "portal/sales/bl_client_list.html", {
        "current": "bl",
        "shipments": qs[:200],
        "status_filter": status_filter,
        "stats": stats,
        "statuses": Shipment.Status.choices,
        **_notif_ctx(request.user),
    })


@login_required
def bl_client_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """BL Client detay sayfası."""
    _has_perm(request, "sales.view_shipment")
    from sales.models import Shipment

    bl = Shipment.objects.select_related(
        "customer", "so", "invoice",
    ).prefetch_related(
        "lines__output_container__container",
        "lines__so_line__product",
    ).get(pk=pk)

    return render(request, "portal/sales/bl_client_detail.html", {
        "current": "bl",
        "bl": bl,
        **_notif_ctx(request.user),
    })


@login_required
def bl_to_invoice_view(request: HttpRequest) -> HttpResponse:
    """Seçili BL Client'lerden fatura oluşturur."""
    _has_perm(request, "sales.add_shipment")
    from sales.models import Shipment
    from sales.services import create_invoice_from_bl
    import datetime as dt

    if request.method != "POST":
        return redirect("portal:bl_client_list")

    ids = request.POST.getlist("bl_ids")
    if not ids:
        messages.error(request, "En az bir BL seçmelisiniz.")
        return redirect("portal:bl_client_list")

    shipments = Shipment.objects.filter(pk__in=ids)
    stamp = dt.datetime.now().strftime("%Y%m%d%H%M%S")
    try:
        inv = create_invoice_from_bl(shipments, invoice_number=f"INV-BL-{stamp}")
        messages.success(request, f"Fatura {inv.invoice_number} oluşturuldu ({shipments.count()} BL).")
        return redirect("portal:accounting_invoice_detail", pk=inv.pk)
    except Exception as e:
        messages.error(request, f"Fatura oluşturulamadı: {e}")
        return redirect("portal:bl_client_list")


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

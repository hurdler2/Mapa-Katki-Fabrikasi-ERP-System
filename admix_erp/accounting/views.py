"""Mizan (Balance) ve Büyük Defter (Grand Livre) sayfaları."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .models import Account, Invoice, Payment
from .services import general_ledger, trial_balance
from masterdata.models import CompanyProfile


def _parse_range(request: HttpRequest):
    today = dt.date.today()
    default_from = today.replace(month=1, day=1)
    try:
        d_from = dt.date.fromisoformat(request.GET.get("from") or "") or default_from
    except ValueError:
        d_from = default_from
    try:
        d_to = dt.date.fromisoformat(request.GET.get("to") or "") or today
    except ValueError:
        d_to = today
    return d_from, d_to


@staff_member_required
def trial_balance_view(request: HttpRequest) -> HttpResponse:
    d_from, d_to = _parse_range(request)
    balance = trial_balance(date_from=d_from, date_to=d_to)
    return render(request, "accounting/trial_balance.html", {
        "balance": balance, "date_from": d_from, "date_to": d_to,
    })


@staff_member_required
def ledger_view(request: HttpRequest, account_id: int) -> HttpResponse:
    account = get_object_or_404(Account, pk=account_id)
    d_from, d_to = _parse_range(request)
    ledger = general_ledger(account, date_from=d_from, date_to=d_to)
    return render(request, "accounting/general_ledger.html", {
        "account": account, "ledger": ledger,
        "date_from": d_from, "date_to": d_to,
    })


def _perm_pay(request):
    if request.user.is_superuser:
        return
    if not request.user.has_perm("accounting.add_payment"):
        raise PermissionDenied("Ödeme eklemek için yetkiniz yok.")


@login_required
def invoice_print(request: HttpRequest, pk: int) -> HttpResponse:
    """Yazdırılabilir / PDF olarak indirilebilir fatura sayfası.

    - A4 boyutunda print CSS
    - Şirket logosu + antet
    - Müşteri/Tedarikçi bilgileri
    - Fatura satırları + iskonto + toplamlar
    - Cezayir yasal alanları (NIF, NIS, RC, RIB)
    - Ctrl+P ile PDF olarak kaydedilir
    - ?auto=1 parametresi ile açılınca otomatik yazdır dialog'u
    """
    inv = get_object_or_404(
        Invoice.objects.select_related("customer", "supplier", "period"), pk=pk)
    company = CompanyProfile.get()
    return render(request, "accounting/invoice_print.html", {
        "inv": inv, "company": company,
        "auto_print": request.GET.get("auto") == "1",
    })


@login_required
def payment_new(request: HttpRequest) -> HttpResponse:
    """Yeni ödeme (havale / çek / nakit / LC / kart).

    Query parametresi `?invoice=<pk>` verilirse ilgili faturaya bağlanır.
    """
    _perm_pay(request)

    inv_pk = request.GET.get("invoice") or request.POST.get("invoice_pk")
    inv = get_object_or_404(Invoice, pk=int(inv_pk)) if inv_pk else None

    if request.method == "POST":
        try:
            data = request.POST
            method = data.get("method")
            # Ödeme numarası otomatik: PAY-YYYY-XXXX
            pay_no = data.get("payment_number") or f"PAY-{dt.date.today():%Y}-{Payment.objects.count() + 1:04d}"

            # Banka/kasa hesabı: dev'de ilk hesap
            bank = Account.objects.filter(code__startswith="512").first() \
                or Account.objects.filter(code__startswith="53").first() \
                or Account.objects.first()
            if bank is None:
                raise ValueError("Sistem'de bir Banka/Kasa hesabı bulunamadı — muhasebe seed'i çalıştırın.")

            payment = Payment(
                payment_number=pay_no,
                date=dt.date.fromisoformat(data.get("date")),
                direction=Payment.Direction.INCOMING if (inv and inv.type in ("SALES", "CN_SALES")) else Payment.Direction.OUTGOING,
                method=method,
                amount=Decimal(data.get("amount", "0")),
                currency="DZD",
                bank_account=bank,
                reference=data.get("reference", ""),
                notes=data.get("notes", ""),
            )
            if inv:
                if inv.customer_id: payment.customer = inv.customer
                if inv.supplier_id: payment.supplier = inv.supplier

            # Çek özel alanları
            if method == Payment.Method.CHECK:
                payment.check_number = data.get("check_number", "")
                payment.check_bank = data.get("check_bank", "")
                payment.check_bank_branch = data.get("check_bank_branch", "")
                if data.get("check_issue_date"):
                    payment.check_issue_date = dt.date.fromisoformat(data["check_issue_date"])
                if data.get("check_due_date"):
                    payment.check_due_date = dt.date.fromisoformat(data["check_due_date"])
                payment.check_status = data.get("check_status") or Payment.CheckStatus.ISSUED
                payment.check_drawer_name = data.get("check_drawer_name", "")
                if request.FILES.get("check_image"):
                    payment.check_image = request.FILES["check_image"]

            # Havale/EFT özel alanları
            if method == Payment.Method.BANK_TRANSFER:
                payment.transfer_bank = data.get("transfer_bank", "")
                payment.transfer_iban = data.get("transfer_iban", "")
                if data.get("transfer_date"):
                    payment.transfer_date = dt.date.fromisoformat(data["transfer_date"])

            # Genel ek
            if request.FILES.get("attachment"):
                payment.attachment = request.FILES["attachment"]

            payment.full_clean()
            payment.save()

            if inv:
                payment.invoices.add(inv)
                # Ödenen tutarı arttır
                inv.amount_paid = (inv.amount_paid or Decimal("0")) + payment.amount
                if inv.amount_paid >= inv.total_ttc:
                    inv.status = Invoice.Status.PAID
                elif inv.amount_paid > 0:
                    inv.status = Invoice.Status.PARTIALLY_PAID
                inv.save(update_fields=["amount_paid", "status", "updated_at"])

            messages.success(request, f"Ödeme {payment.payment_number} kaydedildi.")
            if inv:
                return redirect(f"/portal/muhasebe/faturalar/{inv.pk}/")
            return redirect("portal:accounting")
        except Exception as e:
            messages.error(request, f"Ödeme kaydedilemedi: {e}")

    return render(request, "accounting/payment_new.html", {
        "inv": inv,
        "today": dt.date.today().isoformat(),
        "methods": Payment.Method.choices,
        "banks": Payment.AlgerianBank.choices,
        "check_statuses": Payment.CheckStatus.choices,
    })

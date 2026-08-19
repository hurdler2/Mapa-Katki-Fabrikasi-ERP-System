"""Muhasebe servisleri: yevmiye post, fatura post, ödeme, TVA hesabı, amortisman,
Grand Livre, Balance, dönem kapatma.
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Iterable

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import (
    Account,
    DepreciationEntry,
    FiscalYear,
    FixedAsset,
    Invoice,
    InvoiceLine,
    JournalCode,
    JournalEntry,
    JournalLine,
    Payment,
    Period,
    TVADeclaration,
    TVARate,
)


ZERO = Decimal("0")


# ---------------------------------------------------------------------------
# Dönem yardımcıları
# ---------------------------------------------------------------------------

def get_or_create_period(date: dt.date) -> Period:
    """Verilen tarih için Period nesnesi (yoksa oluştur — mali yıl varsa)."""
    fy = FiscalYear.objects.filter(
        start_date__lte=date, end_date__gte=date
    ).first()
    if fy is None:
        raise ValidationError(f"{date} için tanımlı mali yıl yok.")
    period, _ = Period.objects.get_or_create(
        year=date.year, month=date.month,
        defaults={"fiscal_year": fy, "status": Period.Status.OPEN},
    )
    return period


def _ensure_period_open(period: Period) -> None:
    if period.status != Period.Status.OPEN:
        raise ValidationError(f"Dönem açık değil: {period}")


# ---------------------------------------------------------------------------
# Yevmiye
# ---------------------------------------------------------------------------

@transaction.atomic
def create_journal_entry(
    *,
    entry_number: str,
    journal_code: JournalCode,
    entry_date: dt.date,
    description: str,
    lines: list[dict],
    reference: str = "",
) -> JournalEntry:
    """Yevmiye fişi + satırları oluşturur (DRAFT). Satır listesi:
    [{account, debit, credit, description, customer, supplier}, ...]
    """
    period = get_or_create_period(entry_date)
    _ensure_period_open(period)

    entry = JournalEntry.objects.create(
        entry_number=entry_number,
        journal_code=journal_code,
        period=period,
        entry_date=entry_date,
        description=description,
        reference=reference,
        status=JournalEntry.Status.DRAFT,
    )
    for i, line in enumerate(lines, start=1):
        acc = line["account"]
        if not acc.is_leaf:
            raise ValidationError(f"{acc.code} yaprak değil, post edilemez.")
        JournalLine.objects.create(
            entry=entry,
            account=acc,
            debit=Decimal(str(line.get("debit", 0) or 0)),
            credit=Decimal(str(line.get("credit", 0) or 0)),
            description=line.get("description", "") or description,
            customer=line.get("customer"),
            supplier=line.get("supplier"),
        )
    return entry


@transaction.atomic
def post_journal_entry(entry: JournalEntry, *, user) -> JournalEntry:
    """Yevmiye fişini kesinleştir — dengeli olmalı, dönem açık olmalı."""
    if entry.status == JournalEntry.Status.POSTED:
        raise ValidationError("Fiş zaten kesinleşmiş.")
    if entry.status == JournalEntry.Status.CANCELLED:
        raise ValidationError("İptal edilmiş fiş kesinleştirilemez.")
    if not entry.lines.exists():
        raise ValidationError("Boş fiş kesinleştirilemez.")
    if not entry.is_balanced:
        raise ValidationError(
            f"Fiş dengeli değil: borç={entry.total_debit} alacak={entry.total_credit}"
        )
    _ensure_period_open(entry.period)

    entry.status = JournalEntry.Status.POSTED
    entry.posted_at = timezone.now()
    entry.posted_by = user
    entry.save(update_fields=["status", "posted_at", "posted_by", "updated_at"])
    return entry


@transaction.atomic
def reverse_journal_entry(
    entry: JournalEntry, *, user, reason: str, on_date: dt.date | None = None
) -> JournalEntry:
    """Ters kayıt üret (borç↔alacak) — kesin fiş silinmez."""
    if entry.status != JournalEntry.Status.POSTED:
        raise ValidationError("Yalnız POSTED fiş ters kayıtla iptal edilebilir.")

    on_date = on_date or dt.date.today()
    reverse = create_journal_entry(
        entry_number=f"REV-{entry.entry_number}",
        journal_code=entry.journal_code,
        entry_date=on_date,
        description=f"Ters kayıt: {entry.entry_number} - {reason}",
        lines=[
            {
                "account": l.account,
                "debit": l.credit,
                "credit": l.debit,
                "description": f"Reverse {l.description}",
                "customer": l.customer,
                "supplier": l.supplier,
            }
            for l in entry.lines.all()
        ],
        reference=entry.reference,
    )
    post_journal_entry(reverse, user=user)
    entry.reversed_by = reverse
    entry.status = JournalEntry.Status.CANCELLED
    entry.save(update_fields=["reversed_by", "status", "updated_at"])
    return reverse


# ---------------------------------------------------------------------------
# Fatura
# ---------------------------------------------------------------------------

def recompute_invoice(invoice: Invoice) -> None:
    """Fatura toplamlarını satırlardan yeniden hesapla.

    İskonto akışı:
        1. Her satırın HT'si (miktar × birim fiyat) hesaplanır — iskonto YOK
        2. Satırların HT toplamı = base_ht
        3. Discount amount = base_ht × discount_pct / 100
        4. Fatura HT = base_ht - discount_amount
        5. TVA satır-bazında hesaplanır ama iskonto oranınca kırpılır
        6. TTC = HT + TVA
    """
    total_line_ht = ZERO
    total_line_tva = ZERO
    for line in invoice.lines.all():
        line.recompute()
        line.save(update_fields=["ht_amount", "tva_amount", "ttc_amount", "updated_at"])
        total_line_ht += line.ht_amount
        total_line_tva += line.tva_amount

    discount_pct = invoice.discount_pct or ZERO
    if discount_pct > 0:
        multiplier = (Decimal("100") - discount_pct) / Decimal("100")
        discount_amount = (total_line_ht * discount_pct / Decimal("100")).quantize(
            Decimal("0.01")
        )
        invoice.discount_amount = discount_amount
        invoice.total_ht = (total_line_ht - discount_amount).quantize(Decimal("0.01"))
        invoice.total_tva = (total_line_tva * multiplier).quantize(Decimal("0.01"))
    else:
        invoice.discount_amount = ZERO
        invoice.total_ht = total_line_ht
        invoice.total_tva = total_line_tva
    invoice.total_ttc = (invoice.total_ht + invoice.total_tva).quantize(Decimal("0.01"))
    invoice.save(update_fields=[
        "total_ht", "total_tva", "total_ttc",
        "discount_amount", "updated_at",
    ])


def _get_account(code: str) -> Account:
    try:
        return Account.objects.get(code=code)
    except Account.DoesNotExist:
        raise ValidationError(f"Zorunlu hesap tanımlı değil: {code} (seed_scf çalıştırıldı mı?)")


@transaction.atomic
def post_invoice(invoice: Invoice, *, user) -> Invoice:
    """Faturayı yevmiyeleştir.

    Satış: Müşteri (411) D | Gelir (70x) K + TVA tahsil (44571 = ~4457) K
    Alım:  Gider/Stok (6x/3x) D + TVA indirim (44566) D | Tedarikçi (401) K
    """
    if invoice.status != Invoice.Status.DRAFT:
        raise ValidationError("Yalnız DRAFT fatura muhasebeleştirilebilir.")
    if not invoice.lines.exists():
        raise ValidationError("Boş fatura muhasebeleştirilemez.")

    recompute_invoice(invoice)

    is_sales = invoice.type in {Invoice.Type.SALES, Invoice.Type.CREDIT_NOTE_SALES}
    period = get_or_create_period(invoice.date)
    _ensure_period_open(period)

    if is_sales:
        journal = JournalCode.objects.get(type=JournalCode.Type.SALES)
        third_party_account = _get_account("411")  # Müşteriler
    else:
        journal = JournalCode.objects.get(type=JournalCode.Type.PURCHASE)
        third_party_account = _get_account("401")  # Tedarikçiler

    lines: list[dict] = []

    for line in invoice.lines.all():
        # Gelir/gider satırı
        rev_acc = line.revenue_account or (
            _get_account("701") if is_sales else _get_account("601")
        )
        lines.append({
            "account": rev_acc,
            "debit": ZERO if is_sales else line.ht_amount,
            "credit": line.ht_amount if is_sales else ZERO,
            "description": line.description,
            "customer": invoice.customer if is_sales else None,
            "supplier": invoice.supplier if not is_sales else None,
        })
        # TVA
        if line.tva_amount > 0:
            tva_acc = (
                line.tva_rate.collected_account if is_sales
                else line.tva_rate.deductible_account
            )
            if tva_acc is None:
                tva_acc = _get_account("4457" if is_sales else "44566")
            lines.append({
                "account": tva_acc,
                "debit": ZERO if is_sales else line.tva_amount,
                "credit": line.tva_amount if is_sales else ZERO,
                "description": f"TVA {line.tva_rate.rate_pct}%",
            })

    # Cari karşı satır
    lines.append({
        "account": third_party_account,
        "debit": invoice.total_ttc if is_sales else ZERO,
        "credit": ZERO if is_sales else invoice.total_ttc,
        "description": f"Fatura {invoice.invoice_number}",
        "customer": invoice.customer if is_sales else None,
        "supplier": invoice.supplier if not is_sales else None,
    })

    entry = create_journal_entry(
        entry_number=f"{journal.code}-{invoice.invoice_number}",
        journal_code=journal,
        entry_date=invoice.date,
        description=f"Fatura {invoice.invoice_number}",
        reference=invoice.invoice_number,
        lines=lines,
    )
    post_journal_entry(entry, user=user)

    invoice.journal_entry = entry
    invoice.status = Invoice.Status.POSTED
    invoice.save(update_fields=["journal_entry", "status", "updated_at"])
    return invoice


@transaction.atomic
def create_sales_invoice_from_shipment(
    shipment,
    *,
    invoice_number: str,
    tva_rate: TVARate,
    unit_price_by_product: dict | None = None,
) -> Invoice:
    """Bir sevkiyattan otomatik satış faturası üretir. `unit_price_by_product` verilmezse
    SO satırındaki `unit_price` kullanılır."""
    period = get_or_create_period(shipment.shipped_date)
    inv = Invoice.objects.create(
        invoice_number=invoice_number, type=Invoice.Type.SALES,
        date=shipment.shipped_date, period=period,
        customer=shipment.customer,
        shipment_reference=shipment.shipment_number,
    )
    unit_price_by_product = unit_price_by_product or {}
    for line in shipment.lines.select_related(
        "output_container", "output_container__batch__recipe__product", "so_line",
    ):
        product = line.output_container.batch.recipe.product
        unit_price = unit_price_by_product.get(product.pk)
        if unit_price is None:
            unit_price = line.so_line.unit_price if line.so_line else ZERO
        il = InvoiceLine.objects.create(
            invoice=inv, sequence=line.pk,
            product=product,
            description=f"{product.name} · Parti {line.output_container.batch.batch_number}",
            quantity=line.quantity, unit_price=unit_price,
            tva_rate=tva_rate,
        )
        il.recompute()
        il.save(update_fields=["ht_amount", "tva_amount", "ttc_amount"])
    recompute_invoice(inv)
    return inv


@transaction.atomic
def create_purchase_invoice_from_receipt(
    receipt,
    *,
    invoice_number: str,
    tva_rate: TVARate,
) -> Invoice:
    """Bir mal kabulden satın alma faturası üretir."""
    period = get_or_create_period(receipt.received_date)
    inv = Invoice.objects.create(
        invoice_number=invoice_number, type=Invoice.Type.PURCHASE,
        date=receipt.received_date, period=period,
        supplier=receipt.supplier,
        receipt_reference=receipt.receipt_number,
    )
    for line in receipt.lines.select_related("raw_material", "po_line"):
        unit_price = line.po_line.unit_price if line.po_line else Decimal("0")
        il = InvoiceLine.objects.create(
            invoice=inv, sequence=line.pk,
            description=f"{line.raw_material.name}",
            quantity=line.quantity, unit_price=unit_price,
            tva_rate=tva_rate,
        )
        il.recompute()
        il.save(update_fields=["ht_amount", "tva_amount", "ttc_amount"])
    recompute_invoice(inv)
    return inv


# ---------------------------------------------------------------------------
# Ödeme
# ---------------------------------------------------------------------------

@transaction.atomic
def record_payment(
    *,
    payment_number: str,
    date: dt.date,
    direction: str,
    method: str,
    amount: Decimal,
    bank_account: Account,
    user,
    customer=None,
    supplier=None,
    invoices: Iterable[Invoice] | None = None,
    reference: str = "",
    notes: str = "",
) -> Payment:
    """Ödeme + yevmiye fişi + fatura eşleştirme."""
    if direction == Payment.Direction.INCOMING and customer is None:
        raise ValidationError("Tahsilat için müşteri gerekli.")
    if direction == Payment.Direction.OUTGOING and supplier is None:
        raise ValidationError("Tediye için tedarikçi gerekli.")

    payment = Payment.objects.create(
        payment_number=payment_number, date=date, direction=direction,
        method=method, amount=amount, customer=customer, supplier=supplier,
        bank_account=bank_account, reference=reference, notes=notes,
    )
    if invoices:
        payment.invoices.set(list(invoices))
        for inv in invoices:
            inv.amount_paid = (inv.amount_paid or ZERO) + amount
            inv.status = (
                Invoice.Status.PAID if inv.amount_paid >= inv.total_ttc
                else Invoice.Status.PARTIALLY_PAID
            )
            inv.save(update_fields=["amount_paid", "status", "updated_at"])

    # Yevmiye
    third = _get_account("411" if direction == Payment.Direction.INCOMING else "401")
    journal = JournalCode.objects.get(
        type=JournalCode.Type.BANK if method != Payment.Method.CASH
        else JournalCode.Type.CASH
    )

    if direction == Payment.Direction.INCOMING:
        # Banka D | Müşteri K
        lines = [
            {"account": bank_account, "debit": amount, "credit": ZERO,
                "description": f"Tahsilat {payment_number}"},
            {"account": third, "debit": ZERO, "credit": amount,
                "customer": customer, "description": f"Müşteri kapaması"},
        ]
    else:
        # Tedarikçi D | Banka K
        lines = [
            {"account": third, "debit": amount, "credit": ZERO,
                "supplier": supplier, "description": f"Tedarikçi kapaması"},
            {"account": bank_account, "debit": ZERO, "credit": amount,
                "description": f"Tediye {payment_number}"},
        ]
    entry = create_journal_entry(
        entry_number=f"{journal.code}-{payment_number}",
        journal_code=journal, entry_date=date,
        description=f"Ödeme {payment_number}", reference=payment_number,
        lines=lines,
    )
    post_journal_entry(entry, user=user)
    payment.journal_entry = entry
    payment.save(update_fields=["journal_entry", "updated_at"])
    return payment


# ---------------------------------------------------------------------------
# TVA G50
# ---------------------------------------------------------------------------

@transaction.atomic
def compute_tva_declaration(period: Period) -> TVADeclaration:
    """Dönemin faturalarından TVA topla ve G50 taslağı üret/güncelle."""
    collected = ZERO
    deductible = ZERO
    for inv in Invoice.objects.filter(
        period=period, status__in=[
            Invoice.Status.POSTED, Invoice.Status.PARTIALLY_PAID, Invoice.Status.PAID,
        ]
    ):
        if inv.type in {Invoice.Type.SALES}:
            collected += inv.total_tva or ZERO
        elif inv.type in {Invoice.Type.PURCHASE}:
            deductible += inv.total_tva or ZERO
        elif inv.type == Invoice.Type.CREDIT_NOTE_SALES:
            collected -= inv.total_tva or ZERO
        elif inv.type == Invoice.Type.CREDIT_NOTE_PURCHASE:
            deductible -= inv.total_tva or ZERO

    net = collected - deductible
    decl, _ = TVADeclaration.objects.update_or_create(
        period=period,
        defaults={
            "collected_tva": collected,
            "deductible_tva": deductible,
            "net_tva": net,
        },
    )
    return decl


@transaction.atomic
def submit_tva_declaration(
    decl: TVADeclaration, *, submitted_by, reference_number: str = ""
) -> TVADeclaration:
    decl.submitted_at = dt.date.today()
    decl.submitted_by = submitted_by
    decl.reference_number = reference_number
    decl.status = TVADeclaration.Status.SUBMITTED
    decl.save(update_fields=[
        "submitted_at", "submitted_by", "reference_number", "status", "updated_at",
    ])
    return decl


# ---------------------------------------------------------------------------
# Sabit kıymet amortismanı
# ---------------------------------------------------------------------------

@transaction.atomic
def run_monthly_depreciation(
    period: Period, *, user, book_journal_entries: bool = True
) -> list[DepreciationEntry]:
    """Aktif sabit kıymetler için o dönemin amortismanını hesaplar ve
    (opsiyonel) yevmiye fişini yazar.

    Sadece doğrusal yöntem — decliningi çağıran uygular.
    """
    entries: list[DepreciationEntry] = []
    assets = FixedAsset.objects.filter(status=FixedAsset.Status.ACTIVE)
    journal = JournalCode.objects.filter(
        type=JournalCode.Type.DEPRECIATION
    ).first() or JournalCode.objects.get(type=JournalCode.Type.OPERATIONS)

    for asset in assets:
        # Zaten yazıldıysa geç
        if DepreciationEntry.objects.filter(
            fixed_asset=asset, period=period
        ).exists():
            continue

        if asset.method == FixedAsset.Method.LINEAR:
            amount = asset.monthly_depreciation_linear
        else:
            # Basit azalan bakiye — üretimde daha rafine gerekir
            nbv = asset.net_book_value
            rate = (asset.declining_rate or Decimal("20")) / Decimal("100")
            amount = (nbv * rate / Decimal("12")).quantize(Decimal("0.01"))

        if amount <= 0:
            continue

        # Tam amortisman kontrolü
        remaining = asset.depreciable_base - asset.accumulated_depreciation
        if amount > remaining:
            amount = remaining
        if amount <= 0:
            asset.status = FixedAsset.Status.FULLY_DEPRECIATED
            asset.save(update_fields=["status", "updated_at"])
            continue

        cumulative = asset.accumulated_depreciation + amount
        dep = DepreciationEntry.objects.create(
            fixed_asset=asset, period=period,
            amount=amount, cumulative_amount=cumulative,
        )
        entries.append(dep)

        if book_journal_entries:
            first_day = dt.date(period.year, period.month, 1)
            entry = create_journal_entry(
                entry_number=f"DEP-{asset.asset_number}-{period.year}{period.month:02d}",
                journal_code=journal, entry_date=first_day,
                description=f"Amortisman {asset.asset_number} {period.year}-{period.month:02d}",
                reference=asset.asset_number,
                lines=[
                    {"account": asset.account_expense, "debit": amount, "credit": ZERO,
                        "description": f"Amortisman gideri {asset.name}"},
                    {"account": asset.account_accumulated_depreciation,
                        "debit": ZERO, "credit": amount,
                        "description": f"Birikmiş amortisman {asset.name}"},
                ],
            )
            post_journal_entry(entry, user=user)
            dep.journal_entry = entry
            dep.save(update_fields=["journal_entry", "updated_at"])

        # Tam amortisman
        if cumulative >= asset.depreciable_base:
            asset.status = FixedAsset.Status.FULLY_DEPRECIATED
            asset.save(update_fields=["status", "updated_at"])

    return entries


# ---------------------------------------------------------------------------
# Raporlar: Grand Livre + Balance
# ---------------------------------------------------------------------------

def general_ledger(
    account: Account,
    *,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
) -> dict:
    """Hesap için Grand Livre (defter-i kebir). Sadece POSTED fişler."""
    qs = JournalLine.objects.filter(
        account=account,
        entry__status=JournalEntry.Status.POSTED,
    )
    if date_from:
        qs = qs.filter(entry__entry_date__gte=date_from)
    if date_to:
        qs = qs.filter(entry__entry_date__lte=date_to)

    balance = ZERO
    lines = []
    for l in qs.select_related("entry", "entry__journal_code").order_by(
        "entry__entry_date", "entry_id", "id"
    ):
        balance += (l.debit or ZERO) - (l.credit or ZERO)
        lines.append({
            "date": l.entry.entry_date,
            "entry_number": l.entry.entry_number,
            "journal": l.entry.journal_code.code,
            "description": l.description or l.entry.description,
            "debit": l.debit,
            "credit": l.credit,
            "running_balance": balance,
        })
    totals = qs.aggregate(d=Sum("debit"), c=Sum("credit"))
    return {
        "account": {"code": account.code, "name": account.name},
        "period": {"from": date_from, "to": date_to},
        "total_debit": totals["d"] or ZERO,
        "total_credit": totals["c"] or ZERO,
        "closing_balance": (totals["d"] or ZERO) - (totals["c"] or ZERO),
        "lines": lines,
    }


def trial_balance(
    *,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    only_active: bool = True,
) -> dict:
    """Mizan — tüm yaprak hesaplar için borç/alacak toplamları + bakiye."""
    accounts = Account.objects.filter(is_leaf=True)
    if only_active:
        accounts = accounts.filter(is_active=True)

    rows = []
    total_debit = total_credit = ZERO
    for acc in accounts.order_by("code"):
        qs = JournalLine.objects.filter(
            account=acc, entry__status=JournalEntry.Status.POSTED,
        )
        if date_from:
            qs = qs.filter(entry__entry_date__gte=date_from)
        if date_to:
            qs = qs.filter(entry__entry_date__lte=date_to)
        agg = qs.aggregate(d=Sum("debit"), c=Sum("credit"))
        d = agg["d"] or ZERO
        c = agg["c"] or ZERO
        if d == 0 and c == 0:
            continue
        total_debit += d
        total_credit += c
        balance = d - c
        rows.append({
            "code": acc.code, "name": acc.name,
            "class": acc.account_class,
            "debit": d, "credit": c, "balance": balance,
        })
    return {
        "period": {"from": date_from, "to": date_to},
        "total_debit": total_debit,
        "total_credit": total_credit,
        "difference": total_debit - total_credit,  # 0 olmalı
        "rows": rows,
    }

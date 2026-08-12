"""SCF muhasebe testleri: hesap planı, yevmiye dengesi, fatura post,
TVA G50 hesabı, ödeme, sabit kıymet amortismanı, mizan.
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import call_command

from accounting.models import (
    Account,
    DepreciationEntry,
    FiscalYear,
    FixedAsset,
    Invoice,
    InvoiceLine,
    JournalCode,
    JournalEntry,
    Payment,
    Period,
    TVADeclaration,
    TVARate,
)
from accounting.services import (
    compute_tva_declaration,
    create_journal_entry,
    create_sales_invoice_from_shipment,
    general_ledger,
    get_or_create_period,
    post_invoice,
    post_journal_entry,
    record_payment,
    reverse_journal_entry,
    run_monthly_depreciation,
    trial_balance,
)


pytestmark = pytest.mark.django_db


@pytest.fixture
def scf_seeded(db):
    call_command("seed_scf")
    return True


@pytest.fixture
def fiscal_year_2026(db):
    return FiscalYear.objects.create(
        year=2026, start_date=dt.date(2026, 1, 1), end_date=dt.date(2026, 12, 31),
    )


@pytest.fixture
def accountant(db):
    return User.objects.create_user("acc", password="pw")


# ---- Hesap planı ----------------------------------------------------------

def test_seed_scf_creates_accounts_and_tva(scf_seeded):
    assert Account.objects.filter(code="411").exists()  # Müşteriler
    assert Account.objects.filter(code="701").exists()  # Satış geliri
    assert Account.objects.filter(code="4457").exists()  # TVA tahsil
    assert TVARate.objects.filter(code="TVA19", rate_pct=Decimal("19.00")).exists()
    assert JournalCode.objects.filter(code="JV").exists()


def test_account_class_derived_from_code(scf_seeded):
    acc = Account.objects.get(code="411")
    assert acc.account_class == "4"


def test_account_parent_hierarchy(scf_seeded):
    acc_411 = Account.objects.get(code="411")
    acc_41 = Account.objects.get(code="41")
    assert acc_411.parent == acc_41


# ---- Yevmiye ---------------------------------------------------------------

def test_create_and_post_balanced_entry(scf_seeded, fiscal_year_2026, accountant):
    jv = JournalCode.objects.get(code="JV")
    client = Account.objects.get(code="411")
    sales = Account.objects.get(code="701")

    entry = create_journal_entry(
        entry_number="TEST-JV-1", journal_code=jv,
        entry_date=dt.date(2026, 6, 15),
        description="Test satış",
        lines=[
            {"account": client, "debit": Decimal("1190"), "credit": Decimal("0")},
            {"account": sales, "debit": Decimal("0"), "credit": Decimal("1000")},
            {"account": Account.objects.get(code="4457"),
                "debit": Decimal("0"), "credit": Decimal("190")},
        ],
    )
    assert entry.is_balanced
    post_journal_entry(entry, user=accountant)
    entry.refresh_from_db()
    assert entry.status == JournalEntry.Status.POSTED
    assert entry.posted_by == accountant


def test_unbalanced_entry_rejected(scf_seeded, fiscal_year_2026, accountant):
    jv = JournalCode.objects.get(code="JV")
    entry = create_journal_entry(
        entry_number="TEST-BAD", journal_code=jv,
        entry_date=dt.date(2026, 6, 15), description="Dengesiz",
        lines=[
            {"account": Account.objects.get(code="411"),
                "debit": Decimal("100"), "credit": Decimal("0")},
            {"account": Account.objects.get(code="701"),
                "debit": Decimal("0"), "credit": Decimal("90")},
        ],
    )
    with pytest.raises(ValidationError):
        post_journal_entry(entry, user=accountant)


def test_cannot_post_to_non_leaf_account(scf_seeded, fiscal_year_2026):
    jv = JournalCode.objects.get(code="JV")
    # 41 (Clients et rattachés) is_leaf=False
    with pytest.raises(ValidationError):
        create_journal_entry(
            entry_number="TEST-NONLEAF", journal_code=jv,
            entry_date=dt.date(2026, 6, 15), description="X",
            lines=[
                {"account": Account.objects.get(code="41"),
                    "debit": Decimal("100"), "credit": Decimal("0")},
                {"account": Account.objects.get(code="701"),
                    "debit": Decimal("0"), "credit": Decimal("100")},
            ],
        )


def test_reverse_posted_entry(scf_seeded, fiscal_year_2026, accountant):
    jv = JournalCode.objects.get(code="JV")
    entry = create_journal_entry(
        entry_number="REV-TEST-1", journal_code=jv,
        entry_date=dt.date(2026, 6, 15), description="Test",
        lines=[
            {"account": Account.objects.get(code="411"),
                "debit": Decimal("100"), "credit": Decimal("0")},
            {"account": Account.objects.get(code="701"),
                "debit": Decimal("0"), "credit": Decimal("100")},
        ],
    )
    post_journal_entry(entry, user=accountant)
    reversal = reverse_journal_entry(entry, user=accountant, reason="Yanlış müşteri")
    entry.refresh_from_db()
    assert entry.status == JournalEntry.Status.CANCELLED
    assert entry.reversed_by == reversal
    assert reversal.total_debit == Decimal("100")


# ---- Fatura ---------------------------------------------------------------

@pytest.fixture
def customer(db):
    from masterdata.models import Customer
    return Customer.objects.create(code="CUS-ACC", name="Acc Test Müşteri")


def test_post_sales_invoice_generates_journal(scf_seeded, fiscal_year_2026,
                                                customer, accountant, product):
    tva = TVARate.objects.get(code="TVA19")
    period = get_or_create_period(dt.date(2026, 6, 15))
    inv = Invoice.objects.create(
        invoice_number="INV-001", type=Invoice.Type.SALES,
        date=dt.date(2026, 6, 15), period=period, customer=customer,
    )
    InvoiceLine.objects.create(
        invoice=inv, sequence=1, description="Test ürün",
        quantity=Decimal("100"), unit_price=Decimal("10"), tva_rate=tva,
    )
    post_invoice(inv, user=accountant)
    inv.refresh_from_db()
    assert inv.status == Invoice.Status.POSTED
    assert inv.total_ht == Decimal("1000.00")
    assert inv.total_tva == Decimal("190.00")
    assert inv.total_ttc == Decimal("1190.00")
    assert inv.journal_entry is not None
    assert inv.journal_entry.is_balanced


def test_payment_marks_invoice_paid(scf_seeded, fiscal_year_2026,
                                     customer, accountant, product):
    tva = TVARate.objects.get(code="TVA19")
    period = get_or_create_period(dt.date(2026, 6, 15))
    inv = Invoice.objects.create(
        invoice_number="INV-002", type=Invoice.Type.SALES,
        date=dt.date(2026, 6, 15), period=period, customer=customer,
    )
    InvoiceLine.objects.create(
        invoice=inv, sequence=1, description="X",
        quantity=Decimal("100"), unit_price=Decimal("10"), tva_rate=tva,
    )
    post_invoice(inv, user=accountant)

    bank = Account.objects.get(code="512")
    pay = record_payment(
        payment_number="PAY-001", date=dt.date(2026, 6, 20),
        direction=Payment.Direction.INCOMING, method=Payment.Method.BANK_TRANSFER,
        amount=Decimal("1190.00"), bank_account=bank, user=accountant,
        customer=customer, invoices=[inv], reference="BNK-123",
    )
    inv.refresh_from_db()
    assert inv.status == Invoice.Status.PAID
    assert inv.amount_paid == Decimal("1190.00")
    assert pay.journal_entry is not None


# ---- TVA G50 ---------------------------------------------------------------

def test_tva_g50_computation(scf_seeded, fiscal_year_2026, customer, accountant):
    from masterdata.models import Supplier
    supplier = Supplier.objects.create(code="SUP-ACC", name="Sup")
    tva = TVARate.objects.get(code="TVA19")
    period = get_or_create_period(dt.date(2026, 7, 15))

    # Satış: 1000 HT, 190 TVA
    s = Invoice.objects.create(
        invoice_number="INV-SALES-G50", type=Invoice.Type.SALES,
        date=dt.date(2026, 7, 10), period=period, customer=customer,
    )
    InvoiceLine.objects.create(
        invoice=s, sequence=1, description="S", quantity=Decimal("1"),
        unit_price=Decimal("1000"), tva_rate=tva,
    )
    post_invoice(s, user=accountant)

    # Alım: 500 HT, 95 TVA
    p = Invoice.objects.create(
        invoice_number="INV-PURCH-G50", type=Invoice.Type.PURCHASE,
        date=dt.date(2026, 7, 12), period=period, supplier=supplier,
    )
    InvoiceLine.objects.create(
        invoice=p, sequence=1, description="P", quantity=Decimal("1"),
        unit_price=Decimal("500"), tva_rate=tva,
    )
    post_invoice(p, user=accountant)

    decl = compute_tva_declaration(period)
    assert decl.collected_tva == Decimal("190.00")
    assert decl.deductible_tva == Decimal("95.00")
    assert decl.net_tva == Decimal("95.00")


# ---- Sabit kıymet + amortisman ---------------------------------------------

def test_linear_depreciation_generates_entries_and_journals(
    scf_seeded, fiscal_year_2026, accountant
):
    period = get_or_create_period(dt.date(2026, 3, 15))
    asset = FixedAsset.objects.create(
        asset_number="FA-001", name="Test makine",
        category=FixedAsset.Category.MACHINERY,
        purchase_date=dt.date(2026, 1, 1),
        purchase_cost=Decimal("12000"),
        useful_life_months=60,  # 5 yıl
        account_asset=Account.objects.get(code="2154"),
        account_accumulated_depreciation=Account.objects.get(code="28154"),
        account_expense=Account.objects.get(code="681"),
    )
    # Aylık = 12000 / 60 = 200
    assert asset.monthly_depreciation_linear == Decimal("200.00")

    entries = run_monthly_depreciation(period, user=accountant)
    assert len(entries) == 1
    dep = entries[0]
    assert dep.amount == Decimal("200.00")
    assert dep.journal_entry is not None
    assert dep.journal_entry.is_balanced

    # İkinci kez çağırma mükerrer üretmez
    again = run_monthly_depreciation(period, user=accountant)
    assert len(again) == 0

    asset.refresh_from_db()
    assert asset.accumulated_depreciation == Decimal("200.00")
    assert asset.net_book_value == Decimal("11800.00")


# ---- Raporlar --------------------------------------------------------------

def test_trial_balance_returns_zero_difference(scf_seeded, fiscal_year_2026, accountant):
    jv = JournalCode.objects.get(code="JV")
    entry = create_journal_entry(
        entry_number="TB-1", journal_code=jv, entry_date=dt.date(2026, 6, 1),
        description="Balance test",
        lines=[
            {"account": Account.objects.get(code="411"),
                "debit": Decimal("1000"), "credit": Decimal("0")},
            {"account": Account.objects.get(code="701"),
                "debit": Decimal("0"), "credit": Decimal("1000")},
        ],
    )
    post_journal_entry(entry, user=accountant)

    tb = trial_balance()
    assert tb["difference"] == Decimal("0")
    codes = {r["code"] for r in tb["rows"]}
    assert {"411", "701"} <= codes


def test_general_ledger_running_balance(scf_seeded, fiscal_year_2026, accountant):
    jv = JournalCode.objects.get(code="JV")
    client = Account.objects.get(code="411")
    sales = Account.objects.get(code="701")

    for i in range(3):
        e = create_journal_entry(
            entry_number=f"LG-{i}", journal_code=jv,
            entry_date=dt.date(2026, 6, 1 + i),
            description=f"Sat {i}",
            lines=[
                {"account": client, "debit": Decimal("100"), "credit": Decimal("0")},
                {"account": sales, "debit": Decimal("0"), "credit": Decimal("100")},
            ],
        )
        post_journal_entry(e, user=accountant)

    ledger = general_ledger(client)
    assert len(ledger["lines"]) == 3
    assert ledger["closing_balance"] == Decimal("300")
    assert ledger["lines"][-1]["running_balance"] == Decimal("300")


# ---- Shipment → invoice integration ---------------------------------------

def test_create_sales_invoice_from_shipment_integration(
    scf_seeded, fiscal_year_2026, order, released_lots, ibc, product, uom_kg
):
    """Sevkiyat → fatura otomatik üretimi."""
    from masterdata.models import Customer
    from production.models import OutputContainer, ProductionBatch
    from production.services import create_batch_from_order, record_dosing
    from sales.models import SalesOrder, SalesOrderLine
    from sales.services import ShipmentLineSpec, create_shipment

    cust = Customer.objects.create(code="CUS-ACC-INV", name="Test")
    so = SalesOrder.objects.create(
        order_number="SO-ACC-1", customer=cust, order_date=dt.date(2026, 6, 1),
    )
    SalesOrderLine.objects.create(
        so=so, product=product, quantity=Decimal("500"), unit=uom_kg,
        unit_price=Decimal("10"),
    )

    # Batch → release → ship
    batch = create_batch_from_order(order, batch_number="BATCH-INV-1")
    batch.transition_to(ProductionBatch.Status.IN_PROGRESS)
    for code, w in [("W", Decimal("300")), ("G", Decimal("7.5")),
                    ("SP", Decimal("175")), ("HD", Decimal("17.5"))]:
        c = batch.consumptions.get(raw_material__code=code)
        record_dosing(c, actual_weight=w)
    batch.transition_to(ProductionBatch.Status.COMPLETED)
    batch.qc_status = ProductionBatch.QCStatus.RELEASED
    batch.save()
    batch.transition_to(ProductionBatch.Status.RELEASED)
    oc = OutputContainer.objects.create(batch=batch, container=ibc, quantity=Decimal("500"))
    shipment = create_shipment(
        shipment_number="SH-ACC-1", customer=cust, shipped_date=dt.date(2026, 6, 10),
        so=so,
        lines=[ShipmentLineSpec(output_container=oc, so_line=so.lines.first())],
    )

    tva = TVARate.objects.get(code="TVA19")
    inv = create_sales_invoice_from_shipment(
        shipment, invoice_number="INV-SH-1", tva_rate=tva,
    )
    assert inv.total_ht == Decimal("5000.00")  # 500 × 10
    assert inv.total_tva == Decimal("950.00")  # %19
    assert inv.total_ttc == Decimal("5950.00")
    assert inv.customer == cust
    assert inv.shipment_reference == "SH-ACC-1"

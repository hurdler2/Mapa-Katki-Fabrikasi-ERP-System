"""Sprint 5: CustomerAdvance §23 + AdvanceAllocation testleri."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from accounting.models import (
    AdvanceAllocation,
    CustomerAdvance,
    FiscalYear,
    Invoice,
    InvoiceLine,
    Period,
    TVARate,
)
from accounting.services import allocate_advance_to_invoice, recompute_invoice
from masterdata.models import Customer, Product, UnitOfMeasure


pytestmark = pytest.mark.django_db


@pytest.fixture
def uom():
    return UnitOfMeasure.objects.create(code="kg", name="Kilogram")


@pytest.fixture
def product(uom):
    return Product.objects.create(code="ADX-A", name="ADX-A Test", unit=uom)


@pytest.fixture
def customer():
    return Customer.objects.create(code="CUS-ADV-1", name="Avans Test Musterisi")


@pytest.fixture
def fiscal():
    today = dt.date.today()
    return FiscalYear.objects.create(
        year=today.year,
        start_date=dt.date(today.year, 1, 1),
        end_date=dt.date(today.year, 12, 31),
    )


@pytest.fixture
def period(fiscal):
    today = dt.date.today()
    return Period.objects.create(
        year=today.year, month=today.month, fiscal_year=fiscal,
        status=Period.Status.OPEN,
    )


@pytest.fixture
def tva():
    return TVARate.objects.create(
        code="TVA19", name="TVA 19", rate_pct=Decimal("19.00"),
    )


def _mk_invoice(customer, period, tva, product, uom, amount_ht=Decimal("10000")):
    inv = Invoice.objects.create(
        invoice_number=f"INV-ADV-{Invoice.objects.count() + 1}",
        type=Invoice.Type.SALES,
        date=dt.date.today(),
        period=period,
        customer=customer,
    )
    InvoiceLine.objects.create(
        invoice=inv, sequence=1, product=product,
        description="Test",
        quantity=Decimal("1"), unit_price=amount_ht, tva_rate=tva,
    )
    recompute_invoice(inv)
    return inv


def test_customer_advance_open_default(customer):
    adv = CustomerAdvance.objects.create(
        advance_number="ADV-001", customer=customer,
        date=dt.date.today(), amount=Decimal("50000"),
    )
    assert adv.status == CustomerAdvance.Status.OPEN
    assert adv.remaining_amount == Decimal("50000")
    assert adv.allocated_total == Decimal("0")


def test_allocate_advance_partial(customer, period, tva, product, uom):
    adv = CustomerAdvance.objects.create(
        advance_number="ADV-002", customer=customer,
        date=dt.date.today(), amount=Decimal("50000"),
    )
    inv = _mk_invoice(customer, period, tva, product, uom, amount_ht=Decimal("30000"))
    ttc = inv.total_ttc
    assert ttc == Decimal("35700.00")  # 30000 × 1.19

    allocate_advance_to_invoice(adv, inv, amount=Decimal("20000"))

    inv.refresh_from_db()
    adv.refresh_from_db()
    assert inv.amount_paid == Decimal("20000")
    assert inv.status == Invoice.Status.PARTIALLY_PAID
    assert adv.status == CustomerAdvance.Status.OPEN
    assert adv.remaining_amount == Decimal("30000")


def test_allocate_advance_fully_pays_invoice(customer, period, tva, product, uom):
    adv = CustomerAdvance.objects.create(
        advance_number="ADV-003", customer=customer,
        date=dt.date.today(), amount=Decimal("50000"),
    )
    inv = _mk_invoice(customer, period, tva, product, uom, amount_ht=Decimal("30000"))
    allocate_advance_to_invoice(adv, inv, amount=inv.total_ttc)

    inv.refresh_from_db()
    assert inv.status == Invoice.Status.PAID


def test_allocate_beyond_remaining_fails(customer, period, tva, product, uom):
    adv = CustomerAdvance.objects.create(
        advance_number="ADV-004", customer=customer,
        date=dt.date.today(), amount=Decimal("10000"),
    )
    inv = _mk_invoice(customer, period, tva, product, uom, amount_ht=Decimal("30000"))
    with pytest.raises(ValidationError):
        allocate_advance_to_invoice(adv, inv, amount=Decimal("15000"))


def test_advance_becomes_fully_allocated(customer, period, tva, product, uom):
    adv = CustomerAdvance.objects.create(
        advance_number="ADV-005", customer=customer,
        date=dt.date.today(), amount=Decimal("10000"),
    )
    inv = _mk_invoice(customer, period, tva, product, uom, amount_ht=Decimal("30000"))
    allocate_advance_to_invoice(adv, inv, amount=Decimal("10000"))
    adv.refresh_from_db()
    assert adv.status == CustomerAdvance.Status.FULLY_ALLOCATED
    assert adv.remaining_amount == Decimal("0")


def test_allocate_different_customer_fails(customer, period, tva, product, uom):
    other = Customer.objects.create(code="CUS-OTHER", name="Diger")
    adv = CustomerAdvance.objects.create(
        advance_number="ADV-006", customer=other,
        date=dt.date.today(), amount=Decimal("10000"),
    )
    inv = _mk_invoice(customer, period, tva, product, uom, amount_ht=Decimal("30000"))
    with pytest.raises(ValidationError):
        allocate_advance_to_invoice(adv, inv, amount=Decimal("5000"))


def test_split_advance_across_two_invoices(customer, period, tva, product, uom):
    adv = CustomerAdvance.objects.create(
        advance_number="ADV-007", customer=customer,
        date=dt.date.today(), amount=Decimal("30000"),
    )
    inv1 = _mk_invoice(customer, period, tva, product, uom, amount_ht=Decimal("20000"))
    inv2 = _mk_invoice(customer, period, tva, product, uom, amount_ht=Decimal("20000"))

    allocate_advance_to_invoice(adv, inv1, amount=Decimal("15000"))
    allocate_advance_to_invoice(adv, inv2, amount=Decimal("15000"))

    adv.refresh_from_db()
    assert adv.remaining_amount == Decimal("0")
    assert adv.status == CustomerAdvance.Status.FULLY_ALLOCATED
    assert adv.allocations.count() == 2

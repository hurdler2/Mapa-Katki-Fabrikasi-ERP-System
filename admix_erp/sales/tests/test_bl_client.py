"""Sprint 3: BL Client → Fatura akışı testleri."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from masterdata.models import Customer
from production.models import OutputContainer, ProductionBatch
from production.services import create_batch_from_order, record_dosing
from sales.models import SalesOrder, SalesOrderLine, Shipment
from sales.services import (
    ShipmentLineSpec,
    create_invoice_from_bl,
    create_shipment,
    next_bl_number,
)


pytestmark = pytest.mark.django_db


@pytest.fixture
def customer(db):
    return Customer.objects.create(
        code="CUS-BL-1", name="Beton Cezayir SARL",
        default_discount_pct=Decimal("10.00"),
    )


@pytest.fixture
def so(customer, product, uom_kg):
    so = SalesOrder.objects.create(
        order_number="SO-BL-1", customer=customer,
        order_date=dt.date.today(), status=SalesOrder.Status.CONFIRMED,
    )
    SalesOrderLine.objects.create(
        so=so, product=product, quantity=Decimal("500"), unit=uom_kg,
        unit_price=Decimal("150.00"),
    )
    return so


def _released_batch(order, ibc, batch_number):
    batch = create_batch_from_order(order, batch_number=batch_number)
    batch.transition_to(ProductionBatch.Status.IN_PROGRESS)
    for code, w in [("W", Decimal("300")), ("G", Decimal("7.5")),
                    ("SP", Decimal("175")), ("HD", Decimal("17.5"))]:
        c = batch.consumptions.get(raw_material__code=code)
        record_dosing(c, actual_weight=w)
    batch.transition_to(ProductionBatch.Status.COMPLETED)
    batch.qc_status = ProductionBatch.QCStatus.RELEASED
    batch.save(update_fields=["qc_status"])
    oc = OutputContainer.objects.create(
        batch=batch, container=ibc, quantity=Decimal("500"),
    )
    return batch, oc


def _make_bl(order, released_lots, ibc, customer, so, bl_number):
    _, oc = _released_batch(order, ibc, f"B-{bl_number}")
    return create_shipment(
        shipment_number=bl_number, customer=customer,
        shipped_date=dt.date.today(), so=so,
        lines=[ShipmentLineSpec(
            output_container=oc, so_line=so.lines.first(),
            quantity=Decimal("500"),
        )],
    )


def test_bl_default_status_is_draft(order, released_lots, ibc, customer, so):
    bl = _make_bl(order, released_lots, ibc, customer, so, "BL-TEST-1")
    assert bl.status == Shipment.Status.DRAFT
    assert bl.invoice_id is None


def test_next_bl_number_format():
    n = next_bl_number()
    assert n.startswith("BL-")
    parts = n.split("-")
    assert len(parts) == 3
    assert len(parts[1]) == 6  # YYYYMM
    assert int(parts[2]) >= 1


def test_bl_total_amount(order, released_lots, ibc, customer, so):
    bl = _make_bl(order, released_lots, ibc, customer, so, "BL-TEST-2")
    # 500 kg × 150.00 = 75.000,00
    assert bl.total_amount == Decimal("75000.00")


def test_bl_to_invoice_creates_draft_invoice(order, released_lots, ibc, customer, so, fiscal_year):
    bl = _make_bl(order, released_lots, ibc, customer, so, "BL-TEST-3")
    inv = create_invoice_from_bl([bl], invoice_number="INV-BL-1")
    assert inv.invoice_number == "INV-BL-1"
    assert inv.customer_id == customer.pk
    assert inv.lines.count() == 1
    assert inv.discount_pct == Decimal("10.00")  # müşteri iskonto taşındı
    # BL de INVOICED oldu
    bl.refresh_from_db()
    assert bl.status == Shipment.Status.INVOICED
    assert bl.invoice_id == inv.pk


def test_bl_to_invoice_blocks_already_invoiced(order, released_lots, ibc, customer, so, fiscal_year):
    bl = _make_bl(order, released_lots, ibc, customer, so, "BL-TEST-4")
    create_invoice_from_bl([bl], invoice_number="INV-BL-4")
    bl.refresh_from_db()
    with pytest.raises(ValidationError):
        create_invoice_from_bl([bl], invoice_number="INV-BL-4-DUP")


def test_bl_to_invoice_rejects_mixed_customers(order, released_lots, ibc, customer, so, fiscal_year):
    """Aynı fatura altında iki farklı müşteri olamaz."""
    other = Customer.objects.create(code="CUS-BL-2", name="Diğer Müşteri")
    other_so = SalesOrder.objects.create(
        order_number="SO-BL-2", customer=other,
        order_date=dt.date.today(), status=SalesOrder.Status.CONFIRMED,
    )
    SalesOrderLine.objects.create(
        so=other_so, product=so.lines.first().product,
        quantity=Decimal("100"), unit=so.lines.first().unit,
        unit_price=Decimal("100.00"),
    )

    bl1 = _make_bl(order, released_lots, ibc, customer, so, "BL-TEST-5A")

    # ikinci IBC + BL için ikinci IBC yaratmak lazım
    from masterdata.models import Container, UnitOfMeasure
    uom_l = UnitOfMeasure.objects.get_or_create(code="l", defaults={"name": "Litre"})[0]
    ibc2 = Container.objects.create(
        code="IBC-OUT-02", name="Test IBC 2",
        container_type=Container.ContainerType.IBC,
        capacity=Decimal("1000"), unit=uom_l,
    )
    bl2 = _make_bl(order, released_lots, ibc2, other, other_so, "BL-TEST-5B")

    with pytest.raises(ValidationError):
        create_invoice_from_bl([bl1, bl2], invoice_number="INV-BL-MIX")


@pytest.fixture
def fiscal_year(db):
    from accounting.models import FiscalYear, TVARate
    today = dt.date.today()
    fy, _ = FiscalYear.objects.get_or_create(
        year=today.year,
        defaults={
            "start_date": dt.date(today.year, 1, 1),
            "end_date": dt.date(today.year, 12, 31),
        },
    )
    TVARate.objects.get_or_create(
        code="TVA19",
        defaults={"name": "TVA %19", "rate_pct": Decimal("19.00")},
    )
    return fy

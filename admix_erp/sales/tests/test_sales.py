"""Satış testleri: SO → sevkiyat → forward_trace müşteriye kadar uzanır."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from masterdata.models import Customer
from production.models import OutputContainer, ProductionBatch
from production.services import create_batch_from_order, forward_trace, record_dosing
from sales.models import SalesOrder, SalesOrderLine, Shipment, ShipmentLine
from sales.services import ShipmentLineSpec, create_shipment


pytestmark = pytest.mark.django_db


@pytest.fixture
def customer(db):
    return Customer.objects.create(code="CUS-100", name="Beton İnşaat Ltd.")


@pytest.fixture
def so(customer, product, uom_kg):
    so = SalesOrder.objects.create(
        order_number="SO-001", customer=customer,
        order_date=dt.date.today(), status=SalesOrder.Status.CONFIRMED,
    )
    SalesOrderLine.objects.create(so=so, product=product, quantity=Decimal("500"), unit=uom_kg)
    return so


def _make_released_batch(order, released_lots, ibc, batch_number):
    batch = create_batch_from_order(order, batch_number=batch_number)
    batch.transition_to(ProductionBatch.Status.IN_PROGRESS)
    for code, w in [("W", Decimal("300")), ("G", Decimal("7.5")),
                    ("SP", Decimal("175")), ("HD", Decimal("17.5"))]:
        c = batch.consumptions.get(raw_material__code=code)
        record_dosing(c, actual_weight=w)
    batch.transition_to(ProductionBatch.Status.COMPLETED)
    batch.qc_status = ProductionBatch.QCStatus.RELEASED
    batch.save(update_fields=["qc_status"])
    batch.transition_to(ProductionBatch.Status.RELEASED)
    oc = OutputContainer.objects.create(batch=batch, container=ibc, quantity=Decimal("500"))
    return batch, oc


def test_create_shipment_marks_ibc_and_updates_so(order, released_lots, ibc, customer, so):
    batch, oc = _make_released_batch(order, released_lots, ibc, "BATCH-SHIP-1")
    so_line = so.lines.first()
    shipment = create_shipment(
        shipment_number="SH-001", customer=customer,
        shipped_date=dt.date.today(), so=so,
        lines=[ShipmentLineSpec(output_container=oc, so_line=so_line, quantity=Decimal("500"))],
    )
    oc.refresh_from_db()
    assert oc.shipment_reference == "SH-001"
    so_line.refresh_from_db()
    assert so_line.shipped_qty == Decimal("500")
    so.refresh_from_db()
    assert so.status == SalesOrder.Status.SHIPPED
    assert shipment.lines.count() == 1


def test_cannot_ship_non_released_batch(order, released_lots, ibc, customer):
    """QC-RELEASED değilse sevk edilemez."""
    batch = create_batch_from_order(order, batch_number="BATCH-SHIP-2")
    batch.transition_to(ProductionBatch.Status.IN_PROGRESS)
    for code, w in [("W", Decimal("300")), ("G", Decimal("7.5")),
                    ("SP", Decimal("175")), ("HD", Decimal("17.5"))]:
        c = batch.consumptions.get(raw_material__code=code)
        record_dosing(c, actual_weight=w)
    batch.transition_to(ProductionBatch.Status.COMPLETED)
    oc = OutputContainer.objects.create(batch=batch, container=ibc, quantity=Decimal("500"))
    with pytest.raises(ValidationError):
        create_shipment(
            shipment_number="SH-BAD", customer=customer,
            shipped_date=dt.date.today(),
            lines=[ShipmentLineSpec(output_container=oc)],
        )


def test_cannot_ship_ibc_twice(order, released_lots, ibc, customer):
    batch, oc = _make_released_batch(order, released_lots, ibc, "BATCH-SHIP-3")
    create_shipment(
        shipment_number="SH-010", customer=customer, shipped_date=dt.date.today(),
        lines=[ShipmentLineSpec(output_container=oc)],
    )
    with pytest.raises(ValidationError):
        create_shipment(
            shipment_number="SH-011", customer=customer, shipped_date=dt.date.today(),
            lines=[ShipmentLineSpec(output_container=oc)],
        )


def test_forward_trace_extends_to_customer(order, released_lots, ibc, customer):
    batch, oc = _make_released_batch(order, released_lots, ibc, "BATCH-SHIP-4")
    create_shipment(
        shipment_number="SH-020", customer=customer, shipped_date=dt.date.today(),
        lines=[ShipmentLineSpec(output_container=oc)],
    )
    trace = forward_trace(released_lots["SP"])
    assert len(trace["batches"]) == 1
    outputs = trace["batches"][0]["outputs"]
    assert outputs[0]["container"] == "IBC-OUT-01"
    assert outputs[0]["shipment_reference"] == "SH-020"
    assert outputs[0]["customer"] == "Beton İnşaat Ltd."
    assert outputs[0]["customer_code"] == "CUS-100"

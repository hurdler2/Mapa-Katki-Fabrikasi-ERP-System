"""Satın alma testleri: PO → mal kabul → PENDING lot + stok hareketi."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from inventory.models import RawMaterialLot, StockMovement
from purchasing.models import PurchaseOrder, PurchaseOrderLine
from purchasing.services import ReceiptLineSpec, receive_goods


pytestmark = pytest.mark.django_db


@pytest.fixture
def po(supplier, raws, uom_kg):
    po = PurchaseOrder.objects.create(
        order_number="PO-001", supplier=supplier,
        order_date=dt.date.today(), status=PurchaseOrder.Status.OPEN,
    )
    PurchaseOrderLine.objects.create(
        po=po, raw_material=raws["SP"], quantity=Decimal("2000"), unit=uom_kg,
    )
    PurchaseOrderLine.objects.create(
        po=po, raw_material=raws["G"], quantity=Decimal("500"), unit=uom_kg,
    )
    return po


def test_receive_goods_creates_pending_lot_and_movement(po, supplier, raws):
    sp_line = po.lines.get(raw_material=raws["SP"])
    receipt = receive_goods(
        receipt_number="GR-001",
        supplier=supplier,
        received_date=dt.date.today(),
        po=po,
        lines=[
            ReceiptLineSpec(
                raw_material=raws["SP"], quantity=Decimal("1000"),
                lot_number="LOT-SP-A", coa_reference="COA-SP-A",
                po_line=sp_line,
            ),
        ],
    )
    assert receipt.lines.count() == 1
    lot = RawMaterialLot.objects.get(lot_number="LOT-SP-A")
    assert lot.qc_status == RawMaterialLot.QCStatus.PENDING
    assert lot.remaining_qty == Decimal("1000")
    assert lot.supplier == supplier

    mv = StockMovement.objects.get(lot=lot)
    assert mv.movement_type == StockMovement.MovementType.RECEIPT
    assert mv.quantity == Decimal("1000")
    assert mv.reference == "GR-001"

    sp_line.refresh_from_db()
    assert sp_line.received_qty == Decimal("1000")
    po.refresh_from_db()
    assert po.status == PurchaseOrder.Status.PARTIAL


def test_full_receipt_marks_po_received(po, supplier, raws):
    sp_line = po.lines.get(raw_material=raws["SP"])
    g_line = po.lines.get(raw_material=raws["G"])
    receive_goods(
        receipt_number="GR-002", supplier=supplier,
        received_date=dt.date.today(), po=po,
        lines=[
            ReceiptLineSpec(raw_material=raws["SP"], quantity=Decimal("2000"),
                            lot_number="LOT-SP-B", po_line=sp_line),
            ReceiptLineSpec(raw_material=raws["G"], quantity=Decimal("500"),
                            lot_number="LOT-G-B", po_line=g_line),
        ],
    )
    po.refresh_from_db()
    assert po.status == PurchaseOrder.Status.RECEIVED

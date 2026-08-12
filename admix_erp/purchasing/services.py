"""Satın alma servisleri: mal kabul → hammadde lotu + stok hareketi."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from django.core.exceptions import ValidationError
from django.db import transaction

from inventory.models import RawMaterialLot, StockMovement
from masterdata.models import Container, RawMaterial, Supplier

from .models import GoodsReceipt, GoodsReceiptLine, PurchaseOrder, PurchaseOrderLine


@dataclass
class ReceiptLineSpec:
    raw_material: RawMaterial
    quantity: Decimal
    lot_number: str
    expiry_date: dt.date | None = None
    coa_reference: str = ""
    container: Container | None = None
    po_line: PurchaseOrderLine | None = None
    unit_cost: Decimal | None = None  # None → po_line.unit_price'tan alınır


@transaction.atomic
def receive_goods(
    *,
    receipt_number: str,
    supplier: Supplier,
    received_date: dt.date,
    lines: Iterable[ReceiptLineSpec],
    po: PurchaseOrder | None = None,
    receiver: str = "",
    notes: str = "",
) -> GoodsReceipt:
    """Mal kabul yapar: her satır için PENDING RawMaterialLot ve StockMovement(RECEIPT) yazar.

    Lotlar `qc_status=PENDING` olarak açılır; kalite süreci `quality` app'inde
    yürütülür (release_lot çağrılana kadar tüketilemez).
    """
    lines = list(lines)
    if not lines:
        raise ValidationError("En az bir kabul satırı gereklidir.")

    receipt = GoodsReceipt.objects.create(
        receipt_number=receipt_number,
        po=po,
        supplier=supplier,
        received_date=received_date,
        receiver=receiver,
        notes=notes,
    )

    for spec in lines:
        qty = Decimal(spec.quantity)
        if qty <= 0:
            raise ValidationError("Kabul miktarı pozitif olmalı.")

        unit_cost = spec.unit_cost
        if unit_cost is None:
            unit_cost = spec.po_line.unit_price if spec.po_line else Decimal("0")

        lot = RawMaterialLot.objects.create(
            lot_number=spec.lot_number,
            raw_material=spec.raw_material,
            supplier=supplier,
            received_date=received_date,
            expiry_date=spec.expiry_date,
            received_qty=qty,
            remaining_qty=qty,
            qc_status=RawMaterialLot.QCStatus.PENDING,
            coa_reference=spec.coa_reference,
            unit_cost=Decimal(unit_cost),
            container=spec.container,
        )

        GoodsReceiptLine.objects.create(
            receipt=receipt,
            po_line=spec.po_line,
            raw_material=spec.raw_material,
            lot=lot,
            quantity=qty,
        )

        StockMovement.objects.create(
            lot=lot,
            movement_type=StockMovement.MovementType.RECEIPT,
            quantity=qty,
            reference=receipt.receipt_number,
            note=f"Mal kabul {receipt.receipt_number}",
        )

        if spec.po_line is not None:
            if spec.po_line.raw_material_id != spec.raw_material.id:
                raise ValidationError("PO satırı hammaddesi eşleşmiyor.")
            spec.po_line.received_qty = spec.po_line.received_qty + qty
            spec.po_line.save(update_fields=["received_qty", "updated_at"])

    if po is not None:
        po.refresh_status()

    return receipt

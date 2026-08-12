"""Satış servisleri: sevkiyat oluşturma, mamul IBC eşleştirme."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from django.core.exceptions import ValidationError
from django.db import transaction

from masterdata.models import Customer
from production.models import OutputContainer, ProductionBatch

from .models import SalesOrder, SalesOrderLine, Shipment, ShipmentLine


@dataclass
class ShipmentLineSpec:
    output_container: OutputContainer
    so_line: SalesOrderLine | None = None
    quantity: Decimal | None = None  # None → OutputContainer.quantity


@transaction.atomic
def create_shipment(
    *,
    shipment_number: str,
    customer: Customer,
    shipped_date: dt.date,
    lines: Iterable[ShipmentLineSpec],
    so: SalesOrder | None = None,
    carrier: str = "",
    vehicle_plate: str = "",
    notes: str = "",
) -> Shipment:
    """Sevkiyat oluşturur ve her satırda OutputContainer.shipment_reference set eder.

    Kurallar:
    - IBC (OutputContainer) yalnız QC-RELEASED partilerden sevk edilebilir.
    - Bir IBC iki kez sevk edilemez (OneToOne + shipment_reference kontrolü).
    - SO satırı verilmişse ürünler eşleşmelidir.
    """
    lines = list(lines)
    if not lines:
        raise ValidationError("En az bir sevkiyat satırı gereklidir.")

    shipment = Shipment.objects.create(
        shipment_number=shipment_number,
        so=so,
        customer=customer,
        shipped_date=shipped_date,
        carrier=carrier,
        vehicle_plate=vehicle_plate,
        notes=notes,
    )

    for spec in lines:
        oc = spec.output_container
        if oc.batch.qc_status != ProductionBatch.QCStatus.RELEASED:
            raise ValidationError(
                f"IBC {oc.container.code}: parti QC-RELEASED değil, sevk edilemez."
            )
        if oc.shipment_reference:
            raise ValidationError(
                f"IBC {oc.container.code} zaten '{oc.shipment_reference}' ile sevk edilmiş."
            )
        if spec.so_line is not None:
            if spec.so_line.product_id != oc.batch.recipe.product_id:
                raise ValidationError(
                    "SO satırı ürünü mamul partisinin ürünüyle eşleşmiyor."
                )

        qty = Decimal(spec.quantity) if spec.quantity is not None else oc.quantity

        ShipmentLine.objects.create(
            shipment=shipment,
            so_line=spec.so_line,
            output_container=oc,
            quantity=qty,
        )

        oc.shipment_reference = shipment.shipment_number
        oc.save(update_fields=["shipment_reference", "updated_at"])

        if spec.so_line is not None:
            spec.so_line.shipped_qty = spec.so_line.shipped_qty + qty
            spec.so_line.save(update_fields=["shipped_qty", "updated_at"])

    if so is not None:
        so.refresh_status()

    return shipment

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


# ---------------------------------------------------------------------------
# Sprint 3: BL Client → Fatura dönüşümü (UsineERP paritesi)
# ---------------------------------------------------------------------------

DEFAULT_TVA_CODE = "TVA19"


@transaction.atomic
def create_invoice_from_bl(
    shipments: Iterable[Shipment],
    *,
    invoice_number: str,
    invoice_date: dt.date | None = None,
):
    """Bir veya birkaç BL Client'i tek bir müşteri faturasına dönüştürür.

    Kurallar:
    - Tüm BL'ler aynı müşteriye ait olmalı.
    - Daha önce faturalanmamış (``invoice`` boş) BL'ler işlenir.
    - Statü DELIVERED veya DRAFT olmalı — INVOICED tekrar faturalanamaz.
    - Müşterinin default_discount_pct fatura başlığına taşınır.
    """
    from accounting.models import Invoice, InvoiceLine, TVARate
    from accounting.services import get_or_create_period, recompute_invoice

    shipments = list(shipments)
    if not shipments:
        raise ValidationError("En az bir BL seçmelisiniz.")

    customers = {s.customer_id for s in shipments}
    if len(customers) > 1:
        raise ValidationError("Tüm BL'ler aynı müşteriye ait olmalı.")
    customer = shipments[0].customer

    for s in shipments:
        if s.invoice_id is not None:
            raise ValidationError(f"{s.shipment_number} zaten faturalandı.")
        if s.status == Shipment.Status.INVOICED:
            raise ValidationError(
                f"{s.shipment_number} zaten INVOICED durumunda."
            )
        if s.status == Shipment.Status.CANCELLED:
            raise ValidationError(
                f"{s.shipment_number} iptal edilmiş — faturalanamaz."
            )
        if not s.lines.exists():
            raise ValidationError(f"{s.shipment_number} boş, satır yok.")

    invoice_date = invoice_date or dt.date.today()
    period = get_or_create_period(invoice_date)
    tva = TVARate.objects.get(code=DEFAULT_TVA_CODE)
    discount_pct = getattr(customer, "default_discount_pct", None) or Decimal("0")

    invoice = Invoice.objects.create(
        invoice_number=invoice_number,
        type=Invoice.Type.SALES,
        date=invoice_date,
        due_date=invoice_date + dt.timedelta(days=30),
        period=period,
        customer=customer,
        shipment_reference=", ".join(s.shipment_number for s in shipments),
        discount_pct=discount_pct,
        status=Invoice.Status.DRAFT,
    )

    seq = 1
    for s in shipments:
        for line in s.lines.select_related(
            "so_line__product", "output_container__container",
        ):
            price = line.so_line.unit_price if line.so_line else Decimal("0")
            product = line.so_line.product if line.so_line else None
            description = (
                f"{s.shipment_number} · "
                f"{product.name if product else 'Ürün'} · "
                f"IBC {line.output_container.container.code}"
            )
            InvoiceLine.objects.create(
                invoice=invoice,
                sequence=seq,
                product=product,
                description=description,
                quantity=line.quantity,
                unit_price=price,
                tva_rate=tva,
            )
            seq += 1

    recompute_invoice(invoice)

    Shipment.objects.filter(pk__in=[s.pk for s in shipments]).update(
        invoice=invoice, status=Shipment.Status.INVOICED,
    )
    return invoice


def next_bl_number() -> str:
    """Sıradaki BL numarasını üret: BL-YYYYMM-NNN."""
    today = dt.date.today()
    prefix = f"BL-{today.strftime('%Y%m')}-"
    last = (
        Shipment.objects
        .filter(shipment_number__startswith=prefix)
        .order_by("-shipment_number")
        .values_list("shipment_number", flat=True)
        .first()
    )
    n = 1
    if last:
        try:
            n = int(last.rsplit("-", 1)[1]) + 1
        except (IndexError, ValueError):
            n = Shipment.objects.filter(shipment_number__startswith=prefix).count() + 1
    return f"{prefix}{n:03d}"

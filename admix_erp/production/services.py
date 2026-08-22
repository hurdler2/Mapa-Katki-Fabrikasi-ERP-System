"""Üretim servisleri: parti oluşturma, dozaj kaydı, izlenebilirlik.

Tüm mutasyonlar `@transaction.atomic` bloklarında.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from inventory.models import RawMaterialLot, StockMovement
from masterdata.models import Container

from .models import (
    MaterialConsumption,
    OutputContainer,
    ProductionBatch,
    ProductionOrder,
)


# ---------------------------------------------------------------------------
# Parti oluşturma
# ---------------------------------------------------------------------------

@transaction.atomic
def create_batch_from_order(
    order: ProductionOrder,
    batch_number: str,
    reactor: Container | None = None,
) -> ProductionBatch:
    """Üretim emrinden yeni parti oluşturur.

    Reçeteyi `order.target_qty` için ölçekleyip, her satır için henüz
    `actual_weight=null` olan `MaterialConsumption` kayıtları açar.
    Reçete versiyonu partiye snapshot olarak bağlanır.
    """
    reactor = reactor or order.reactor
    if reactor.container_type != Container.ContainerType.REACTOR:
        raise ValidationError("Seçilen kap reaktör tipinde değil.")

    batch = ProductionBatch.objects.create(
        batch_number=batch_number,
        production_order=order,
        recipe=order.recipe,
        reactor=reactor,
        target_qty=order.target_qty,
        status=ProductionBatch.Status.PLANNED,
    )

    for scaled in order.recipe.scaled_lines(order.target_qty):
        MaterialConsumption.objects.create(
            batch=batch,
            raw_material=scaled["raw_material"],
            target_weight=scaled["quantity"],
            sequence=scaled["sequence"],
        )

    return batch


# ---------------------------------------------------------------------------
# FEFO lot tahsisi
# ---------------------------------------------------------------------------

def _select_fefo_lot(raw_material, required_qty: Decimal) -> RawMaterialLot | None:
    """En yakın son kullanma tarihli, RELEASED ve yeterli miktarlı lotu döner."""
    return (
        RawMaterialLot.objects
        .filter(
            raw_material=raw_material,
            qc_status=RawMaterialLot.QCStatus.RELEASED,
            remaining_qty__gte=required_qty,
        )
        .order_by("expiry_date", "received_date")
        .first()
    )


# ---------------------------------------------------------------------------
# Dozaj kaydı
# ---------------------------------------------------------------------------

@dataclass
class DosingResult:
    consumption: MaterialConsumption
    lot: RawMaterialLot
    deviation_pct: Decimal | None
    tolerance_exceeded: bool


@transaction.atomic
def record_dosing(
    consumption: MaterialConsumption,
    actual_weight: Decimal,
    lot: RawMaterialLot | None = None,
    source: str = MaterialConsumption.Source.MANUAL,
) -> DosingResult:
    """Gerçek tartımı işler.

    - Lot verilmediyse FEFO ile seçer (yalnız RELEASED lotlar).
    - Seçilen lotun `remaining_qty`'sini düşer.
    - `StockMovement(CONSUMPTION)` yazar.
    - Reçete satırındaki toleransa karşı sapmayı denetler; aşımda parti
      `QC_HOLD`'a çekilir (mümkün durumdan).
    """
    actual_weight = Decimal(actual_weight)
    if actual_weight <= 0:
        raise ValidationError("actual_weight pozitif olmalı.")

    # Kilit alarak lot seç (yarış durumunu önle)
    if lot is None:
        candidate = _select_fefo_lot(consumption.raw_material, actual_weight)
        if candidate is None:
            raise ValidationError(
                f"{consumption.raw_material.code} için yeterli RELEASED lot yok."
            )
        lot = RawMaterialLot.objects.select_for_update().get(pk=candidate.pk)
    else:
        lot = RawMaterialLot.objects.select_for_update().get(pk=lot.pk)
        if lot.raw_material_id != consumption.raw_material_id:
            raise ValidationError("Lot hammaddesi tüketim hammaddesiyle eşleşmiyor.")
        if lot.qc_status != RawMaterialLot.QCStatus.RELEASED:
            raise ValidationError("Yalnız RELEASED lot tüketilebilir.")
        if lot.remaining_qty < actual_weight:
            raise ValidationError("Lot bakiyesi tüketim için yetersiz.")

    lot.remaining_qty = lot.remaining_qty - actual_weight
    lot.save(update_fields=["remaining_qty", "updated_at"])

    StockMovement.objects.create(
        lot=lot,
        movement_type=StockMovement.MovementType.CONSUMPTION,
        quantity=-actual_weight,
        reference=consumption.batch.batch_number,
        document_source=f"Ordre de Production {consumption.batch.batch_number}",
        unit_price=lot.unit_cost,
        observations=f"Parti {consumption.batch.batch_number} · {consumption.raw_material.code}",
        note=f"Parti {consumption.batch.batch_number} · {consumption.raw_material.code}",
    )

    consumption.lot = lot
    consumption.actual_weight = actual_weight
    consumption.source = source
    consumption.dosed_at = timezone.now()
    consumption.save(update_fields=[
        "lot", "actual_weight", "source", "dosed_at", "updated_at",
    ])

    # Tolerans kontrolü
    tolerance_exceeded = False
    deviation = consumption.deviation_pct
    line_tolerance = (
        consumption.batch.recipe.lines
        .filter(raw_material=consumption.raw_material)
        .values_list("tolerance_pct", flat=True)
        .first()
    )
    if deviation is not None and line_tolerance is not None:
        if abs(deviation) > Decimal(line_tolerance):
            tolerance_exceeded = True
            batch = consumption.batch
            if batch.status == ProductionBatch.Status.COMPLETED:
                batch.transition_to(ProductionBatch.Status.QC_HOLD)

    return DosingResult(
        consumption=consumption,
        lot=lot,
        deviation_pct=deviation,
        tolerance_exceeded=tolerance_exceeded,
    )


# ---------------------------------------------------------------------------
# İzlenebilirlik
# ---------------------------------------------------------------------------

def backward_trace(batch: ProductionBatch) -> dict:
    """Parti → tüketilen tüm hammadde lotları + tedarikçiler + COA.

    Kalite denetimi / şikayet kökü için kullanılır.
    """
    items: list[dict] = []
    for c in batch.consumptions.select_related("raw_material", "lot", "lot__supplier").all():
        items.append({
            "raw_material": c.raw_material.code,
            "lot_number": c.lot.lot_number if c.lot else None,
            "supplier": c.lot.supplier.name if (c.lot and c.lot.supplier) else None,
            "coa_reference": c.lot.coa_reference if c.lot else None,
            "target_weight": c.target_weight,
            "actual_weight": c.actual_weight,
            "deviation_pct": c.deviation_pct,
            "dosed_at": c.dosed_at,
            "source": c.source,
        })
    return {
        "batch_number": batch.batch_number,
        "product": batch.recipe.product.code,
        "recipe_version": batch.recipe.version,
        "reactor": batch.reactor.code,
        "consumptions": items,
    }


def forward_trace(raw_lot: RawMaterialLot) -> dict:
    """Hammadde lotu → giren tüm partiler ve doldurulan IBC'ler.

    Recall (geri çağırma) kapsamının çıkarılması için kullanılır.
    """
    batches: list[dict] = []
    consumptions = (
        raw_lot.consumptions
        .select_related("batch", "batch__recipe__product")
        .prefetch_related("batch__outputs__container")
    )
    seen: set[int] = set()
    for c in consumptions:
        b = c.batch
        if b.pk in seen:
            continue
        seen.add(b.pk)
        outputs = []
        for o in b.outputs.all():
            sl = getattr(o, "shipment_line", None)
            outputs.append({
                "container": o.container.code,
                "quantity": o.quantity,
                "filled_at": o.filled_at,
                "shipment_reference": o.shipment_reference,
                "customer": sl.shipment.customer.name if sl else None,
                "customer_code": sl.shipment.customer.code if sl else None,
                "shipped_date": sl.shipment.shipped_date if sl else None,
            })
        batches.append({
            "batch_number": b.batch_number,
            "product": b.recipe.product.code,
            "status": b.status,
            "qc_status": b.qc_status,
            "outputs": outputs,
        })
    return {
        "lot_number": raw_lot.lot_number,
        "raw_material": raw_lot.raw_material.code,
        "supplier": raw_lot.supplier.name if raw_lot.supplier else None,
        "batches": batches,
    }

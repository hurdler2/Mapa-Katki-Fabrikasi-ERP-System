"""Uçtan uca: emir → parti → dozaj → IBC → backward/forward trace."""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from inventory.models import RawMaterialLot, StockMovement
from production.models import MaterialConsumption, OutputContainer, ProductionBatch
from production.services import (
    backward_trace,
    create_batch_from_order,
    forward_trace,
    record_dosing,
)


pytestmark = pytest.mark.django_db


def test_scaled_lines_factor(recipe):
    """target_qty=500, base=1000 → factor 0.5."""
    scaled = recipe.scaled_lines(Decimal("500"))
    by_code = {s["raw_material"].code: s["quantity"] for s in scaled}
    assert by_code["W"] == Decimal("300.0000")
    assert by_code["G"] == Decimal("7.5000")
    assert by_code["SP"] == Decimal("175.0000")
    assert by_code["HD"] == Decimal("17.5000")


def test_create_batch_from_order_creates_consumptions(order):
    batch = create_batch_from_order(order, batch_number="BATCH-001")
    assert batch.recipe_id == order.recipe_id
    codes = set(batch.consumptions.values_list("raw_material__code", flat=True))
    assert codes == {"W", "G", "SP", "HD"}
    weights = {c.raw_material.code: c.target_weight for c in batch.consumptions.all()}
    assert weights["W"] == Decimal("300.0000")
    assert weights["SP"] == Decimal("175.0000")
    # actual_weight henüz null
    assert all(c.actual_weight is None for c in batch.consumptions.all())


def test_record_dosing_fefo_and_stock_movement(order, released_lots):
    batch = create_batch_from_order(order, batch_number="BATCH-002")
    consumption = batch.consumptions.get(raw_material__code="SP")
    initial_qty = released_lots["SP"].remaining_qty

    result = record_dosing(consumption, actual_weight=Decimal("175"))

    assert result.lot.lot_number == "LOT-SP-001"
    consumption.refresh_from_db()
    assert consumption.actual_weight == Decimal("175")
    assert consumption.lot_id == released_lots["SP"].pk
    assert consumption.dosed_at is not None

    lot = RawMaterialLot.objects.get(pk=released_lots["SP"].pk)
    assert lot.remaining_qty == initial_qty - Decimal("175")

    mv = StockMovement.objects.filter(lot=lot).first()
    assert mv is not None
    assert mv.movement_type == StockMovement.MovementType.CONSUMPTION
    assert mv.quantity == Decimal("-175")


def test_record_dosing_rejects_non_released_lot(order, released_lots):
    batch = create_batch_from_order(order, batch_number="BATCH-003")
    consumption = batch.consumptions.get(raw_material__code="SP")
    bad = released_lots["SP"]
    bad.qc_status = RawMaterialLot.QCStatus.QUARANTINE
    bad.save(update_fields=["qc_status"])
    with pytest.raises(ValidationError):
        record_dosing(consumption, actual_weight=Decimal("175"), lot=bad)


def test_tolerance_exceeded_flags_qc_hold(order, released_lots):
    batch = create_batch_from_order(order, batch_number="BATCH-004")
    # Toleransı aşan sapma yaratmak için partiyi COMPLETED'a taşı
    batch.transition_to(ProductionBatch.Status.IN_PROGRESS)
    batch.transition_to(ProductionBatch.Status.COMPLETED)

    c = batch.consumptions.get(raw_material__code="SP")  # tolerans %0.50
    # Hedef 175 → %5 sapma
    result = record_dosing(c, actual_weight=Decimal("183.75"))
    assert result.tolerance_exceeded is True
    batch.refresh_from_db()
    assert batch.status == ProductionBatch.Status.QC_HOLD


def test_backward_trace_returns_lot_chain(order, released_lots, ibc):
    batch = create_batch_from_order(order, batch_number="BATCH-005")
    for code, weight in [("W", Decimal("300")), ("G", Decimal("7.5")),
                          ("SP", Decimal("175")), ("HD", Decimal("17.5"))]:
        c = batch.consumptions.get(raw_material__code=code)
        record_dosing(c, actual_weight=weight)

    trace = backward_trace(batch)
    assert trace["batch_number"] == "BATCH-005"
    assert trace["product"] == "ADX-100"
    codes = {item["raw_material"]: item for item in trace["consumptions"]}
    assert codes["SP"]["lot_number"] == "LOT-SP-001"
    assert codes["SP"]["supplier"] == "Test Kimya A.Ş."
    assert codes["SP"]["coa_reference"] == "COA-LOT-SP-001"


def test_forward_trace_from_lot_to_batches_and_ibcs(order, released_lots, ibc):
    batch = create_batch_from_order(order, batch_number="BATCH-006")
    c = batch.consumptions.get(raw_material__code="SP")
    record_dosing(c, actual_weight=Decimal("175"))

    OutputContainer.objects.create(
        batch=batch, container=ibc, quantity=Decimal("500"),
    )

    trace = forward_trace(released_lots["SP"])
    assert trace["lot_number"] == "LOT-SP-001"
    assert len(trace["batches"]) == 1
    b = trace["batches"][0]
    assert b["batch_number"] == "BATCH-006"
    assert len(b["outputs"]) == 1
    assert b["outputs"][0]["container"] == "IBC-OUT-01"


def test_batch_state_machine_rejects_invalid_transition(order):
    batch = create_batch_from_order(order, batch_number="BATCH-007")
    batch.transition_to(ProductionBatch.Status.IN_PROGRESS)
    with pytest.raises(ValidationError):
        # IN_PROGRESS'ten doğrudan RELEASED'a geçilemez
        batch.transition_to(ProductionBatch.Status.RELEASED)


def test_active_recipe_uniqueness(product, uom_kg):
    from formulation.models import Recipe
    r1 = Recipe.objects.create(product=product, version=1, base_batch_size=Decimal("1000"), unit=uom_kg, is_active=True)
    r2 = Recipe.objects.create(product=product, version=2, base_batch_size=Decimal("1000"), unit=uom_kg, is_active=True)
    r1.refresh_from_db()
    assert r1.is_active is False
    assert r2.is_active is True

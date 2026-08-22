"""Sprint 6: Stok düzeltmesi (Ajustement) testleri."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from inventory.models import StockAdjustment, StockMovement
from inventory.services import apply_stock_adjustment


pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return get_user_model().objects.create_user(username="wh1", password="x")


def test_adjustment_updates_lot_and_creates_movement(released_lots, user):
    lot = released_lots["W"]
    initial = lot.remaining_qty

    adj = apply_stock_adjustment(
        lot,
        adjustment_type=StockAdjustment.AdjustmentType.INVENTORY,
        reason="Envanter sayımı",
        new_qty=initial - Decimal("50"),
        performed_by=user,
    )

    lot.refresh_from_db()
    assert lot.remaining_qty == initial - Decimal("50")
    assert adj.delta == Decimal("-50")
    assert adj.movement is not None
    assert adj.movement.quantity == Decimal("-50")
    assert adj.movement.movement_type == StockMovement.MovementType.ADJUSTMENT


def test_loss_requires_justification(released_lots, user):
    """Perte (kayıp) türünde belge zorunlu — BR eşleniği."""
    lot = released_lots["SP"]
    with pytest.raises(ValidationError):
        apply_stock_adjustment(
            lot,
            adjustment_type=StockAdjustment.AdjustmentType.LOSS,
            reason="Yere döküldü",
            new_qty=lot.remaining_qty - Decimal("10"),
            performed_by=user,
        )


def test_loss_with_justification_ok(released_lots, user):
    lot = released_lots["SP"]
    doc = SimpleUploadedFile("rapor.pdf", b"pdf-bytes", content_type="application/pdf")
    adj = apply_stock_adjustment(
        lot,
        adjustment_type=StockAdjustment.AdjustmentType.LOSS,
        reason="Yere döküldü — kalibrasyon esnasında",
        new_qty=lot.remaining_qty - Decimal("10"),
        performed_by=user,
        document_type="Vardiya raporu",
        document_ref="RAP-2026-071",
        document=doc,
    )
    assert adj.pk is not None
    assert adj.document is not None


def test_inventory_type_does_not_need_justification(released_lots, user):
    """INVENTORY, CORRECTION, OTHER için belge zorunlu değil."""
    lot = released_lots["G"]
    adj = apply_stock_adjustment(
        lot,
        adjustment_type=StockAdjustment.AdjustmentType.CORRECTION,
        reason="Manuel giriş hatası düzeltildi",
        new_qty=lot.remaining_qty + Decimal("5"),
        performed_by=user,
    )
    assert adj.delta == Decimal("5")


def test_negative_qty_rejected(released_lots, user):
    lot = released_lots["W"]
    with pytest.raises(ValidationError):
        apply_stock_adjustment(
            lot,
            adjustment_type=StockAdjustment.AdjustmentType.INVENTORY,
            reason="Yanlış",
            new_qty=Decimal("-100"),
            performed_by=user,
        )

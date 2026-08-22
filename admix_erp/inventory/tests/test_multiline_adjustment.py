"""Sprint 8: Multi-line stok düzeltmesi testleri."""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from inventory.models import (
    StockAdjustment,
    StockAdjustmentLine,
    StockMovement,
)
from inventory.services import apply_multi_line_adjustment


pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return get_user_model().objects.create_user(username="wh_ml", password="x")


def test_multi_line_creates_lines_and_movements(released_lots, user):
    """Envanter sayımı — 3 lot düzeltmesi tek belgede."""
    lots = [released_lots["W"], released_lots["G"], released_lots["SP"]]
    lines = [
        {"lot": lots[0], "new_qty": lots[0].remaining_qty - Decimal("100"),
         "line_reason": "Sayım eksik"},
        {"lot": lots[1], "new_qty": lots[1].remaining_qty + Decimal("50"),
         "line_reason": "Sayım fazla"},
        {"lot": lots[2], "new_qty": lots[2].remaining_qty - Decimal("25"),
         "line_reason": "Kayıp"},
    ]

    adj = apply_multi_line_adjustment(
        adjustment_type=StockAdjustment.AdjustmentType.INVENTORY,
        reason="Aylık envanter sayımı — Ağustos 2026",
        lines=lines,
        performed_by=user,
    )

    assert adj.lot is None
    assert adj.lines.count() == 3
    # Toplam delta = -100 + 50 - 25 = -75
    assert adj.delta == Decimal("-75")

    # Her lotun stok güncellendi mi?
    for orig_lot, line in zip(lots, adj.lines.all().order_by("id")):
        orig_lot.refresh_from_db()
        assert orig_lot.remaining_qty == line.qty_after

    # Her satır bir StockMovement üretti mi?
    for line in adj.lines.all():
        assert line.movement is not None
        assert line.movement.movement_type == StockMovement.MovementType.ADJUSTMENT


def test_multi_line_empty_rejected(user):
    with pytest.raises(ValidationError):
        apply_multi_line_adjustment(
            adjustment_type=StockAdjustment.AdjustmentType.INVENTORY,
            reason="Boş", lines=[], performed_by=user,
        )


def test_multi_line_negative_qty_rejected(released_lots, user):
    lot = released_lots["W"]
    lines = [{"lot": lot, "new_qty": Decimal("-1"), "line_reason": ""}]
    with pytest.raises(ValidationError):
        apply_multi_line_adjustment(
            adjustment_type=StockAdjustment.AdjustmentType.INVENTORY,
            reason="Hata", lines=lines, performed_by=user,
        )


def test_multi_line_loss_requires_document(released_lots, user):
    """Kayıp türünde belge zorunlu — multi-line'da da geçerli."""
    lot = released_lots["W"]
    lines = [{"lot": lot, "new_qty": lot.remaining_qty - Decimal("10")}]
    with pytest.raises(ValidationError):
        apply_multi_line_adjustment(
            adjustment_type=StockAdjustment.AdjustmentType.LOSS,
            reason="Yer değişimi kayıpları",
            lines=lines, performed_by=user,
        )

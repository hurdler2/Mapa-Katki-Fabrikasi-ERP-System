"""Envanter servisleri: stok düzeltmesi (Ajustement)."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import RawMaterialLot, StockAdjustment, StockAdjustmentLine, StockMovement

if TYPE_CHECKING:  # pragma: no cover
    from django.core.files.uploadedfile import UploadedFile


@transaction.atomic
def apply_stock_adjustment(
    lot: RawMaterialLot,
    *,
    adjustment_type: str,
    reason: str,
    new_qty: Decimal,
    performed_by,
    adjustment_number: str | None = None,
    document_type: str = "",
    document_ref: str = "",
    document=None,
) -> StockAdjustment:
    """Bir lotun kalan miktarını ``new_qty`` yapar ve belgeler.

    - ``StockAdjustment`` kaydını üretir (justificatif zorunluluğunu ``clean()``
      kontrol eder).
    - Delta ile ``StockMovement`` (ADJUSTMENT) oluşturur.
    - ``RawMaterialLot.remaining_qty`` güncellenir.
    """
    new_qty = Decimal(new_qty)
    if new_qty < 0:
        raise ValidationError("Yeni miktar negatif olamaz.")

    qty_before = lot.remaining_qty
    delta = new_qty - qty_before

    if adjustment_number is None:
        stamp = timezone.now().strftime("%Y%m%d%H%M%S")
        adjustment_number = f"ADJ-{stamp}"

    adj = StockAdjustment(
        adjustment_number=adjustment_number,
        lot=lot,
        adjustment_type=adjustment_type,
        reason=reason,
        qty_before=qty_before,
        qty_after=new_qty,
        delta=delta,
        document_type=document_type,
        document_ref=document_ref,
        document=document,
        performed_by=performed_by,
        performed_at=timezone.now(),
    )
    adj.full_clean()
    adj.save()

    # Stok hareketi (zenginleştirilmiş — Sprint 7)
    mv = StockMovement.objects.create(
        lot=lot,
        movement_type=StockMovement.MovementType.ADJUSTMENT,
        quantity=delta,
        reference=adjustment_number,
        document_source=f"Ajustement {adjustment_number}",
        unit_price=lot.unit_cost,
        performed_by=performed_by,
        observations=f"{adjustment_type} — {reason[:180]}",
        note=f"{adjustment_type} — {reason[:100]}",
    )
    adj.movement = mv
    adj.save(update_fields=["movement", "updated_at"])

    # Lot güncelle
    lot.remaining_qty = new_qty
    lot.save(update_fields=["remaining_qty", "updated_at"])

    return adj


@transaction.atomic
def apply_multi_line_adjustment(
    *,
    adjustment_type: str,
    reason: str,
    lines: list[dict],
    performed_by,
    adjustment_number: str | None = None,
    document_type: str = "",
    document_ref: str = "",
    document=None,
) -> StockAdjustment:
    """Bir belgede birden fazla lot düzeltmesi (UsineERP paritesi).

    Her ``lines`` öğesi: ``{"lot": <RawMaterialLot>, "new_qty": Decimal,
                            "line_reason": str}``
    """
    if not lines:
        raise ValidationError("En az bir satır gereklidir.")

    if adjustment_number is None:
        stamp = timezone.now().strftime("%Y%m%d%H%M%S")
        adjustment_number = f"ADJ-M-{stamp}"

    # Ana belge (tek satır alanları boş)
    adj = StockAdjustment(
        adjustment_number=adjustment_number,
        lot=None,
        adjustment_type=adjustment_type,
        reason=reason,
        qty_before=None,
        qty_after=None,
        delta=Decimal("0"),
        document_type=document_type,
        document_ref=document_ref,
        document=document,
        performed_by=performed_by,
        performed_at=timezone.now(),
    )
    adj.full_clean()
    adj.save()

    total_delta = Decimal("0")
    for row in lines:
        lot: RawMaterialLot = row["lot"]
        new_qty = Decimal(row["new_qty"])
        if new_qty < 0:
            raise ValidationError(
                f"Lot {lot.lot_number}: yeni miktar negatif olamaz."
            )
        qty_before = lot.remaining_qty
        delta = new_qty - qty_before
        line_reason = row.get("line_reason", "")

        mv = StockMovement.objects.create(
            lot=lot,
            movement_type=StockMovement.MovementType.ADJUSTMENT,
            quantity=delta,
            reference=adjustment_number,
            document_source=f"Ajustement {adjustment_number} (multi-line)",
            unit_price=lot.unit_cost,
            performed_by=performed_by,
            observations=f"{adjustment_type} · {reason[:80]}"
                         + (f" — {line_reason[:60]}" if line_reason else ""),
        )
        StockAdjustmentLine.objects.create(
            adjustment=adj, lot=lot,
            qty_before=qty_before, qty_after=new_qty, delta=delta,
            line_reason=line_reason, movement=mv,
        )
        lot.remaining_qty = new_qty
        lot.save(update_fields=["remaining_qty", "updated_at"])
        total_delta += delta

    # Ana belgeye özet delta
    adj.delta = total_delta
    adj.save(update_fields=["delta", "updated_at"])
    return adj

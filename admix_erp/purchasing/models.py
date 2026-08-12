"""Satın alma modelleri: PO, PO satırı, mal kabul (goods receipt)."""
from __future__ import annotations

from decimal import Decimal

from django.db import models

from common.models import TimeStamped
from masterdata.models import RawMaterial, Supplier, UnitOfMeasure


class PurchaseOrder(TimeStamped):
    """Satın alma siparişi (PO)."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Taslak"
        OPEN = "OPEN", "Açık"
        PARTIAL = "PARTIAL", "Kısmi teslim"
        RECEIVED = "RECEIVED", "Tamamlandı"
        CANCELLED = "CANCELLED", "İptal"

    order_number = models.CharField("Sipariş No", max_length=40, unique=True)
    business_line = models.ForeignKey(
        "businessline.BusinessLine", on_delete=models.PROTECT,
        null=True, blank=True, related_name="purchase_orders",
        verbose_name="İş Kolu",
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT,
        related_name="purchase_orders", verbose_name="Tedarikçi",
    )
    order_date = models.DateField("Sipariş tarihi")
    expected_date = models.DateField("Beklenen tarih", null=True, blank=True)
    status = models.CharField(
        "Durum", max_length=12, choices=Status.choices, default=Status.DRAFT
    )
    notes = models.TextField("Notlar", blank=True)

    class Meta:
        verbose_name = "Satın Alma Siparişi"
        verbose_name_plural = "Satın Alma Siparişleri"
        ordering = ["-order_date", "-created_at"]

    def __str__(self) -> str:
        return f"{self.order_number} · {self.supplier.code}"

    def refresh_status(self) -> None:
        """Satırların received_qty toplamlarına göre statüyü güncelle."""
        lines = list(self.lines.all())
        if not lines:
            return
        total_target = sum(l.quantity for l in lines)
        total_received = sum(l.received_qty for l in lines)
        if total_received <= 0:
            new_status = PurchaseOrder.Status.OPEN
        elif total_received >= total_target:
            new_status = PurchaseOrder.Status.RECEIVED
        else:
            new_status = PurchaseOrder.Status.PARTIAL
        if new_status != self.status and self.status != PurchaseOrder.Status.CANCELLED:
            self.status = new_status
            self.save(update_fields=["status", "updated_at"])


class PurchaseOrderLine(TimeStamped):
    """PO satırı — hammadde başına sipariş miktarı."""

    po = models.ForeignKey(
        PurchaseOrder, on_delete=models.CASCADE,
        related_name="lines", verbose_name="Sipariş",
    )
    raw_material = models.ForeignKey(
        RawMaterial, on_delete=models.PROTECT,
        related_name="po_lines", verbose_name="Hammadde",
    )
    quantity = models.DecimalField("Miktar", max_digits=12, decimal_places=4)
    unit = models.ForeignKey(
        UnitOfMeasure, on_delete=models.PROTECT,
        related_name="po_lines", verbose_name="Birim",
    )
    unit_price = models.DecimalField(
        "Birim fiyat", max_digits=12, decimal_places=4, default=Decimal("0")
    )
    received_qty = models.DecimalField(
        "Kabul edilen miktar", max_digits=12, decimal_places=4, default=Decimal("0")
    )

    class Meta:
        verbose_name = "PO Satırı"
        verbose_name_plural = "PO Satırları"
        unique_together = (("po", "raw_material"),)

    def __str__(self) -> str:
        return f"{self.po.order_number} · {self.raw_material.code} × {self.quantity}"

    @property
    def outstanding_qty(self) -> Decimal:
        return self.quantity - self.received_qty


class GoodsReceipt(TimeStamped):
    """Mal kabul başlığı. Tek bir kabulde birden fazla lot oluşabilir."""

    receipt_number = models.CharField("Kabul No", max_length=40, unique=True)
    po = models.ForeignKey(
        PurchaseOrder, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="receipts", verbose_name="Sipariş",
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT,
        related_name="receipts", verbose_name="Tedarikçi",
    )
    received_date = models.DateField("Kabul tarihi")
    receiver = models.CharField("Teslim alan", max_length=120, blank=True)
    notes = models.TextField("Notlar", blank=True)

    class Meta:
        verbose_name = "Mal Kabul"
        verbose_name_plural = "Mal Kabuller"
        ordering = ["-received_date", "-created_at"]

    def __str__(self) -> str:
        return f"{self.receipt_number} · {self.supplier.code}"


class GoodsReceiptLine(TimeStamped):
    """Mal kabul satırı — bir hammadde lotu oluşturur."""

    receipt = models.ForeignKey(
        GoodsReceipt, on_delete=models.CASCADE,
        related_name="lines", verbose_name="Kabul",
    )
    po_line = models.ForeignKey(
        PurchaseOrderLine, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="receipt_lines", verbose_name="PO Satırı",
    )
    raw_material = models.ForeignKey(
        RawMaterial, on_delete=models.PROTECT,
        related_name="receipt_lines", verbose_name="Hammadde",
    )
    lot = models.OneToOneField(
        "inventory.RawMaterialLot", on_delete=models.PROTECT,
        related_name="receipt_line", verbose_name="Oluşturulan Lot",
    )
    quantity = models.DecimalField("Miktar", max_digits=12, decimal_places=4)

    class Meta:
        verbose_name = "Mal Kabul Satırı"
        verbose_name_plural = "Mal Kabul Satırları"

    def __str__(self) -> str:
        return f"{self.receipt.receipt_number} · {self.raw_material.code} → {self.lot.lot_number}"

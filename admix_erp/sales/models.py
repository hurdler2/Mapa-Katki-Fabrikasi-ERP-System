"""Satış modelleri: müşteri siparişi, satırı, sevkiyat, sevkiyat satırı."""
from __future__ import annotations

from decimal import Decimal

from django.db import models

from common.models import TimeStamped
from masterdata.models import Customer, Product, UnitOfMeasure
from production.models import OutputContainer


class SalesOrder(TimeStamped):
    """Müşteri siparişi."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Taslak"
        CONFIRMED = "CONFIRMED", "Onaylandı"
        PARTIAL = "PARTIAL", "Kısmi sevk"
        SHIPPED = "SHIPPED", "Sevk edildi"
        CANCELLED = "CANCELLED", "İptal"

    order_number = models.CharField("Sipariş No", max_length=40, unique=True)
    business_line = models.ForeignKey(
        "businessline.BusinessLine", on_delete=models.PROTECT,
        null=True, blank=True, related_name="sales_orders",
        verbose_name="İş Kolu",
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT,
        related_name="sales_orders", verbose_name="Müşteri",
    )
    order_date = models.DateField("Sipariş tarihi")
    delivery_date = models.DateField("Sevk tarihi", null=True, blank=True)
    status = models.CharField(
        "Durum", max_length=12, choices=Status.choices, default=Status.DRAFT
    )
    notes = models.TextField("Notlar", blank=True)

    class Meta:
        verbose_name = "Müşteri Siparişi"
        verbose_name_plural = "Müşteri Siparişleri"
        ordering = ["-order_date", "-created_at"]

    def __str__(self) -> str:
        return f"{self.order_number} · {self.customer.code}"

    def refresh_status(self) -> None:
        lines = list(self.lines.all())
        if not lines:
            return
        total_ordered = sum(l.quantity for l in lines)
        total_shipped = sum(l.shipped_qty for l in lines)
        if total_shipped <= 0:
            new_status = SalesOrder.Status.CONFIRMED
        elif total_shipped >= total_ordered:
            new_status = SalesOrder.Status.SHIPPED
        else:
            new_status = SalesOrder.Status.PARTIAL
        if new_status != self.status and self.status not in {
            SalesOrder.Status.DRAFT, SalesOrder.Status.CANCELLED
        }:
            self.status = new_status
            self.save(update_fields=["status", "updated_at"])


class SalesOrderLine(TimeStamped):
    """Müşteri siparişi satırı."""

    so = models.ForeignKey(
        SalesOrder, on_delete=models.CASCADE,
        related_name="lines", verbose_name="Sipariş",
    )
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT,
        related_name="so_lines", verbose_name="Ürün",
    )
    quantity = models.DecimalField("Miktar", max_digits=12, decimal_places=4)
    unit = models.ForeignKey(
        UnitOfMeasure, on_delete=models.PROTECT,
        related_name="so_lines", verbose_name="Birim",
    )
    unit_price = models.DecimalField(
        "Birim fiyat", max_digits=12, decimal_places=4, default=Decimal("0")
    )
    shipped_qty = models.DecimalField(
        "Sevk edilen miktar", max_digits=12, decimal_places=4, default=Decimal("0")
    )

    class Meta:
        verbose_name = "SO Satırı"
        verbose_name_plural = "SO Satırları"
        unique_together = (("so", "product"),)

    def __str__(self) -> str:
        return f"{self.so.order_number} · {self.product.code} × {self.quantity}"

    @property
    def outstanding_qty(self) -> Decimal:
        return self.quantity - self.shipped_qty


class Shipment(TimeStamped):
    """Sevkiyat / irsaliye başlığı."""

    shipment_number = models.CharField("Sevk No / İrsaliye", max_length=40, unique=True)
    so = models.ForeignKey(
        SalesOrder, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="shipments", verbose_name="Sipariş",
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT,
        related_name="shipments", verbose_name="Müşteri",
    )
    shipped_date = models.DateField("Sevk tarihi")
    carrier = models.CharField("Taşıyıcı", max_length=120, blank=True)
    vehicle_plate = models.CharField("Araç plaka", max_length=30, blank=True)
    notes = models.TextField("Notlar", blank=True)

    class Meta:
        verbose_name = "Sevkiyat"
        verbose_name_plural = "Sevkiyatlar"
        ordering = ["-shipped_date", "-created_at"]

    def __str__(self) -> str:
        return f"{self.shipment_number} · {self.customer.code}"


class ShipmentLine(TimeStamped):
    """Sevkiyat satırı — bir OutputContainer (IBC) müşteriye eşleşir."""

    shipment = models.ForeignKey(
        Shipment, on_delete=models.CASCADE,
        related_name="lines", verbose_name="Sevkiyat",
    )
    so_line = models.ForeignKey(
        SalesOrderLine, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="shipment_lines", verbose_name="SO Satırı",
    )
    output_container = models.OneToOneField(
        OutputContainer, on_delete=models.PROTECT,
        related_name="shipment_line", verbose_name="Mamul IBC",
    )
    quantity = models.DecimalField("Miktar", max_digits=12, decimal_places=4)

    class Meta:
        verbose_name = "Sevkiyat Satırı"
        verbose_name_plural = "Sevkiyat Satırları"

    def __str__(self) -> str:
        return f"{self.shipment.shipment_number} · IBC {self.output_container.container.code}"

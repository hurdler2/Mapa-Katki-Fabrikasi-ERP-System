"""Stok modelleri: hammadde lotu ve stok hareketi."""
from __future__ import annotations

from decimal import Decimal

from django.db import models
from simple_history.models import HistoricalRecords

from common.models import TimeStamped
from masterdata.models import Container, RawMaterial, Supplier


class RawMaterialLot(TimeStamped):
    """Hammadde lotu — izlenebilirliğin giriş düğümü."""

    class QCStatus(models.TextChoices):
        PENDING = "PENDING", "Beklemede"
        RELEASED = "RELEASED", "Serbest"
        QUARANTINE = "QUARANTINE", "Karantina"
        REJECTED = "REJECTED", "Reddedildi"

    lot_number = models.CharField("Lot No", max_length=60, unique=True)
    raw_material = models.ForeignKey(
        RawMaterial, on_delete=models.PROTECT, related_name="lots", verbose_name="Hammadde"
    )
    business_line = models.ForeignKey(
        "businessline.BusinessLine", on_delete=models.PROTECT,
        null=True, blank=True, related_name="raw_material_lots",
        verbose_name="İş Kolu",
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="lots", verbose_name="Tedarikçi",
    )
    received_date = models.DateField("Kabul tarihi")
    expiry_date = models.DateField("Son kullanma", null=True, blank=True)
    received_qty = models.DecimalField("Kabul miktarı", max_digits=12, decimal_places=4)
    remaining_qty = models.DecimalField("Kalan miktar", max_digits=12, decimal_places=4)
    qc_status = models.CharField(
        "Kalite durumu", max_length=16, choices=QCStatus.choices, default=QCStatus.PENDING
    )
    coa_reference = models.CharField("COA referansı", max_length=120, blank=True)
    unit_cost = models.DecimalField(
        "Birim maliyet", max_digits=12, decimal_places=4, default=Decimal("0"),
        help_text="Kabul anındaki birim fiyat (PO'dan kopyalanır).",
    )
    container = models.ForeignKey(
        Container, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="lots", verbose_name="Kap",
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Hammadde Lotu"
        verbose_name_plural = "Hammadde Lotları"
        ordering = ["expiry_date", "received_date"]

    def __str__(self) -> str:
        return f"{self.lot_number} · {self.raw_material.code}"


class StockMovement(TimeStamped):
    """Stok hareketi (audit trail). Silinmez; iptal ters kayıtla yapılır."""

    class MovementType(models.TextChoices):
        RECEIPT = "RECEIPT", "Kabul"
        CONSUMPTION = "CONSUMPTION", "Tüketim"
        ADJUSTMENT = "ADJUSTMENT", "Düzeltme"

    lot = models.ForeignKey(
        RawMaterialLot, on_delete=models.PROTECT, related_name="movements", verbose_name="Lot"
    )
    movement_type = models.CharField(
        "Hareket tipi", max_length=16, choices=MovementType.choices
    )
    quantity = models.DecimalField("Miktar (+/−)", max_digits=12, decimal_places=4)
    reference = models.CharField("Referans", max_length=120, blank=True)
    timestamp = models.DateTimeField("Zaman damgası", auto_now_add=True)
    note = models.TextField("Not", blank=True)

    class Meta:
        verbose_name = "Stok Hareketi"
        verbose_name_plural = "Stok Hareketleri"
        ordering = ["-timestamp"]

    def __str__(self) -> str:
        return f"{self.get_movement_type_display()} · {self.lot.lot_number} · {self.quantity}"

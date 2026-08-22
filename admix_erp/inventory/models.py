"""Stok modelleri: hammadde lotu, stok hareketi ve düzeltme (Ajustement)."""
from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
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
    document_source = models.CharField(
        "Document source", max_length=200, blank=True,
        help_text="Belge kaynağı — Ör. 'Ordre de Production OP-2026-0001', 'Ajustement ADJ-2026-0002'.",
    )
    unit_price = models.DecimalField(
        "Prix unitaire", max_digits=12, decimal_places=4, null=True, blank=True,
        help_text="Hareket anındaki birim fiyat (varsa).",
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="stock_movements",
        verbose_name="Opérateur",
    )
    observations = models.TextField("Observations", blank=True)
    timestamp = models.DateTimeField("Zaman damgası", auto_now_add=True)
    note = models.TextField("Not", blank=True)

    class Meta:
        verbose_name = "Stok Hareketi"
        verbose_name_plural = "Stok Hareketleri"
        ordering = ["-timestamp"]

    def __str__(self) -> str:
        return f"{self.get_movement_type_display()} · {self.lot.lot_number} · {self.quantity}"


# ---------------------------------------------------------------------------
# Sprint 6 — Stok Düzeltmesi (Ajustement de stock)
# ---------------------------------------------------------------------------

class StockAdjustment(TimeStamped):
    """Ajustement de stock — belgeli stok düzeltmesi.

    UsineERP paritesi:
    - Tür (envanter, fire, kayıp, iade vs.)
    - Motif (serbest metin gerekçe)
    - Qté avant → Qté après → Delta (otomatik)
    - Document justificatif (isteğe bağlı ama bazı tiplerde zorunlu)

    Kaydedildiğinde arka planda ilgili ``RawMaterialLot.remaining_qty``
    güncellenir ve ``StockMovement`` (ADJUSTMENT) yaratılır.
    """

    class AdjustmentType(models.TextChoices):
        INVENTORY = "INVENTORY", "Envanter sayımı (Inventaire)"
        LOSS = "LOSS", "Kayıp / Fire (Perte)"
        DAMAGE = "DAMAGE", "Hasar (Dégât)"
        RETURN = "RETURN", "Tedarikçiye iade"
        CORRECTION = "CORRECTION", "Düzeltme (Correction)"
        OTHER = "OTHER", "Diğer"

    REQUIRES_JUSTIFICATION = {
        AdjustmentType.LOSS,
        AdjustmentType.DAMAGE,
        AdjustmentType.RETURN,
    }

    adjustment_number = models.CharField(
        "Ajustement No", max_length=40, unique=True,
    )
    lot = models.ForeignKey(
        RawMaterialLot, on_delete=models.PROTECT,
        related_name="adjustments", verbose_name="Lot (tek satırlık)",
        null=True, blank=True,
        help_text="Tek satırlık ajustement için. Multi-line ise lines kullan.",
    )
    adjustment_type = models.CharField(
        "Type d'ajustement", max_length=16, choices=AdjustmentType.choices,
    )
    reason = models.TextField(
        "Motif",
        help_text="Düzeltme sebebi — envanter farkı, döküntü, kırılma vs.",
    )
    qty_before = models.DecimalField(
        "Qté avant", max_digits=12, decimal_places=4, null=True, blank=True,
    )
    qty_after = models.DecimalField(
        "Qté après", max_digits=12, decimal_places=4, null=True, blank=True,
    )
    delta = models.DecimalField(
        "Delta", max_digits=12, decimal_places=4, default=0,
        help_text="Tek satırlık ajustement için qty_after − qty_before.",
    )
    document_type = models.CharField(
        "Document type", max_length=80, blank=True,
        help_text="Örn. Rapor No, Envanter listesi, İç yazışma.",
    )
    document_ref = models.CharField(
        "Document référence", max_length=120, blank=True,
    )
    document = models.FileField(
        "Document justificatif",
        upload_to="stock_adjustments/", null=True, blank=True,
        help_text="Perte / Dégât / Retour için zorunlu.",
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="stock_adjustments", verbose_name="Yapan",
    )
    performed_at = models.DateTimeField("Zaman")
    movement = models.OneToOneField(
        StockMovement, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="adjustment", verbose_name="Stok hareketi",
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Ajustement de stock"
        verbose_name_plural = "Ajustements de stock"
        ordering = ["-performed_at"]

    def __str__(self) -> str:
        return f"{self.adjustment_number} · {self.lot.lot_number} · Δ {self.delta}"

    def clean(self) -> None:
        """Delta = after - before; belirli türlerde justificatif zorunlu."""
        super().clean()
        # Delta oto-set (form dolduranın kolaylığı için) — tek satırlı ise
        if self.qty_before is not None and self.qty_after is not None:
            self.delta = self.qty_after - self.qty_before

        if self.adjustment_type in self.REQUIRES_JUSTIFICATION and not self.document:
            raise ValidationError({
                "document": (
                    "Perte / Dégât / Retour için justificatif belge zorunlu."
                ),
            })


class StockAdjustmentLine(TimeStamped):
    """Multi-line ajustement satırı — bir StockAdjustment belgesi
    birden fazla lot düzeltmesini kapsayabilir (envanter sayımı gibi).
    """

    adjustment = models.ForeignKey(
        StockAdjustment, on_delete=models.CASCADE,
        related_name="lines", verbose_name="Ajustement",
    )
    lot = models.ForeignKey(
        RawMaterialLot, on_delete=models.PROTECT,
        related_name="adjustment_lines", verbose_name="Lot",
    )
    qty_before = models.DecimalField(
        "Qté avant", max_digits=12, decimal_places=4,
    )
    qty_after = models.DecimalField(
        "Qté après", max_digits=12, decimal_places=4,
    )
    delta = models.DecimalField(
        "Delta", max_digits=12, decimal_places=4,
    )
    line_reason = models.CharField(
        "Satır motifi", max_length=200, blank=True,
        help_text="Ana motif dışı, bu satıra özel not.",
    )
    movement = models.OneToOneField(
        StockMovement, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="adjustment_line", verbose_name="Stok hareketi",
    )

    class Meta:
        verbose_name = "Ajustement Satırı"
        verbose_name_plural = "Ajustement Satırları"
        ordering = ["adjustment", "id"]

    def __str__(self) -> str:
        return f"{self.adjustment.adjustment_number} · {self.lot.lot_number} · Δ {self.delta}"

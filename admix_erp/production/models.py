"""Üretim modelleri: emir, parti, tüketim, çıkış kabı."""
from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from simple_history.models import HistoricalRecords

from common.models import TimeStamped
from formulation.models import Recipe
from inventory.models import RawMaterialLot
from masterdata.models import Container, Product, RawMaterial, UnitOfMeasure


# Parti durum geçişleri (state machine)
BATCH_TRANSITIONS: dict[str, set[str]] = {
    "PLANNED": {"IN_PROGRESS", "CANCELLED"},
    "IN_PROGRESS": {"COMPLETED", "CANCELLED"},
    "COMPLETED": {"QC_HOLD", "RELEASED", "REJECTED"},
    "QC_HOLD": {"RELEASED", "REJECTED"},
    "RELEASED": set(),
    "REJECTED": set(),
    "CANCELLED": set(),
}


class ProductionOrder(TimeStamped):
    """Üretim emri."""

    class Status(models.TextChoices):
        PLANNED = "PLANNED", "Planlandı"
        RELEASED = "RELEASED", "Serbest bırakıldı"
        IN_PROGRESS = "IN_PROGRESS", "Devam ediyor"
        COMPLETED = "COMPLETED", "Tamamlandı"
        CANCELLED = "CANCELLED", "İptal"

    order_number = models.CharField("Emir No", max_length=40, unique=True)
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="production_orders", verbose_name="Ürün"
    )
    business_line = models.ForeignKey(
        "businessline.BusinessLine", on_delete=models.PROTECT,
        null=True, blank=True, related_name="production_orders",
        verbose_name="İş Kolu",
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.PROTECT, related_name="production_orders", verbose_name="Reçete"
    )
    target_qty = models.DecimalField("Hedef miktar", max_digits=12, decimal_places=4)
    unit = models.ForeignKey(
        UnitOfMeasure, on_delete=models.PROTECT, related_name="production_orders", verbose_name="Birim"
    )
    scheduled_date = models.DateField("Planlanan tarih", null=True, blank=True)
    reactor = models.ForeignKey(
        Container, on_delete=models.PROTECT, related_name="production_orders",
        verbose_name="Reaktör",
        limit_choices_to={"container_type": Container.ContainerType.REACTOR},
    )
    status = models.CharField(
        "Durum", max_length=16, choices=Status.choices, default=Status.PLANNED
    )
    notes = models.TextField("Notlar", blank=True)

    class Meta:
        verbose_name = "Üretim Emri"
        verbose_name_plural = "Üretim Emirleri"
        ordering = ["-scheduled_date", "-created_at"]

    def __str__(self) -> str:
        return f"{self.order_number} · {self.product.code}"

    @property
    def scale_factor(self) -> Decimal:
        """Facteur d'échelle: target_qty / recipe.base_batch_size."""
        base = self.recipe.base_batch_size
        if base <= 0:
            return Decimal("0")
        return (self.target_qty / base).quantize(Decimal("0.0001"))

    def theoretical_needs(self) -> list[dict]:
        """Besoins théoriques MP + stok yeterlilik.

        Her satır: {raw_material, needed, available, sufficient, shortfall,
                    tolerance_pct, is_complement}
        `available` = ilgili hammaddenin RELEASED lotlarındaki remaining_qty toplamı.
        """
        from inventory.models import RawMaterialLot

        rows = self.recipe.scaled_lines(self.target_qty)
        out: list[dict] = []
        for r in rows:
            avail = RawMaterialLot.objects.filter(
                raw_material=r["raw_material"],
                qc_status=RawMaterialLot.QCStatus.RELEASED,
            ).aggregate(total=models.Sum("remaining_qty"))["total"] or Decimal("0")
            needed = r["quantity"]
            out.append({
                "raw_material": r["raw_material"],
                "needed": needed,
                "available": avail,
                "sufficient": avail >= needed,
                "shortfall": (needed - avail) if avail < needed else Decimal("0"),
                "tolerance_pct": r["tolerance_pct"],
                "is_complement": r["is_complement"],
            })
        return out


class ProductionBatch(TimeStamped):
    """Üretim partisi. batch_number = mamul lot numarasıdır."""

    class Status(models.TextChoices):
        PLANNED = "PLANNED", "Planlandı"
        IN_PROGRESS = "IN_PROGRESS", "Devam ediyor"
        COMPLETED = "COMPLETED", "Tamamlandı"
        QC_HOLD = "QC_HOLD", "Kalite bekletme"
        RELEASED = "RELEASED", "Serbest bırakıldı"
        REJECTED = "REJECTED", "Reddedildi"
        CANCELLED = "CANCELLED", "İptal"

    class QCStatus(models.TextChoices):
        PENDING = "PENDING", "Beklemede"
        RELEASED = "RELEASED", "Serbest"
        REJECTED = "REJECTED", "Reddedildi"

    batch_number = models.CharField("Parti No (Mamul Lot)", max_length=60, unique=True)
    controlled_code = models.ForeignKey(
        "registry.ControlledCode", on_delete=models.PROTECT,
        null=True, blank=True, related_name="production_batches",
        verbose_name="MCOS Kontrollü Kod (BMR şablonu)",
    )
    business_line = models.ForeignKey(
        "businessline.BusinessLine", on_delete=models.PROTECT,
        null=True, blank=True, related_name="production_batches",
        verbose_name="İş Kolu",
    )
    production_order = models.ForeignKey(
        ProductionOrder, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="batches", verbose_name="Üretim emri",
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.PROTECT, related_name="batches", verbose_name="Reçete (snapshot)"
    )
    reactor = models.ForeignKey(
        Container, on_delete=models.PROTECT, related_name="batches", verbose_name="Reaktör",
        limit_choices_to={"container_type": Container.ContainerType.REACTOR},
    )
    target_qty = models.DecimalField("Hedef miktar", max_digits=12, decimal_places=4)
    actual_qty = models.DecimalField(
        "Gerçek miktar", max_digits=12, decimal_places=4, null=True, blank=True
    )
    status = models.CharField(
        "Durum", max_length=16, choices=Status.choices, default=Status.PLANNED
    )
    operator = models.CharField("Operatör", max_length=120, blank=True)
    started_at = models.DateTimeField("Başlama", null=True, blank=True)
    completed_at = models.DateTimeField("Bitiş", null=True, blank=True)
    qc_status = models.CharField(
        "Kalite durumu", max_length=16, choices=QCStatus.choices, default=QCStatus.PENDING
    )
    qc_notes = models.TextField("Kalite notu", blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Üretim Partisi"
        verbose_name_plural = "Üretim Partileri"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.batch_number} · {self.recipe.product.code}"

    def transition_to(self, new_status: str) -> None:
        """Durum makinesini zorla. Geçersiz geçişte ValidationError."""
        allowed = BATCH_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise ValidationError(
                f"Geçersiz parti durum geçişi: {self.status} → {new_status}"
            )
        self.status = new_status
        self.save(update_fields=["status", "updated_at"])


class MaterialConsumption(TimeStamped):
    """İzlenebilirlik omurgası — parti ↔ tüketilen hammadde lotu."""

    class Source(models.TextChoices):
        MANUAL = "MANUAL", "Manuel"
        SCADA = "SCADA", "SCADA"

    batch = models.ForeignKey(
        ProductionBatch, on_delete=models.CASCADE,
        related_name="consumptions", verbose_name="Parti",
    )
    raw_material = models.ForeignKey(
        RawMaterial, on_delete=models.PROTECT,
        related_name="consumptions", verbose_name="Hammadde",
    )
    lot = models.ForeignKey(
        RawMaterialLot, on_delete=models.PROTECT, null=True, blank=True,
        related_name="consumptions", verbose_name="Lot",
    )
    target_weight = models.DecimalField(
        "Hedef ağırlık", max_digits=12, decimal_places=4
    )
    actual_weight = models.DecimalField(
        "Gerçek ağırlık", max_digits=12, decimal_places=4, null=True, blank=True
    )
    sequence = models.PositiveIntegerField("Sıra", default=1)
    dosed_at = models.DateTimeField("Dozaj zamanı", null=True, blank=True)
    source = models.CharField(
        "Kaynak", max_length=10, choices=Source.choices, default=Source.MANUAL
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Malzeme Tüketimi"
        verbose_name_plural = "Malzeme Tüketimleri"
        ordering = ["batch", "sequence"]

    def __str__(self) -> str:
        return f"{self.batch.batch_number} · {self.raw_material.code} → {self.actual_weight or '-'}"

    @property
    def deviation_pct(self) -> Decimal | None:
        """Hedef ağırlıktan sapma yüzdesi. actual_weight yoksa None."""
        if self.actual_weight is None or self.target_weight == 0:
            return None
        return (
            (self.actual_weight - self.target_weight) / self.target_weight * Decimal("100")
        ).quantize(Decimal("0.01"))


class ProductionCampaign(TimeStamped):
    """Üretim kampanyası — bir üründen ardışık N parti planlaması (MES super batch).

    Sika/BASF modeli: kampanya = tek reaktörde art arda 5-20 batch üretim.
    Kampanya toplam hedef miktar, süre, tek reaktör atanır.
    """

    class Status(models.TextChoices):
        PLANNED = "PLANNED", "Planlandı"
        RUNNING = "RUNNING", "Devam ediyor"
        PAUSED = "PAUSED", "Duraklatıldı"
        COMPLETED = "COMPLETED", "Tamamlandı"
        CANCELLED = "CANCELLED", "İptal"

    campaign_number = models.CharField("Campaign No", max_length=40, unique=True)
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT,
        related_name="campaigns", verbose_name="Ürün",
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.PROTECT,
        related_name="campaigns", verbose_name="Reçete",
    )
    reactor = models.ForeignKey(
        Container, on_delete=models.PROTECT,
        related_name="campaigns", verbose_name="Reaktör",
        limit_choices_to={"container_type": Container.ContainerType.REACTOR},
    )
    planned_batch_count = models.PositiveIntegerField(
        "Planlanan parti sayısı",
        help_text="Kampanya boyunca üretilecek toplam parti sayısı.",
    )
    completed_batch_count = models.PositiveIntegerField(
        "Tamamlanan parti", default=0,
    )
    total_target_qty = models.DecimalField(
        "Toplam hedef", max_digits=14, decimal_places=2,
    )
    scheduled_start = models.DateField("Başlangıç")
    scheduled_end = models.DateField("Bitiş")
    status = models.CharField(
        "Durum", max_length=12, choices=Status.choices, default=Status.PLANNED,
    )
    notes = models.TextField("Notlar", blank=True)

    class Meta:
        verbose_name = "Production Campaign"
        verbose_name_plural = "Production Campaigns"
        ordering = ["-scheduled_start"]

    def __str__(self) -> str:
        return f"{self.campaign_number} · {self.product.code} × {self.planned_batch_count}"

    @property
    def progress_pct(self):
        if self.planned_batch_count == 0:
            return 0
        return int((self.completed_batch_count / self.planned_batch_count) * 100)


class OutputContainer(TimeStamped):
    """Mamul çıkışı — doldurulan IBC (ileri izlenebilirlik → sevkiyat)."""

    batch = models.ForeignKey(
        ProductionBatch, on_delete=models.CASCADE,
        related_name="outputs", verbose_name="Parti",
    )
    container = models.ForeignKey(
        Container, on_delete=models.PROTECT,
        related_name="output_fillings", verbose_name="Kap (IBC)",
        limit_choices_to={"container_type": Container.ContainerType.IBC},
    )
    quantity = models.DecimalField("Miktar", max_digits=12, decimal_places=4)
    filled_at = models.DateTimeField("Dolum zamanı", null=True, blank=True)
    shipment_reference = models.CharField(
        "Sevkiyat referansı", max_length=120, blank=True
    )

    class Meta:
        verbose_name = "Mamul Çıkış Kabı"
        verbose_name_plural = "Mamul Çıkış Kapları"
        ordering = ["-filled_at"]

    def __str__(self) -> str:
        return f"{self.batch.batch_number} → {self.container.code} · {self.quantity}"

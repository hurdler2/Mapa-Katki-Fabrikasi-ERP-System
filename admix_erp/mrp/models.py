"""MRP modelleri: talep tahmini, malzeme ihtiyacı, satın alma talebi."""
from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models

from common.models import TimeStamped
from masterdata.models import Product, RawMaterial


class DemandForecast(TimeStamped):
    """Manuel talep tahmini — bir ürün için gelecek dönem beklenen miktar."""

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE,
        related_name="forecasts", verbose_name="Ürün",
    )
    period_start = models.DateField("Dönem başı")
    period_end = models.DateField("Dönem sonu")
    quantity = models.DecimalField(
        "Beklenen miktar", max_digits=14, decimal_places=4
    )
    confidence = models.DecimalField(
        "Güven (%)", max_digits=5, decimal_places=2, default=Decimal("80")
    )
    notes = models.TextField("Notlar", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="demand_forecasts", verbose_name="Oluşturan",
    )

    class Meta:
        verbose_name = "Talep Tahmini"
        verbose_name_plural = "Talep Tahminleri"
        ordering = ["-period_start"]

    def __str__(self) -> str:
        return f"{self.product.code} · {self.period_start}..{self.period_end} = {self.quantity}"


class MRPRun(TimeStamped):
    """MRP koşusu — bir tarihe kadar toplam ihtiyaç hesaplanır."""

    run_number = models.CharField("Koşu no", max_length=40, unique=True)
    horizon_date = models.DateField(
        "Ufuk (bu tarihe kadar)",
        help_text="MRP bu tarihe kadar planlanmış üretim emirleri + siparişleri toplar.",
    )
    include_forecasts = models.BooleanField("Talep tahminlerini dahil et", default=True)
    include_open_sales_orders = models.BooleanField(
        "Açık müşteri siparişleri", default=True
    )
    include_planned_production_orders = models.BooleanField(
        "Planlanmış üretim emirleri", default=True
    )
    executed_at = models.DateTimeField("Çalıştırma zamanı", auto_now_add=True)
    executed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="mrp_runs", verbose_name="Çalıştıran",
    )
    notes = models.TextField("Notlar", blank=True)

    class Meta:
        verbose_name = "MRP Koşusu"
        verbose_name_plural = "MRP Koşuları"
        ordering = ["-executed_at"]

    def __str__(self) -> str:
        return f"MRP {self.run_number} · ufuk {self.horizon_date}"


class MaterialRequirement(TimeStamped):
    """Bir MRP koşusunun bir hammadde satırı — brüt/net ihtiyaç."""

    class Status(models.TextChoices):
        OK = "OK", "Yeterli"
        SHORTAGE = "SHORTAGE", "Eksik"
        REORDER = "REORDER", "Reorder önerildi"

    run = models.ForeignKey(
        MRPRun, on_delete=models.CASCADE,
        related_name="requirements", verbose_name="MRP koşusu",
    )
    raw_material = models.ForeignKey(
        RawMaterial, on_delete=models.PROTECT,
        related_name="requirements", verbose_name="Hammadde",
    )
    gross_requirement = models.DecimalField(
        "Brüt ihtiyaç", max_digits=14, decimal_places=4, default=Decimal("0")
    )
    on_hand = models.DecimalField(
        "Mevcut stok (RELEASED lot)", max_digits=14, decimal_places=4, default=Decimal("0")
    )
    on_order = models.DecimalField(
        "Açık PO miktarı", max_digits=14, decimal_places=4, default=Decimal("0")
    )
    net_requirement = models.DecimalField(
        "Net ihtiyaç", max_digits=14, decimal_places=4, default=Decimal("0"),
        help_text="brüt - mevcut - açık PO",
    )
    suggested_order_qty = models.DecimalField(
        "Önerilen sipariş miktarı", max_digits=14, decimal_places=4, default=Decimal("0")
    )
    status = models.CharField(
        "Durum", max_length=10, choices=Status.choices, default=Status.OK
    )
    notes = models.TextField("Notlar", blank=True)

    class Meta:
        verbose_name = "Malzeme İhtiyacı"
        verbose_name_plural = "Malzeme İhtiyaçları"
        unique_together = (("run", "raw_material"),)
        ordering = ["-net_requirement"]

    def __str__(self) -> str:
        return f"{self.raw_material.code} · net={self.net_requirement}"


class PurchaseRequisition(TimeStamped):
    """Satın alma talebi — MRP çıktısından veya elle oluşturulur; PO kaynağı."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Taslak"
        SUBMITTED = "SUBMITTED", "Sunuldu"
        APPROVED = "APPROVED", "Onaylandı"
        REJECTED = "REJECTED", "Reddedildi"
        CONVERTED = "CONVERTED", "PO'ya dönüştürüldü"
        CANCELLED = "CANCELLED", "İptal"

    requisition_number = models.CharField("Talep no", max_length=40, unique=True)
    raw_material = models.ForeignKey(
        RawMaterial, on_delete=models.PROTECT,
        related_name="requisitions", verbose_name="Hammadde",
    )
    quantity = models.DecimalField("Miktar", max_digits=14, decimal_places=4)
    needed_by = models.DateField("Gerekli olduğu tarih", null=True, blank=True)
    source_mrp = models.ForeignKey(
        MRPRun, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="requisitions", verbose_name="Kaynak MRP",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="requested_requisitions", verbose_name="Talep eden",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="approved_requisitions", verbose_name="Onaylayan",
    )
    approved_at = models.DateTimeField("Onay zamanı", null=True, blank=True)
    status = models.CharField(
        "Durum", max_length=12, choices=Status.choices, default=Status.DRAFT
    )
    justification = models.TextField("Gerekçe", blank=True)

    class Meta:
        verbose_name = "Satın Alma Talebi"
        verbose_name_plural = "Satın Alma Talepleri"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.requisition_number} · {self.raw_material.code} × {self.quantity}"

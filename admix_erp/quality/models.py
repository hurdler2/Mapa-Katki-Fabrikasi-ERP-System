"""Kalite modelleri: QC parametreleri, spec'ler, ölçüm sonuçları, COA.

EN 934 kapsamında beton katkısı için tipik parametreler:
yoğunluk, pH, katı madde (%), klorür (%), viskozite.
"""
from __future__ import annotations

from decimal import Decimal

from django.db import models
from simple_history.models import HistoricalRecords

from common.models import TimeStamped
from inventory.models import RawMaterialLot
from masterdata.models import Product, RawMaterial
from production.models import ProductionBatch


class QCParameter(TimeStamped):
    """Kalite parametresi tanımı (yoğunluk, pH, katı %, klorür, viskozite ...)."""

    class Method(models.TextChoices):
        EN_934_2 = "EN_934_2", "EN 934-2 Genel"
        EN_ISO_758 = "EN_ISO_758", "EN ISO 758 (Yoğunluk)"
        EN_480_1 = "EN_480_1", "EN 480-1 (Numune hazırlama)"
        EN_480_8 = "EN_480_8", "EN 480-8 (Katı madde %)"
        EN_480_10 = "EN_480_10", "EN 480-10 (Klorür)"
        INTERNAL = "INTERNAL", "İç metot"

    code = models.CharField("Kod", max_length=30, unique=True)
    name = models.CharField("Ad", max_length=120)
    unit = models.CharField("Birim", max_length=30, blank=True)
    method = models.CharField(
        "Metot", max_length=32, choices=Method.choices, default=Method.EN_934_2
    )
    is_active = models.BooleanField("Aktif", default=True)

    class Meta:
        verbose_name = "QC Parametresi"
        verbose_name_plural = "QC Parametreleri"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} ({self.unit or '-'})"


class QCSpec(TimeStamped):
    """Ürün veya hammadde için parametre spesifikasyonu (min/max/target).

    `product` veya `raw_material`'dan yalnızca biri dolu olur (XOR).
    """

    parameter = models.ForeignKey(
        QCParameter, on_delete=models.PROTECT, related_name="specs", verbose_name="Parametre"
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, null=True, blank=True,
        related_name="qc_specs", verbose_name="Ürün",
    )
    raw_material = models.ForeignKey(
        RawMaterial, on_delete=models.CASCADE, null=True, blank=True,
        related_name="qc_specs", verbose_name="Hammadde",
    )
    min_value = models.DecimalField(
        "Alt sınır", max_digits=12, decimal_places=4, null=True, blank=True
    )
    max_value = models.DecimalField(
        "Üst sınır", max_digits=12, decimal_places=4, null=True, blank=True
    )
    target_value = models.DecimalField(
        "Hedef", max_digits=12, decimal_places=4, null=True, blank=True
    )
    is_mandatory = models.BooleanField("Zorunlu", default=True)

    class Meta:
        verbose_name = "QC Spec"
        verbose_name_plural = "QC Spec'ler"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(product__isnull=False, raw_material__isnull=True)
                    | models.Q(product__isnull=True, raw_material__isnull=False)
                ),
                name="qcspec_product_xor_rawmaterial",
            ),
            models.UniqueConstraint(
                fields=["parameter", "product"], name="qcspec_unique_product",
                condition=models.Q(product__isnull=False),
            ),
            models.UniqueConstraint(
                fields=["parameter", "raw_material"], name="qcspec_unique_rawmaterial",
                condition=models.Q(raw_material__isnull=False),
            ),
        ]

    def __str__(self) -> str:
        target = self.product or self.raw_material
        return f"{target} · {self.parameter.code} [{self.min_value or ''}..{self.max_value or ''}]"

    def evaluate(self, value: Decimal | None) -> str:
        """Ölçüm değerini spec'e göre değerlendir: PASS / FAIL / N/A."""
        if value is None:
            return QCTestResult.Verdict.NA
        value = Decimal(value)
        if self.min_value is not None and value < self.min_value:
            return QCTestResult.Verdict.FAIL
        if self.max_value is not None and value > self.max_value:
            return QCTestResult.Verdict.FAIL
        return QCTestResult.Verdict.PASS


class QCTestResult(TimeStamped):
    """Bir hammadde lotu veya üretim partisi için tek parametre ölçümü.

    `lot` veya `batch`'ten yalnız biri dolu olur.
    """

    class Verdict(models.TextChoices):
        PASS = "PASS", "Geçti"
        FAIL = "FAIL", "Kaldı"
        NA = "NA", "Uygulanamaz"

    parameter = models.ForeignKey(
        QCParameter, on_delete=models.PROTECT, related_name="results", verbose_name="Parametre"
    )
    lot = models.ForeignKey(
        RawMaterialLot, on_delete=models.CASCADE, null=True, blank=True,
        related_name="qc_results", verbose_name="Hammadde Lotu",
    )
    batch = models.ForeignKey(
        ProductionBatch, on_delete=models.CASCADE, null=True, blank=True,
        related_name="qc_results", verbose_name="Üretim Partisi",
    )
    value = models.DecimalField(
        "Ölçüm", max_digits=12, decimal_places=4, null=True, blank=True
    )
    verdict = models.CharField(
        "Sonuç", max_length=8, choices=Verdict.choices, default=Verdict.NA
    )
    tested_at = models.DateTimeField("Test zamanı", auto_now_add=True)
    tester = models.CharField("Testi yapan", max_length=120, blank=True)
    notes = models.TextField("Notlar", blank=True)

    class Meta:
        verbose_name = "QC Test Sonucu"
        verbose_name_plural = "QC Test Sonuçları"
        ordering = ["-tested_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(lot__isnull=False, batch__isnull=True)
                    | models.Q(lot__isnull=True, batch__isnull=False)
                ),
                name="qcresult_lot_xor_batch",
            ),
        ]

    def __str__(self) -> str:
        target = self.lot or self.batch
        return f"{target} · {self.parameter.code}={self.value} → {self.verdict}"


class CertificateOfAnalysis(TimeStamped):
    """Analiz sertifikası (COA). Bir üretim partisi için imzalı özet."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Taslak"
        ISSUED = "ISSUED", "Yayımlandı"
        REVOKED = "REVOKED", "İptal"

    coa_number = models.CharField("COA No", max_length=40, unique=True)
    controlled_code = models.ForeignKey(
        "registry.ControlledCode", on_delete=models.PROTECT,
        null=True, blank=True, related_name="coas",
        verbose_name="MCOS Kontrollü Kod",
    )
    business_line = models.ForeignKey(
        "businessline.BusinessLine", on_delete=models.PROTECT,
        null=True, blank=True, related_name="coas",
        verbose_name="İş Kolu",
    )
    batch = models.OneToOneField(
        ProductionBatch, on_delete=models.PROTECT,
        related_name="coa", verbose_name="Parti",
    )
    issued_at = models.DateTimeField("Yayım zamanı", null=True, blank=True)
    issued_by = models.CharField("Yayımlayan", max_length=120, blank=True)
    status = models.CharField(
        "Durum", max_length=10, choices=Status.choices, default=Status.DRAFT
    )
    summary = models.TextField("Özet / Notlar", blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Analiz Sertifikası (COA)"
        verbose_name_plural = "Analiz Sertifikaları (COA)"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.coa_number} · {self.batch.batch_number}"

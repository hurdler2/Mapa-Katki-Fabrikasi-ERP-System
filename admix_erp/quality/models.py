"""Kalite modelleri: QC parametreleri, spec'ler, ölçüm sonuçları, COA.

EN 934 kapsamında beton katkısı için tipik parametreler:
yoğunluk, pH, katı madde (%), klorür (%), viskozite.

Sprint 2 (UsineERP paritesi):
- QCParameter: `decimal_precision` (Précision décimales)
- QCSpec: version + effective_date + created_by + approved_by (QA workflow),
          per-Gate checkboxes (A/B/C) + is_critical (BR-QA-05) + tolerance_pct
- QCTestResult: `spec_locked` FK (BR-QA-04: numune spec versiyonu kilidi)
- SamplingPlan: örnekleme planı (Plans d'échantillonnage)
"""
from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
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
    decimal_precision = models.PositiveSmallIntegerField(
        "Ondalık hane", default=2,
        help_text="Précision décimales — sonuç girişinde kullanılacak ondalık hane sayısı.",
    )
    en480_method_ref = models.CharField(
        "EN 480 metot referansı", max_length=80, blank=True,
        help_text="Örn. 'EN 480-8 (Katı madde %)', 'EN 480-10 (Klorür)', 'ISO 758'.",
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
    tolerance_pct = models.DecimalField(
        "Tolerans (%)", max_digits=5, decimal_places=2, default=Decimal("0"),
    )
    is_mandatory = models.BooleanField("Zorunlu", default=True)
    is_critical = models.BooleanField(
        "Kritik (BR-QA-05)", default=False,
        help_text="CRITIQUE — ihlali kritik NCR açar (BR-QA-05).",
    )

    # Per-Gate kontrol
    check_at_gate_a = models.BooleanField("Gate A'da kontrol", default=False)
    check_at_gate_b = models.BooleanField("Gate B'de kontrol", default=False)
    check_at_gate_c = models.BooleanField("Gate C'de kontrol", default=False)

    # Versiyonlama + QA onayı
    version = models.PositiveIntegerField("Versiyon", default=1)
    effective_date = models.DateField("Yürürlük tarihi", null=True, blank=True)
    is_active = models.BooleanField("Aktif", default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="qc_specs_created",
        verbose_name="Oluşturan",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="qc_specs_approved",
        verbose_name="QA Onaylayan",
    )
    approved_at = models.DateTimeField("Onay zamanı", null=True, blank=True)

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
                fields=["parameter", "product", "version"], name="qcspec_unique_product_v",
                condition=models.Q(product__isnull=False),
            ),
            models.UniqueConstraint(
                fields=["parameter", "raw_material", "version"], name="qcspec_unique_rawmaterial_v",
                condition=models.Q(raw_material__isnull=False),
            ),
            models.UniqueConstraint(
                fields=["parameter", "product"], name="qcspec_active_unique_product",
                condition=models.Q(product__isnull=False, is_active=True),
            ),
            models.UniqueConstraint(
                fields=["parameter", "raw_material"], name="qcspec_active_unique_rawmaterial",
                condition=models.Q(raw_material__isnull=False, is_active=True),
            ),
        ]

    def clean(self) -> None:
        """Aktif olabilmesi için approved_by dolu olmalı (QA workflow)."""
        super().clean()
        if self.is_active and self.approved_by_id is None:
            raise ValidationError({
                "is_active": "Aktif hale getirilmeden önce QA tarafından onaylanmalıdır.",
            })

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
    spec_locked = models.ForeignKey(
        QCSpec, on_delete=models.PROTECT, null=True, blank=True,
        related_name="locked_results",
        verbose_name="Kilitli Spec (BR-QA-04)",
        help_text="Numune alındığı andaki spec versiyonu — sonradan spec değişse bile evrilmez.",
    )
    gate = models.CharField(
        "Gate", max_length=1, choices=[("A", "A"), ("B", "B"), ("C", "C")],
        blank=True,
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


class SamplingPlan(TimeStamped):
    """Plan d'échantillonnage — hangi Gate'te, hangi tetikleyicide,
    hangi sıklıkta ve hangi boyutta numune alınacağını belirtir.

    Bir plan bir hammadde VEYA bir ürüne bağlanır (XOR).
    Deaktif edildiyse ``deactivation_reason`` zorunludur (BR-QA-12).
    """

    class Gate(models.TextChoices):
        A = "A", "Gate A (Mal kabul / MP)"
        B = "B", "Gate B (Üretim ara / IPC)"
        C = "C", "Gate C (Bitmiş ürün / PF)"

    class Trigger(models.TextChoices):
        ON_RECEIPT = "on_receipt", "À la réception"
        PER_BL_LINE = "per_bl_line", "Par ligne de BL"
        AFTER_MIX = "after_mix", "Après mélange"
        PER_BATCH = "per_batch", "Par batch de production"
        ON_SHIPMENT = "on_shipment", "À l'expédition"
        SCHEDULED = "scheduled", "Programmé (calendrier)"

    code = models.CharField("Plan Kodu", max_length=40, unique=True)
    name = models.CharField("Ad", max_length=200)
    raw_material = models.ForeignKey(
        RawMaterial, on_delete=models.CASCADE, null=True, blank=True,
        related_name="sampling_plans", verbose_name="Hammadde",
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, null=True, blank=True,
        related_name="sampling_plans", verbose_name="Ürün",
    )
    gate = models.CharField("Gate", max_length=1, choices=Gate.choices)
    trigger = models.CharField(
        "Déclencheur", max_length=20, choices=Trigger.choices,
    )
    frequency_n = models.PositiveIntegerField(
        "Sıklık (her N'de bir)", default=1,
        help_text="Örn. 5 → her 5 partide 1 numune.",
    )
    sample_size_rule = models.CharField(
        "Numune sayısı kuralı", max_length=200,
        help_text="Örn. 'sqrt(N)+1', 'MIL-STD-105E S-2', '3 numune sabit'.",
    )
    is_active = models.BooleanField("Aktif", default=True)
    deactivation_reason = models.TextField(
        "Deaktifleştirme sebebi (BR-QA-12)", blank=True,
    )
    notes = models.TextField("Notlar", blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Plan d'échantillonnage"
        verbose_name_plural = "Plans d'échantillonnage"
        ordering = ["code"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(raw_material__isnull=False, product__isnull=True)
                    | models.Q(raw_material__isnull=True, product__isnull=False)
                ),
                name="samplingplan_rm_xor_product",
            ),
        ]

    def __str__(self) -> str:
        target = self.raw_material or self.product
        return f"{self.code} · {target} · Gate {self.gate}"

    def clean(self) -> None:
        """BR-QA-12: pasifleştirilen plan için sebep zorunlu."""
        super().clean()
        if not self.is_active and not (self.deactivation_reason or "").strip():
            raise ValidationError({
                "deactivation_reason": "BR-QA-12: Pasifleştirme sebebi girilmelidir.",
            })


class CustomerSiteTest(TimeStamped):
    """Müşteri saha kabul testi — 7/14/28 gün küp mukavemet + slump + sıcaklık.

    Sipariş edilen ürünün müşteri sahasında yapılan gerçek performans
    ölçümleri. Şikayet analizi + kalite trendleri için kritik veri.
    """

    class TestType(models.TextChoices):
        SLUMP = "SLUMP", "Slump testi"
        CUBE_7 = "CUBE_7", "Küp mukavemet 7 gün"
        CUBE_14 = "CUBE_14", "Küp mukavemet 14 gün"
        CUBE_28 = "CUBE_28", "Küp mukavemet 28 gün"
        TEMPERATURE = "TEMP", "Sıcaklık"
        AIR_CONTENT = "AIR", "Hava içeriği"
        DURABILITY = "DUR", "Dayanıklılık"
        OTHER = "OTHER", "Diğer"

    class Verdict(models.TextChoices):
        PASS = "PASS", "Geçti"
        FAIL = "FAIL", "Kaldı"
        MARGINAL = "MARGINAL", "Sınırda"
        NA = "NA", "Uygulanamaz"

    test_number = models.CharField("Test No", max_length=40, unique=True)
    invoice_line = models.ForeignKey(
        "accounting.InvoiceLine", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="site_tests",
        verbose_name="Fatura satırı (satın alınan)",
    )
    batch = models.ForeignKey(
        ProductionBatch, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="customer_site_tests",
        verbose_name="Üretim partisi (mamul)",
    )
    project_name = models.CharField("Proje adı", max_length=200, blank=True)
    site_location = models.CharField("Saha konumu", max_length=200, blank=True)
    test_date = models.DateField("Test tarihi")
    test_type = models.CharField(
        "Test tipi", max_length=10, choices=TestType.choices,
    )
    measured_value = models.DecimalField(
        "Ölçülen değer", max_digits=12, decimal_places=2,
    )
    unit = models.CharField(
        "Birim", max_length=20, blank=True,
        help_text="Örn. MPa (mukavemet), mm (slump), °C (sıcaklık)",
    )
    target_value = models.DecimalField(
        "Hedef değer", max_digits=12, decimal_places=2, null=True, blank=True,
    )
    verdict = models.CharField(
        "Sonuç", max_length=10, choices=Verdict.choices, default=Verdict.NA,
    )
    tested_by = models.CharField(
        "Testi yapan (müşteri/lab)", max_length=200, blank=True,
    )
    lab_report_file = models.FileField(
        "Lab raporu (PDF)", upload_to="site_tests/%Y/",
        null=True, blank=True,
    )
    notes = models.TextField("Notlar", blank=True)

    class Meta:
        verbose_name = "Müşteri Saha Testi"
        verbose_name_plural = "Müşteri Saha Testleri"
        ordering = ["-test_date"]

    def __str__(self) -> str:
        return f"{self.test_number} · {self.get_test_type_display()} · {self.measured_value} {self.unit}"


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

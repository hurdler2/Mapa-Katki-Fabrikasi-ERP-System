"""QMS modelleri: uygunsuzluk (NCR), sapma (Deviation), CAPA, müşteri şikayeti.

ISO 9001:2015 §8.7 (nonconforming outputs), §9.1.2 (customer satisfaction),
§10.2 (nonconformity and corrective action), §10.3 (continual improvement).
"""
from __future__ import annotations

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from simple_history.models import HistoricalRecords

from common.models import TimeStamped
from masterdata.models import Customer


class Severity(models.TextChoices):
    LOW = "LOW", "Düşük"
    MEDIUM = "MEDIUM", "Orta"
    HIGH = "HIGH", "Yüksek"
    CRITICAL = "CRITICAL", "Kritik"


# ---------------------------------------------------------------------------
# Uygunsuzluk (NCR)
# ---------------------------------------------------------------------------

class Nonconformance(TimeStamped):
    """Uygunsuzluk raporu (NCR) — bir ürün/proses/sistem uygunsuzluğu.

    ISO 9001 §8.7 & §10.2. Kaynak: kalite testi, iç denetim, müşteri şikayeti,
    üretim sırası, tedarikçi.
    """

    class Source(models.TextChoices):
        QC_TEST = "QC_TEST", "Kalite testi"
        PRODUCTION = "PRODUCTION", "Üretim"
        INTERNAL_AUDIT = "INTERNAL_AUDIT", "İç denetim"
        SUPPLIER = "SUPPLIER", "Tedarikçi"
        CUSTOMER_COMPLAINT = "CUSTOMER_COMPLAINT", "Müşteri şikayeti"
        MAINTENANCE = "MAINTENANCE", "Bakım"
        EHS = "EHS", "İSG/Çevre"
        OTHER = "OTHER", "Diğer"

    class Disposition(models.TextChoices):
        PENDING = "PENDING", "Karar bekliyor"
        USE_AS_IS = "USE_AS_IS", "Olduğu gibi kullan (concession)"
        REWORK = "REWORK", "Yeniden işle"
        REJECT = "REJECT", "Reddet / imha"
        RETURN_TO_SUPPLIER = "RETURN_TO_SUPPLIER", "Tedarikçiye iade"
        DOWNGRADE = "DOWNGRADE", "Sınıf düşür"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Açık"
        INVESTIGATING = "INVESTIGATING", "İnceleme"
        DISPOSITIONED = "DISPOSITIONED", "Karar verildi"
        CLOSED = "CLOSED", "Kapatıldı"
        CANCELLED = "CANCELLED", "İptal"

    ncr_number = models.CharField("NCR No", max_length=40, unique=True)
    controlled_code = models.ForeignKey(
        "registry.ControlledCode", on_delete=models.PROTECT,
        null=True, blank=True, related_name="ncrs",
        verbose_name="MCOS Kontrollü Kod",
    )
    business_line = models.ForeignKey(
        "businessline.BusinessLine", on_delete=models.PROTECT,
        null=True, blank=True, related_name="ncrs",
        verbose_name="İş Kolu",
    )
    case = models.ForeignKey(
        "records.Case", on_delete=models.PROTECT,
        null=True, blank=True, related_name="ncrs",
        verbose_name="MCOS Case",
        help_text="NCR bir MCOS case'e bağlı olabilir (Faz D).",
    )
    source = models.CharField("Kaynak", max_length=24, choices=Source.choices)
    severity = models.CharField(
        "Ağırlık", max_length=10, choices=Severity.choices, default=Severity.MEDIUM
    )
    detected_at = models.DateTimeField("Tespit zamanı")
    detected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="detected_ncrs", verbose_name="Tespit eden",
    )
    title = models.CharField("Başlık", max_length=200)
    description = models.TextField("Açıklama")

    # Generic hedef: hangi kayıt uygun değil?
    content_type = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL, null=True, blank=True
    )
    object_id = models.PositiveBigIntegerField(null=True, blank=True)
    target = GenericForeignKey("content_type", "object_id")

    quantity_affected = models.DecimalField(
        "Etkilenen miktar", max_digits=12, decimal_places=4, null=True, blank=True
    )
    disposition = models.CharField(
        "Karar (disposition)", max_length=20, choices=Disposition.choices,
        default=Disposition.PENDING,
    )
    disposition_reason = models.TextField("Karar gerekçesi", blank=True)
    status = models.CharField(
        "Durum", max_length=16, choices=Status.choices, default=Status.OPEN
    )
    closed_at = models.DateTimeField("Kapanış zamanı", null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="closed_ncrs", verbose_name="Kapatan",
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Uygunsuzluk (NCR)"
        verbose_name_plural = "Uygunsuzluklar (NCR)"
        ordering = ["-detected_at"]
        indexes = [models.Index(fields=["content_type", "object_id"])]

    def __str__(self) -> str:
        return f"{self.ncr_number} · {self.title}"


# ---------------------------------------------------------------------------
# Sapma (Deviation)
# ---------------------------------------------------------------------------

class Deviation(TimeStamped):
    """Planlanandan sapma. NCR'dan farkı: bir gereksinim ihlali değil, planın
    dışına çıkma. Ör. proses parametresinin tolerans içi ama alışılmadık değeri.
    """

    class Status(models.TextChoices):
        OPEN = "OPEN", "Açık"
        REVIEWED = "REVIEWED", "İncelendi"
        CLOSED = "CLOSED", "Kapatıldı"

    deviation_number = models.CharField("Sapma No", max_length=40, unique=True)
    detected_at = models.DateTimeField("Tespit zamanı")
    detected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="detected_deviations", verbose_name="Tespit eden",
    )
    title = models.CharField("Başlık", max_length=200)
    description = models.TextField("Açıklama")
    severity = models.CharField(
        "Ağırlık", max_length=10, choices=Severity.choices, default=Severity.LOW
    )
    content_type = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL, null=True, blank=True
    )
    object_id = models.PositiveBigIntegerField(null=True, blank=True)
    target = GenericForeignKey("content_type", "object_id")
    impact_assessment = models.TextField("Etki değerlendirmesi", blank=True)
    status = models.CharField(
        "Durum", max_length=10, choices=Status.choices, default=Status.OPEN
    )
    closed_at = models.DateTimeField("Kapanış zamanı", null=True, blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Sapma"
        verbose_name_plural = "Sapmalar"
        ordering = ["-detected_at"]

    def __str__(self) -> str:
        return f"{self.deviation_number} · {self.title}"


# ---------------------------------------------------------------------------
# CAPA
# ---------------------------------------------------------------------------

class CAPA(TimeStamped):
    """Düzeltici / Önleyici Faaliyet. ISO 9001 §10.2.

    Bir veya daha fazla NCR/Deviation'a bağlanır. Kök neden analizi + aksiyon
    planı + etkinlik doğrulama zorunlu.
    """

    class Type(models.TextChoices):
        CORRECTIVE = "CORRECTIVE", "Düzeltici"
        PREVENTIVE = "PREVENTIVE", "Önleyici"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Taslak"
        PLANNED = "PLANNED", "Planlandı"
        IN_PROGRESS = "IN_PROGRESS", "Devam ediyor"
        VERIFICATION = "VERIFICATION", "Etkinlik doğrulama"
        CLOSED = "CLOSED", "Kapatıldı"
        CANCELLED = "CANCELLED", "İptal"

    class RootCauseMethod(models.TextChoices):
        FIVE_WHY = "5WHY", "5 Neden"
        ISHIKAWA = "ISHIKAWA", "Balık Kılçığı (Ishikawa)"
        FMEA = "FMEA", "FMEA"
        FTA = "FTA", "Hata Ağacı (FTA)"
        OTHER = "OTHER", "Diğer"

    capa_number = models.CharField("CAPA No", max_length=40, unique=True)
    controlled_code = models.ForeignKey(
        "registry.ControlledCode", on_delete=models.PROTECT,
        null=True, blank=True, related_name="capas",
        verbose_name="MCOS Kontrollü Kod",
    )
    business_line = models.ForeignKey(
        "businessline.BusinessLine", on_delete=models.PROTECT,
        null=True, blank=True, related_name="capas",
        verbose_name="İş Kolu",
    )
    case = models.ForeignKey(
        "records.Case", on_delete=models.PROTECT,
        null=True, blank=True, related_name="capas",
        verbose_name="MCOS Case",
    )
    record_instance = models.ForeignKey(
        "records.RecordInstance", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="capas",
        verbose_name="MCOS Record Instance",
        help_text="CAPA form kaydı (örn. MAPA-IMS-FRM-CAPA-001).",
    )
    type = models.CharField("Tip", max_length=12, choices=Type.choices)
    title = models.CharField("Başlık", max_length=200)
    description = models.TextField("Açıklama")
    severity = models.CharField(
        "Ağırlık", max_length=10, choices=Severity.choices, default=Severity.MEDIUM
    )

    # Kaynak NCR/Deviation'lar
    ncrs = models.ManyToManyField(
        Nonconformance, blank=True, related_name="capas", verbose_name="Kaynak NCR'lar"
    )
    deviations = models.ManyToManyField(
        Deviation, blank=True, related_name="capas", verbose_name="Kaynak Sapmalar"
    )

    root_cause_method = models.CharField(
        "Kök neden yöntemi", max_length=10, choices=RootCauseMethod.choices,
        default=RootCauseMethod.FIVE_WHY,
    )
    root_cause_analysis = models.TextField("Kök neden analizi", blank=True)
    action_plan = models.TextField("Aksiyon planı")

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="owned_capas", verbose_name="Sorumlu",
    )
    opened_at = models.DateTimeField("Açılış", auto_now_add=True)
    target_date = models.DateField("Hedef kapanış tarihi", null=True, blank=True)

    verification_notes = models.TextField("Etkinlik doğrulama notları", blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="verified_capas", verbose_name="Doğrulayan",
    )
    verified_at = models.DateTimeField("Doğrulama zamanı", null=True, blank=True)

    status = models.CharField(
        "Durum", max_length=16, choices=Status.choices, default=Status.DRAFT
    )
    closed_at = models.DateTimeField("Kapanış", null=True, blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "CAPA"
        verbose_name_plural = "CAPA'lar"
        ordering = ["-opened_at"]

    def __str__(self) -> str:
        return f"{self.capa_number} · {self.title}"


class CAPAAction(TimeStamped):
    """CAPA'nın alt görevi — atanmış sorumlu + due date + kapanış."""

    class Status(models.TextChoices):
        OPEN = "OPEN", "Açık"
        IN_PROGRESS = "IN_PROGRESS", "Devam ediyor"
        COMPLETED = "COMPLETED", "Tamamlandı"
        BLOCKED = "BLOCKED", "Bloklandı"

    capa = models.ForeignKey(
        CAPA, on_delete=models.CASCADE, related_name="actions", verbose_name="CAPA"
    )
    sequence = models.PositiveIntegerField("Sıra", default=1)
    description = models.CharField("Görev", max_length=255)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="assigned_capa_actions", verbose_name="Atanan",
    )
    due_date = models.DateField("Due date", null=True, blank=True)
    status = models.CharField(
        "Durum", max_length=12, choices=Status.choices, default=Status.OPEN
    )
    completed_at = models.DateTimeField("Tamamlanma", null=True, blank=True)
    evidence = models.TextField("Kanıt / açıklama", blank=True)

    class Meta:
        verbose_name = "CAPA Aksiyon"
        verbose_name_plural = "CAPA Aksiyonları"
        ordering = ["capa", "sequence"]

    def __str__(self) -> str:
        return f"{self.capa.capa_number} · #{self.sequence} {self.description[:40]}"


# ---------------------------------------------------------------------------
# Müşteri Şikayeti
# ---------------------------------------------------------------------------

class CustomerComplaint(TimeStamped):
    """Müşteri şikayeti. ISO 9001 §9.1.2, §10.2."""

    class Status(models.TextChoices):
        NEW = "NEW", "Yeni"
        UNDER_REVIEW = "UNDER_REVIEW", "İnceleme"
        RESOLVED = "RESOLVED", "Çözüldü"
        REJECTED = "REJECTED", "Reddedildi"

    complaint_number = models.CharField("Şikayet No", max_length=40, unique=True)
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT,
        related_name="complaints", verbose_name="Müşteri",
    )
    received_at = models.DateTimeField("Alındığı zaman")
    received_via = models.CharField(
        "Kanal", max_length=40, blank=True,
        help_text="e-posta / telefon / saha ziyareti / mektup",
    )
    reference_shipment = models.CharField(
        "İlgili sevkiyat", max_length=80, blank=True,
        help_text="Shipment.shipment_number (opsiyonel)",
    )
    reference_batch = models.CharField(
        "İlgili parti", max_length=80, blank=True,
        help_text="ProductionBatch.batch_number (opsiyonel)",
    )
    severity = models.CharField(
        "Ağırlık", max_length=10, choices=Severity.choices, default=Severity.MEDIUM
    )
    description = models.TextField("Şikayet detayı")

    ncr = models.ForeignKey(
        Nonconformance, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="complaints", verbose_name="Bağlı NCR",
    )
    capa = models.ForeignKey(
        CAPA, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="complaints", verbose_name="Bağlı CAPA",
    )

    resolution = models.TextField("Çözüm notu", blank=True)
    resolved_at = models.DateTimeField("Çözüm zamanı", null=True, blank=True)
    status = models.CharField(
        "Durum", max_length=14, choices=Status.choices, default=Status.NEW
    )
    customer_satisfied = models.BooleanField(
        "Müşteri memnun mu?", null=True, blank=True,
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Müşteri Şikayeti"
        verbose_name_plural = "Müşteri Şikayetleri"
        ordering = ["-received_at"]

    def __str__(self) -> str:
        return f"{self.complaint_number} · {self.customer.code}"

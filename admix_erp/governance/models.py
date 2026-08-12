"""Governance modelleri: iç denetim, risk kaydı, yönetim gözden geçirme.

ISO 9001:2015 §6.1 (risks & opportunities), §9.2 (internal audit),
§9.3 (management review).
"""
from __future__ import annotations

from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from common.models import TimeStamped
from qms.models import CAPA, Nonconformance


# ---------------------------------------------------------------------------
# Risk & Fırsat (§6.1)
# ---------------------------------------------------------------------------

class RiskItem(TimeStamped):
    """Risk veya fırsat kaydı."""

    class Type(models.TextChoices):
        RISK = "RISK", "Risk"
        OPPORTUNITY = "OPPORTUNITY", "Fırsat"

    class Category(models.TextChoices):
        STRATEGIC = "STRATEGIC", "Stratejik"
        OPERATIONAL = "OPERATIONAL", "Operasyonel"
        QUALITY = "QUALITY", "Kalite"
        SAFETY = "SAFETY", "İSG"
        ENVIRONMENT = "ENVIRONMENT", "Çevre"
        FINANCIAL = "FINANCIAL", "Finansal"
        COMPLIANCE = "COMPLIANCE", "Uyum"
        SUPPLY_CHAIN = "SUPPLY_CHAIN", "Tedarik zinciri"
        IT_CYBER = "IT_CYBER", "BT / Siber"
        OTHER = "OTHER", "Diğer"

    class Status(models.TextChoices):
        IDENTIFIED = "IDENTIFIED", "Tanımlandı"
        ASSESSED = "ASSESSED", "Değerlendirildi"
        MITIGATING = "MITIGATING", "Aksiyon devam ediyor"
        MONITORED = "MONITORED", "İzlemede"
        CLOSED = "CLOSED", "Kapatıldı"

    code = models.CharField("Risk Kodu", max_length=30, unique=True)
    type = models.CharField("Tip", max_length=12, choices=Type.choices,
                            default=Type.RISK)
    category = models.CharField(
        "Kategori", max_length=16, choices=Category.choices, default=Category.OPERATIONAL
    )
    title = models.CharField("Başlık", max_length=200)
    description = models.TextField("Açıklama")

    # 1..5 ölçekli
    inherent_likelihood = models.PositiveSmallIntegerField("İçsel olasılık (1-5)", default=3)
    inherent_impact = models.PositiveSmallIntegerField("İçsel etki (1-5)", default=3)
    residual_likelihood = models.PositiveSmallIntegerField(
        "Kalıntı olasılık", null=True, blank=True
    )
    residual_impact = models.PositiveSmallIntegerField(
        "Kalıntı etki", null=True, blank=True
    )

    treatment_plan = models.TextField("Aksiyon planı", blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="owned_risks", verbose_name="Sorumlu",
    )
    review_date = models.DateField("Sonraki gözden geçirme", null=True, blank=True)
    status = models.CharField(
        "Durum", max_length=12, choices=Status.choices, default=Status.IDENTIFIED
    )
    capa = models.ForeignKey(
        CAPA, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="risks", verbose_name="Bağlı CAPA",
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Risk / Fırsat"
        verbose_name_plural = "Risk / Fırsatlar"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.code} · {self.title}"

    @property
    def inherent_score(self) -> int:
        return (self.inherent_likelihood or 0) * (self.inherent_impact or 0)

    @property
    def residual_score(self) -> int | None:
        if self.residual_likelihood and self.residual_impact:
            return self.residual_likelihood * self.residual_impact
        return None


# ---------------------------------------------------------------------------
# İç Denetim (§9.2)
# ---------------------------------------------------------------------------

class InternalAuditPlan(TimeStamped):
    """Yıllık iç denetim programı."""

    year = models.PositiveIntegerField("Yıl", unique=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="approved_audit_plans", verbose_name="Onaylayan",
    )
    approved_at = models.DateField("Onay tarihi")
    notes = models.TextField("Notlar", blank=True)

    class Meta:
        verbose_name = "İç Denetim Planı"
        verbose_name_plural = "İç Denetim Planları"
        ordering = ["-year"]

    def __str__(self) -> str:
        return f"İç Denetim Programı {self.year}"


class InternalAudit(TimeStamped):
    """Bir denetim etkinliği (departman/proses bazında)."""

    class Status(models.TextChoices):
        PLANNED = "PLANNED", "Planlandı"
        IN_PROGRESS = "IN_PROGRESS", "Devam ediyor"
        REPORTED = "REPORTED", "Raporlandı"
        CLOSED = "CLOSED", "Kapatıldı"
        CANCELLED = "CANCELLED", "İptal"

    audit_number = models.CharField("Denetim No", max_length=40, unique=True)
    plan = models.ForeignKey(
        InternalAuditPlan, on_delete=models.PROTECT,
        related_name="audits", verbose_name="Plan",
    )
    scope = models.CharField(
        "Kapsam", max_length=255,
        help_text="Departman(lar) / proses(ler) / ISO madde(leri)",
    )
    criteria = models.TextField("Denetim kriterleri", blank=True)
    scheduled_date = models.DateField("Planlanan tarih")
    executed_date = models.DateField("Uygulama tarihi", null=True, blank=True)
    lead_auditor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="led_audits", verbose_name="Baş denetçi",
    )
    auditors = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True,
        related_name="audits_as_auditor", verbose_name="Denetim ekibi",
    )
    status = models.CharField(
        "Durum", max_length=14, choices=Status.choices, default=Status.PLANNED
    )
    summary = models.TextField("Özet", blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "İç Denetim"
        verbose_name_plural = "İç Denetimler"
        ordering = ["-scheduled_date"]

    def __str__(self) -> str:
        return f"{self.audit_number} · {self.scope[:40]}"


class AuditFinding(TimeStamped):
    """Denetim bulgusu (major / minor / observation / OFI)."""

    class Level(models.TextChoices):
        MAJOR = "MAJOR", "Majör uygunsuzluk"
        MINOR = "MINOR", "Minör uygunsuzluk"
        OBSERVATION = "OBSERVATION", "Gözlem"
        OFI = "OFI", "İyileştirme fırsatı (OFI)"
        CONFORMITY = "CONFORMITY", "Uygunluk (positive)"

    audit = models.ForeignKey(
        InternalAudit, on_delete=models.CASCADE,
        related_name="findings", verbose_name="Denetim",
    )
    reference = models.CharField(
        "Referans", max_length=80,
        help_text="ISO madde / SOP no / süreç adı",
    )
    level = models.CharField("Seviye", max_length=12, choices=Level.choices)
    description = models.TextField("Bulgu")
    evidence = models.TextField("Kanıt", blank=True)
    ncr = models.ForeignKey(
        Nonconformance, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="audit_findings", verbose_name="Açılan NCR",
    )
    capa = models.ForeignKey(
        CAPA, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="audit_findings", verbose_name="Bağlı CAPA",
    )

    class Meta:
        verbose_name = "Denetim Bulgusu"
        verbose_name_plural = "Denetim Bulguları"
        ordering = ["audit", "level"]

    def __str__(self) -> str:
        return f"{self.audit.audit_number} · {self.get_level_display()}"


# ---------------------------------------------------------------------------
# Yönetim Gözden Geçirme (§9.3)
# ---------------------------------------------------------------------------

class ManagementReview(TimeStamped):
    """Yönetim gözden geçirme toplantı kaydı. ISO 9001 §9.3.2 girdileri."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Taslak"
        HELD = "HELD", "Yapıldı"
        CLOSED = "CLOSED", "Kapatıldı"

    review_number = models.CharField("Toplantı No", max_length=40, unique=True)
    meeting_date = models.DateField("Toplantı tarihi")
    chairperson = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="chaired_reviews", verbose_name="Toplantı başkanı",
    )
    attendees = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True,
        related_name="attended_reviews", verbose_name="Katılımcılar",
    )

    # §9.3.2 girdileri
    input_previous_actions = models.TextField("Önceki gözden geçirme aksiyonları", blank=True)
    input_context_changes = models.TextField("Bağlam / ilgili taraf değişiklikleri", blank=True)
    input_qms_performance = models.TextField("QMS performansı (KPI'lar)", blank=True)
    input_customer_feedback = models.TextField("Müşteri geri bildirimi + şikayet", blank=True)
    input_process_performance = models.TextField("Proses performansı + ürün uygunluğu", blank=True)
    input_ncr_capa = models.TextField("NCR / CAPA özeti", blank=True)
    input_audit_results = models.TextField("İç ve dış denetim sonuçları", blank=True)
    input_supplier_performance = models.TextField("Tedarikçi performansı", blank=True)
    input_resource_adequacy = models.TextField("Kaynakların yeterliliği", blank=True)
    input_risks_opportunities = models.TextField("Risk & fırsat aksiyonları", blank=True)
    input_improvement = models.TextField("Sürekli iyileştirme fırsatları", blank=True)

    # §9.3.3 çıktıları
    output_decisions = models.TextField("Kararlar", blank=True)
    output_resources = models.TextField("Kaynak ihtiyaçları", blank=True)
    output_improvement_actions = models.TextField("İyileştirme aksiyonları", blank=True)

    status = models.CharField(
        "Durum", max_length=8, choices=Status.choices, default=Status.DRAFT
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Yönetim Gözden Geçirme"
        verbose_name_plural = "Yönetim Gözden Geçirmeler"
        ordering = ["-meeting_date"]

    def __str__(self) -> str:
        return f"{self.review_number} · {self.meeting_date}"


class ManagementReviewAction(TimeStamped):
    """MR çıktı aksiyonu — atanmış sorumlu + due date."""

    class Status(models.TextChoices):
        OPEN = "OPEN", "Açık"
        IN_PROGRESS = "IN_PROGRESS", "Devam"
        DONE = "DONE", "Tamamlandı"

    review = models.ForeignKey(
        ManagementReview, on_delete=models.CASCADE,
        related_name="actions", verbose_name="Toplantı",
    )
    description = models.CharField("Aksiyon", max_length=255)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="assigned_mr_actions", verbose_name="Atanan",
    )
    due_date = models.DateField("Due date", null=True, blank=True)
    status = models.CharField(
        "Durum", max_length=12, choices=Status.choices, default=Status.OPEN
    )
    completed_at = models.DateTimeField("Tamamlanma", null=True, blank=True)

    class Meta:
        verbose_name = "MR Aksiyonu"
        verbose_name_plural = "MR Aksiyonları"

    def __str__(self) -> str:
        return f"{self.review.review_number} · {self.description[:40]}"

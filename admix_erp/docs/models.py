"""Doküman kontrol modelleri (ISO 9001 §7.5.1-3): SOP, WI, form, kalite el kitabı."""
from __future__ import annotations

from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from common.models import TimeStamped


class DocumentCategory(TimeStamped):
    """Doküman kategorisi (Kalite El Kitabı, SOP, WI, Form, Talimat, Politika...)."""

    code = models.CharField("Kod", max_length=20, unique=True)
    name = models.CharField("Ad", max_length=120)
    prefix = models.CharField(
        "Numara ön eki", max_length=10,
        help_text="Doküman numarasında kullanılır (örn. SOP, WI, F, POL).",
    )

    class Meta:
        verbose_name = "Doküman Kategorisi"
        verbose_name_plural = "Doküman Kategorileri"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} · {self.name}"


class ControlledDocument(TimeStamped):
    """Kontrollü doküman (başlık kaydı). Versiyonlar `DocumentRevision`'da tutulur."""

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Aktif"
        RETIRED = "RETIRED", "Geri çekildi"

    document_number = models.CharField("Doküman No", max_length=40, unique=True)
    controlled_code = models.ForeignKey(
        "registry.ControlledCode", on_delete=models.PROTECT,
        null=True, blank=True, related_name="documents",
        verbose_name="MCOS Kontrollü Kod",
    )
    business_line = models.ForeignKey(
        "businessline.BusinessLine", on_delete=models.PROTECT,
        null=True, blank=True, related_name="controlled_documents",
        verbose_name="İş Kolu",
    )
    title = models.CharField("Başlık", max_length=200)
    category = models.ForeignKey(
        DocumentCategory, on_delete=models.PROTECT,
        related_name="documents", verbose_name="Kategori",
    )
    process_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="owned_documents", verbose_name="Süreç sahibi",
    )
    status = models.CharField(
        "Durum", max_length=8, choices=Status.choices, default=Status.ACTIVE
    )
    retention_years = models.PositiveIntegerField(
        "Saklama süresi (yıl)", default=10,
        help_text="ISO 9001 §7.5 gereği saklama süresi.",
    )
    description = models.TextField("Açıklama", blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Kontrollü Doküman"
        verbose_name_plural = "Kontrollü Dokümanlar"
        ordering = ["document_number"]

    def __str__(self) -> str:
        return f"{self.document_number} · {self.title}"

    @property
    def current_revision(self):
        return self.revisions.filter(status=DocumentRevision.Status.EFFECTIVE).first()


class DocumentRevision(TimeStamped):
    """Doküman revizyonu — DRAFT → REVIEW → APPROVED → EFFECTIVE → SUPERSEDED."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Taslak"
        REVIEW = "REVIEW", "İnceleme"
        APPROVED = "APPROVED", "Onaylandı"
        EFFECTIVE = "EFFECTIVE", "Yürürlükte"
        SUPERSEDED = "SUPERSEDED", "Yerine yenisi geldi"
        WITHDRAWN = "WITHDRAWN", "Geri çekildi"

    document = models.ForeignKey(
        ControlledDocument, on_delete=models.CASCADE,
        related_name="revisions", verbose_name="Doküman",
    )
    revision = models.CharField("Revizyon", max_length=10, help_text="Örn. 01, 02, A, B")
    file = models.FileField(
        "Dosya", upload_to="docs/%Y/%m/", null=True, blank=True,
        help_text="PDF veya diğer dosya. Sistemin ağ paylaşımından da referanslanabilir.",
    )
    external_url = models.URLField(
        "Harici URL", blank=True,
        help_text="Dosya yerine harici link (opsiyonel).",
    )
    change_summary = models.TextField("Değişiklik özeti")
    status = models.CharField(
        "Durum", max_length=12, choices=Status.choices, default=Status.DRAFT
    )

    prepared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="prepared_revisions", verbose_name="Hazırlayan",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reviewed_revisions", verbose_name="İnceleyen",
    )
    reviewed_at = models.DateTimeField("İnceleme zamanı", null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="approved_revisions", verbose_name="Onaylayan",
    )
    approved_at = models.DateTimeField("Onay zamanı", null=True, blank=True)
    effective_date = models.DateField("Yürürlük tarihi", null=True, blank=True)
    next_review_date = models.DateField("Sonraki gözden geçirme", null=True, blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Doküman Revizyonu"
        verbose_name_plural = "Doküman Revizyonları"
        ordering = ["document", "-effective_date"]
        unique_together = (("document", "revision"),)

    def __str__(self) -> str:
        return f"{self.document.document_number} r{self.revision}"


class DocumentAcknowledgement(TimeStamped):
    """Personelin bir dokümanı okuyup anladığına dair kayıt (ISO 9001 §7.2, §7.5.3)."""

    revision = models.ForeignKey(
        DocumentRevision, on_delete=models.CASCADE,
        related_name="acknowledgements", verbose_name="Revizyon",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="doc_acknowledgements", verbose_name="Kullanıcı",
    )
    acknowledged_at = models.DateTimeField("Onay zamanı", auto_now_add=True)
    note = models.TextField("Not", blank=True)

    class Meta:
        verbose_name = "Doküman Okundu Onayı"
        verbose_name_plural = "Doküman Okundu Onayları"
        unique_together = (("revision", "user"),)

    def __str__(self) -> str:
        return f"{self.user.get_username()} → {self.revision}"


class DocumentDistribution(TimeStamped):
    """Bir revizyonun hangi departmana/kişiye dağıtıldığı — ISO 9001 §7.5.3."""

    revision = models.ForeignKey(
        DocumentRevision, on_delete=models.CASCADE,
        related_name="distributions", verbose_name="Revizyon",
    )
    department_code = models.CharField("Departman kodu", max_length=20, blank=True)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="doc_distributions", verbose_name="Alıcı",
    )
    copy_number = models.CharField(
        "Kopya no", max_length=20, blank=True,
        help_text="Kontrollü basılı kopya için sıra numarası.",
    )
    distributed_at = models.DateTimeField("Dağıtım zamanı", auto_now_add=True)
    recalled_at = models.DateTimeField("Geri çekme zamanı", null=True, blank=True)

    class Meta:
        verbose_name = "Doküman Dağıtımı"
        verbose_name_plural = "Doküman Dağıtımları"

    def __str__(self) -> str:
        return f"{self.revision} → {self.department_code or self.recipient}"

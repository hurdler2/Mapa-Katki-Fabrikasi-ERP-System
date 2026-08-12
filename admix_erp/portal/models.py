"""ApprovalRequest — kritik iş akışları için jenerik onay/reddetme."""
from __future__ import annotations

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from common.models import TimeStamped


class ApprovalRequest(TimeStamped):
    """Herhangi bir modelin herhangi bir kaydı için onay talebi.

    Kullanımı:
    - Fatura post öncesi Muhasebe Müdürü onayı
    - Batch release öncesi IMS QA Müdürü onayı
    - CAPA kapatma öncesi IMS QA Müdürü onayı
    - PO yüksek tutar için Genel Müdür onayı
    """

    class Kind(models.TextChoices):
        INVOICE_POST = "INVOICE_POST", "Fatura Muhasebeleştirme"
        BATCH_RELEASE = "BATCH_RELEASE", "Parti Serbest Bırakma"
        CAPA_CLOSE = "CAPA_CLOSE", "CAPA Kapatma"
        PO_HIGH_AMOUNT = "PO_HIGH_AMOUNT", "Yüksek Tutarlı PO"
        DOC_APPROVE = "DOC_APPROVE", "Doküman Onayı"
        NCR_DISPOSITION = "NCR_DISPOSITION", "NCR Karar (Disposition)"
        OTHER = "OTHER", "Diğer"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Bekliyor"
        APPROVED = "APPROVED", "Onaylandı"
        REJECTED = "REJECTED", "Reddedildi"
        CANCELLED = "CANCELLED", "İptal"

    kind = models.CharField("Tür", max_length=20, choices=Kind.choices)
    title = models.CharField("Başlık", max_length=200)
    description = models.TextField("Açıklama", blank=True)

    # Onaylanacak nesne
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE
    )
    object_id = models.PositiveBigIntegerField()
    target = GenericForeignKey("content_type", "object_id")

    # Kim istedi
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="approval_requests",
        verbose_name="Talep eden",
    )

    # Hangi role verilecek
    required_role = models.CharField(
        "Onaylayacak rol", max_length=40,
        help_text="Grup adı — bu roldeki herhangi bir aktif kullanıcı onaylayabilir.",
    )

    # MCOS Faz B — D1-D4 karar seviyesi + veto sahibi rol
    class DecisionLevel(models.TextChoices):
        D1 = "D1", "D1 Routine execution"
        D2 = "D2", "D2 Functional decision"
        D3 = "D3", "D3 Major decision"
        D4 = "D4", "D4 Strategic / crisis"

    decision_level = models.CharField(
        "MCOS karar seviyesi", max_length=2,
        choices=DecisionLevel.choices, default=DecisionLevel.D2,
        help_text="NAV-002 §3 — talep bu seviyede karar bekliyor.",
    )
    veto_holder_role = models.CharField(
        "Veto sahibi rol", max_length=60, blank=True,
        help_text="Bu talebe veto edebilecek rol (örn. IMS_QA_MANAGER, HSE_OFFICER). "
                  "Boşsa veto uygulanmaz.",
    )

    # Durum
    status = models.CharField(
        "Durum", max_length=10, choices=Status.choices, default=Status.PENDING
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="decided_approvals",
        verbose_name="Karar veren",
    )
    decided_at = models.DateTimeField("Karar zamanı", null=True, blank=True)
    decision_reason = models.CharField(
        "Karar gerekçesi", max_length=500, blank=True
    )

    class Meta:
        verbose_name = "Onay Talebi"
        verbose_name_plural = "Onay Talepleri"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "required_role"]),
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} · {self.get_status_display()}"

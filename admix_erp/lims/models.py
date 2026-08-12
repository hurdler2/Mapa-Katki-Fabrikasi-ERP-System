"""LIMS (Laboratory Information Management System) entegrasyon modelleri.

- LimsEndpoint: lab. sistemine bağlantı tanımı (HTTP/REST veya dosya tabanlı).
- SampleRequest: ERP'den LIMS'e gönderilen örnekleme talebi (parti/lot bazlı).
- LimsSyncLog: her sync çağrısının audit kaydı.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models

from common.models import TimeStamped
from inventory.models import RawMaterialLot
from production.models import ProductionBatch
from quality.models import QCParameter


class LimsEndpoint(TimeStamped):
    """LIMS sistem tanımı."""

    class Protocol(models.TextChoices):
        MOCK = "MOCK", "Mock (test)"
        REST = "REST", "REST API (JSON)"
        FILE = "FILE", "Dosya (CSV/XML)"
        HL7 = "HL7", "HL7 (klinik)"

    code = models.CharField("Kod", max_length=30, unique=True)
    name = models.CharField("Ad", max_length=200)
    protocol = models.CharField(
        "Protokol", max_length=8, choices=Protocol.choices, default=Protocol.MOCK
    )
    endpoint_url = models.CharField(
        "Endpoint URL", max_length=255, blank=True,
        help_text="REST için tam URL, dosya için dizin yolu",
    )
    credentials_env = models.CharField(
        "Kimlik env anahtarı", max_length=80, blank=True,
        help_text="user:password ya da API key env değişkeni",
    )
    is_active = models.BooleanField("Aktif", default=True)

    class Meta:
        verbose_name = "LIMS Endpoint"
        verbose_name_plural = "LIMS Endpoint'ler"

    def __str__(self) -> str:
        return f"{self.code} ({self.get_protocol_display()})"


class SampleRequest(TimeStamped):
    """LIMS'e gönderilen örnek analiz talebi."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Beklemede"
        SENT = "SENT", "Gönderildi"
        RECEIVED = "RECEIVED", "Sonuç alındı"
        FAILED = "FAILED", "Hata"

    request_number = models.CharField("Talep no", max_length=40, unique=True)
    endpoint = models.ForeignKey(
        LimsEndpoint, on_delete=models.PROTECT,
        related_name="requests", verbose_name="Endpoint",
    )
    batch = models.ForeignKey(
        ProductionBatch, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="lims_requests", verbose_name="Parti",
    )
    lot = models.ForeignKey(
        RawMaterialLot, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="lims_requests", verbose_name="Lot",
    )
    parameters = models.ManyToManyField(
        QCParameter, related_name="lims_requests",
        verbose_name="Talep edilen parametreler",
    )
    priority = models.CharField(
        "Öncelik", max_length=10, default="NORMAL",
        help_text="LOW / NORMAL / HIGH / URGENT",
    )
    status = models.CharField(
        "Durum", max_length=10, choices=Status.choices, default=Status.PENDING
    )
    sent_at = models.DateTimeField("Gönderim zamanı", null=True, blank=True)
    received_at = models.DateTimeField("Sonuç alım zamanı", null=True, blank=True)
    lims_reference = models.CharField(
        "LIMS referansı", max_length=80, blank=True,
        help_text="LIMS'in atadığı iç ID.",
    )
    payload_sent = models.JSONField("Gönderilen payload", default=dict, blank=True)
    payload_received = models.JSONField("Alınan sonuç", default=dict, blank=True)
    notes = models.TextField("Notlar", blank=True)

    class Meta:
        verbose_name = "Örnek İstek (LIMS)"
        verbose_name_plural = "Örnek İstekler (LIMS)"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        target = self.batch or self.lot
        return f"{self.request_number} → {target}"


class LimsSyncLog(TimeStamped):
    """Bir sync çağrısı (push / pull) için audit kaydı."""

    class Direction(models.TextChoices):
        PUSH = "PUSH", "Push (ERP → LIMS)"
        PULL = "PULL", "Pull (LIMS → ERP)"

    class Status(models.TextChoices):
        SUCCESS = "SUCCESS", "Başarılı"
        FAILED = "FAILED", "Hatalı"
        PARTIAL = "PARTIAL", "Kısmi"

    endpoint = models.ForeignKey(
        LimsEndpoint, on_delete=models.CASCADE,
        related_name="sync_logs", verbose_name="Endpoint",
    )
    direction = models.CharField("Yön", max_length=6, choices=Direction.choices)
    status = models.CharField("Durum", max_length=8, choices=Status.choices)
    executed_at = models.DateTimeField("Çalıştırma", auto_now_add=True)
    executed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="lims_syncs", verbose_name="Kullanıcı",
    )
    records_processed = models.PositiveIntegerField("İşlenen kayıt sayısı", default=0)
    error_message = models.TextField("Hata mesajı", blank=True)
    payload_summary = models.TextField("Özet", blank=True)

    class Meta:
        verbose_name = "LIMS Sync Log"
        verbose_name_plural = "LIMS Sync Logları"
        ordering = ["-executed_at"]

    def __str__(self) -> str:
        return f"{self.endpoint.code} · {self.direction} · {self.status}"

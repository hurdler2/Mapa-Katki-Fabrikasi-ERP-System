"""SCADA köprüsü modelleri: PLC endpoint, reçete indirme kaydı, tartım eventi.

Güvenlik: OT/L2 (PLC + SCADA) ağı DMZ'den izole. Bu köprü tek yönlü/kontrollü
tek geçiş noktasıdır. Kimlik bilgileri env üzerinden okunur; DB'de plaintext tutulmaz.
"""
from __future__ import annotations

from django.db import models

from common.models import TimeStamped
from production.models import MaterialConsumption, ProductionBatch, ProductionOrder


class PLCEndpoint(TimeStamped):
    """PLC / SCADA endpoint tanımı."""

    class Protocol(models.TextChoices):
        MOCK = "MOCK", "Mock (test)"
        OPC_UA = "OPC_UA", "OPC UA"
        MODBUS_TCP = "MODBUS_TCP", "Modbus TCP"
        MQTT = "MQTT", "MQTT"

    code = models.CharField("Kod", max_length=40, unique=True)
    name = models.CharField("Ad", max_length=120)
    protocol = models.CharField(
        "Protokol", max_length=12, choices=Protocol.choices, default=Protocol.MOCK
    )
    host = models.CharField("Host / IP", max_length=120, blank=True)
    port = models.PositiveIntegerField("Port", null=True, blank=True)
    endpoint_url = models.CharField(
        "Endpoint URL", max_length=255, blank=True,
        help_text="opc.tcp://... veya mqtt://... veya modbus.tcp://host:port/unit",
    )
    credentials_env = models.CharField(
        "Kimlik env anahtarı", max_length=80, blank=True,
        help_text="Kullanıcı/şifre bu env değişkeninden okunur.",
    )
    is_active = models.BooleanField("Aktif", default=True)

    class Meta:
        verbose_name = "PLC Endpoint"
        verbose_name_plural = "PLC Endpoint'ler"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} ({self.get_protocol_display()})"


class RecipeDownload(TimeStamped):
    """PLC'ye reçete indirme kaydı (audit)."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Beklemede"
        SENT = "SENT", "Gönderildi"
        FAILED = "FAILED", "Başarısız"
        SIMULATED = "SIMULATED", "Simüle edildi"

    endpoint = models.ForeignKey(
        PLCEndpoint, on_delete=models.PROTECT,
        related_name="recipe_downloads", verbose_name="Endpoint",
    )
    production_order = models.ForeignKey(
        ProductionOrder, on_delete=models.PROTECT,
        related_name="recipe_downloads", verbose_name="Üretim Emri",
    )
    batch = models.ForeignKey(
        ProductionBatch, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="recipe_downloads", verbose_name="Parti",
    )
    payload = models.JSONField("Payload", default=dict, blank=True)
    status = models.CharField(
        "Durum", max_length=10, choices=Status.choices, default=Status.PENDING
    )
    sent_at = models.DateTimeField("Gönderim zamanı", null=True, blank=True)
    response = models.TextField("PLC yanıtı", blank=True)

    class Meta:
        verbose_name = "Reçete İndirme"
        verbose_name_plural = "Reçete İndirmeleri"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.production_order.order_number} → {self.endpoint.code} ({self.status})"


class WeighmentEvent(TimeStamped):
    """PLC'den gelen ham tartım eventi (audit)."""

    class Status(models.TextChoices):
        RECEIVED = "RECEIVED", "Alındı"
        MATCHED = "MATCHED", "Eşleşti"
        UNMATCHED = "UNMATCHED", "Eşleşmedi"
        FAILED = "FAILED", "Hata"

    endpoint = models.ForeignKey(
        PLCEndpoint, on_delete=models.PROTECT,
        related_name="weighments", verbose_name="Endpoint",
    )
    tag = models.CharField(
        "Tag / adres", max_length=120,
        help_text="Format: <batch_number>.<material_code> (örn. BATCH-005.SP)",
    )
    weight = models.DecimalField("Ağırlık", max_digits=12, decimal_places=4)
    plc_timestamp = models.DateTimeField("PLC zaman damgası", null=True, blank=True)
    consumption = models.ForeignKey(
        MaterialConsumption, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="weighment_events", verbose_name="Eşlenen tüketim",
    )
    status = models.CharField(
        "Durum", max_length=12, choices=Status.choices, default=Status.RECEIVED
    )
    error_message = models.TextField("Hata mesajı", blank=True)
    raw_payload = models.JSONField("Ham veri", default=dict, blank=True)

    class Meta:
        verbose_name = "Tartım Eventi"
        verbose_name_plural = "Tartım Event'leri"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.tag}={self.weight} · {self.status}"

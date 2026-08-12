"""Bildirim / görev kutusu modeli."""
from __future__ import annotations

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from common.models import TimeStamped


class Notification(TimeStamped):
    """Bir kullanıcıya bildirim."""

    class Level(models.TextChoices):
        INFO = "INFO", "Bilgi"
        SUCCESS = "SUCCESS", "Başarı"
        WARNING = "WARNING", "Uyarı"
        ERROR = "ERROR", "Hata"
        TASK = "TASK", "Görev (aksiyon gerektirir)"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="notifications", verbose_name="Alıcı",
    )
    title = models.CharField("Başlık", max_length=200)
    message = models.TextField("Mesaj")
    level = models.CharField(
        "Seviye", max_length=8, choices=Level.choices, default=Level.INFO
    )
    # Generic FK: bir kayda bağlı olabilir (NCR, CAPA, WorkOrder, Fatura vb.)
    content_type = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL, null=True, blank=True
    )
    object_id = models.PositiveBigIntegerField(null=True, blank=True)
    target = GenericForeignKey("content_type", "object_id")
    action_url = models.CharField(
        "Aksiyon URL", max_length=255, blank=True,
        help_text="Kullanıcıyı ilgili sayfaya götüren bağlantı.",
    )
    is_read = models.BooleanField("Okundu", default=False)
    read_at = models.DateTimeField("Okunma zamanı", null=True, blank=True)

    class Meta:
        verbose_name = "Bildirim"
        verbose_name_plural = "Bildirimler"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.recipient.get_username()} · {self.title[:40]}"

"""API app models — MCOS Faz F retrieval örneklem raporları."""
from __future__ import annotations

from django.db import models

from common.models import TimeStamped


class RetrievalSampleReport(TimeStamped):
    """Aylık rastgele örneklem sonucu — 00_MCO_1 sınav kriteri (2 dk SLA)."""

    class Result(models.TextChoices):
        PASS = "PASS", "PASS (SLA içi)"
        SLOW = "SLOW", "SLOW (SLA ihlali)"
        NOT_FOUND = "NOT_FOUND", "NOT FOUND"
        ERROR = "ERROR", "ERROR"

    ref = models.CharField("Ref", max_length=100)
    resolved_type = models.CharField("Çözülen tür", max_length=30, blank=True)
    result = models.CharField("Sonuç", max_length=10, choices=Result.choices)
    elapsed_ms = models.PositiveIntegerField("Süre (ms)", default=0)
    error_note = models.TextField("Hata / not", blank=True)
    sampled_at = models.DateTimeField("Örneklem zamanı", auto_now_add=True)

    class Meta:
        verbose_name = "Retrieval Örneklem Raporu"
        verbose_name_plural = "Retrieval Örneklem Raporları"
        ordering = ["-sampled_at"]
        indexes = [
            models.Index(fields=["result"]),
            models.Index(fields=["-sampled_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.ref} · {self.result} · {self.elapsed_ms}ms"

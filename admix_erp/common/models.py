"""Ortak soyut modeller."""
from django.db import models


class TimeStamped(models.Model):
    """Tüm modellerin türediği zaman damgalı soyut model."""

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncellenme")

    class Meta:
        abstract = True

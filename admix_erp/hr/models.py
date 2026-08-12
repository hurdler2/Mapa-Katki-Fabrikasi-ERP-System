"""HR modelleri: vardiya + eğitim + izin.

iam.UserProfile ve iam.Competency zaten mevcuttur; burada bu üstyapının
operasyonel eklerini tutuyoruz.
"""
from __future__ import annotations

import datetime as dt

from django.conf import settings
from django.db import models

from common.models import TimeStamped
from iam.models import Competency


# ---------------------------------------------------------------------------
# Vardiya
# ---------------------------------------------------------------------------

class Shift(TimeStamped):
    """Vardiya tanımı: 08-16, 16-24, 24-08 vb."""

    code = models.CharField("Kod", max_length=20, unique=True)
    name = models.CharField("Ad", max_length=80)
    start_time = models.TimeField("Başlangıç saati")
    end_time = models.TimeField("Bitiş saati")
    is_night = models.BooleanField("Gece vardiyası", default=False)
    is_active = models.BooleanField("Aktif", default=True)

    class Meta:
        verbose_name = "Vardiya"
        verbose_name_plural = "Vardiyalar"
        ordering = ["start_time"]

    def __str__(self) -> str:
        return f"{self.code} · {self.start_time}-{self.end_time}"


class ShiftAssignment(TimeStamped):
    """Kullanıcı × vardiya × gün ataması."""

    class Status(models.TextChoices):
        SCHEDULED = "SCHEDULED", "Planlandı"
        COMPLETED = "COMPLETED", "Yapıldı"
        ABSENT = "ABSENT", "Devamsız"
        SWAPPED = "SWAPPED", "Değiştirildi"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="shift_assignments", verbose_name="Personel",
    )
    shift = models.ForeignKey(
        Shift, on_delete=models.PROTECT,
        related_name="assignments", verbose_name="Vardiya",
    )
    date = models.DateField("Tarih")
    role = models.CharField(
        "Görev", max_length=80, blank=True,
        help_text="Operatör / kalite / lider / vb.",
    )
    status = models.CharField(
        "Durum", max_length=10, choices=Status.choices, default=Status.SCHEDULED
    )
    notes = models.TextField("Not", blank=True)

    class Meta:
        verbose_name = "Vardiya Ataması"
        verbose_name_plural = "Vardiya Atamaları"
        unique_together = (("user", "date", "shift"),)
        ordering = ["-date", "shift"]

    def __str__(self) -> str:
        return f"{self.user.get_username()} · {self.date} · {self.shift.code}"


# ---------------------------------------------------------------------------
# Eğitim
# ---------------------------------------------------------------------------

class TrainingCourse(TimeStamped):
    """Eğitim kursu tanımı."""

    class Category(models.TextChoices):
        HSE = "HSE", "İSG / Çevre"
        QUALITY = "QUALITY", "Kalite"
        TECHNICAL = "TECHNICAL", "Teknik"
        REGULATORY = "REGULATORY", "Mevzuat"
        SOFT_SKILL = "SOFT_SKILL", "Kişisel gelişim"
        ONBOARDING = "ONBOARDING", "Oryantasyon"

    code = models.CharField("Kod", max_length=30, unique=True)
    name = models.CharField("Ad", max_length=200)
    category = models.CharField(
        "Kategori", max_length=12, choices=Category.choices, default=Category.QUALITY
    )
    duration_hours = models.DecimalField(
        "Süre (saat)", max_digits=5, decimal_places=1, default=1
    )
    provider = models.CharField("Sağlayıcı", max_length=200, blank=True)
    validity_days = models.PositiveIntegerField(
        "Geçerlilik (gün)", null=True, blank=True,
        help_text="Boşsa sınırsız.",
    )
    grants_competency = models.ForeignKey(
        Competency, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="granting_courses",
        verbose_name="Kazandırdığı yetkinlik",
    )
    is_active = models.BooleanField("Aktif", default=True)

    class Meta:
        verbose_name = "Eğitim Kursu"
        verbose_name_plural = "Eğitim Kursları"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} · {self.name}"


class TrainingSession(TimeStamped):
    """Belirli bir tarihte gerçekleştirilen eğitim etkinliği."""

    class Status(models.TextChoices):
        PLANNED = "PLANNED", "Planlandı"
        DELIVERED = "DELIVERED", "Verildi"
        CANCELLED = "CANCELLED", "İptal"

    course = models.ForeignKey(
        TrainingCourse, on_delete=models.PROTECT,
        related_name="sessions", verbose_name="Kurs",
    )
    session_number = models.CharField("Etkinlik No", max_length=40, unique=True)
    date = models.DateField("Tarih")
    location = models.CharField("Yer", max_length=200, blank=True)
    trainer = models.CharField("Eğitmen", max_length=200, blank=True)
    status = models.CharField(
        "Durum", max_length=10, choices=Status.choices, default=Status.PLANNED
    )

    class Meta:
        verbose_name = "Eğitim Etkinliği"
        verbose_name_plural = "Eğitim Etkinlikleri"
        ordering = ["-date"]

    def __str__(self) -> str:
        return f"{self.session_number} · {self.course.code}"


class TrainingRecord(TimeStamped):
    """Bir kullanıcının bir eğitim etkinliğine katılım + sonuç kaydı."""

    class Result(models.TextChoices):
        PASSED = "PASSED", "Geçti"
        FAILED = "FAILED", "Kaldı"
        ATTENDED = "ATTENDED", "Katıldı (sınavsız)"
        ABSENT = "ABSENT", "Katılmadı"

    session = models.ForeignKey(
        TrainingSession, on_delete=models.CASCADE,
        related_name="records", verbose_name="Etkinlik",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="training_records", verbose_name="Personel",
    )
    result = models.CharField(
        "Sonuç", max_length=8, choices=Result.choices, default=Result.ATTENDED
    )
    score = models.DecimalField(
        "Puan", max_digits=5, decimal_places=2, null=True, blank=True
    )
    certificate_number = models.CharField("Sertifika no", max_length=60, blank=True)
    certificate_file = models.FileField(
        "Sertifika PDF", upload_to="training/%Y/", null=True, blank=True
    )
    valid_until = models.DateField("Geçerlilik sonu", null=True, blank=True)
    notes = models.TextField("Not", blank=True)

    class Meta:
        verbose_name = "Eğitim Kaydı"
        verbose_name_plural = "Eğitim Kayıtları"
        unique_together = (("session", "user"),)
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user.get_username()} · {self.session.course.code} · {self.result}"


# ---------------------------------------------------------------------------
# İzin
# ---------------------------------------------------------------------------

class LeaveRequest(TimeStamped):
    """Personel izin talebi."""

    class Type(models.TextChoices):
        ANNUAL = "ANNUAL", "Yıllık izin"
        SICK = "SICK", "Hastalık"
        UNPAID = "UNPAID", "Ücretsiz"
        MATERNITY = "MATERNITY", "Doğum"
        BEREAVEMENT = "BEREAVEMENT", "Vefat"
        OTHER = "OTHER", "Diğer"

    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Talep edildi"
        APPROVED = "APPROVED", "Onaylandı"
        REJECTED = "REJECTED", "Reddedildi"
        CANCELLED = "CANCELLED", "İptal"

    request_number = models.CharField("Talep no", max_length=40, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="leave_requests", verbose_name="Personel",
    )
    type = models.CharField("Tip", max_length=12, choices=Type.choices)
    start_date = models.DateField("Başlangıç")
    end_date = models.DateField("Bitiş")
    days = models.PositiveIntegerField("Gün sayısı", default=1)
    reason = models.TextField("Gerekçe", blank=True)
    status = models.CharField(
        "Durum", max_length=10, choices=Status.choices, default=Status.REQUESTED
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="approved_leaves", verbose_name="Onaylayan",
    )
    approved_at = models.DateTimeField("Onay zamanı", null=True, blank=True)
    rejection_reason = models.TextField("Ret gerekçesi", blank=True)

    class Meta:
        verbose_name = "İzin Talebi"
        verbose_name_plural = "İzin Talepleri"
        ordering = ["-start_date"]

    def __str__(self) -> str:
        return f"{self.request_number} · {self.user.get_username()} ({self.type})"

    def save(self, *args, **kwargs):
        if self.start_date and self.end_date:
            delta = (self.end_date - self.start_date).days + 1
            self.days = max(1, delta)
        super().save(*args, **kwargs)

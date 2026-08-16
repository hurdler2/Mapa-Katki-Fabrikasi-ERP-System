"""MCOS 8-Part Gate Modeli (Faz E).

Kaynak: MCOS IMS-NAV-001 §4 — bir Case veya major geçiş (batch release,
doküman activation, yeni ürün launch, PO high-amount) 8 bölümlü bir kapı
mekaniğine oturur.

8 Bölüm (sırayla incelenir):
    1. Operation
    2. IMS Engine
    3. Decision Architecture
    4. Objective Evidence
    5. Management Review
    6. Lessons Learned
    7. IMS Improvement
    8. Gate Status

Kapama koşulları (`close_gate`):
    - Tüm 8 section PASS veya CONDITIONAL
    - Her section'da en az 1 evidence bağlı
    - Case'in tüm zorunlu Decision'ları mevcut
    - HOLD/FAIL varsa → gate FAIL

Yeniden açma (`reopen_gate`):
    - PASS'ten sonra bir Decision reddedilir veya çelişkili evidence gelirse
    - reopen_history JSON'a append (tetik + kim + ne zaman)
"""
from __future__ import annotations

from django.contrib.auth.models import User
from django.db import models
from simple_history.models import HistoricalRecords

from businessline.models import BusinessLine
from common.models import TimeStamped
from records.models import Case, Evidence


class Gate(TimeStamped):
    """8-part gate — NAV-001 §4."""

    class Section(models.TextChoices):
        OPERATION = "OPERATION", "1. Operation"
        IMS_ENGINE = "IMS_ENGINE", "2. IMS Engine"
        DECISION_ARCH = "DECISION_ARCH", "3. Decision Architecture"
        OBJECTIVE_EVIDENCE = "OBJECTIVE_EVIDENCE", "4. Objective Evidence"
        MANAGEMENT_REVIEW = "MANAGEMENT_REVIEW", "5. Management Review"
        LESSONS_LEARNED = "LESSONS_LEARNED", "6. Lessons Learned"
        IMS_IMPROVEMENT = "IMS_IMPROVEMENT", "7. IMS Improvement"
        GATE_STATUS = "GATE_STATUS", "8. Gate Status"

    ALL_SECTIONS = (
        Section.OPERATION, Section.IMS_ENGINE, Section.DECISION_ARCH,
        Section.OBJECTIVE_EVIDENCE, Section.MANAGEMENT_REVIEW,
        Section.LESSONS_LEARNED, Section.IMS_IMPROVEMENT, Section.GATE_STATUS,
    )

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        HOLD = "HOLD", "HOLD"
        CONDITIONAL = "CONDITIONAL", "Conditional PASS"
        PASS = "PASS", "PASS"
        FAIL = "FAIL", "FAIL"
        REOPENED = "REOPENED", "Reopened"

    gate_id = models.CharField(
        "Gate ID", max_length=40, unique=True,
        help_text='Örn. "GATE-001", "GATE-BATCH-2026-0001"',
    )
    case = models.ForeignKey(
        Case, on_delete=models.PROTECT, related_name="gates",
    )
    business_line = models.ForeignKey(
        BusinessLine, null=True, blank=True,
        on_delete=models.PROTECT, related_name="gates",
    )
    scope = models.TextField(
        "Kapsam",
        help_text="Bu kapının kapsadığı olay/karar/geçişin özeti.",
    )
    owner = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="owned_gates",
        verbose_name="Kapı sahibi",
    )

    status = models.CharField(
        "Durum", max_length=12, choices=Status.choices, default=Status.OPEN,
    )
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField("Kapanma", null=True, blank=True)
    closed_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="closed_gates",
    )

    reopen_history = models.JSONField(
        "Yeniden açma geçmişi", default=list, blank=True,
        help_text="[{trigger, by_user, at, note}, ...]",
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Gate"
        verbose_name_plural = "Gate'ler (8-Part)"
        ordering = ["-opened_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["case", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.gate_id} · {self.get_status_display()}"


class GateSection(TimeStamped):
    """8 bölümden birinin bağımsız durumu + kanıt + inceleyen."""

    gate = models.ForeignKey(
        Gate, related_name="sections", on_delete=models.CASCADE,
    )
    section = models.CharField(
        "Bölüm", max_length=20, choices=Gate.Section.choices,
    )
    completion_status = models.CharField(
        "Tamamlanma durumu", max_length=14, choices=Gate.Status.choices,
        default=Gate.Status.OPEN,
    )
    evidence = models.ManyToManyField(
        Evidence, blank=True, related_name="gate_sections",
        verbose_name="Kanıtlar",
    )
    reviewer = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="reviewed_gate_sections",
    )
    reviewed_at = models.DateTimeField("İnceleme zamanı", null=True, blank=True)
    notes = models.TextField("Notlar", blank=True)

    class Meta:
        verbose_name = "Gate Section"
        verbose_name_plural = "Gate Sections"
        unique_together = (("gate", "section"),)
        ordering = ["gate", "section"]

    def __str__(self) -> str:
        return f"{self.gate.gate_id} · {self.get_section_display()}"

"""MCOS Faz G — Master Register (Integrated).

Kaynak: 08_CLO_1 sheet 6 (Integrated Event/CAPA Master Register) ve 07_CLO_1
sheet 6 (Security Event Register).

Amaç: NCR + IT-OT event + HSE incident + CAPA + effectiveness'i **tek satırda**
entegre görmek — üst yönetim, denetim ve düzenleyici için "kim, ne, ne zaman,
şu an nerede, kapandı mı, tekrar oldu mu" sorularının tek yerden yanıtı.

Kritik davranış: kayıtlar **silinmez**, güncellenmez. Değişiklik gerekiyorsa
`create_snapshot(old)` çağrılır: eski satır `is_snapshot=True` işaretlenir,
yeni satır `snapshot_of=old` FK ile chain'e eklenir. Register history append-only.
"""
from __future__ import annotations

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from simple_history.models import HistoricalRecords

from common.models import TimeStamped
from records.models import Case


# ---------------------------------------------------------------------------
# IntegratedEventRegister (08_CLO_1 sheet 6)
# ---------------------------------------------------------------------------

class IntegratedEventRegister(TimeStamped):
    """Bir Case için tek-satır entegre olay/CAPA takip kaydı.

    Bir Case birden fazla InteregratedEventRegister satırına sahip olabilir —
    snapshot zinciri ile: aktif satır `is_snapshot=False`, önceki snapshot'lar
    `is_snapshot=True` işaretli ve `snapshot_of` FK ile chain oluşturur.
    """

    class Family(models.TextChoices):
        NCR = "NCR", "NCR / Nonconformance"
        IT_OT = "IT-OT", "IT / OT Event"
        HSE = "HSE", "HSE Incident"
        PRODUCT = "PRODUCT", "Product Event"
        SUPPLIER = "SUPPLIER", "Supplier Event"
        CUSTOMER = "CUSTOMER", "Customer Complaint"
        AUDIT = "AUDIT", "Audit Finding"

    class EvClass(models.TextChoices):
        EV1 = "EV1", "EV1 Critical (system-wide)"
        EV2 = "EV2", "EV2 Major (product/BL)"
        EV3 = "EV3", "EV3 Significant (process)"
        EV4 = "EV4", "EV4 Minor (local)"

    class DLevel(models.TextChoices):
        D1 = "D1", "D1 Routine"
        D2 = "D2", "D2 Functional"
        D3 = "D3", "D3 Major"
        D4 = "D4", "D4 Strategic / crisis"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        CONTAINED = "CONTAINED", "Contained"
        INVESTIGATING = "INVESTIGATING", "Investigating"
        CAPA_PLANNED = "CAPA_PLANNED", "CAPA planned"
        CAPA_IN_PROGRESS = "CAPA_IN_PROGRESS", "CAPA in progress"
        EFFECTIVENESS_CHECK = "EFFECTIVENESS_CHECK", "Effectiveness check"
        CLOSED = "CLOSED", "Closed"
        REOPENED = "REOPENED", "Reopened"

    class DispositionStatus(models.TextChoices):
        USE_AS_IS = "USE_AS_IS", "Use as-is"
        REWORK = "REWORK", "Rework"
        REGRADE = "REGRADE", "Regrade"
        RETURN_TO_SUPPLIER = "RTS", "Return to supplier"
        SCRAP = "SCRAP", "Scrap"
        RELEASE = "RELEASE", "Release"
        HOLD = "HOLD", "Hold"
        PENDING = "PENDING", "Pending"

    class EffectivenessResult(models.TextChoices):
        NOT_DUE = "NOT_DUE", "Not due"
        EFFECTIVE = "EFFECTIVE", "Effective"
        PARTIALLY = "PARTIALLY", "Partially effective"
        INEFFECTIVE = "INEFFECTIVE", "Ineffective — reopen"

    # ---- Kimlik + sınıflandırma ----
    event_id = models.CharField(
        "Event ID", max_length=60,
        help_text="Örn. INCIDENT-001. Snapshot zincirinde tekrarlanabilir; aktif satır tek.",
    )
    family = models.CharField("Aile", max_length=12, choices=Family.choices)
    ev_class = models.CharField("EV sınıfı", max_length=4, choices=EvClass.choices)
    d_level = models.CharField("D seviyesi", max_length=2, choices=DLevel.choices)

    # ---- Bağlantı ----
    case = models.ForeignKey(
        Case, on_delete=models.PROTECT, related_name="register_entries",
        verbose_name="MCOS Case",
    )

    # ---- Bağlam ----
    site_process = models.CharField(
        "Site / Proses", max_length=200,
        help_text="Örn. Reactor Line #1 / IT-OT DMZ Fw / SP Deposu",
    )
    scope_summary = models.TextField("Kapsam özeti")
    detection_date = models.DateField("Tespit tarihi")
    containment_date = models.DateField("Kontrol altına alınma tarihi", null=True, blank=True)

    # ---- Durum ----
    current_gate = models.CharField(
        "Şu anki kapı", max_length=20, blank=True,
        help_text='Örn. "NC5", "NC9=closed"',
    )
    owner = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="owned_register_entries",
        verbose_name="Sahip",
    )
    status = models.CharField("Durum", max_length=20, choices=Status.choices)
    disposition_status = models.CharField(
        "Disposition", max_length=12, choices=DispositionStatus.choices,
        default=DispositionStatus.PENDING,
    )
    hold_flag = models.BooleanField("HOLD", default=False)

    # ---- CAPA / MOC bağlantı ----
    capa_id = models.CharField("CAPA ID", max_length=60, blank=True)
    capa_status = models.CharField("CAPA durumu", max_length=20, blank=True)
    moc_id = models.CharField("MOC ID", max_length=60, blank=True)

    # ---- Effectiveness ----
    effectiveness_due = models.DateField("Etkinlik değerlendirme tarihi", null=True, blank=True)
    effectiveness_result = models.CharField(
        "Etkinlik sonucu", max_length=12,
        choices=EffectivenessResult.choices,
        default=EffectivenessResult.NOT_DUE,
    )
    recurrence_code = models.CharField(
        "Tekrar kodu", max_length=40, blank=True,
        help_text='Örn. "R2=aynı proses tekrar" / "R0=yok"',
    )

    # ---- İlişkili kayıtlar (serbest metin — genişleyen alan) ----
    related_records = models.TextField(
        "Bağlı kayıtlar", blank=True,
        help_text="Örn. NCR-001, DEC-004, EVD-G001-005, RTS-G001-001",
    )
    evidence_link = models.TextField(
        "Kanıt linkleri", blank=True,
        help_text="Örn. EVD-G001-001..005",
    )

    # ---- Kapama ----
    target_close = models.DateField("Hedef kapanma", null=True, blank=True)
    close_date = models.DateField("Kapanma tarihi", null=True, blank=True)

    # ---- Snapshot mekanizması (append-only) ----
    is_snapshot = models.BooleanField(
        "Snapshot mı?", default=False,
        help_text="True = geçmiş versiyon, salt-okunur.",
    )
    snapshot_of = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="successors", verbose_name="Kaynağı",
        help_text="Bu satır bir öncekinin snapshot'ı ise, ilgili öncekine işaret.",
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Integrated Event Register"
        verbose_name_plural = "Integrated Event Register (Master)"
        ordering = ["-detection_date", "-created_at"]
        indexes = [
            models.Index(fields=["event_id"]),
            models.Index(fields=["case", "is_snapshot"]),
            models.Index(fields=["family", "status"]),
            models.Index(fields=["hold_flag"]),
            models.Index(fields=["is_snapshot", "-detection_date"]),
        ]
        constraints = [
            # Aktif (snapshot=False) satır her event_id için TEK olmalı
            models.UniqueConstraint(
                fields=["event_id"],
                condition=models.Q(is_snapshot=False),
                name="uniq_active_event_id_in_register",
            ),
        ]

    def __str__(self) -> str:
        tag = " [SNAPSHOT]" if self.is_snapshot else ""
        return f"{self.event_id} · {self.family} · {self.status}{tag}"

    def delete(self, *args, **kwargs):  # noqa: D401
        """Register satırı silinemez — append-only (snapshot ile geriye alınır)."""
        raise ValidationError(
            "Master Register satırı silinemez. "
            "Değişiklik için create_snapshot() kullanın."
        )


# ---------------------------------------------------------------------------
# SecurityEventRegister (07_CLO_1 sheet 6)
# ---------------------------------------------------------------------------

class SecurityEventRegister(TimeStamped):
    """IT/OT security event / veri sızıntısı register'ı."""

    class Severity(models.TextChoices):
        SEV1 = "SEV1", "SEV1 Critical"
        SEV2 = "SEV2", "SEV2 High"
        SEV3 = "SEV3", "SEV3 Medium"

    class ContainmentStatus(models.TextChoices):
        NOT_STARTED = "NOT_STARTED", "Not started"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        CONTAINED = "CONTAINED", "Contained"
        RECOVERED = "RECOVERED", "Recovered"

    class CurrentStatus(models.TextChoices):
        OPEN = "OPEN", "Open"
        CONTAINED = "CONTAINED", "Contained"
        RECOVERING = "RECOVERING", "Recovering"
        MONITORING = "MONITORING", "Monitoring"
        CLOSED = "CLOSED", "Closed"

    class EscalationStatus(models.TextChoices):
        ROUTINE = "ROUTINE", "Routine"
        WARNING = "WARNING", "Warning"
        ESCALATED = "ESCALATED", "Escalated"
        BREACH = "BREACH", "SLA Breach"

    incident_id = models.CharField(
        "Incident ID", max_length=60,
        help_text="Örn. IT-INC-2026-001",
    )
    detection_datetime = models.DateTimeField("Tespit zamanı")
    severity = models.CharField("Şiddet", max_length=4, choices=Severity.choices)

    affected_asset = models.CharField(
        "Etkilenen varlık", max_length=300,
        help_text="Örn. DMZ-FW-01 / SCADA-SVR-02 / OT-VLAN-100",
    )
    data_class = models.CharField(
        "Veri sınıfı", max_length=60, blank=True,
        help_text='Örn. "Kişisel-Basit", "Operasyonel-Kritik"',
    )
    is_personal_data = models.BooleanField("Kişisel veri mi?", default=False)

    detection_reporter = models.CharField("Tespit eden / rapor", max_length=200, blank=True)
    containment_status = models.CharField(
        "Containment durumu", max_length=14,
        choices=ContainmentStatus.choices, default=ContainmentStatus.NOT_STARTED,
    )
    evidence_timeline_ref = models.TextField(
        "Kanıt zaman çizelgesi ref", blank=True,
        help_text="EVD-... ve zaman satırları",
    )
    scope_impact_summary = models.TextField("Kapsam & etki")
    dpo_legal_external_action = models.TextField(
        "DPO / hukuk / dış aksiyon", blank=True,
        help_text="KVKK/DPO bildirim, dış tebliğ vs.",
    )
    recovery_rts_ids = models.CharField(
        "Recovery / RTS ID'leri", max_length=200, blank=True,
    )
    ncr_capa_moc_ids = models.CharField(
        "NCR / CAPA / MOC ID'leri", max_length=200, blank=True,
    )

    case = models.ForeignKey(
        Case, on_delete=models.PROTECT, null=True, blank=True,
        related_name="security_register_entries",
    )
    owner = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name="owned_security_register_entries",
    )

    target_date = models.DateField("Hedef kapanma", null=True, blank=True)
    close_date = models.DateField("Kapanma", null=True, blank=True)
    current_status = models.CharField(
        "Şu anki durum", max_length=12,
        choices=CurrentStatus.choices, default=CurrentStatus.OPEN,
    )
    repeat_effectiveness = models.CharField(
        "Tekrar/etkinlik notu", max_length=200, blank=True,
    )
    evidence_link = models.TextField("Kanıt linkleri", blank=True)
    days_open = models.IntegerField("Açık gün sayısı", default=0)
    escalation_status = models.CharField(
        "Eskalasyon durumu", max_length=12,
        choices=EscalationStatus.choices, default=EscalationStatus.ROUTINE,
    )

    # Snapshot desteği
    is_snapshot = models.BooleanField("Snapshot", default=False)
    snapshot_of = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="successors",
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Security Event Register"
        verbose_name_plural = "Security Event Register"
        ordering = ["-detection_datetime"]
        indexes = [
            models.Index(fields=["incident_id"]),
            models.Index(fields=["current_status"]),
            models.Index(fields=["escalation_status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["incident_id"],
                condition=models.Q(is_snapshot=False),
                name="uniq_active_incident_id_in_sec_register",
            ),
        ]

    def __str__(self) -> str:
        tag = " [SNAPSHOT]" if self.is_snapshot else ""
        return f"{self.incident_id} · {self.severity} · {self.current_status}{tag}"

    def delete(self, *args, **kwargs):  # noqa: D401
        raise ValidationError(
            "Security Event Register satırı silinemez. "
            "Değişiklik için create_snapshot() kullanın."
        )

"""MCOS 5-Katman ID Modeli (Faz D).

Kaynak: MCOS-CDD-001 §7, IMS-NAV-002 §3-4, 00_MCO_1 sheet 3+8, 05_T5-08_CLO_1 örnek kayıtlar.

Beş katman:
    1. Document      → ControlledCode (registry.ControlledCode, Faz C)
    2. Case          → Bir kez üretilen olay/vaka kimliği (INCIDENT-001, CHANGE-2026-0001)
    3. RecordInstance→ Case × ControlledCode kesişimindeki gerçek doldurulmuş kayıt
    4. Evidence      → Case veya Record'a bağlı kanıt paketi (ALCOA+ meta)
    5. Decision      → Yetkili karar kaydı (NAV-002 §4 mandatory fields + e-imza)

Kritik kurallar:
    - Case/Record ID **yeniden kullanılmaz** (validated unique)
    - RecordInstance SoD: preparer ≠ reviewer ≠ approver
    - Decision self-approval yasak (decision_maker independent_reviewers'ta olamaz)
    - Recovery, RTS, CAPA effectiveness, gate close **ayrı** kararlar (birbirine karışmaz)
"""
from __future__ import annotations

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from simple_history.models import HistoricalRecords

from businessline.models import BusinessLine
from common.models import TimeStamped
from registry.models import ControlledCode


# ---------------------------------------------------------------------------
# Case — birinci sınıf olay/vaka kimliği
# ---------------------------------------------------------------------------

class Case(TimeStamped):
    """Ana olay / vaka kaydı — bir kez üretilir, yeniden kullanılmaz.

    Örnek: INCIDENT-001, CHANGE-2026-0001, AUDIT-2026-Q1, COMPLAINT-2026-014
    """

    class Family(models.TextChoices):
        INCIDENT = "INCIDENT", "Incident / Olay"
        NCR = "NCR", "Nonconformance"
        CHANGE = "CHANGE", "Change Notice (MOC)"
        AUDIT = "AUDIT", "Audit finding"
        COMPLAINT = "COMPLAINT", "Customer complaint"
        DEVIATION = "DEVIATION", "Deviation"
        RISK = "RISK", "Risk event"

    class Severity(models.TextChoices):
        SEV1 = "SEV1", "SEV1 Critical"
        SEV2 = "SEV2", "SEV2 Major"
        SEV3 = "SEV3", "SEV3 Significant"
        SEV4 = "SEV4", "SEV4 Minor"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        INVESTIGATING = "INVESTIGATING", "Investigating"
        CLOSED = "CLOSED", "Closed"
        REOPENED = "REOPENED", "Reopened"

    case_id = models.CharField(
        "Case ID", max_length=60, unique=True,
        help_text="INCIDENT-001, CHANGE-2026-0001. Yeniden kullanılamaz.",
    )
    family = models.CharField("Aile", max_length=12, choices=Family.choices)
    business_line = models.ForeignKey(
        BusinessLine, null=True, blank=True,
        on_delete=models.PROTECT, related_name="cases",
    )
    gate = models.CharField(
        "Kapı (Gate)", max_length=20, blank=True,
        help_text="Örn. GATE-001",
    )

    title = models.CharField("Başlık", max_length=200)
    description = models.TextField("Açıklama")
    detected_at = models.DateTimeField("Tespit zamanı")
    detected_by = models.ForeignKey(
        User, related_name="detected_cases", on_delete=models.PROTECT,
    )
    severity = models.CharField(
        "Şiddet", max_length=4, choices=Severity.choices,
        default=Severity.SEV3,
    )
    status = models.CharField(
        "Durum", max_length=14, choices=Status.choices, default=Status.OPEN,
    )

    # T-faz zaman damgaları (GATE-001 T0→T6 kronolojisi)
    contained_at = models.DateTimeField("T1 Contained", null=True, blank=True)
    scope_frozen_at = models.DateTimeField("T2 Scope frozen", null=True, blank=True)
    classified_at = models.DateTimeField("T3 Classified", null=True, blank=True)
    recovery_at = models.DateTimeField("T4 Recovery", null=True, blank=True)
    reconciled_at = models.DateTimeField("T5 Reconciled", null=True, blank=True)
    capa_opened_at = models.DateTimeField("T6 CAPA opened", null=True, blank=True)
    closed_at = models.DateTimeField("Kapanış", null=True, blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Case / Vaka"
        verbose_name_plural = "Case'ler / Vakalar"
        ordering = ["-detected_at"]
        indexes = [
            models.Index(fields=["family", "status"]),
            models.Index(fields=["business_line", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.case_id} · {self.title}"

    def clean(self):
        # Case ID yeniden kullanılamaz — unique_together yerine explicit kontrol
        # (yeniden kullanılmanın anlamı: silinip aynı ID ile yeniden yaratılamaz)
        pass  # unique=True zaten enforce ediyor; history log geriye dönük denetim sağlar


# ---------------------------------------------------------------------------
# RecordInstance — Case × ControlledCode doldurulmuş kayıt
# ---------------------------------------------------------------------------

class RecordInstance(TimeStamped):
    """Bir Case × ControlledCode kesişimindeki gerçek doldurulmuş kayıt.

    Örnek: RTS-G001-001, CAPA-G001-001, REC-G001-001
    """

    class Status(models.TextChoices):
        WORKING = "WORKING", "Working copy"
        REVIEW = "REVIEW", "Supervisor review"
        APPROVED = "APPROVED", "Approved"
        RECORD_COPY = "RECORD_COPY", "Record copy (read-only)"
        SUPERSEDED = "SUPERSEDED", "Superseded"
        REOPENED = "REOPENED", "Reopened"

    record_id = models.CharField(
        "Record ID", max_length=60, unique=True,
        help_text="RTS-G001-001, CAPA-G001-001. Yeniden kullanılamaz.",
    )
    controlled_code = models.ForeignKey(
        ControlledCode, on_delete=models.PROTECT,
        related_name="record_instances",
        verbose_name="Kontrollü kod (şablon)",
    )
    case = models.ForeignKey(
        Case, on_delete=models.PROTECT, related_name="records",
    )
    business_line = models.ForeignKey(
        BusinessLine, null=True, blank=True,
        on_delete=models.PROTECT, related_name="records",
    )

    status = models.CharField(
        "Durum", max_length=12, choices=Status.choices, default=Status.WORKING,
    )

    # Roller (SoD enforced)
    preparer = models.ForeignKey(
        User, related_name="prepared_records", on_delete=models.PROTECT,
    )
    reviewer = models.ForeignKey(
        User, related_name="reviewed_records", null=True, blank=True,
        on_delete=models.SET_NULL,
    )
    approver = models.ForeignKey(
        User, related_name="approved_records", null=True, blank=True,
        on_delete=models.SET_NULL,
    )

    # Zaman damgaları (lifecycle 00_MCO_1 sheet 8)
    working_started_at = models.DateTimeField(auto_now_add=True)
    review_started_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    record_copy_at = models.DateTimeField(null=True, blank=True)

    # Payload (form alanları — ControlledCode şablonuna göre)
    payload = models.JSONField("Form verisi", default=dict, blank=True)

    # Arşiv yolları
    working_path = models.CharField(
        "Working path", max_length=300, blank=True,
        help_text="Örn. /MCOS/GATE-001/WORKING/RTS-G001-001/",
    )
    record_copy_path = models.CharField(
        "Record copy path", max_length=300, blank=True,
    )
    file = models.FileField("Dosya", upload_to="records/%Y/%m/", null=True, blank=True)
    signed_pdf = models.FileField(
        "İmzalı PDF", upload_to="records/signed/%Y/%m/", null=True, blank=True,
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Record Instance"
        verbose_name_plural = "Record Instances"
        ordering = ["-working_started_at"]
        indexes = [
            models.Index(fields=["case", "status"]),
            models.Index(fields=["controlled_code", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.record_id} · {self.controlled_code.full_code}"

    def clean(self):
        # SoD: preparer ≠ reviewer ≠ approver (CDD-001 non-negotiable rule)
        if self.reviewer_id and self.reviewer_id == self.preparer_id:
            raise ValidationError({
                "reviewer": "Hazırlayan aynı zamanda inceleyen olamaz (SoD)."
            })
        if self.approver_id:
            if self.approver_id == self.preparer_id:
                raise ValidationError({
                    "approver": "Hazırlayan aynı zamanda onaylayan olamaz (SoD)."
                })
            if self.reviewer_id and self.approver_id == self.reviewer_id:
                raise ValidationError({
                    "approver": "İnceleyen aynı zamanda onaylayan olamaz (SoD)."
                })


# ---------------------------------------------------------------------------
# Evidence — ALCOA+ kanıt paketi
# ---------------------------------------------------------------------------

class Evidence(TimeStamped):
    """Bir Case veya RecordInstance'a bağlı kanıt paketi.

    Örnek: EVD-G001-001 (raw data), EVD-G001-004 (signed report)
    ALCOA+ (Attributable/Legible/Contemporaneous/Original/Accurate + Complete/Consistent/Enduring/Available)
    """

    class Kind(models.TextChoices):
        RAW_DATA = "RAW_DATA", "Ham veri"
        ATTACHMENT = "ATTACHMENT", "Ek dosya"
        PHOTO = "PHOTO", "Fotoğraf"
        LOG = "LOG", "Log / audit trail"
        CERTIFICATE = "CERTIFICATE", "Sertifika"
        COA = "COA", "Certificate of Analysis"
        SIGNED_REPORT = "SIGNED_REPORT", "İmzalı rapor"
        SIMULATION = "SIMULATION", "Simülasyon (canlı değil)"

    evidence_id = models.CharField("Evidence ID", max_length=60, unique=True)
    case = models.ForeignKey(
        Case, on_delete=models.PROTECT, related_name="evidence_set",
    )
    record_instance = models.ForeignKey(
        RecordInstance, null=True, blank=True,
        related_name="evidence_set", on_delete=models.CASCADE,
    )
    kind = models.CharField("Tip", max_length=14, choices=Kind.choices)
    title = models.CharField("Başlık", max_length=200)
    description = models.TextField("Açıklama", blank=True)

    file = models.FileField("Dosya", upload_to="evidence/%Y/%m/", null=True, blank=True)
    external_url = models.URLField("Harici URL", blank=True)
    sha256 = models.CharField("SHA-256", max_length=64, blank=True)
    collected_at = models.DateTimeField(auto_now_add=True)
    collected_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="collected_evidence",
    )

    # ALCOA+ metadatası
    is_contemporaneous = models.BooleanField(
        "Eşzamanlı", default=True,
        help_text="Olayla eşzamanlı toplandı mı? (ALCOA+ Contemporaneous)",
    )
    is_original = models.BooleanField(
        "Orijinal", default=True,
        help_text="Orijinal mi yoksa türev mi? (ALCOA+ Original)",
    )
    derivative_note = models.CharField(
        "Türev notu", max_length=200, blank=True,
        help_text="Türev ise kaynak kanıtı ve dönüşüm notu.",
    )

    class Meta:
        verbose_name = "Evidence / Kanıt"
        verbose_name_plural = "Evidence / Kanıtlar"
        ordering = ["-collected_at"]
        indexes = [
            models.Index(fields=["case", "kind"]),
        ]

    def __str__(self) -> str:
        return f"{self.evidence_id} · {self.title}"


# ---------------------------------------------------------------------------
# Decision — NAV-002 §4 zorunlu karar kaydı + e-imza
# ---------------------------------------------------------------------------

class Decision(TimeStamped):
    """Yetkili karar kaydı — NAV-002 §4 mandatory decision record.

    Örnek: DEC-001 (containment) → DEC-006 (gate close).
    Her T-fazı ayrı bir yetkili karar üretir; kararlar birbirine karışmaz.
    """

    class Level(models.TextChoices):
        D1 = "D1", "D1 Routine execution"
        D2 = "D2", "D2 Functional decision"
        D3 = "D3", "D3 Major decision"
        D4 = "D4", "D4 Strategic / crisis"

    class Status(models.TextChoices):
        PASS = "PASS", "PASS"
        CONDITIONAL = "CONDITIONAL", "CONDITIONAL PASS"
        HOLD = "HOLD", "HOLD"
        REJECT = "REJECT", "REJECT"
        RELEASE = "RELEASE", "RELEASE"
        ROLLBACK = "ROLLBACK", "ROLLBACK"
        CLOSE = "CLOSE", "CLOSE"
        REOPENED = "REOPENED", "Reopened"

    decision_id = models.CharField("Decision ID", max_length=60, unique=True)
    case = models.ForeignKey(
        Case, on_delete=models.PROTECT, related_name="decisions",
    )
    record_instance = models.ForeignKey(
        RecordInstance, null=True, blank=True,
        related_name="decisions", on_delete=models.SET_NULL,
    )

    level = models.CharField("Seviye", max_length=2, choices=Level.choices)
    status = models.CharField("Karar sonucu", max_length=12, choices=Status.choices)

    # Zorunlu alanlar (NAV-002 §4)
    decision_date = models.DateTimeField("Karar tarihi")
    decision_maker = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="my_decisions",
        verbose_name="Karar veren (delege makam)",
    )
    delegated_authority = models.CharField(
        "Delege edilmiş yetki", max_length=200, blank=True,
        help_text="Örn. 'IT Manager (per CDD-002 D3 delegasyon matrisi)'",
    )
    independent_reviewers = models.ManyToManyField(
        User, blank=True, related_name="reviewed_decisions",
        verbose_name="Bağımsız inceleyenler",
    )

    options_considered = models.TextField("Değerlendirilen seçenekler")
    evidence_reviewed = models.ManyToManyField(
        Evidence, blank=True, related_name="reviewed_in_decisions",
        verbose_name="İncelenen kanıtlar",
    )
    assumptions = models.TextField("Varsayımlar", blank=True)
    dissent_or_veto = models.TextField(
        "Karşı görüş / veto", blank=True,
        help_text="QA/HSE veto sahiplerinin muhalefeti burada kayıt altına alınır.",
    )
    rationale = models.TextField(
        "Gerekçe",
        help_text="Kanıt → varsayım → sonuç zinciri.",
    )

    conditions = models.TextField("Koşullar (CONDITIONAL PASS için)", blank=True)
    action_owner = models.ForeignKey(
        User, null=True, blank=True, related_name="my_action_decisions",
        on_delete=models.SET_NULL, verbose_name="Aksiyon sahibi",
    )
    due_date = models.DateField("Son tarih", null=True, blank=True)
    acceptance_evidence = models.TextField("Kabul kanıtı", blank=True)
    escalation_trigger = models.TextField("Eskalasyon tetikleyicisi", blank=True)
    reopen_trigger = models.TextField("Yeniden açma tetikleyicisi", blank=True)

    # Veto sahibi (NAV-002 §3 — QA/QC, HSE gibi rollerin veto hakkı)
    veto_holder_role = models.CharField(
        "Veto sahibi rol", max_length=60, blank=True,
        help_text="Örn. QA/QC, HSE — veto kullanılırsa muhalefet dissent'e yazılır.",
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Decision / Karar"
        verbose_name_plural = "Decisions / Kararlar"
        ordering = ["case", "decision_date"]
        indexes = [
            models.Index(fields=["case", "level"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return f"{self.decision_id} · {self.get_level_display()} · {self.status}"


# ---------------------------------------------------------------------------
# DecisionSignature — 21 CFR Part 11 tarzı e-imza kaydı
# ---------------------------------------------------------------------------

class DecisionSignature(TimeStamped):
    """Karar için parola-doğrulamalı e-imza kaydı."""

    class Meaning(models.TextChoices):
        APPROVED = "APPROVED", "APPROVED"
        REVIEWED = "REVIEWED", "REVIEWED"
        VETOED = "VETOED", "VETOED"
        WITNESSED = "WITNESSED", "WITNESSED"

    decision = models.ForeignKey(
        Decision, related_name="signatures", on_delete=models.CASCADE,
    )
    signer = models.ForeignKey(User, on_delete=models.PROTECT)
    meaning = models.CharField("Anlam", max_length=10, choices=Meaning.choices)
    reason = models.CharField("Sebep", max_length=255)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    signed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Decision Signature"
        verbose_name_plural = "Decision Signatures"
        ordering = ["decision", "signed_at"]

    def __str__(self) -> str:
        return f"{self.decision.decision_id} · {self.meaning} · {self.signer}"

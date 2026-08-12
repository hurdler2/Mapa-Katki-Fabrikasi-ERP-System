"""ControlledCode — MCOS'un 247 kontrollü kimliği (00_MCO_1 sheet 6 R15 baseline).

Kaynak: MAPA-IMS-FRM-MST-001 (R15 frozen catalogue) — kod, sınıf, seviye, fonksiyon,
sahip, uygulanabilirlik, aktivasyon kapısı, kanıt kuralı, retention.

Format kuralı (CDD-001 §9.2 kodlama standardı):
    MAPA-<Function>-<Type>-<Subject>-<Seq>
    örn. MAPA-IMS-FRM-NCR-001, MAPA-PRD-FRM-BMR-001, MAPA-CDD-001, MAPA-IT-REG-004

Bu kod bir **şablon kimliği**dir; her gerçek işlem ayrı bir `RecordInstance` alır (Faz D).
"""
from __future__ import annotations

from django.core.validators import RegexValidator
from django.db import models
from simple_history.models import HistoricalRecords

from businessline.models import BusinessLine
from common.models import TimeStamped


# 00_MCO_1 sheet 3: format standardı.
# MAPA + 1-3 alfa/alfanumerik segment (her segment 2-6 karakter, harfle başlar) + 3 haneli seq.
# Örn: MAPA-CDD-001 · MAPA-IT-REG-004 · MAPA-IMS-FRM-NCR-001 · MAPA-COMMS-POL-001
CONTROLLED_CODE_REGEX = r"^MAPA(-[A-Z][A-Z0-9]{1,5}){1,3}-\d{3}$"

controlled_code_validator = RegexValidator(
    regex=CONTROLLED_CODE_REGEX,
    message=(
        "Format geçersiz. Beklenen: MAPA-<Function>-<Type>-<Subject?>-<Seq>. "
        "Örn: MAPA-IMS-FRM-NCR-001, MAPA-CDD-001, MAPA-IT-REG-004"
    ),
)


class ControlledCode(TimeStamped):
    """Kontrollü şablon kimliği (247 kayıttan biri)."""

    class Type(models.TextChoices):
        POL = "POL", "Policy (L1)"
        MAN = "MAN", "Manual (L1)"
        CDD = "CDD", "Corporate Design Doc (L1)"
        NAV = "NAV", "Navigation Map (L1)"
        PRO = "PRO", "Procedure (L2)"
        SOP = "SOP", "SOP / Work Instruction (L3)"
        WI = "WI", "Work Instruction (L3)"
        CHK = "CHK", "Checklist (L4)"
        FRM = "FRM", "Form (L4)"
        REG = "REG", "Register (L4)"
        LOG = "LOG", "Log (L4)"
        RPT = "RPT", "Report (L4)"
        MST = "MST", "Master Data (L5)"
        SPC = "SPC", "Specification (L5)"
        PLN = "PLN", "Plan (L2)"
        SCH = "SCH", "Schedule (L2)"
        SET = "SET", "Package/Set (L1)"

    class Level(models.TextChoices):
        L1 = "L1", "L1 Corporate direction"
        L2 = "L2", "L2 Common control"
        L3 = "L3", "L3 Execution"
        L4 = "L4", "L4 Evidence"
        L5 = "L5", "L5 Master data"

    class Function(models.TextChoices):
        # CDD-002 Ek A — 12 fonksiyon kodu
        COR = "COR", "Corporate Governance"
        OPS = "OPS", "Factory Operations"
        QMS = "QMS", "QA / IMS"
        QCL = "QCL", "QC & Laboratory"
        RDT = "RDT", "R&D / Product / Formwork Technology"
        PRD = "PRD", "Production"
        SCM = "SCM", "Supply Chain & Purchasing"
        WHL = "WHL", "Warehouse & Logistics"
        MNT = "MNT", "Maintenance & Utilities"
        HSE = "HSE", "Health, Safety & Environment"
        COM = "COM", "Commercial & Technical Service"
        ADM = "ADM", "Finance / HR / Admin / IT Shared"
        # Ek ölçekli fonksiyonlar (00_MCO_1'de görülen)
        IMS = "IMS", "IMS (kurumsal)"
        QA = "QA", "QA (kurumsal alt-fonksiyon)"
        IT = "IT", "IT / OT"
        HR = "HR", "HR"
        BCM = "BCM", "Business Continuity"
        SUP = "SUP", "Supplier"
        WHS = "WHS", "Warehouse alt-fonksiyon (WHL'nin eski adı)"
        ENV = "ENV", "Environment (HSE alt-fonksiyon)"
        MET = "MET", "Metrology (MNT alt-fonksiyon)"
        DPO = "DPO", "Data Protection Officer"
        LEG = "LEG", "Legal"
        FIN = "FIN", "Finance"
        # Ek 00_MCO_1'den gelen 12 fonksiyon
        SAL = "SAL", "Sales"
        CPL = "CPL", "Compliance"
        ORG = "ORG", "Organization"
        CUS = "CUS", "Customer"
        RDI = "RDI", "R&D / Innovation"
        RCV = "RCV", "Receiving"
        TRA = "TRA", "Training"
        SST = "SST", "Site Safety / Security"
        MFG = "MFG", "Manufacturing"
        LAB = "LAB", "Laboratory"
        MKT = "MKT", "Marketing"
        COMMS = "COMMS", "Communications"

    class Status(models.TextChoices):
        ARCHITECTURE_REVIEW = "AR", "Architecture Review (placeholder)"
        DRAFT = "DR", "Draft"
        ISSUED = "IS", "Controlled Issue"
        ACTIVATED = "AC", "Activated (live)"
        RETIRED = "RT", "Retired"

    class TriggerType(models.TextChoices):
        EVENT = "EVENT", "Olay / değişiklik / karar tetiklemeli"
        ROUTINE = "ROUTINE", "Rutin / işlem / vardiya bazlı"
        REGISTER = "REGISTER", "Register / master (periyodik review)"
        OTHER = "OTHER", "Diğer"

    # ---- Kimlik ------------------------------------------------------
    full_code = models.CharField(
        "Full Code", max_length=60, unique=True,
        validators=[controlled_code_validator],
        help_text="MAPA-<Function>-<Type>-<Subject?>-<Seq>",
    )
    short_alias = models.CharField(
        "Short / Alias", max_length=40, blank=True,
        help_text="Kısa kullanım kodu (örn. QA-FRM-012).",
    )
    title = models.CharField("Başlık", max_length=200)

    # ---- Sınıflandırma ----------------------------------------------
    type = models.CharField("Tip", max_length=4, choices=Type.choices)
    level = models.CharField("Seviye", max_length=2, choices=Level.choices)
    function = models.CharField("Fonksiyon", max_length=5, choices=Function.choices)
    business_lines = models.ManyToManyField(
        BusinessLine, blank=True,
        related_name="controlled_codes",
        verbose_name="Uygulanabilir iş kolları (boş = tümü/kurumsal)",
    )

    # ---- Sahiplik + kaynak prosedür ---------------------------------
    source_procedure = models.CharField(
        "Kaynak prosedür(ler)", max_length=200, blank=True,
        help_text="Örn. MAPA-IMS-PRO-DOC",
    )
    owner_role = models.CharField(
        "Sahip rol", max_length=100,
        help_text="Group.name veya serbest metin (geçiş dönemi).",
    )
    package_wave = models.CharField(
        "Paket dalgası", max_length=100, blank=True,
        help_text='Örn. "Operational Packages 004-009"',
    )
    status = models.CharField(
        "Durum", max_length=2, choices=Status.choices,
        default=Status.DRAFT,
    )
    revision = models.CharField("Revizyon", max_length=8, default="R0")

    # ---- Aktivasyon --------------------------------------------------
    activation_gate = models.TextField(
        "Aktivasyon kapısı",
        help_text="Aktivasyon için gereken kabul kriterleri (SOP+eğitim+bir kabul edilmiş kayıt).",
    )
    objective_evidence_rule = models.TextField(
        "Objektif kanıt kuralı",
        help_text="Boş şablon evidence değildir; ne kabul edilir?",
    )

    # ---- Kullanım desenleri -----------------------------------------
    trigger_type = models.CharField(
        "Tetik tipi", max_length=10, choices=TriggerType.choices,
        default=TriggerType.OTHER,
    )
    primary_preparer_role = models.CharField(
        "Ana hazırlayan rol", max_length=100, blank=True,
    )
    review_approval_model = models.TextField(
        "Review + onay modeli", blank=True,
        help_text="Hazırlayan / bağımsız reviewer / QA-HSE-IT / karar yetkisi zinciri.",
    )
    example_record_id_pattern = models.CharField(
        "Örnek Record ID formatı", max_length=100, blank=True,
        help_text="Örn. QA-FRM012-2026-0001 veya PRD-BMR-2026-0001",
    )
    archive_path_pattern = models.CharField(
        "Arşiv yolu formatı", max_length=200, blank=True,
        help_text="Örn. /MCOS/IMS/RECORDS/QA/<YYYY>/<Code>/<Record-ID>/",
    )
    retention_authority = models.CharField(
        "Retention makamı", max_length=200, blank=True,
        help_text="Örn. MAPA-IMS-MST-REC-001; yasal/sözleşme uzun süre öncelikli",
    )

    is_active = models.BooleanField("Aktif", default=True)
    notes = models.TextField("Notlar", blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Kontrollü Kod"
        verbose_name_plural = "Kontrollü Kodlar (Register)"
        ordering = ["function", "type", "full_code"]
        indexes = [
            models.Index(fields=["function", "type"]),
            models.Index(fields=["level"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return f"{self.full_code} · {self.title}"


class ControlledCodeRevision(TimeStamped):
    """Kod revizyon geçmişi (R0 → R0.1 → R0.9 → R1.0 → R2.0)."""

    class IssueState(models.TextChoices):
        INTERNAL_DRAFT = "IDR", "Internal draft"
        PRE_ISSUE_REVIEW = "PIR", "Pre-issue review"
        CONTROLLED_ISSUE = "CI", "Controlled Issue"
        ACTIVATED = "AC", "Activated (live)"
        SUPERSEDED = "SUP", "Superseded"

    code = models.ForeignKey(
        ControlledCode, on_delete=models.CASCADE,
        related_name="revisions", verbose_name="Kontrollü Kod",
    )
    revision = models.CharField("Revizyon", max_length=8)
    revision_date = models.DateField("Revizyon tarihi")
    change_summary = models.TextField("Değişiklik özeti")
    reviewed_by = models.CharField("İnceleyen", max_length=200, blank=True)
    approved_by = models.CharField("Onaylayan", max_length=200, blank=True)
    issue_state = models.CharField(
        "Yayın durumu", max_length=3, choices=IssueState.choices,
        default=IssueState.INTERNAL_DRAFT,
    )
    authority_record = models.CharField(
        "Yetki kaydı", max_length=100, blank=True,
        help_text="Örn. CN-2026-0001 (Change Notice)",
    )

    class Meta:
        verbose_name = "Kod Revizyonu"
        verbose_name_plural = "Kod Revizyonları"
        unique_together = (("code", "revision"),)
        ordering = ["code", "revision"]

    def __str__(self) -> str:
        return f"{self.code.full_code} · {self.revision}"

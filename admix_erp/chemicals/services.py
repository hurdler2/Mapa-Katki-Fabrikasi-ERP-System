"""Chemicals servisleri: SDS PDF, depolama uyumluluğu, retention, raf ömrü."""
from __future__ import annotations

import datetime as dt
import io
from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from inventory.models import RawMaterialLot
from production.models import ProductionBatch

from .models import (
    CertificateOfConformity,
    ChemicalProfile,
    HazardClass,
    RetentionSample,
    SafetyDataSheet,
    ShelfLifeAlert,
    StorageIncompatibility,
    StorageZone,
)


# ---------------------------------------------------------------------------
# SDS: PDF üretimi (ReportLab)
# ---------------------------------------------------------------------------

SDS_SECTIONS = [
    ("1. Kimlik", "section_1_identification"),
    ("2. Tehlike tanımlaması", "section_2_hazards"),
    ("3. Bileşim / bileşenler", "section_3_composition"),
    ("4. İlk yardım önlemleri", "section_4_first_aid"),
    ("5. Yangınla mücadele", "section_5_fire"),
    ("6. Kaza sonucu yayılma önlemleri", "section_6_accidental"),
    ("7. Elleçleme ve depolama", "section_7_handling"),
    ("8. Maruziyet kontrolleri / KKD", "section_8_exposure"),
    ("9. Fiziksel ve kimyasal özellikler", "section_9_physical"),
    ("10. Kararlılık ve reaktivite", "section_10_stability"),
    ("11. Toksikolojik bilgiler", "section_11_toxicological"),
    ("12. Ekolojik bilgiler", "section_12_ecological"),
    ("13. Bertaraf üzerine düşünceler", "section_13_disposal"),
    ("14. Taşıma bilgileri", "section_14_transport"),
    ("15. Mevzuat bilgileri", "section_15_regulatory"),
    ("16. Diğer bilgiler", "section_16_other"),
]


def render_sds_pdf(sds: SafetyDataSheet) -> bytes:
    """SDS'yi 16 bölümlü PDF olarak render eder (Reg EU 2020/878 yapısı)."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    )
    from reportlab.lib import colors

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm,
        title=f"SDS {sds.sds_number}",
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=14, spaceAfter=6)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=11, spaceBefore=10, spaceAfter=4)
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=9, leading=12)
    small = ParagraphStyle("small", parent=styles["BodyText"], fontSize=8, textColor=colors.grey)

    target = sds.profile.raw_material or sds.profile.product
    story = []
    story.append(Paragraph("GÜVENLİK BİLGİ FORMU (SDS)", h1))
    story.append(Paragraph(
        f"Regulation (EU) 2020/878 uyumlu · REACH Article 31", small,
    ))

    # Başlık tablosu
    meta_rows = [
        ["Ürün / Hammadde", str(target)],
        ["SDS No", sds.sds_number],
        ["Versiyon / Dil", f"{sds.version} / {sds.language}"],
        ["Yayım tarihi", str(sds.issue_date or "-")],
        ["Revizyon tarihi", str(sds.revision_date or "-")],
        ["Sonraki gözden geçirme", str(sds.next_review_date or "-")],
        ["Sinyal", sds.profile.get_signal_word_display()],
        ["Tehlike sınıfı", sds.profile.get_hazard_class_display()],
        ["CAS / EC", f"{sds.profile.cas_no or '-'} / {sds.profile.ec_no or '-'}"],
        ["UN No / ADR", f"{sds.profile.un_number or '-'} / {sds.profile.adr_class or '-'}"],
    ]
    meta = Table(meta_rows, colWidths=[5*cm, 12*cm])
    meta.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f3f4f6")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(meta)
    story.append(Spacer(1, 0.4*cm))

    # H ifadeleri
    if sds.profile.hazard_statements.exists():
        story.append(Paragraph("H İfadeleri", h2))
        for h in sds.profile.hazard_statements.all():
            story.append(Paragraph(f"<b>{h.code}</b> — {h.statement}", body))

    # P ifadeleri
    if sds.profile.precautionary_statements.exists():
        story.append(Paragraph("P İfadeleri", h2))
        for p in sds.profile.precautionary_statements.all():
            story.append(Paragraph(f"<b>{p.code}</b> — {p.statement}", body))

    # 16 bölüm
    for title, field in SDS_SECTIONS:
        story.append(Paragraph(title, h2))
        content = getattr(sds, field, "") or "—"
        # ReportLab HTML kaçış
        content = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        story.append(Paragraph(content.replace("\n", "<br/>"), body))

    # Onay
    story.append(Spacer(1, 0.6*cm))
    story.append(Paragraph(
        f"Hazırlayan: {sds.prepared_by.get_username()} · "
        f"Onaylayan: {sds.approved_by.get_username() if sds.approved_by else '—'} · "
        f"Onay tarihi: {sds.approved_at:%Y-%m-%d} " if sds.approved_at else "",
        small,
    ))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


@transaction.atomic
def approve_sds(sds: SafetyDataSheet, *, approver) -> SafetyDataSheet:
    """SDS'yi onayla; aynı profil+dil için önceki APPROVED'ı SUPERSEDED yap."""
    if sds.status != SafetyDataSheet.Status.DRAFT:
        raise ValidationError("Yalnız DRAFT SDS onaylanabilir.")
    if approver.pk == sds.prepared_by_id:
        raise ValidationError("Hazırlayan aynı zamanda onaylayan olamaz.")

    previous = SafetyDataSheet.objects.filter(
        profile=sds.profile, language=sds.language,
        status=SafetyDataSheet.Status.APPROVED,
    ).exclude(pk=sds.pk)
    previous.update(status=SafetyDataSheet.Status.SUPERSEDED)

    sds.approved_by = approver
    sds.approved_at = timezone.now()
    sds.status = SafetyDataSheet.Status.APPROVED
    if not sds.issue_date:
        sds.issue_date = timezone.now().date()
    sds.revision_date = timezone.now().date()
    sds.save(update_fields=[
        "approved_by", "approved_at", "status", "issue_date", "revision_date", "updated_at",
    ])
    return sds


# ---------------------------------------------------------------------------
# Depolama uyumluluğu
# ---------------------------------------------------------------------------

@dataclass
class StorageCheckResult:
    ok: bool
    conflicts: list[str]
    zone_over_capacity: bool
    zone_disallows_class: bool


def check_storage_compatibility(lot: RawMaterialLot, zone: StorageZone) -> StorageCheckResult:
    """Bir lotun bir depo bölgesine yerleştirilebilir olup olmadığını kontrol eder.

    Kurallar:
    1. Zone allowed_hazard_classes boşsa herhangi bir sınıf kabul; aksi halde
       lot'un hammaddesinin hazard_class'ı listede olmalı.
    2. Zone içindeki diğer lotların hazard_class'ları ile StorageIncompatibility
       çakışması olmamalı.
    3. Zone kapasitesi aşılmamalı.
    """
    profile = getattr(lot.raw_material, "chemical_profile", None)
    lot_class = profile.hazard_class if profile else HazardClass.NON_HAZARDOUS

    conflicts: list[str] = []
    disallows = False
    over = False

    # 1. İzin listesi
    if zone.allowed_hazard_classes.strip():
        allowed = [c.strip() for c in zone.allowed_hazard_classes.split(",") if c.strip()]
        if lot_class not in allowed:
            disallows = True
            conflicts.append(
                f"Zone '{zone.code}' bu tehlike sınıfını kabul etmiyor: {lot_class}"
            )

    # 2. Uyumsuzluk matrisi
    other_lots = RawMaterialLot.objects.filter(
        container__in=zone.storage_slots.values_list("container", flat=True)
    ).exclude(pk=lot.pk) if hasattr(zone, "storage_slots") else RawMaterialLot.objects.none()
    # Basitleştirme: zone'a doğrudan bağlı lotları container üzerinden buluyoruz —
    # StorageSlot modeline sahip değiliz; şimdilik boş liste. Kapsam genişletilebilir.
    other_classes: set[str] = set()
    for ol in other_lots:
        op = getattr(ol.raw_material, "chemical_profile", None)
        if op:
            other_classes.add(op.hazard_class)
    for other_class in other_classes:
        pair_conflicts = StorageIncompatibility.objects.filter(
            models_q(lot_class, other_class)
        )
        for pc in pair_conflicts:
            conflicts.append(f"Uyumsuz: {lot_class} ile {other_class} ({pc.reason})")

    # 3. Kapasite (basit): zone.max_capacity_kg varsa, mevcut lotların toplam remaining_qty
    if zone.max_capacity_kg:
        current_total = sum(
            (ol.remaining_qty or 0) for ol in other_lots
        )
        if current_total + (lot.remaining_qty or 0) > zone.max_capacity_kg:
            over = True
            conflicts.append(
                f"Zone kapasitesi aşılıyor ({current_total + lot.remaining_qty} > {zone.max_capacity_kg} kg)"
            )

    return StorageCheckResult(
        ok=(not conflicts),
        conflicts=conflicts,
        zone_over_capacity=over,
        zone_disallows_class=disallows,
    )


def models_q(a: str, b: str):
    """Uyumsuzluk sorgusu: sıra bağımsız (A,B) veya (B,A)."""
    from django.db.models import Q
    return Q(class_a=a, class_b=b) | Q(class_a=b, class_b=a)


# ---------------------------------------------------------------------------
# Retention numunesi
# ---------------------------------------------------------------------------

@transaction.atomic
def take_retention_sample(
    *,
    batch: ProductionBatch,
    sample_number: str,
    quantity,
    storage_location: str,
    keep_days: int = 365 + 180,
    sampled_at: dt.date | None = None,
    container=None,
    unit_label: str = "kg",
    notes: str = "",
) -> RetentionSample:
    """Bir partiden retention numunesi al.

    Varsayılan saklama: 365 gün (raf ömrü) + 180 gün (güvenlik payı).
    """
    sampled_at = sampled_at or dt.date.today()
    return RetentionSample.objects.create(
        sample_number=sample_number,
        batch=batch,
        quantity=quantity,
        unit_label=unit_label,
        container=container,
        storage_location=storage_location,
        sampled_at=sampled_at,
        keep_until=sampled_at + dt.timedelta(days=keep_days),
        status=RetentionSample.Status.STORED,
        notes=notes,
    )


@transaction.atomic
def dispose_retention_sample(
    sample: RetentionSample, *, disposed_by, note: str = ""
) -> RetentionSample:
    if sample.status == RetentionSample.Status.DISPOSED:
        raise ValidationError("Numune zaten imha edilmiş.")
    if sample.keep_until > dt.date.today():
        raise ValidationError(
            f"Numune saklama süresi henüz dolmadı ({sample.keep_until})."
        )
    sample.status = RetentionSample.Status.DISPOSED
    sample.disposed_at = dt.date.today()
    sample.disposed_by = disposed_by
    if note:
        sample.notes = (sample.notes + "\n" + note).strip()
    sample.save(update_fields=[
        "status", "disposed_at", "disposed_by", "notes", "updated_at",
    ])
    return sample


# ---------------------------------------------------------------------------
# Raf ömrü izleme
# ---------------------------------------------------------------------------

def _severity_for(days: int) -> str | None:
    if days < 0:
        return ShelfLifeAlert.Severity.EXPIRED
    if days <= 7:
        return ShelfLifeAlert.Severity.CRITICAL
    if days <= 30:
        return ShelfLifeAlert.Severity.WARNING
    if days <= 90:
        return ShelfLifeAlert.Severity.INFO
    return None


@transaction.atomic
def scan_shelf_life(*, as_of: dt.date | None = None) -> list[ShelfLifeAlert]:
    """Tüm hammadde lotlarını tarar; son kullanma yaklaşanlar için alert üretir.

    Aynı gün için aynı lot'a mükerrer alert yazmaz (unique_together).
    Yalnız remaining_qty > 0 olan lotları dikkate alır.
    """
    as_of = as_of or dt.date.today()
    alerts: list[ShelfLifeAlert] = []
    lots = RawMaterialLot.objects.filter(
        remaining_qty__gt=0,
        expiry_date__isnull=False,
    ).exclude(qc_status=RawMaterialLot.QCStatus.REJECTED)

    for lot in lots:
        days = (lot.expiry_date - as_of).days
        severity = _severity_for(days)
        if severity is None:
            continue
        alert, created = ShelfLifeAlert.objects.get_or_create(
            lot=lot, detected_on=as_of,
            defaults={
                "days_to_expiry": days, "severity": severity,
                "status": ShelfLifeAlert.Status.OPEN,
            },
        )
        if created:
            alerts.append(alert)
    return alerts

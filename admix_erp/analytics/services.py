"""Analytics servisleri: OEE, fire trendi, tedarikçi/QC/şikayet KPI'ları,
ISO denetim paketi verisi.
"""
from __future__ import annotations

import datetime as dt
from collections import defaultdict
from decimal import Decimal

from django.db.models import Avg, Count, Q, Sum

from chemicals.models import ShelfLifeAlert
from cmms.models import CalibrationRecord, CalibrationSchedule, Equipment, WorkOrder
from cmms.services import calculate_mtbf_mttr
from docs.models import ControlledDocument, DocumentRevision
from ehs.models import Incident, LegalRequirement
from governance.models import AuditFinding, InternalAudit, ManagementReview, RiskItem
from inventory.models import RawMaterialLot
from production.models import MaterialConsumption, ProductionBatch
from purchasing.models import GoodsReceipt, PurchaseOrder
from qms.models import CAPA, CustomerComplaint, Nonconformance
from quality.models import QCTestResult


ZERO = Decimal("0")


def _month_range(months: int = 6, as_of: dt.date | None = None) -> list[dt.date]:
    """Son N ay için (yılın 1'i) tarih listesi."""
    as_of = as_of or dt.date.today()
    out = []
    y, m = as_of.year, as_of.month
    for _ in range(months):
        out.append(dt.date(y, m, 1))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return list(reversed(out))


# ---------------------------------------------------------------------------
# OEE
# ---------------------------------------------------------------------------

def oee_by_equipment(*, since: dt.date | None = None, until: dt.date | None = None) -> list[dict]:
    """Ekipman başına OEE (Overall Equipment Effectiveness) tahminleri.

    OEE = Availability × Performance × Quality
    Bu ERP sınırlı bilgi tuttuğu için basitleştirilmiş yaklaşım:
      Availability: (period_hours - downtime) / period_hours [CMMS]
      Performance:  actual_qty / target_qty [production]
      Quality:      RELEASED batch / total batch [production]
    """
    since = since or (dt.date.today() - dt.timedelta(days=30))
    until = until or dt.date.today()
    out = []

    for eq in Equipment.objects.filter(category=Equipment.Category.REACTOR):
        metrics = calculate_mtbf_mttr(eq, since=since, until=until)
        availability = metrics.get("availability_pct") or 100.0

        # Ekipman bir Container'a bağlıysa o Container üzerinden partileri bul.
        # (ProductionBatch.reactor bir Container FK'sidir; Equipment değil.)
        if eq.container_id is None:
            batches = ProductionBatch.objects.none()
        else:
            batches = ProductionBatch.objects.filter(
                reactor_id=eq.container_id,
                completed_at__date__gte=since,
                completed_at__date__lte=until,
            )
        total = batches.count()
        released = batches.filter(qc_status=ProductionBatch.QCStatus.RELEASED).count()
        with_actual = batches.filter(actual_qty__isnull=False)
        agg = with_actual.aggregate(t=Sum("target_qty"), a=Sum("actual_qty"))
        performance = 100.0
        if agg["t"] and agg["t"] > 0:
            performance = float(agg["a"] or 0) / float(agg["t"]) * 100
        quality = 100.0 if total == 0 else (released / total) * 100
        oee = availability * performance * quality / 10000

        out.append({
            "equipment": eq.equipment_number,
            "name": eq.name,
            "availability_pct": round(availability, 2),
            "performance_pct": round(performance, 2),
            "quality_pct": round(quality, 2),
            "oee_pct": round(oee, 2),
            "batches": total,
        })
    return out


# ---------------------------------------------------------------------------
# Fire trendi (aylık)
# ---------------------------------------------------------------------------

def waste_trend(months: int = 6) -> list[dict]:
    """Aylık toplam fire (target - actual) ve fire yüzdesi."""
    trend = []
    for month_start in _month_range(months):
        # Ayın son günü
        if month_start.month == 12:
            month_end = dt.date(month_start.year + 1, 1, 1) - dt.timedelta(days=1)
        else:
            month_end = dt.date(month_start.year, month_start.month + 1, 1) - dt.timedelta(days=1)

        qs = ProductionBatch.objects.filter(
            completed_at__date__gte=month_start,
            completed_at__date__lte=month_end,
            actual_qty__isnull=False,
        )
        agg = qs.aggregate(t=Sum("target_qty"), a=Sum("actual_qty"))
        target = agg["t"] or ZERO
        actual = agg["a"] or ZERO
        waste = max(ZERO, target - actual)
        pct = float(waste / target * 100) if target > 0 else 0
        trend.append({
            "month": month_start.strftime("%Y-%m"),
            "target_qty": float(target),
            "actual_qty": float(actual),
            "waste_qty": float(waste),
            "waste_pct": round(pct, 2),
            "batches": qs.count(),
        })
    return trend


# ---------------------------------------------------------------------------
# Tedarikçi performansı
# ---------------------------------------------------------------------------

def supplier_scorecard(*, since: dt.date | None = None) -> list[dict]:
    """Tedarikçi başına: mal kabul sayısı, ret oranı, ortalama gecikme (basitleştirilmiş)."""
    since = since or (dt.date.today() - dt.timedelta(days=180))

    rows = []
    for gr_supplier_id in GoodsReceipt.objects.filter(
        received_date__gte=since,
    ).values_list("supplier_id", flat=True).distinct():
        receipts = GoodsReceipt.objects.filter(
            supplier_id=gr_supplier_id, received_date__gte=since,
        )
        lots = RawMaterialLot.objects.filter(
            supplier_id=gr_supplier_id, received_date__gte=since,
        )
        total_lots = lots.count()
        rejected = lots.filter(qc_status=RawMaterialLot.QCStatus.REJECTED).count()
        quarantine = lots.filter(qc_status=RawMaterialLot.QCStatus.QUARANTINE).count()
        released = lots.filter(qc_status=RawMaterialLot.QCStatus.RELEASED).count()
        ncr_count = Nonconformance.objects.filter(
            source=Nonconformance.Source.SUPPLIER,
            detected_at__date__gte=since,
        ).count()

        rej_pct = (rejected / total_lots * 100) if total_lots else 0
        first_rec = receipts.first()
        supplier_name = first_rec.supplier.name if first_rec else "?"

        rows.append({
            "supplier": supplier_name,
            "receipts": receipts.count(),
            "lots_total": total_lots,
            "lots_released": released,
            "lots_quarantine": quarantine,
            "lots_rejected": rejected,
            "rejection_pct": round(rej_pct, 2),
            "ncr_count": ncr_count,
        })
    return sorted(rows, key=lambda r: r["rejection_pct"], reverse=True)


# ---------------------------------------------------------------------------
# Müşteri şikayeti trendi
# ---------------------------------------------------------------------------

def complaint_trend(months: int = 6) -> list[dict]:
    """Aylık müşteri şikayet sayısı ve ortalama çözüm süresi."""
    trend = []
    for month_start in _month_range(months):
        if month_start.month == 12:
            month_end = dt.date(month_start.year + 1, 1, 1) - dt.timedelta(days=1)
        else:
            month_end = dt.date(month_start.year, month_start.month + 1, 1) - dt.timedelta(days=1)

        qs = CustomerComplaint.objects.filter(
            received_at__date__gte=month_start,
            received_at__date__lte=month_end,
        )
        by_sev = {s: qs.filter(severity=s).count() for s in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]}
        resolved_qs = qs.filter(resolved_at__isnull=False)
        # ortalama çözüm süresi (gün)
        deltas = [
            (c.resolved_at - c.received_at).total_seconds() / 86400
            for c in resolved_qs
        ]
        avg_days = round(sum(deltas) / len(deltas), 1) if deltas else 0

        trend.append({
            "month": month_start.strftime("%Y-%m"),
            "total": qs.count(),
            "resolved": resolved_qs.count(),
            "by_severity": by_sev,
            "avg_resolution_days": avg_days,
        })
    return trend


# ---------------------------------------------------------------------------
# QC ret oranı + hammadde tüketimi
# ---------------------------------------------------------------------------

def qc_pass_fail_stats(*, since: dt.date | None = None) -> dict:
    """QCTestResult PASS/FAIL/NA dağılımı."""
    since = since or (dt.date.today() - dt.timedelta(days=90))
    qs = QCTestResult.objects.filter(tested_at__date__gte=since)
    total = qs.count()
    counts = dict(qs.values_list("verdict").annotate(n=Count("id")).values_list("verdict", "n"))
    fail = counts.get("FAIL", 0)
    return {
        "total": total,
        "pass_count": counts.get("PASS", 0),
        "fail_count": fail,
        "na_count": counts.get("NA", 0),
        "fail_pct": round((fail / total * 100), 2) if total else 0,
    }


# ---------------------------------------------------------------------------
# NCR/CAPA yaşlanma
# ---------------------------------------------------------------------------

def ncr_capa_aging() -> dict:
    """Açık NCR ve CAPA'lar için yaşlanma (0-7, 8-30, 31-90, >90 gün)."""
    buckets = {"0-7": 0, "8-30": 0, "31-90": 0, ">90": 0}
    today = dt.date.today()

    def _bucketize(created_date):
        age = (today - created_date).days
        if age <= 7:
            return "0-7"
        if age <= 30:
            return "8-30"
        if age <= 90:
            return "31-90"
        return ">90"

    open_ncrs = Nonconformance.objects.exclude(status=Nonconformance.Status.CLOSED)
    ncr_buckets = dict(buckets)
    for n in open_ncrs:
        ncr_buckets[_bucketize(n.detected_at.date())] += 1

    open_capas = CAPA.objects.exclude(status=CAPA.Status.CLOSED)
    capa_buckets = dict(buckets)
    for c in open_capas:
        capa_buckets[_bucketize(c.opened_at.date())] += 1

    return {
        "ncr_open": open_ncrs.count(),
        "ncr_by_age": ncr_buckets,
        "capa_open": open_capas.count(),
        "capa_by_age": capa_buckets,
    }


# ---------------------------------------------------------------------------
# ISO Denetim Paketi
# ---------------------------------------------------------------------------

def iso_audit_package(*, since: dt.date | None = None) -> dict:
    """Bir ISO denetimi için hazır özet paket.

    Denetçiye sunulacak tüm ana veriler tek yerde:
    - Doküman kontrolü durumu (SOP/WI aktif revizyonlar)
    - QMS: açık NCR/CAPA + yaşlanma
    - Bakım/Kalibrasyon: vade durumu, FAIL sayısı
    - İç denetim özeti (majör/minör/OFI)
    - Yönetim gözden geçirme
    - Yasal uyum durumu
    - EHS olay istatistiği
    - Kalite KPI'ları (test PASS/FAIL, müşteri şikayeti)
    """
    since = since or (dt.date.today() - dt.timedelta(days=365))

    # Doküman kontrolü
    docs_active = ControlledDocument.objects.filter(
        status=ControlledDocument.Status.ACTIVE
    ).count()
    revs_effective = DocumentRevision.objects.filter(
        status=DocumentRevision.Status.EFFECTIVE
    ).count()
    revs_overdue_review = DocumentRevision.objects.filter(
        status=DocumentRevision.Status.EFFECTIVE,
        next_review_date__isnull=False,
        next_review_date__lt=dt.date.today(),
    ).count()

    # NCR/CAPA
    aging = ncr_capa_aging()
    ncr_by_source = dict(
        Nonconformance.objects.values("source").annotate(n=Count("id")).values_list("source", "n")
    )

    # Kalibrasyon
    cal_schedules_total = CalibrationSchedule.objects.filter(is_active=True).count()
    cal_overdue = CalibrationSchedule.objects.filter(
        is_active=True, next_due_date__isnull=False,
        next_due_date__lt=dt.date.today(),
    ).count()
    cal_last_12mo = CalibrationRecord.objects.filter(
        performed_at__gte=dt.date.today() - dt.timedelta(days=365)
    )
    cal_pass_count = cal_last_12mo.filter(result=CalibrationRecord.Result.PASS).count()
    cal_fail_count = cal_last_12mo.filter(result=CalibrationRecord.Result.FAIL).count()

    # İç denetim
    audits = InternalAudit.objects.filter(scheduled_date__gte=since)
    findings_by_level = dict(
        AuditFinding.objects.filter(audit__in=audits)
        .values("level").annotate(n=Count("id")).values_list("level", "n")
    )

    # Yönetim gözden geçirme
    mrs = ManagementReview.objects.filter(meeting_date__gte=since).order_by("-meeting_date")

    # Yasal uyum
    legal_stats = dict(
        LegalRequirement.objects.values("compliance_status").annotate(n=Count("id"))
        .values_list("compliance_status", "n")
    )

    # EHS
    incidents = Incident.objects.filter(occurred_at__date__gte=since)
    incidents_by_severity = dict(
        incidents.values("severity").annotate(n=Count("id"))
        .values_list("severity", "n")
    )

    # Kalite
    qc = qc_pass_fail_stats(since=since)
    complaint_total = CustomerComplaint.objects.filter(received_at__date__gte=since).count()

    # Risk
    open_risks = RiskItem.objects.exclude(status=RiskItem.Status.CLOSED)
    high_risks = [r for r in open_risks if r.inherent_score >= 15]

    return {
        "period": {"from": since, "to": dt.date.today()},
        "documents": {
            "active": docs_active,
            "effective_revisions": revs_effective,
            "overdue_reviews": revs_overdue_review,
        },
        "qms": {
            **aging,
            "ncr_by_source": ncr_by_source,
        },
        "calibration": {
            "schedules_total": cal_schedules_total,
            "overdue": cal_overdue,
            "pass_last_12mo": cal_pass_count,
            "fail_last_12mo": cal_fail_count,
        },
        "internal_audit": {
            "audits_count": audits.count(),
            "findings_by_level": findings_by_level,
        },
        "management_review": {
            "count": mrs.count(),
            "last_date": mrs.first().meeting_date if mrs.exists() else None,
        },
        "legal_compliance": legal_stats,
        "ehs": {
            "incidents_total": incidents.count(),
            "by_severity": incidents_by_severity,
            "lost_days": incidents.aggregate(t=Sum("days_lost"))["t"] or 0,
        },
        "quality": {
            **qc,
            "customer_complaints": complaint_total,
        },
        "risk": {
            "open_total": open_risks.count(),
            "high_score_15plus": len(high_risks),
        },
        "shelf_life_alerts_open": ShelfLifeAlert.objects.filter(
            status=ShelfLifeAlert.Status.OPEN
        ).count(),
    }

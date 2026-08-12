"""BI dashboard, ISO denetim paketi (JSON + PDF)."""
from __future__ import annotations

import io
import json
import zipfile
import datetime as dt

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render

from .services import (
    complaint_trend,
    iso_audit_package,
    ncr_capa_aging,
    oee_by_equipment,
    qc_pass_fail_stats,
    supplier_scorecard,
    waste_trend,
)


@staff_member_required
def bi_dashboard(request: HttpRequest) -> HttpResponse:
    ctx = {
        "oee": oee_by_equipment(),
        "waste": waste_trend(6),
        "supplier": supplier_scorecard(),
        "complaints": complaint_trend(6),
        "qc": qc_pass_fail_stats(),
        "aging": ncr_capa_aging(),
        "waste_json": json.dumps(waste_trend(6)),
        "complaints_json": json.dumps(complaint_trend(6)),
        "oee_json": json.dumps(oee_by_equipment()),
        "aging_json": json.dumps(ncr_capa_aging()),
    }
    return render(request, "analytics/bi_dashboard.html", ctx)


@staff_member_required
def iso_audit_view(request: HttpRequest) -> HttpResponse:
    pkg = iso_audit_package()
    return render(request, "analytics/iso_audit.html", {"pkg": pkg})


@staff_member_required
def iso_audit_json(request: HttpRequest) -> JsonResponse:
    """JSON export — denetçi harici tool ile analiz eder."""
    pkg = iso_audit_package()
    # datetime.date'i str yap
    def _default(o):
        if isinstance(o, dt.date):
            return o.isoformat()
        return str(o)
    return JsonResponse(pkg, safe=False, json_dumps_params={"default": _default,
                                                              "indent": 2})


def _build_iso_audit_pdf_bytes() -> bytes:
    """ISO denetim paketi PDF gövdesi (view-agnostik)."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    )

    pkg = iso_audit_package()
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Heading1"], fontSize=15, spaceAfter=6)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=11,
                        spaceBefore=10, spaceAfter=4)
    body = ParagraphStyle("body", parent=ss["BodyText"], fontSize=9, leading=12)
    small = ParagraphStyle("small", parent=ss["BodyText"], fontSize=8,
                           textColor=colors.grey)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm, topMargin=1.5*cm, bottomMargin=2*cm,
        title="ISO Denetim Paketi",
    )
    story = []
    story.append(Paragraph("ISO DENETİM PAKETİ", h1))
    story.append(Paragraph(
        f"Dönem: {pkg['period']['from']} → {pkg['period']['to']}", small))
    story.append(Spacer(1, 0.3*cm))

    def _kv_table(items):
        rows = [[k, str(v)] for k, v in items]
        if not rows:
            rows = [["(kayıt yok)", ""]]
        t = Table(rows, colWidths=[8*cm, 8*cm])
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f3f4f6")),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))
        return t

    story.append(Paragraph("Doküman Kontrolü (ISO 9001 §7.5)", h2))
    story.append(_kv_table([
        ("Aktif doküman sayısı", pkg["documents"]["active"]),
        ("Yürürlükteki revizyon", pkg["documents"]["effective_revisions"]),
        ("Vadesi geçen gözden geçirme", pkg["documents"]["overdue_reviews"]),
    ]))

    story.append(Paragraph("QMS — NCR/CAPA (§8.7, §10.2)", h2))
    story.append(_kv_table([
        ("Açık NCR", pkg["qms"]["ncr_open"]),
        ("NCR yaş dağılımı", pkg["qms"]["ncr_by_age"]),
        ("NCR kaynak dağılımı", pkg["qms"]["ncr_by_source"]),
        ("Açık CAPA", pkg["qms"]["capa_open"]),
        ("CAPA yaş dağılımı", pkg["qms"]["capa_by_age"]),
    ]))

    story.append(Paragraph("Kalibrasyon (§7.1.5.2)", h2))
    story.append(_kv_table([
        ("Toplam plan", pkg["calibration"]["schedules_total"]),
        ("Vadesi geçen", pkg["calibration"]["overdue"]),
        ("Son 12 ay PASS", pkg["calibration"]["pass_last_12mo"]),
        ("Son 12 ay FAIL", pkg["calibration"]["fail_last_12mo"]),
    ]))

    story.append(Paragraph("İç Denetim (§9.2)", h2))
    story.append(_kv_table([
        ("Denetim sayısı", pkg["internal_audit"]["audits_count"]),
        ("Bulgu dağılımı (majör/minör/OFI)",
            pkg["internal_audit"]["findings_by_level"]),
    ]))

    story.append(Paragraph("Yönetim Gözden Geçirme (§9.3)", h2))
    story.append(_kv_table([
        ("Toplantı sayısı", pkg["management_review"]["count"]),
        ("Son toplantı", pkg["management_review"]["last_date"] or "-"),
    ]))

    story.append(Paragraph("Yasal Uyum", h2))
    story.append(_kv_table(pkg["legal_compliance"].items()))

    story.append(Paragraph("EHS", h2))
    story.append(_kv_table([
        ("Olay sayısı", pkg["ehs"]["incidents_total"]),
        ("Ağırlık dağılımı", pkg["ehs"]["by_severity"]),
        ("Toplam kayıp işgünü", pkg["ehs"]["lost_days"]),
    ]))

    story.append(Paragraph("Kalite (QC)", h2))
    story.append(_kv_table([
        ("Toplam test", pkg["quality"]["total"]),
        ("PASS", pkg["quality"]["pass_count"]),
        ("FAIL", pkg["quality"]["fail_count"]),
        ("FAIL %", pkg["quality"]["fail_pct"]),
        ("Müşteri şikayeti (12 ay)", pkg["quality"]["customer_complaints"]),
    ]))

    story.append(Paragraph("Risk (§6.1)", h2))
    story.append(_kv_table([
        ("Toplam açık", pkg["risk"]["open_total"]),
        ("Yüksek skor (≥15)", pkg["risk"]["high_score_15plus"]),
    ]))

    story.append(Paragraph("Raf Ömrü Alertları", h2))
    story.append(_kv_table([
        ("Açık alert", pkg["shelf_life_alerts_open"]),
    ]))

    story.append(Spacer(1, 0.6*cm))
    story.append(Paragraph(
        "Bu belge ADMIX-ERP tarafından otomatik üretilmiştir. "
        "İlgili modüllerin altındaki ayrıntı kayıtları denetçiye ayrıca sunulur.",
        small,
    ))

    doc.build(story)
    pdf = buf.getvalue()
    buf.close()
    return pdf


@staff_member_required
def iso_audit_pdf(request: HttpRequest) -> HttpResponse:
    """ISO denetim paketi PDF view."""
    pdf = _build_iso_audit_pdf_bytes()
    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="iso_audit_{dt.date.today()}.pdf"'
    return resp


@staff_member_required
def iso_audit_zip(request: HttpRequest) -> HttpResponse:
    """ISO denetim paketi ZIP — JSON + PDF birlikte."""
    pdf_bytes = _build_iso_audit_pdf_bytes()

    # JSON
    pkg = iso_audit_package()
    def _default(o):
        if isinstance(o, dt.date):
            return o.isoformat()
        return str(o)
    json_bytes = json.dumps(pkg, indent=2, default=_default).encode("utf-8")

    # ZIP
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"iso_audit_{dt.date.today()}.pdf", pdf_bytes)
        zf.writestr(f"iso_audit_{dt.date.today()}.json", json_bytes)
    zip_bytes = buf.getvalue()
    buf.close()

    resp = HttpResponse(zip_bytes, content_type="application/zip")
    resp["Content-Disposition"] = f'attachment; filename="iso_audit_{dt.date.today()}.zip"'
    return resp

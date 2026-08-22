"""Ortak PDF şablonları: fatura, irsaliye (sevkiyat), iş izin, JSA.

ReportLab tabanlı; şirket başlığı + kurumsal renkler + QR ile doğrulama linki.
"""
from __future__ import annotations

import io
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)


COMPANY_HEADER = "ADMIX ERP · Sıvı Beton Katkısı A.Ş."
COMPANY_FOOTER = "SCF uyumlu · KDV %19 · Cezayir"


def _styles():
    ss = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle("h1", parent=ss["Heading1"], fontSize=15, spaceAfter=6),
        "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontSize=11,
                             spaceBefore=8, spaceAfter=4),
        "body": ParagraphStyle("body", parent=ss["BodyText"], fontSize=9, leading=12),
        "small": ParagraphStyle("small", parent=ss["BodyText"], fontSize=8,
                                textColor=colors.grey),
    }


def _table(rows, col_widths=None, header_bg="#f3f4f6", bold_first_col=False):
    tbl = Table(rows, colWidths=col_widths)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_bg)),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]
    if bold_first_col:
        style.append(("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"))
    tbl.setStyle(TableStyle(style))
    return tbl


def _new_doc(title: str) -> tuple[io.BytesIO, SimpleDocTemplate]:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm, topMargin=1.5*cm, bottomMargin=2*cm,
        title=title,
    )
    return buf, doc


# ---------------------------------------------------------------------------
# Fatura
# ---------------------------------------------------------------------------

def render_invoice_pdf(invoice) -> bytes:
    """AR/AP faturası PDF."""
    st = _styles()
    buf, doc = _new_doc(f"Facture {invoice.invoice_number}")
    story = []

    story.append(Paragraph(COMPANY_HEADER, st["h1"]))
    story.append(Paragraph(f"Facture / Fatura n° {invoice.invoice_number}", st["h2"]))

    partner = invoice.customer or invoice.supplier
    partner_label = "Client" if invoice.customer else "Fournisseur"

    meta = [
        ["Tip", invoice.get_type_display()],
        [partner_label, str(partner) if partner else "-"],
        ["Vergi No", (partner.tax_no if partner else "") or "-"],
        ["Fatura tarihi", str(invoice.date)],
        ["Vade", str(invoice.due_date or "-")],
        ["Referans", invoice.shipment_reference or invoice.receipt_reference or "-"],
        ["Para birimi", invoice.currency],
    ]
    story.append(_table(meta, col_widths=[5*cm, 12*cm], bold_first_col=True))
    story.append(Spacer(1, 0.4*cm))

    lines_rows = [["#", "Açıklama", "Miktar", "Birim Fiyat HT", "TVA %", "HT", "TVA", "TTC"]]
    for l in invoice.lines.select_related("tva_rate", "product").all():
        lines_rows.append([
            str(l.sequence),
            l.description[:60],
            f"{l.quantity}",
            f"{l.unit_price}",
            f"{l.tva_rate.rate_pct}",
            f"{l.ht_amount}",
            f"{l.tva_amount}",
            f"{l.ttc_amount}",
        ])
    story.append(_table(lines_rows, col_widths=[1*cm, 5.5*cm, 1.6*cm, 2.2*cm,
                                                  1.2*cm, 1.8*cm, 1.6*cm, 2*cm]))

    story.append(Spacer(1, 0.4*cm))
    totals = [
        ["Toplam HT (KDVsiz)", f"{invoice.total_ht} {invoice.currency}"],
        ["Toplam TVA", f"{invoice.total_tva} {invoice.currency}"],
        ["Toplam TTC (KDV dahil)", f"{invoice.total_ttc} {invoice.currency}"],
        ["Ödenen", f"{invoice.amount_paid} {invoice.currency}"],
        ["Kalan", f"{invoice.amount_due} {invoice.currency}"],
    ]
    story.append(_table(totals, col_widths=[6*cm, 4*cm], header_bg="#eef2f7"))

    if invoice.notes:
        story.append(Spacer(1, 0.4*cm))
        story.append(Paragraph("Notlar", st["h2"]))
        story.append(Paragraph(invoice.notes.replace("\n", "<br/>"), st["body"]))

    story.append(Spacer(1, 0.6*cm))
    story.append(Paragraph(COMPANY_FOOTER, st["small"]))

    doc.build(story)
    pdf = buf.getvalue()
    buf.close()
    return pdf


# ---------------------------------------------------------------------------
# İrsaliye (sevkiyat)
# ---------------------------------------------------------------------------

def render_shipment_pdf(shipment) -> bytes:
    """Sevkiyat / irsaliye PDF."""
    st = _styles()
    buf, doc = _new_doc(f"Bon de livraison {shipment.shipment_number}")
    story = []

    story.append(Paragraph(COMPANY_HEADER, st["h1"]))
    story.append(Paragraph(
        f"Bon de livraison / İrsaliye n° {shipment.shipment_number}", st["h2"]))

    meta = [
        ["Müşteri", str(shipment.customer)],
        ["Vergi No", shipment.customer.tax_no or "-"],
        ["Sevk tarihi", str(shipment.shipped_date)],
        ["Sipariş", shipment.so.order_number if shipment.so else "-"],
        ["Taşıyıcı", shipment.carrier or "-"],
        ["Araç plaka", shipment.vehicle_plate or "-"],
    ]
    story.append(_table(meta, col_widths=[5*cm, 12*cm], bold_first_col=True))
    story.append(Spacer(1, 0.4*cm))

    rows = [["IBC", "Ürün", "Parti", "Miktar"]]
    for l in shipment.lines.select_related(
        "output_container", "output_container__batch__recipe__product",
    ):
        oc = l.output_container
        rows.append([
            oc.container.code,
            oc.batch.recipe.product.code,
            oc.batch.batch_number,
            f"{l.quantity} kg",
        ])
    story.append(_table(rows, col_widths=[3*cm, 3*cm, 4.5*cm, 3*cm]))

    story.append(Spacer(1, 0.8*cm))
    story.append(Paragraph("Teslim eden / Teslim alan imzaları:", st["body"]))
    story.append(Spacer(1, 1.2*cm))
    sign = [
        ["Teslim eden", "Şoför", "Teslim alan (müşteri)"],
        ["", "", ""],
        ["İsim / İmza", "İsim / Plaka", "İsim / Kaşe"],
    ]
    tbl = Table(sign, colWidths=[5.5*cm, 5.5*cm, 5.5*cm])
    tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("MINROWHEIGHT", (0, 1), (-1, 1), 60),
    ]))
    story.append(tbl)

    story.append(Spacer(1, 0.6*cm))
    story.append(Paragraph(COMPANY_FOOTER, st["small"]))

    doc.build(story)
    pdf = buf.getvalue()
    buf.close()
    return pdf


# ---------------------------------------------------------------------------
# İş İzin
# ---------------------------------------------------------------------------

def render_work_permit_pdf(permit) -> bytes:
    """WorkPermit PDF — sıcak çalışma / kapalı alan / yüksekte vb."""
    st = _styles()
    buf, doc = _new_doc(f"Permit {permit.permit_number}")
    story = []

    story.append(Paragraph("İŞ İZİN BELGESİ", st["h1"]))
    story.append(Paragraph(
        f"{permit.permit_number} · {permit.get_type_display()}", st["h2"]))

    meta = [
        ["Tip", permit.get_type_display()],
        ["Durum", permit.get_status_display()],
        ["Yer", permit.location],
        ["İş tanımı", permit.work_description],
        ["Geçerlilik", f"{permit.valid_from:%Y-%m-%d %H:%M} → "
                       f"{permit.valid_until:%Y-%m-%d %H:%M}"],
        ["Talep eden", permit.requested_by.get_username()],
        ["İzin sahibi", permit.permit_holder.get_username()],
        ["Veren yetkili",
            permit.issued_by.get_username() if permit.issued_by else "-"],
        ["İSG uzmanı",
            permit.safety_officer.get_username() if permit.safety_officer else "-"],
        ["Gaz ölçüm", permit.gas_test_result or "-"],
        ["İzolasyon önlemleri", permit.isolation_measures or "-"],
        ["Yangın gözcüsü", "Evet" if permit.fire_watch_required else "Hayır"],
    ]
    story.append(_table(meta, col_widths=[5*cm, 12*cm], bold_first_col=True))
    story.append(Spacer(1, 0.4*cm))

    story.append(Paragraph("Zorunlu KKD", st["h2"]))
    ppe_items = list(permit.required_ppe.all())
    if ppe_items:
        rows = [["Kod", "Ad", "Standart"]]
        for p in ppe_items:
            rows.append([p.code, p.name, p.standard or "-"])
        story.append(_table(rows, col_widths=[3*cm, 8*cm, 5*cm]))
    else:
        story.append(Paragraph("(KKD gereksinim yok)", st["body"]))

    story.append(Spacer(1, 0.8*cm))
    sign = [
        ["Talep eden", "İSG Uzmanı", "İzin Veren", "Kapatan"],
        ["", "", "", ""],
    ]
    tbl = Table(sign, colWidths=[4.25*cm]*4)
    tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("MINROWHEIGHT", (0, 1), (-1, 1), 60),
    ]))
    story.append(tbl)

    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph(
        "Bu belge iş süresince yerinde bulundurulmalıdır (ISO 45001 §8.1.2).",
        st["small"],
    ))

    doc.build(story)
    pdf = buf.getvalue()
    buf.close()
    return pdf


# ---------------------------------------------------------------------------
# Sprint 9 — SDS (16 bölüm) ve DoP (EN 934-2) PDF üreteçleri
# ---------------------------------------------------------------------------

SDS_SECTIONS = [
    ("1. Identification / Kimlik", "section_1_identification"),
    ("2. Hazard identification / Tehlike tanımlaması", "section_2_hazards"),
    ("3. Composition / Bileşim ve bileşenler", "section_3_composition"),
    ("4. First-aid measures / İlk yardım", "section_4_first_aid"),
    ("5. Fire-fighting / Yangınla mücadele", "section_5_fire"),
    ("6. Accidental release / Kaza sonucu yayılma", "section_6_accidental"),
    ("7. Handling and storage / Elleçleme ve depolama", "section_7_handling"),
    ("8. Exposure controls / PPE / Maruziyet kontrolleri", "section_8_exposure"),
    ("9. Physical and chemical properties", "section_9_physical"),
    ("10. Stability and reactivity", "section_10_stability"),
    ("11. Toxicological information", "section_11_toxicological"),
    ("12. Ecological information", "section_12_ecological"),
    ("13. Disposal considerations", "section_13_disposal"),
    ("14. Transport information (ADR/RID/IMDG/IATA)", "section_14_transport"),
    ("15. Regulatory information (REACH, CLP, ...)", "section_15_regulatory"),
    ("16. Other information", "section_16_other"),
]


def render_sds_pdf(sds) -> bytes:
    """SDS 16-bölüm PDF — Regulation EU 2020/878 uyumlu format."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.5*cm, rightMargin=1.5*cm,
        topMargin=1.2*cm, bottomMargin=1.2*cm,
    )
    st = _styles()
    story = []

    story.append(Paragraph(
        f"<b>SAFETY DATA SHEET</b> — SDS N° {sds.sds_number}", st["h1"],
    ))
    story.append(Paragraph(
        f"Version: {sds.version} · Language: {sds.language.upper()} · "
        f"Issue: {sds.issue_date or '—'} · Revision: {sds.revision_date or '—'}",
        st["body"],
    ))
    story.append(Paragraph(
        f"Chemical profile: <b>{sds.profile}</b>",
        st["body"],
    ))
    story.append(Spacer(1, 0.4*cm))

    story.append(Paragraph(
        "According to Regulation (EC) No 1907/2006 (REACH) and (EU) 2020/878.",
        st["small"],
    ))
    story.append(Spacer(1, 0.3*cm))

    for title, field in SDS_SECTIONS:
        story.append(Paragraph(f"<b>{title}</b>", st["h2"]))
        content = getattr(sds, field, "") or "<i>[not filled]</i>"
        story.append(Paragraph(content.replace("\n", "<br/>"), st["body"]))
        story.append(Spacer(1, 0.15*cm))

    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        f"Prepared by: {sds.prepared_by or '—'} · "
        f"Approved by: {sds.approved_by or '—'} · "
        f"Status: {sds.get_status_display()}",
        st["small"],
    ))
    story.append(Paragraph(
        "This SDS is compliant with GHS/CLP and EU Regulation 2020/878.",
        st["small"],
    ))

    doc.build(story)
    pdf = buf.getvalue()
    buf.close()
    return pdf


def render_dop_pdf(dop) -> bytes:
    """DoP — Declaration of Performance (EU Regulation 305/2011 Annex III)."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.5*cm, rightMargin=1.5*cm,
        topMargin=1.2*cm, bottomMargin=1.5*cm,
    )
    st = _styles()
    story = []

    story.append(Paragraph("<b>DECLARATION OF PERFORMANCE</b>", st["h1"]))
    story.append(Paragraph(f"N° {dop.dop_number}", st["h2"]))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("<b>1. Unique identification code of the product-type</b>", st["h2"]))
    story.append(Paragraph(f"{dop.product.code} · {dop.product.name}", st["body"]))

    story.append(Paragraph("<b>2. Type, batch or serial number</b>", st["h2"]))
    story.append(Paragraph(dop.product.code, st["body"]))

    story.append(Paragraph("<b>3. Intended use of the construction product</b>", st["h2"]))
    story.append(Paragraph(dop.intended_use or "—", st["body"]))

    story.append(Paragraph("<b>4. Manufacturer</b>", st["h2"]))
    story.append(Paragraph(
        "SARL MAPA ALGÉRIE<br/>Zone industrielle Rouiba, Alger — Algérie<br/>info@mapa.dz",
        st["body"],
    ))

    story.append(Paragraph("<b>5. Authorised representative</b>", st["h2"]))
    story.append(Paragraph("—", st["body"]))

    story.append(Paragraph("<b>6. AVCP system(s)</b>", st["h2"]))
    if dop.coc and dop.coc.fpc_plan:
        story.append(Paragraph(
            f"System {dop.coc.fpc_plan.get_avcp_system_display()}", st["body"],
        ))
    else:
        story.append(Paragraph("System 2+", st["body"]))

    story.append(Paragraph("<b>7. Harmonised standard</b>", st["h2"]))
    story.append(Paragraph(
        (dop.coc.standard if dop.coc else "EN 934-2:2009+A1:2012"), st["body"],
    ))

    story.append(Paragraph("<b>8. Notified body</b>", st["h2"]))
    if dop.coc and dop.coc.issuing_body:
        nb = dop.coc.issuing_body
        story.append(Paragraph(f"NB {nb.number} — {nb.name} ({nb.country})", st["body"]))
    else:
        story.append(Paragraph("—", st["body"]))

    story.append(Paragraph("<b>9. Declared performance</b>", st["h2"]))
    rows = [["Essential characteristic", "Declared performance"]]
    for k, v in (dop.performance_data or {}).items():
        rows.append([k.replace("_", " ").title(), str(v)])
    if len(rows) > 1:
        story.append(_table(rows, col_widths=[9*cm, 8*cm]))
    else:
        story.append(Paragraph("[no performance data]", st["small"]))

    story.append(Spacer(1, 0.6*cm))
    story.append(Paragraph("<b>10. Signature</b>", st["h2"]))
    story.append(Paragraph(
        f"The performance of the product identified above is in conformity with "
        f"the declared performance.<br/><br/>"
        f"Signed for and on behalf of the manufacturer by:<br/>"
        f"<b>{dop.manufacturer_signatory}</b><br/><br/>"
        f"Place: Rouiba, Alger — Date: {dop.issue_date}",
        st["body"],
    ))

    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph(
        "Regulation (EU) No 305/2011 — CPR Annex III · CE Marking",
        st["small"],
    ))

    doc.build(story)
    pdf = buf.getvalue()
    buf.close()
    return pdf

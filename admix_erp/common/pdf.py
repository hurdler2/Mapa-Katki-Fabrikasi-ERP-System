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

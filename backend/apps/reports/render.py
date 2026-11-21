"""Render Document ke Excel (openpyxl) atau PDF (reportlab)."""

from io import BytesIO
from xml.sax.saxutils import escape
from pathlib import Path

from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .documents import Document

PRIMARY = "0F766E"
STATUS_FILL = {"✓": "DCF3E3", "✕": "FBE1E1", "…": "FBEED8"}
MONEY = "#,##0"

# ---------- Excel ----------

def to_xlsx(doc: Document) -> bytes:
    wb = Workbook()
    wb.remove(wb.active)
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor=PRIMARY)
    for section in doc.sections:
        ws = wb.create_sheet(section.title[:31])
        ws["A1"] = doc.title
        ws["A1"].font = Font(bold=True, size=14)
        ws["A2"] = doc.subtitle
        ws["A2"].font = Font(color="5D6B67")
        start = 4
        if section.note:
            ws["A3"] = section.note
            ws["A3"].font = Font(italic=True, color="B45309")
        for c, h in enumerate(section.headers, start=1):
            cell = ws.cell(row=start, column=c, value=h)
            cell.font, cell.fill = header_font, header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        body = section.rows + ([section.footer] if section.footer else [])
        for r, row in enumerate(body, start=start + 1):
            for c, value in enumerate(row):
                cell = ws.cell(row=r, column=c + 1, value=value)
                if c in section.money_cols or (isinstance(value, int) and value >= 1000):
                    cell.number_format = MONEY
                if c in section.center_cols:
                    cell.alignment = Alignment(horizontal="center")
                if value in STATUS_FILL:
                    cell.fill = PatternFill("solid", fgColor=STATUS_FILL[value])
                if section.footer and r == start + len(body):
                    cell.font = Font(bold=True)
        for c, h in enumerate(section.headers):
            longest = max([len(str(h))] + [len(f"{row[c]:,}" if isinstance(row[c], int) else str(row[c])) for row in body if c < len(row)])
            ws.column_dimensions[get_column_letter(c + 1)].width = min(max(longest + 2, 5), 45)
        ws.freeze_panes = ws.cell(row=start + 1, column=1)
        ws.auto_filter.ref = f"A{start}:{get_column_letter(len(section.headers))}{start + len(section.rows)}"
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ---------- PDF ----------

FONT, FONT_BOLD = "Helvetica", "Helvetica-Bold"
_dejavu = Path("/usr/share/fonts/truetype/dejavu")
if (_dejavu / "DejaVuSans.ttf").exists():  # mendukung simbol ✓ ✕ …
    pdfmetrics.registerFont(TTFont("DejaVu", str(_dejavu / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(_dejavu / "DejaVuSans-Bold.ttf")))
    FONT, FONT_BOLD = "DejaVu", "DejaVu-Bold"


def _money(v) -> str:
    return f"{v:,}".replace(",", ".") if isinstance(v, int) else str(v)


def to_pdf(doc: Document) -> bytes:
    buf = BytesIO()
    pagesize = landscape(A4) if doc.landscape else A4
    margin = 12 * mm
    pdf = SimpleDocTemplate(
        buf, pagesize=pagesize, leftMargin=margin, rightMargin=margin, topMargin=margin, bottomMargin=margin + 4 * mm,
        title=doc.title, author="Aplikasi RT",
    )
    avail = pagesize[0] - 2 * margin
    title_style = ParagraphStyle("t", fontName=FONT_BOLD, fontSize=15, leading=19, spaceAfter=2)
    sub_style = ParagraphStyle("s", fontName=FONT, fontSize=9, textColor=colors.HexColor("#5D6B67"), spaceAfter=8)
    h_style = ParagraphStyle("h", fontName=FONT_BOLD, fontSize=11, spaceBefore=6, spaceAfter=4)
    note_style = ParagraphStyle("n", fontName=FONT, fontSize=8, textColor=colors.HexColor("#B45309"), spaceAfter=4)
    cell_style = ParagraphStyle("c", fontName=FONT, fontSize=7.5, leading=9)
    head_style = ParagraphStyle("hc", parent=cell_style, fontName=FONT_BOLD, textColor=colors.white)

    story = [Paragraph(escape(doc.title), title_style), Paragraph(escape(doc.subtitle), sub_style)]
    for section in doc.sections:
        story.append(Paragraph(escape(section.title), h_style))
        if section.note:
            story.append(Paragraph(escape(section.note), note_style))
        if not section.rows:
            story.append(Paragraph("Belum ada data.", cell_style))
            continue
        total_w = sum(section.widths)
        col_widths = [avail * w / total_w for w in section.widths]
        body = section.rows + ([section.footer] if section.footer else [])
        data = [[Paragraph(escape(h), head_style) for h in section.headers]]
        for row in body:
            data.append([
                _money(v) if (c in section.money_cols or isinstance(v, int)) else (v if c in section.center_cols else Paragraph(escape(str(v)), cell_style))
                for c, v in enumerate(row)
            ])
        style = [
            ("FONTNAME", (0, 0), (-1, -1), FONT),
            ("FONTSIZE", (0, 1), (-1, -1), 7.5),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#" + PRIMARY)),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#DDE4E2")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F6F5")]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]
        for c in section.money_cols:
            style.append(("ALIGN", (c, 1), (c, -1), "RIGHT"))
        for c in section.center_cols:
            style.append(("ALIGN", (c, 1), (c, -1), "CENTER"))
        for r, row in enumerate(section.rows, start=1):
            for c, v in enumerate(row):
                if v in STATUS_FILL:
                    style.append(("BACKGROUND", (c, r), (c, r), colors.HexColor("#" + STATUS_FILL[v])))
        if section.footer:
            style += [("FONTNAME", (0, -1), (-1, -1), FONT_BOLD), ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#D7EFEC"))]
        table = Table(data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle(style))
        story += [table, Spacer(1, 8)]

    printed = timezone.localtime().strftime("%d-%m-%Y %H:%M")

    def footer(canvas, _doc):
        canvas.saveState()
        canvas.setFont(FONT, 7)
        canvas.setFillColor(colors.HexColor("#5D6B67"))
        canvas.drawString(margin, 8 * mm, f"Aplikasi RT · {doc.title} · dicetak {printed} WIB")
        canvas.drawRightString(pagesize[0] - margin, 8 * mm, f"Halaman {_doc.page}")
        canvas.restoreState()

    pdf.build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()

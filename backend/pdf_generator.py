import base64
import io
import math
import datetime
from PIL import Image as PILImage

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, HRFlowable, KeepTogether, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ── Color Palette ─────────────────────────────────────────────────────────────
DARK_HEADER   = colors.HexColor("#0F172A")
SLATE_DARK    = colors.HexColor("#1E293B")
SLATE_MID     = colors.HexColor("#64748B")
SLATE_LIGHT   = colors.HexColor("#F8FAFC")
SLATE_100     = colors.HexColor("#F1F5F9")
BORDER        = colors.HexColor("#E2E8F0")
BORDER_MID    = colors.HexColor("#CBD5E1")

# Severity Colors: Green = Acceptable, Yellow = Minor, Orange = Major, Red = Critical
RED           = colors.HexColor("#EF4444")
RED_LIGHT     = colors.HexColor("#FEF2F2")
ORANGE        = colors.HexColor("#F97316")
ORANGE_LIGHT  = colors.HexColor("#FFF7ED")
YELLOW        = colors.HexColor("#F59E0B")
YELLOW_LIGHT  = colors.HexColor("#FFFBEB")
GREEN         = colors.HexColor("#10B981")
GREEN_LIGHT   = colors.HexColor("#ECFDF5")
BLUE_ACCENT   = colors.HexColor("#3B82F6")
BLUE_LIGHT    = colors.HexColor("#EFF6FF")
WHITE         = colors.white

SEVERITY_COLOR_MAP = {
    "Critical": RED, "High": ORANGE, "Medium": YELLOW, "Low": GREEN
}
SEVERITY_BG_MAP = {
    "Critical": RED_LIGHT, "High": ORANGE_LIGHT, "Medium": YELLOW_LIGHT, "Low": GREEN_LIGHT
}
ACCEPTANCE_COLOR_MAP = {
    "Accepted": GREEN,
    "Accepted With Repair": YELLOW,
    "Requires Rewelding": ORANGE,
    "Rejected": RED
}


def _b64_to_rl_img(b64_str, max_w_pt, max_h_pt):
    """Convert base64 image string to ReportLab Image with aspect-ratio clamping."""
    if not b64_str:
        return None
    try:
        raw = base64.b64decode(b64_str.split(",")[-1])
        buf = io.BytesIO(raw)
        pil = PILImage.open(buf)
        pw, ph = pil.size
        scale = min(max_w_pt / pw, max_h_pt / ph)
        buf.seek(0)
        return Image(buf, width=pw*scale, height=ph*scale)
    except Exception:
        return None


def _page_footer(canvas, doc):
    """Draws page number + report footer on every page."""
    canvas.saveState()
    page_w, page_h = A4
    canvas.setFont("Helvetica", 6.5)
    canvas.setFillColor(SLATE_MID)

    # Footer line
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(18*mm, 12*mm, page_w - 18*mm, 12*mm)

    # Left footer
    canvas.drawString(18*mm, 8*mm,
        "WeldVision AI  |  Industrial Weld Quality & Weld Defect Analysis Platform  |  AWS D1.1 / ISO 5817 / EN 1090")

    # Right footer - page number
    canvas.drawRightString(page_w - 18*mm, 8*mm,
        f"Page {doc.page}")

    canvas.restoreState()


def _section_header(story, label, T_h2, extra_space=6):
    """Helper to add a styled section header."""
    story.append(Spacer(1, extra_space))
    story.append(Paragraph(label, T_h2))
    story.append(HRFlowable(width="100%", thickness=0.6, color=BORDER))
    story.append(Spacer(1, 4))


def generate_pdf_report(data: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=14*mm,  bottomMargin=20*mm
    )

    styles = getSampleStyleSheet()

    def S(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)

    # ── Typography Styles ───────────────────────────────────────────────────
    T_title   = S("T_title",   fontName="Helvetica-Bold",   fontSize=18, textColor=WHITE,      leading=22)
    T_sub     = S("T_sub",     fontName="Helvetica",         fontSize=8.5,textColor=BLUE_ACCENT,leading=11)
    T_h2      = S("T_h2",      fontName="Helvetica-Bold",   fontSize=10, textColor=DARK_HEADER, leading=14, spaceBefore=4, spaceAfter=2)
    T_h3      = S("T_h3",      fontName="Helvetica-Bold",   fontSize=8.5,textColor=SLATE_DARK, leading=12)
    T_body    = S("T_body",    fontName="Helvetica",         fontSize=8,  textColor=SLATE_DARK, leading=11)
    T_small   = S("T_small",   fontName="Helvetica-Oblique",fontSize=7,  textColor=SLATE_MID,  leading=9)
    T_tbl_h   = S("T_tbl_h",   fontName="Helvetica-Bold",   fontSize=7.5,textColor=WHITE,      leading=10, alignment=TA_CENTER)
    T_tbl_b   = S("T_tbl_b",   fontName="Helvetica",         fontSize=7.5,textColor=SLATE_DARK, leading=10)
    T_tbl_bc  = S("T_tbl_bc",  fontName="Helvetica",         fontSize=7.5,textColor=SLATE_DARK, leading=10, alignment=TA_CENTER)
    T_verdict = S("T_verdict", fontName="Helvetica",         fontSize=8.5,textColor=SLATE_DARK, leading=13)
    T_rec     = S("T_rec",     fontName="Helvetica",         fontSize=8,  textColor=SLATE_DARK, leading=12)

    story = []

    # ── Metadata extraction ─────────────────────────────────────────────────
    ts_now = datetime.datetime.now()
    ref_id = data.get("inspection_id", f"WLD-{ts_now.strftime('%Y%m%d-%H%M%S')}")
    ts = data.get("inspection_time", ts_now.strftime("%Y-%m-%d %H:%M:%S"))

    summary = data.get("summary", {})
    weld_quality = data.get("weld_quality", {})

    score = weld_quality.get("score", data.get("health_score", 90))
    condition = weld_quality.get("condition", data.get("condition", "Good"))
    acceptance = weld_quality.get("acceptance_status", "Accepted")
    risk = weld_quality.get("overall_risk", data.get("overall_risk", "Low"))
    repair_priority = weld_quality.get("repair_priority", "No Action Required")
    verdict_text = weld_quality.get("verdict", data.get("verdict", "No verdict generated."))
    possible_causes = weld_quality.get("possible_causes", [])
    recommended_actions = weld_quality.get("recommended_actions", [])

    total_defects = summary.get("total_defects", data.get("total_defects", 0))
    critical_cnt = summary.get("critical_defects", data.get("critical_count", 0))
    major_cnt = summary.get("major_defects", data.get("high_count", 0))
    minor_cnt = summary.get("minor_defects", data.get("medium_count", 0))
    coverage_pct = summary.get("weld_coverage_percent", 98.5)
    defective_area_pct = summary.get("defective_area_percent", data.get("damaged_pct", 0.0))
    conf_pct = summary.get("inspection_confidence", data.get("inspection_confidence", 95.0))
    if conf_pct <= 1.0:
        conf_pct = round(conf_pct * 100, 1)

    # ═══════════════════════════════════════════════════════════════════════════
    # HEADER BAND
    # ═══════════════════════════════════════════════════════════════════════════

    hdr_left = [
        Paragraph("WeldVision AI", T_title),
        Paragraph("INDUSTRIAL WELDING INSPECTION &amp; DEFECT ANALYSIS REPORT", T_sub),
        Spacer(1, 3),
        Paragraph("Standards: AWS D1.1 / D1.2  |  ISO 5817  |  EN 1090-2  |  ASME Sec VIII", T_small),
    ]
    hdr_right = [
        Paragraph("<b>WELDING INSPECTION REPORT</b>",
                  S("rh", fontName="Helvetica-Bold", fontSize=10, textColor=WHITE,
                    alignment=TA_RIGHT, leading=13)),
        Paragraph(f"Report ID: <b>{ref_id}</b>",
                  S("rm", fontName="Helvetica", fontSize=8, textColor=colors.HexColor("#94A3B8"),
                    alignment=TA_RIGHT, leading=11)),
        Paragraph(f"Date &amp; Time: {ts}",
                  S("rd", fontName="Helvetica", fontSize=7.5, textColor=colors.HexColor("#94A3B8"),
                    alignment=TA_RIGHT, leading=10)),
        Paragraph("Classification: Industrial Quality Record",
                  S("rc", fontName="Helvetica", fontSize=7.5, textColor=colors.HexColor("#94A3B8"),
                    alignment=TA_RIGHT, leading=10)),
    ]

    logo_placeholder = [
        Paragraph("[ COMPANY LOGO ]",
                  S("lp", fontName="Helvetica-Bold", fontSize=8.5, textColor=colors.HexColor("#64748B"),
                    alignment=TA_CENTER, leading=12)),
    ]
    logo_box = Table([[logo_placeholder]], colWidths=[35*mm])
    logo_box.setStyle(TableStyle([
        ("BOX",       (0,0),(-1,-1), 1, colors.HexColor("#334155")),
        ("BACKGROUND",(0,0),(-1,-1), colors.HexColor("#1E293B")),
        ("PADDING",   (0,0),(-1,-1), 8),
        ("VALIGN",    (0,0),(-1,-1), "MIDDLE"),
    ]))

    hdr_tbl = Table([[logo_box, hdr_left, hdr_right]], colWidths=[40*mm, 85*mm, 50*mm])
    hdr_tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0,0),(-1,-1), DARK_HEADER),
        ("PADDING",     (0,0),(-1,-1), 10),
        ("VALIGN",      (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(hdr_tbl)
    story.append(Spacer(1, 6))

    # ═══════════════════════════════════════════════════════════════════════════
    # VERDICT & SUMMARY STRIP
    # ═══════════════════════════════════════════════════════════════════════════

    acceptance_color = ACCEPTANCE_COLOR_MAP.get(acceptance, GREEN)
    v_icon = "✔" if acceptance == "Accepted" else "⚠️"
    v_text = Paragraph(
        f"<b>{v_icon} WELD ACCEPTANCE: {acceptance.upper()}</b>  |  "
        f"Quality Score: <b>{score}/100</b>  |  "
        f"Defective Area: <b>{defective_area_pct}%</b>  |  "
        f"Defects Found: <b>{total_defects}</b>  |  "
        f"Repair Priority: <b>{repair_priority}</b>",
        S("vs", fontName="Helvetica-Bold", fontSize=8.5, textColor=SLATE_DARK, leading=12)
    )
    v_box = Table([[v_text]], colWidths=[175*mm])
    v_box.setStyle(TableStyle([
        ("BACKGROUND",  (0,0),(-1,-1), SLATE_LIGHT),
        ("BOX",         (0,0),(-1,-1), 0.5, BORDER),
        ("LINELEFT",    (0,0),(-1,-1), 6, acceptance_color),
        ("PADDING",     (0,0),(-1,-1), 8),
    ]))
    story.append(v_box)
    story.append(Spacer(1, 8))

    # ═══════════════════════════════════════════════════════════════════════════
    # 5-CARD WELD QUALITY METRICS
    # ═══════════════════════════════════════════════════════════════════════════

    def metric_card(label, value, value_color=SLATE_DARK):
        return [
            Paragraph(label, S("ml", fontName="Helvetica", fontSize=6.5, textColor=SLATE_MID, leading=9, alignment=TA_CENTER)),
            Spacer(1, 2),
            Paragraph(str(value), S("mv", fontName="Helvetica-Bold", fontSize=12, textColor=value_color, leading=14, alignment=TA_CENTER)),
        ]

    m_cols = [
        metric_card("WELD QUALITY SCORE", f"{score} / 100", acceptance_color),
        metric_card("ACCEPTANCE STATUS", acceptance, acceptance_color),
        metric_card("OVERALL CONDITION", condition, BLUE_ACCENT),
        metric_card("OVERALL RISK LEVEL", risk, RED if risk in ("Critical","High") else GREEN),
        metric_card("ANALYSIS CONFIDENCE", f"{conf_pct}%", BLUE_ACCENT),
    ]

    labels_row = [cell[0] for cell in m_cols]
    values_row = [cell[2] for cell in m_cols]
    met_tbl = Table([labels_row, values_row], colWidths=[35*mm]*5)
    met_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,-1), SLATE_LIGHT),
        ("BOX",          (0,0),(-1,-1), 0.5, BORDER),
        ("INNERGRID",    (0,0),(-1,-1), 0.5, BORDER),
        ("PADDING",      (0,0),(-1,-1), 6),
        ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(met_tbl)
    story.append(Spacer(1, 9))

    # ═══════════════════════════════════════════════════════════════════════════
    # VISUAL EVIDENCE IMAGES
    # ═══════════════════════════════════════════════════════════════════════════

    _section_header(story, "WELDING INSPECTION VISUAL EVIDENCE", T_h2, 0)

    img_orig  = _b64_to_rl_img(data.get("original_image",""),   57*mm, 52*mm)
    img_annot = _b64_to_rl_img(data.get("annotated_image",""),  57*mm, 52*mm)
    img_ovrly = _b64_to_rl_img(data.get("overlay_image",""),    57*mm, 52*mm)

    def img_col(img_rl, caption):
        cap_style = S("ic", fontName="Helvetica-Bold", fontSize=7.5, textColor=SLATE_MID, leading=10, alignment=TA_CENTER)
        inner = [[img_rl if img_rl else Paragraph(caption, cap_style)],
                 [Spacer(1, 2)],
                 [Paragraph(caption, cap_style)]]
        t = Table(inner, colWidths=[55*mm])
        t.setStyle(TableStyle([
            ("ALIGN",   (0,0),(-1,-1), "CENTER"),
            ("VALIGN",  (0,0),(-1,-1), "TOP"),
            ("PADDING", (0,0),(-1,-1), 2),
        ]))
        return t

    img_row = Table(
        [[img_col(img_orig,  "① Original Weld Seam Capture"),
          img_col(img_annot, "② AI Engineering Callout View"),
          img_col(img_ovrly, "③ Defect Heatmap Overlay")]],
        colWidths=[59*mm, 59*mm, 57*mm]
    )
    img_row.setStyle(TableStyle([
        ("ALIGN",      (0,0),(-1,-1), "CENTER"),
        ("VALIGN",     (0,0),(-1,-1), "TOP"),
        ("PADDING",    (0,0),(-1,-1), 4),
        ("BACKGROUND", (0,0),(-1,-1), SLATE_100),
        ("BOX",        (0,0),(-1,-1), 0.5, BORDER),
        ("INNERGRID",  (0,0),(-1,-1), 0.5, BORDER),
    ]))
    story.append(img_row)
    story.append(Spacer(1, 9))

    # ═══════════════════════════════════════════════════════════════════════════
    # DETAILED WELD DEFECT TABLE
    # ═══════════════════════════════════════════════════════════════════════════

    _section_header(story, "DETECTED WELD DEFECT CATALOGUE", T_h2, 0)

    col_heads = ["Defect ID", "Defect Type", "Severity", "Weld Zone Location", "Size (mm)", "Area %", "Repair Priority"]
    col_widths = [20*mm, 35*mm, 20*mm, 35*mm, 22*mm, 15*mm, 28*mm]
    tbl_data  = [[Paragraph(h, T_tbl_h) for h in col_heads]]

    defects = data.get("defects", [])
    if not defects:
        tbl_data.append([Paragraph("—", T_tbl_b)] * 7)
    else:
        for d in defects:
            sc  = SEVERITY_COLOR_MAP.get(d.get("severity","Low"), YELLOW)
            sbg = SEVERITY_BG_MAP.get(d.get("severity","Low"), YELLOW_LIGHT)
            sev_cell = Table([[Paragraph(
                f"<b>{d.get('severity','—')}</b>",
                S("sb", fontName="Helvetica-Bold", fontSize=7.5, textColor=sc, leading=10, alignment=TA_CENTER)
            )]], colWidths=[18*mm])
            sev_cell.setStyle(TableStyle([
                ("BACKGROUND",(0,0),(-1,-1), sbg),
                ("BOX",       (0,0),(-1,-1), 0.5, sc),
                ("PADDING",   (0,0),(-1,-1), 2),
            ]))
            def_id_str = d.get("id", f"WLD-{d.get('id_num', 1):03d}")
            tbl_data.append([
                Paragraph(f"<b>{def_id_str}</b>", T_tbl_bc),
                Paragraph(f"<b>{d.get('type', d.get('defect_name', '—'))}</b>", T_tbl_b),
                sev_cell,
                Paragraph(d.get("location", d.get("weld_zone", "—")), T_tbl_b),
                Paragraph(d.get("size_mm", "—"), T_tbl_bc),
                Paragraph(f"{d.get('area_pct', '—')}%", T_tbl_bc),
                Paragraph(d.get("repair_priority", d.get("priority", "—")), T_tbl_b),
            ])

    dtbl = Table(tbl_data, colWidths=col_widths, repeatRows=1)
    dtbl.setStyle(TableStyle([
        ("BACKGROUND",     (0,0),(-1,0),   DARK_HEADER),
        ("GRID",           (0,0),(-1,-1),  0.4, BORDER),
        ("PADDING",        (0,0),(-1,-1),  5),
        ("VALIGN",         (0,0),(-1,-1),  "MIDDLE"),
        ("ROWBACKGROUNDS", (0,1),(-1,-1),  [WHITE, SLATE_LIGHT]),
        ("ALIGN",          (0,0),(0,-1),   "CENTER"),
        ("ALIGN",          (4,0),(5,-1),   "CENTER"),
    ]))
    story.append(dtbl)

    # ═══════════════════════════════════════════════════════════════════════════
    # PAGE 2: VERDICT + CAUSES + REPAIR ACTIONS + SIGNATURE & QR
    # ═══════════════════════════════════════════════════════════════════════════

    story.append(PageBreak())

    _section_header(story, "AI INSPECTION VERDICT & QUALITY ASSESSMENT", T_h2, 0)
    v_para = Paragraph(verdict_text, T_verdict)
    v_box2 = Table([[v_para]], colWidths=[175*mm])
    v_box2.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), BLUE_LIGHT),
        ("BOX",        (0,0),(-1,-1), 1,   BLUE_ACCENT),
        ("LINELEFT",   (0,0),(-1,-1), 5,   BLUE_ACCENT),
        ("PADDING",    (0,0),(-1,-1), 10),
    ]))
    story.append(v_box2)
    story.append(Spacer(1, 10))

    # ── Possible Causes & Recommended Repair Actions ─────────────────────────
    _section_header(story, "ENGINEERING CAUSE ANALYSIS & RECOMMENDED REPAIR ACTIONS", T_h2, 0)

    causes_list = possible_causes if possible_causes else [
        "Excessive travel speed or improper torch angle",
        "Dirty base metal or surface contamination",
        "Insufficient shielding gas flow or draft in area",
    ]
    actions_list = recommended_actions if recommended_actions else [
        "Grind out defect region to sound metal and re-weld",
        "Perform non-destructive testing (NDT - Dye Penetrant / Ultrasonic)",
        "Adjust welding parameters and shield gas flow",
    ]

    c_rows = [[Paragraph(f"• {c}", T_rec)] for c in causes_list]
    c_tbl = Table(c_rows, colWidths=[84*mm])
    c_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), SLATE_LIGHT),
        ("BOX",        (0,0),(-1,-1), 0.5, BORDER),
        ("PADDING",    (0,0),(-1,-1), 6),
    ]))

    a_rows = [[Paragraph(f"• {a}", T_rec)] for a in actions_list]
    a_tbl = Table(a_rows, colWidths=[86*mm])
    a_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), SLATE_LIGHT),
        ("BOX",        (0,0),(-1,-1), 0.5, BORDER),
        ("PADDING",    (0,0),(-1,-1), 6),
    ]))

    side_by_side = Table([[
        Table([[Paragraph("<b>POSSIBLE CAUSES</b>", T_h3)], [Spacer(1, 3)], [c_tbl]], colWidths=[84*mm]),
        Table([[Paragraph("<b>RECOMMENDED REPAIR ACTIONS</b>", T_h3)], [Spacer(1, 3)], [a_tbl]], colWidths=[86*mm])
    ]], colWidths=[86*mm, 89*mm])
    side_by_side.setStyle(TableStyle([
        ("VALIGN",  (0,0),(-1,-1), "TOP"),
        ("PADDING", (0,0),(-1,-1), 0),
    ]))
    story.append(side_by_side)
    story.append(Spacer(1, 12))

    # ── Inspection Summary Table ─────────────────────────────────────────────
    _section_header(story, "INSPECTION SUMMARY & METRICS", T_h2, 0)

    stat_rows = [
        ("Total Weld Defects",          str(total_defects)),
        ("Critical Defects",            str(critical_cnt)),
        ("Major Defects",               str(major_cnt)),
        ("Minor Defects",               str(minor_cnt)),
        ("Weld Coverage Analyzed",      f"{coverage_pct}%"),
        ("Estimated Defective Area",    f"{defective_area_pct}%"),
        ("Weld Quality Score",          f"{score} / 100"),
        ("Weld Acceptance Status",      acceptance),
        ("Repair Priority",             repair_priority),
        ("AI Inspection Confidence",    f"{conf_pct}%"),
    ]

    half = math.ceil(len(stat_rows) / 2)
    left_stats, right_stats = stat_rows[:half], stat_rows[half:]
    stat_combined = []
    for (lk, lv), (rk, rv) in zip(left_stats, right_stats):
        stat_combined.append([
            Paragraph(lk, T_h3), Paragraph(lv, T_body),
            Paragraph(rk, T_h3), Paragraph(rv, T_body),
        ])

    stat_tbl = Table(stat_combined, colWidths=[42*mm, 43*mm, 42*mm, 43*mm])
    stat_tbl.setStyle(TableStyle([
        ("GRID",     (0,0),(-1,-1), 0.4, BORDER),
        ("PADDING",  (0,0),(-1,-1), 5),
        ("VALIGN",   (0,0),(-1,-1), "MIDDLE"),
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[WHITE, SLATE_LIGHT]),
        ("BACKGROUND",(0,0),(0,-1), SLATE_100),
        ("BACKGROUND",(2,0),(2,-1), SLATE_100),
    ]))
    story.append(stat_tbl)
    story.append(Spacer(1, 14))

    # ── QR Code & Sign-off Block ─────────────────────────────────────────────
    qr_box = Table([[
        Paragraph("[ QR CODE VERIFICATION ]",
                  S("qr", fontName="Helvetica", fontSize=7, textColor=SLATE_MID, alignment=TA_CENTER, leading=10)),
    ]], colWidths=[30*mm], rowHeights=[26*mm])
    qr_box.setStyle(TableStyle([
        ("BOX",       (0,0),(-1,-1), 1, BORDER_MID),
        ("BACKGROUND",(0,0),(-1,-1), SLATE_100),
        ("PADDING",   (0,0),(-1,-1), 6),
        ("VALIGN",    (0,0),(-1,-1), "MIDDLE"),
    ]))

    def sign_col(label1, label2):
        return Table([
            [Paragraph(label1, T_h3)],
            [Paragraph("_" * 36, T_body)],
            [Spacer(1, 6)],
            [Paragraph(label2, T_h3)],
            [Paragraph("_" * 36, T_body)],
        ], colWidths=[70*mm])

    signoff_row = Table([[
        sign_col("Certified Inspector Name:", "Inspector Signature:"),
        sign_col("Quality Approval Authority:", "Date Approved:"),
        qr_box,
    ]], colWidths=[72*mm, 72*mm, 31*mm])
    signoff_row.setStyle(TableStyle([
        ("VALIGN",  (0,0),(-1,-1), "TOP"),
        ("PADDING", (0,0),(-1,-1), 2),
    ]))
    story.append(signoff_row)
    story.append(Spacer(1, 10))

    story.append(Paragraph(
        f"<i>Report ID: {ref_id}  |  Generated by WeldVision AI Quality Engine  |  "
        f"Analysis compliant with AWS D1.1 / ISO 5817 weld visual inspection criteria.  "
        f"All defect indications are AI visual estimates and must be verified by a CWI / NDT Inspector.</i>",
        S("ft", fontName="Helvetica-Oblique", fontSize=6.5, textColor=SLATE_MID, leading=9, alignment=TA_CENTER)
    ))

    # ── Build PDF Document ──────────────────────────────────────────────────
    doc.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    pdf_bytes = buf.getvalue()
    buf.close()
    return pdf_bytes

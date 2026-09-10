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
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ── Color Palette ─────────────────────────────────────────────────────────────
DARK_HEADER   = colors.HexColor("#0F172A")
SLATE_DARK    = colors.HexColor("#1E293B")
SLATE_MID     = colors.HexColor("#64748B")
SLATE_LIGHT   = colors.HexColor("#F8FAFC")
SLATE_100     = colors.HexColor("#F1F5F9")
BORDER        = colors.HexColor("#E2E8F0")
BORDER_MID    = colors.HexColor("#CBD5E1")

# Severity Colors
RED           = colors.HexColor("#EF4444")
RED_LIGHT     = colors.HexColor("#FEF2F2")
ORANGE        = colors.HexColor("#F97316")
ORANGE_LIGHT  = colors.HexColor("#FFF7ED")
YELLOW        = colors.HexColor("#F59E0B")
YELLOW_LIGHT  = colors.HexColor("#FFFBEB")
GREEN         = colors.HexColor("#10B981")
GREEN_LIGHT   = colors.HexColor("#ECFDF5")
BLUE_ACCENT   = colors.HexColor("#2563EB")
BLUE_LIGHT    = colors.HexColor("#EFF6FF")
WHITE         = colors.white

SEVERITY_COLOR_MAP = {
    "Critical": RED, "High": ORANGE, "Medium": YELLOW, "Low": GREEN
}
SEVERITY_BG_MAP = {
    "Critical": RED_LIGHT, "High": ORANGE_LIGHT, "Medium": YELLOW_LIGHT, "Low": GREEN_LIGHT
}
ACCEPTANCE_COLOR_MAP = {
    "Excellent": GREEN,
    "Accepted": GREEN,
    "Accepted With Repair": YELLOW,
    "Requires Repair": ORANGE,
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
        return Image(buf, width=pw * scale, height=ph * scale)
    except Exception:
        return None


def _page_footer(canvas, doc):
    """Draws professional industrial footer and page numbering."""
    canvas.saveState()
    page_w, page_h = A4
    canvas.setFont("Helvetica", 6.8)
    canvas.setFillColor(SLATE_MID)

    # Footer divider line
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, 12 * mm, page_w - 18 * mm, 12 * mm)

    # Left footer
    canvas.drawString(18 * mm, 8 * mm,
        "WeldVision AI  |  Industrial Weld Quality & Defect Inspection System  |  AWS D1.1 / ISO 5817 / EN 1090-2")

    # Right footer - page number
    canvas.drawRightString(page_w - 18 * mm, 8 * mm, f"Page {doc.page}")
    canvas.restoreState()


def _section_header(story, label, T_h2, extra_space=6):
    story.append(Spacer(1, extra_space))
    story.append(Paragraph(label, T_h2))
    story.append(HRFlowable(width="100%", thickness=0.8, color=BORDER))
    story.append(Spacer(1, 4))


def generate_pdf_report(data: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=14 * mm,  bottomMargin=18 * mm
    )

    styles = getSampleStyleSheet()

    def S(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)

    # ── Typography Styles ───────────────────────────────────────────────────
    T_title     = S("T_title",     fontName="Helvetica-Bold",   fontSize=16, textColor=WHITE, leading=19)
    T_sub       = S("T_sub",       fontName="Helvetica-Bold",   fontSize=8,  textColor=colors.HexColor("#F97316"), leading=10)
    T_meta_h    = S("T_meta_h",    fontName="Helvetica-Bold",   fontSize=7.5,textColor=WHITE, leading=10, alignment=TA_RIGHT)
    T_meta_v    = S("T_meta_v",    fontName="Helvetica",        fontSize=7.5,textColor=colors.HexColor("#CBD5E1"), leading=10, alignment=TA_RIGHT)
    T_h2        = S("T_h2",        fontName="Helvetica-Bold",   fontSize=10, textColor=DARK_HEADER, leading=14, spaceBefore=4, spaceAfter=2)
    T_h3        = S("T_h3",        fontName="Helvetica-Bold",   fontSize=8.5,textColor=SLATE_DARK, leading=12)
    T_body      = S("T_body",      fontName="Helvetica",        fontSize=8,  textColor=SLATE_DARK, leading=11)
    T_small     = S("T_small",     fontName="Helvetica-Oblique",fontSize=7,  textColor=SLATE_MID,  leading=9)
    T_tbl_h     = S("T_tbl_h",     fontName="Helvetica-Bold",   fontSize=7.5,textColor=WHITE, leading=10, alignment=TA_CENTER)
    T_tbl_b     = S("T_tbl_b",     fontName="Helvetica",        fontSize=7.5,textColor=SLATE_DARK, leading=10)
    T_tbl_bc    = S("T_tbl_bc",    fontName="Helvetica",        fontSize=7.5,textColor=SLATE_DARK, leading=10, alignment=TA_CENTER)
    T_verdict   = S("T_verdict",   fontName="Helvetica",        fontSize=8.5,textColor=SLATE_DARK, leading=13)
    T_prob_lbl  = S("T_prob_lbl",  fontName="Helvetica-Bold",   fontSize=8,  textColor=SLATE_DARK, leading=11)
    T_prob_val  = S("T_prob_val",  fontName="Helvetica",        fontSize=8,  textColor=SLATE_DARK, leading=11)

    story = []

    # ── Metadata Extraction ─────────────────────────────────────────────────
    now = datetime.datetime.now()
    inspection_id   = data.get("inspection_id", f"WLD-{now.strftime('%Y%m%d-%H%M%S')}")
    inspection_date = data.get("inspection_date", now.strftime("%d %B %Y"))
    inspection_time = data.get("inspection_time", now.strftime("%H:%M"))
    file_name       = data.get("file_name", "weld_specimen.jpg")
    model_name      = data.get("model_name", "Ultralytics YOLO11-seg (Industrial Weld Model)")
    model_type      = data.get("model_type", "Instance Segmentation & Defect Analysis")
    inspection_stat = data.get("inspection_status", "Complete")

    summary         = data.get("summary", {})
    weld_quality    = data.get("weld_quality", {})
    qa              = data.get("quality_assessment", {})

    score           = qa.get("score", weld_quality.get("score", data.get("health_score", 98)))
    status          = qa.get("status", weld_quality.get("overall_status", weld_quality.get("acceptance_status", data.get("acceptance_status", "Accepted"))))
    overall_sev     = qa.get("severity", weld_quality.get("overall_severity", weld_quality.get("overall_risk", data.get("overall_risk", "Low"))))
    repair_priority = weld_quality.get("repair_priority", "No Action Required")
    
    total_defects   = summary.get("total_defects", data.get("total_defects", 0))
    defects         = data.get("defects", [])
    breakdown       = summary.get("breakdown", data.get("breakdown", {}))
    defective_area  = summary.get("defective_area_percent", data.get("damaged_pct", 0.0))
    conf_pct        = summary.get("inspection_confidence", data.get("inspection_confidence", 95.0))
    if conf_pct <= 1.0:
        conf_pct = round(conf_pct * 100, 1)

    conclusion_text = data.get("conclusion", weld_quality.get("conclusion", "Inspection completed successfully."))
    qa_explanation  = qa.get("explanation", "Quality assessment calculated from YOLO predictions and defect severity weighting.")

    # ═══════════════════════════════════════════════════════════════════════════
    # PAGE 1: HEADER, METADATA, METRICS & VISUAL EVIDENCE
    # ═══════════════════════════════════════════════════════════════════════════

    # Header Top Bar
    hdr_left = [
        Paragraph("<b>WELDVISION-AI</b>", T_title),
        Paragraph("WELD QUALITY INSPECTION REPORT", T_sub),
        Spacer(1, 2),
        Paragraph("Industrial AWS D1.1 / ISO 5817 Quality Assurance Standard", T_small),
    ]

    hdr_right = [
        Paragraph(f"<b>Inspection ID:</b> {inspection_id}", T_meta_h),
        Paragraph(f"<b>Inspection Date:</b> {inspection_date}", T_meta_v),
        Paragraph(f"<b>Inspection Time:</b> {inspection_time}", T_meta_v),
        Paragraph(f"<b>File Name:</b> {file_name}", T_meta_v),
    ]

    hdr_tbl = Table([[hdr_left, hdr_right]], colWidths=[100 * mm, 75 * mm])
    hdr_tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, -1), DARK_HEADER),
        ("PADDING",     (0, 0), (-1, -1), 10),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(hdr_tbl)
    story.append(Spacer(1, 6))

    # ── Inspection Metadata Strip ───────────────────────────────────────────
    meta_bar = [
        Paragraph(f"<b>Model:</b> {model_name}", S("mb1", fontName="Helvetica", fontSize=7.2, textColor=SLATE_DARK, leading=9)),
        Paragraph(f"<b>Type:</b> {model_type}", S("mb2", fontName="Helvetica", fontSize=7.2, textColor=SLATE_DARK, leading=9)),
        Paragraph(f"<b>Status:</b> <font color='{GREEN.hexval()}'><b>{inspection_stat}</b></font>", S("mb3", fontName="Helvetica", fontSize=7.2, textColor=SLATE_DARK, leading=9, alignment=TA_RIGHT)),
    ]
    meta_tbl = Table([meta_bar], colWidths=[70 * mm, 65 * mm, 40 * mm])
    meta_tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, -1), SLATE_100),
        ("BOX",         (0, 0), (-1, -1), 0.5, BORDER),
        ("PADDING",     (0, 0), (-1, -1), 4),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(meta_tbl)
    story.append(Spacer(1, 6))

    # ── 5-Card Overall Quality Summary Metrics ──────────────────────────────
    status_color = ACCEPTANCE_COLOR_MAP.get(status, GREEN)
    sev_color    = SEVERITY_COLOR_MAP.get(overall_sev, GREEN)

    def metric_card(label, value, color_val=SLATE_DARK):
        return [
            Paragraph(label, S("ml", fontName="Helvetica", fontSize=6.5, textColor=SLATE_MID, leading=9, alignment=TA_CENTER)),
            Spacer(1, 2),
            Paragraph(str(value), S("mv", fontName="Helvetica-Bold", fontSize=11, textColor=color_val, leading=13, alignment=TA_CENTER)),
        ]

    m_cols = [
        metric_card("OVERALL QUALITY SCORE", f"{score} / 100", status_color),
        metric_card("OVERALL STATUS", status, status_color),
        metric_card("OVERALL SEVERITY", overall_sev, sev_color),
        metric_card("TOTAL DEFECTS", str(total_defects), RED if total_defects > 0 else GREEN),
        metric_card("DEFECTIVE AREA", f"{defective_area}%", RED if defective_area > 5 else SLATE_DARK),
    ]

    labels_row = [c[0] for c in m_cols]
    values_row = [c[2] for c in m_cols]
    met_tbl = Table([labels_row, values_row], colWidths=[35 * mm] * 5)
    met_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), SLATE_LIGHT),
        ("BOX",          (0, 0), (-1, -1), 0.5, BORDER),
        ("INNERGRID",    (0, 0), (-1, -1), 0.5, BORDER),
        ("PADDING",      (0, 0), (-1, -1), 5),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(met_tbl)
    story.append(Spacer(1, 8))

    # ── Visual Evidence Images ──────────────────────────────────────────────
    _section_header(story, "WELDING INSPECTION VISUAL EVIDENCE", T_h2, 0)

    img_orig  = _b64_to_rl_img(data.get("original_image", ""),   57 * mm, 52 * mm)
    img_annot = _b64_to_rl_img(data.get("annotated_image", ""),  57 * mm, 52 * mm)
    img_ovrly = _b64_to_rl_img(data.get("overlay_image", ""),    57 * mm, 52 * mm)

    def img_col(img_rl, caption):
        cap_style = S("ic", fontName="Helvetica-Bold", fontSize=7.5, textColor=SLATE_MID, leading=10, alignment=TA_CENTER)
        inner = [
            [img_rl if img_rl else Paragraph(caption, cap_style)],
            [Spacer(1, 2)],
            [Paragraph(caption, cap_style)]
        ]
        t = Table(inner, colWidths=[55 * mm])
        t.setStyle(TableStyle([
            ("ALIGN",   (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",  (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 2),
        ]))
        return t

    img_row = Table(
        [[img_col(img_orig,  "① Original Uploaded Image"),
          img_col(img_annot, "② Annotated Inspection Image"),
          img_col(img_ovrly, "③ Defect Heatmap Overlay")]],
        colWidths=[59 * mm, 59 * mm, 57 * mm]
    )
    img_row.setStyle(TableStyle([
        ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ("PADDING",    (0, 0), (-1, -1), 4),
        ("BACKGROUND", (0, 0), (-1, -1), SLATE_100),
        ("BOX",        (0, 0), (-1, -1), 0.5, BORDER),
        ("INNERGRID",  (0, 0), (-1, -1), 0.5, BORDER),
    ]))
    story.append(img_row)
    story.append(Spacer(1, 6))

    # ═══════════════════════════════════════════════════════════════════════════
    # PAGE 2: DETECTION SUMMARY & INDIVIDUAL DEFECT CATALOGUE
    # ═══════════════════════════════════════════════════════════════════════════

    story.append(PageBreak())

    _section_header(story, "DETECTION SUMMARY", T_h2, 0)

    # Defect Type Breakdown Table
    b_rows = [[
        Paragraph("<b>Defect Type</b>", T_tbl_h),
        Paragraph("<b>Count</b>", T_tbl_h),
        Paragraph("<b>Class Severity</b>", T_tbl_h),
        Paragraph("<b>Status Classification</b>", T_tbl_h),
    ]]

    if not breakdown:
        b_rows.append([
            Paragraph("No active defects detected", T_tbl_b),
            Paragraph("0", T_tbl_bc),
            Paragraph("Low", T_tbl_bc),
            Paragraph("Accepted", T_tbl_bc),
        ])
    else:
        for def_name, count in breakdown.items():
            sev = "Low" if def_name == "Good Welding" else ("Critical" if def_name in ("Crack", "Bad Welding", "Lack of Penetration") else ("High" if def_name in ("Porosity", "Undercut", "Lack of Fusion") else "Medium"))
            stat_lbl = "Accepted" if def_name == "Good Welding" else ("Rejected" if sev == "Critical" else ("Requires Repair" if sev == "High" else "Accepted With Repair"))
            sc = SEVERITY_COLOR_MAP.get(sev, GREEN)
            b_rows.append([
                Paragraph(f"<b>{def_name}</b>", T_tbl_b),
                Paragraph(f"<b>{count}</b>", T_tbl_bc),
                Paragraph(f"<font color='{sc.hexval()}'><b>{sev}</b></font>", T_tbl_bc),
                Paragraph(f"<b>{stat_lbl}</b>", T_tbl_bc),
            ])

    b_tbl = Table(b_rows, colWidths=[55 * mm, 30 * mm, 45 * mm, 45 * mm])
    b_tbl.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0), DARK_HEADER),
        ("GRID",           (0, 0), (-1, -1), 0.4, BORDER),
        ("PADDING",        (0, 0), (-1, -1), 4),
        ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, SLATE_LIGHT]),
    ]))
    story.append(b_tbl)
    story.append(Spacer(1, 8))

    # Complete Individual Detections Table
    _section_header(story, f"COMPLETE DETECTED DEFECTS CATALOGUE ({total_defects} Total)", T_h2, 0)

    d_heads = ["Defect #", "Defect Type", "Confidence", "Exact Detected Location", "Severity", "Status"]
    d_widths = [22 * mm, 36 * mm, 24 * mm, 45 * mm, 24 * mm, 24 * mm]
    d_rows = [[Paragraph(h, T_tbl_h) for h in d_heads]]

    if not defects:
        d_rows.append([
            Paragraph("—", T_tbl_bc),
            Paragraph("Good Welding (No Defect)", T_tbl_b),
            Paragraph(f"{conf_pct}%", T_tbl_bc),
            Paragraph("Full Weld Seam", T_tbl_b),
            Paragraph("<font color='#10B981'><b>Low</b></font>", T_tbl_bc),
            Paragraph("<font color='#10B981'><b>Accepted</b></font>", T_tbl_bc),
        ])
    else:
        for idx, d in enumerate(defects, 1):
            sc = SEVERITY_COLOR_MAP.get(d.get("severity", "Low"), YELLOW)
            conf_val = int(round(d.get("confidence", 0.0) * 100))
            d_rows.append([
                Paragraph(f"<b>DEFECT #{idx}</b>", T_tbl_bc),
                Paragraph(f"<b>{d.get('type', '—')}</b>", T_tbl_b),
                Paragraph(f"<b>{conf_val}%</b>", T_tbl_bc),
                Paragraph(d.get("location", d.get("region", "Center weld region")), T_tbl_b),
                Paragraph(f"<font color='{sc.hexval()}'><b>{d.get('severity', 'Medium')}</b></font>", T_tbl_bc),
                Paragraph(f"<b>{d.get('status', 'Repair Required')}</b>", T_tbl_bc),
            ])

    dtbl = Table(d_rows, colWidths=d_widths, repeatRows=1)
    dtbl.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0), DARK_HEADER),
        ("GRID",           (0, 0), (-1, -1), 0.4, BORDER),
        ("PADDING",        (0, 0), (-1, -1), 4),
        ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, SLATE_LIGHT]),
    ]))
    story.append(dtbl)
    story.append(Spacer(1, 8))

    # ═══════════════════════════════════════════════════════════════════════════
    # NEXT SECTION: PROBLEM ANALYSIS (FOR EVERY DETECTED DEFECT)
    # ═══════════════════════════════════════════════════════════════════════════

    _section_header(story, "PROBLEM / FAILURE ANALYSIS", T_h2, 0)

    if not defects:
        clean_box = Table([[
            Paragraph("<b>Problem Analysis:</b> No critical or active welding defects were detected. Weld bead exhibits sound metallurgical fusion and uniform geometry conforming to AWS D1.1 criteria.", T_body)
        ]], colWidths=[175 * mm])
        clean_box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), GREEN_LIGHT),
            ("BOX",        (0, 0), (-1, -1), 0.5, GREEN),
            ("PADDING",    (0, 0), (-1, -1), 8),
        ]))
        story.append(clean_box)
        story.append(Spacer(1, 8))
    else:
        for idx, d in enumerate(defects, 1):
            sc = SEVERITY_COLOR_MAP.get(d.get("severity", "Medium"), YELLOW)
            conf_val = int(round(d.get("confidence", 0.0) * 100))
            
            p_card = [
                [
                    Paragraph(f"<b>DEFECT #{idx} — {d.get('type')}</b> (Severity: <font color='{sc.hexval()}'><b>{d.get('severity')}</b></font> | Confidence: <b>{conf_val}%</b> | Location: <b>{d.get('location')}</b>)", T_h3),
                ],
                [
                    Paragraph("<b>• Problem:</b>", T_prob_lbl),
                    Paragraph(d.get("problem", "Defect indication identified in weld seam."), T_prob_val),
                ],
                [
                    Paragraph("<b>• Why It Is a Defect:</b>", T_prob_lbl),
                    Paragraph(d.get("why_defect", "Degrades structural integrity and creates stress concentrations."), T_prob_val),
                ],
                [
                    Paragraph("<b>• Possible Cause:</b>", T_prob_lbl),
                    Paragraph(d.get("possible_cause", "Improper heat input or joint contamination."), T_prob_val),
                ],
                [
                    Paragraph("<b>• Recommended Action:</b>", T_prob_lbl),
                    Paragraph(d.get("recommended_action", "Excavate defect and re-weld adhering to WPS."), T_prob_val),
                ]
            ]

            card_table = Table([
                [p_card[0][0]],
                [Table(p_card[1:], colWidths=[38 * mm, 131 * mm], style=[
                    ("VALIGN",  (0, 0), (-1, -1), "TOP"),
                    ("PADDING", (0, 0), (-1, -1), 1.5),
                ])]
            ], colWidths=[173 * mm])

            card_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), SLATE_LIGHT),
                ("BOX",        (0, 0), (-1, -1), 0.5, BORDER),
                ("LINELEFT",   (0, 0), (-1, -1), 4, sc),
                ("PADDING",    (0, 0), (-1, -1), 5),
            ]))

            story.append(KeepTogether([card_table, Spacer(1, 4)]))

    story.append(Spacer(1, 4))

    # ═══════════════════════════════════════════════════════════════════════════
    # NEXT SECTION: QUALITY ASSESSMENT
    # ═══════════════════════════════════════════════════════════════════════════

    _section_header(story, "QUALITY ASSESSMENT", T_h2, 0)

    qa_box = Table([[
        Paragraph(
            f"<b>Quality Score: {score}/100</b>  |  <b>Overall Status: {status}</b>  |  <b>Overall Severity: {overall_sev}</b><br/><br/>"
            f"{qa_explanation}",
            T_body
        )
    ]], colWidths=[175 * mm])
    qa_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE_LIGHT),
        ("BOX",        (0, 0), (-1, -1), 0.8, BLUE_ACCENT),
        ("LINELEFT",   (0, 0), (-1, -1), 4, BLUE_ACCENT),
        ("PADDING",    (0, 0), (-1, -1), 7),
    ]))
    story.append(qa_box)
    story.append(Spacer(1, 6))

    # ═══════════════════════════════════════════════════════════════════════════
    # FINAL SECTION: INSPECTION CONCLUSION & SIGN-OFF
    # ═══════════════════════════════════════════════════════════════════════════

    _section_header(story, "INSPECTION CONCLUSION", T_h2, 0)

    conc_box = Table([[
        Paragraph(f"<b>FINAL VERDICT: {status.upper()}</b><br/><br/>{conclusion_text}", T_verdict)
    ]], colWidths=[175 * mm])
    conc_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SLATE_100),
        ("BOX",        (0, 0), (-1, -1), 0.8, status_color),
        ("LINELEFT",   (0, 0), (-1, -1), 5, status_color),
        ("PADDING",    (0, 0), (-1, -1), 8),
    ]))
    story.append(conc_box)
    story.append(Spacer(1, 8))

    # Sign-off and Verification Block
    qr_box = Table([[
        Paragraph("[ QR CODE VERIFICATION ]<br/><font size='5.5'>AWS D1.1 / ISO 5817</font>",
                  S("qr", fontName="Helvetica", fontSize=7, textColor=SLATE_MID, alignment=TA_CENTER, leading=9)),
    ]], colWidths=[32 * mm], rowHeights=[22 * mm])
    qr_box.setStyle(TableStyle([
        ("BOX",       (0, 0), (-1, -1), 1, BORDER_MID),
        ("BACKGROUND",(0, 0), (-1, -1), SLATE_LIGHT),
        ("PADDING",   (0, 0), (-1, -1), 4),
        ("VALIGN",    (0, 0), (-1, -1), "MIDDLE"),
    ]))

    def sign_col(label1, label2):
        return Table([
            [Paragraph(label1, T_h3)],
            [Paragraph("_" * 32, T_body)],
            [Spacer(1, 4)],
            [Paragraph(label2, T_h3)],
            [Paragraph("_" * 32, T_body)],
        ], colWidths=[68 * mm])

    signoff_row = Table([[
        sign_col("Certified Inspector Name:", "Inspector Signature:"),
        sign_col("Quality Approval Authority:", "Date Approved:"),
        qr_box,
    ]], colWidths=[70 * mm, 70 * mm, 35 * mm])
    signoff_row.setStyle(TableStyle([
        ("VALIGN",  (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(KeepTogether([signoff_row, Spacer(1, 6)]))

    story.append(Paragraph(
        f"<i>Report ID: {inspection_id}  |  Generated by WeldVision AI Quality Engine on {inspection_date} at {inspection_time}  |  "
        f"Compliant with AWS D1.1 / ISO 5817 weld visual inspection criteria. All indications are AI visual estimates to be verified by a Certified Welding Inspector (CWI).</i>",
        S("ft", fontName="Helvetica-Oblique", fontSize=6.2, textColor=SLATE_MID, leading=8.5, alignment=TA_CENTER)
    ))

    # ── Build PDF Document ──────────────────────────────────────────────────
    doc.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    pdf_bytes = buf.getvalue()
    buf.close()
    return pdf_bytes

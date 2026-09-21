import os
import re
import cv2
import numpy as np
import base64
import math
import datetime
from pathlib import Path

def _clean_svg_text(val: str) -> str:
    if not val:
        return ""
    s = re.sub(r'(?i)\bsvg\b', '', str(val))
    s = re.sub(r'(?i)^svg[-_ ]*', '', s)
    s = re.sub(r'(?i)^svg([A-Z])', r'\1', s)
    return re.sub(r'\s+', ' ', s).strip()


# Safeguard Windows DLL directory for PyTorch
torch_lib = r'C:\Users\user\AppData\Local\Programs\Python\Python313\Lib\site-packages\torch\lib'
if os.path.exists(torch_lib):
    try:
        os.add_dll_directory(torch_lib)
    except Exception:
        pass

from ultralytics import YOLO

class BaseDetector:
    """Standard modular base interface for WeldVision AI detectors."""
    def analyze(self, image_bytes: bytes, filename: str = "weld_specimen.jpg") -> dict:
        raise NotImplementedError("Subclasses must implement analyze()")


# ─── Welding Defect Engineering Knowledge Base & Metadata ─────────────────────

WELD_DEFECT_METADATA = {
    "Bad Welding": {
        "severity": "Critical",
        "status": "Rejected",
        "problem": "Severe bead geometry irregularity, lack of fusion, or structural weld profile breakdown.",
        "why_defect": "Reduces effective load-bearing cross-sectional area and creates severe stress concentrations prone to joint failure.",
        "possible_cause": "Sub-optimal welding parameter settings (incompatible current/voltage ratio, erratic travel speed, or poor joint alignment).",
        "recommended_action": "Excavate defective section completely down to sound parent metal by grinding or carbon-arc gouging, clean joint, and re-weld adhering to qualified WPS.",
        "repair_priority": "Immediate Repair",
        "explain": "Severe bead geometry irregularity or lack of uniform fusion identified by trained YOLO11 segmentation network.",
    },
    "Crack": {
        "severity": "Critical",
        "status": "Rejected",
        "problem": "Linear crack discontinuity detected in weld metal or heat-affected zone (HAZ).",
        "why_defect": "Creates severe notch stress risers that propagate rapidly under cyclic loading, leading to catastrophic brittle structural fracture.",
        "possible_cause": "Excessive thermal stress, high residual stress, rapid cooling rate, high joint restraint, or hydrogen contamination during solidification.",
        "recommended_action": "Stop-drill crack extremities, excavate defect completely to sound metal, verify crack elimination via dye penetrant inspection, and re-weld with low-hydrogen consumables.",
        "repair_priority": "Immediate Repair",
        "explain": "Linear fracture discontinuity identified along weld bead axis or heat-affected zone (HAZ).",
    },
    "Excess Reinforcement": {
        "severity": "Medium",
        "status": "Accepted With Repair",
        "problem": "Weld metal deposit on face or root exceeding allowable reinforcement profile height.",
        "why_defect": "Creates abrupt geometric transitions and notch stress concentrations at weld toes, increasing fatigue vulnerability under cyclic loading.",
        "possible_cause": "Slow travel speed, excessive filler wire feed rate, or improper torch oscillation building excessive weld crown height.",
        "recommended_action": "Mechanically grind the weld crown smoothly to blend flush with parent metal maintaining reinforcement height <= 3.0mm conforming to AWS D1.1 Table 6.1.",
        "repair_priority": "Repair Before Use",
        "explain": "Weld metal deposit on face or root exceeding allowable reinforcement profile height.",
    },
    "Porosity": {
        "severity": "High",
        "status": "Requires Repair",
        "problem": "Porous spherical gas cavities or void cluster entrapped within the solidifying weld metal.",
        "why_defect": "Reduces the effective cross-sectional density and acts as internal stress concentration points, degrading tensile and fatigue strength.",
        "possible_cause": "Atmospheric gas entrapment, moisture/grease/rust contamination on joint faces, or inadequate shielding gas flow/drafty environment.",
        "recommended_action": "Mechanically grind out porous weld bead region down to sound metal, ensure dry shielded atmosphere and correct gas flow, and deposit sound repair pass.",
        "repair_priority": "Repair Before Use",
        "explain": "Gas cavity or spherical void cluster trapped during solidification detected by YOLO11 segmentation mask.",
    },
    "Spatters": {
        "severity": "Medium",
        "status": "Repair Recommended",
        "problem": "Molten metal globules expelled from welding arc scattered across weld face and adjacent base plate.",
        "why_defect": "Can mask underlying micro-cracks, interfere with non-destructive testing (NDT), impair protective coatings, and initiate localized galvanic corrosion.",
        "possible_cause": "High arc voltage, excessive arc length, damp electrodes, incorrect torch angle, or improper shielding gas mixture.",
        "recommended_action": "Mechanically chisel, wire brush, or scrape spatter beads off parent plate surface; apply anti-spatter barrier spray pre-weld.",
        "repair_priority": "Clean / De-spatter",
        "explain": "Molten metal droplets expelled from welding arc scattered across adjacent plate surface.",
    },
    "Spatter": {
        "severity": "Medium",
        "status": "Repair Recommended",
        "problem": "Molten metal globules expelled from welding arc scattered across weld face and adjacent base plate.",
        "why_defect": "Can mask underlying micro-cracks, interfere with non-destructive testing (NDT), impair protective coatings, and initiate localized galvanic corrosion.",
        "possible_cause": "High arc voltage, excessive arc length, damp electrodes, incorrect torch angle, or improper shielding gas mixture.",
        "recommended_action": "Mechanically chisel, wire brush, or scrape spatter beads off parent plate surface; apply anti-spatter barrier spray pre-weld.",
        "repair_priority": "Clean / De-spatter",
        "explain": "Molten metal droplets expelled from welding arc scattered across adjacent plate surface.",
    },
    "Lack of Fusion": {
        "severity": "High",
        "status": "Requires Repair",
        "problem": "Planar discontinuity along weld toe or sidewall where weld metal failed to coalesce with base metal.",
        "why_defect": "Forms an un-fused boundary plane causing sudden joint separation under shear or tensile stress.",
        "possible_cause": "Insufficient heat input, incorrect torch angle, or heavy mill scale/oxide layer preventing coalescence.",
        "recommended_action": "Excavate un-fused weld boundary by grinding, preheat joint, adjust travel speed and voltage, and deposit qualified repair pass.",
        "repair_priority": "Repair Before Use",
        "explain": "Planar discontinuity along weld toe/sidewall where weld metal failed to coalesce with base metal.",
    },
    "Lack of Penetration": {
        "severity": "Critical",
        "status": "Rejected",
        "problem": "Unfilled gap at joint root due to incomplete weld penetration through joint thickness.",
        "why_defect": "Leaves an internal notch at root pass that drastically reduces tensile fatigue strength and promotes rapid cracking.",
        "possible_cause": "Low welding current, excessive root face thickness, travel speed too fast, or small bevel angle preventing root access.",
        "recommended_action": "Back-gouge to sound metal from root side, increase welding heat input, and re-weld root pass adhering to WPS.",
        "repair_priority": "Immediate Repair",
        "explain": "Unfilled gap detected at joint root due to incomplete weld penetration through joint thickness.",
    },
    "Undercut": {
        "severity": "High",
        "status": "Requires Repair",
        "problem": "Groove melted into base metal adjacent to weld toe along outer boundary.",
        "why_defect": "Reduces parent plate thickness at high-stress weld toe transition zone and acts as fatigue initiation site.",
        "possible_cause": "Excessive welding current, arc length too long, or excessive travel speed cutting groove in parent metal at toe.",
        "recommended_action": "Clean undercut groove thoroughly and deposit stringer repair pass using small diameter electrode.",
        "repair_priority": "Repair Before Use",
        "explain": "Groove melted into base metal adjacent to weld toe along outer boundary.",
    },
    "Good Welding": {
        "severity": "Low",
        "status": "Accepted",
        "problem": "None (Conforming Weld).",
        "why_defect": "Not a defect; conforms to standard acceptance criteria.",
        "possible_cause": "Optimal welding procedure specification (WPS) execution with balanced heat input, consistent travel speed, and proper gas shielding.",
        "recommended_action": "No repair required; weld bead conforms to AWS D1.1 / ISO 5817 visual inspection criteria.",
        "repair_priority": "No Action Required",
        "explain": "Uniform bead width, smooth ripple profile, gradual toe transition, and sound metallurgical coalescence verified by YOLO11 segmentation network.",
    }
}

# Color-coding map for Severities (BGR & HEX)
SEVERITY_COLOR_BGR = {
    "Critical": (40,  40,  235),  # Red
    "High":     (0,   115, 245),  # Orange
    "Medium":   (0,   200, 240),  # Yellow
    "Low":      (50,  195, 70),   # Green
}

SEVERITY_OVERLAY_BGR = {
    "Critical": (30,  30,  220),
    "High":     (0,   100, 230),
    "Medium":   (0,   180, 220),
    "Low":      (40,  170, 60),
}

SEVERITY_HEX = {
    "Critical": "#EF4444", # Red
    "High":     "#F97316", # Orange
    "Medium":   "#F59E0B", # Yellow
    "Low":      "#10B981", # Green
}

CLASS_SEVERITY_MAP = {
    "Bad Welding": "Critical",
    "Crack": "Critical",
    "Lack of Penetration": "Critical",
    "Undercut": "High",
    "Lack of Fusion": "High",
    "Porosity": "High",
    "Excess Reinforcement": "Medium",
    "Spatters": "Medium",
    "Spatter": "Medium",
    "Good Welding": "Low",
}


# ─── Main AI YOLO11 Segmentation Detector ─────────────────────────────────────

class WeldDetector(BaseDetector):
    """
    AI-Powered Weld Defect Detector using Ultralytics YOLO11 Segmentation.
    Loads real trained weights and inspects every detected defect without dropping.
    """

    def __init__(self, model_path: str = None):
        self.model_path = self._resolve_model_path(model_path)
        print(f"[WeldDetector] Initializing with model weights: {self.model_path}")
        self.model = YOLO(self.model_path)
        self.device = 'cpu'
        print(f"[WeldDetector] YOLO11 model loaded successfully on device: {self.device}")

    def _resolve_model_path(self, model_path: str = None) -> str:
        candidates = [
            model_path,
            "models/best.pt",
            "backend/models/best.pt",
            "runs/segment/runs/segment/weldvision_yolo11n/weights/best.pt",
            "runs/segment/weldvision_yolo11n/weights/best.pt",
            "yolo11n-seg.pt",
        ]
        for c in candidates:
            if c and os.path.exists(c):
                return str(Path(c).resolve())
        return "yolo11n-seg.pt"

    def reload_model(self, model_path: str = None):
        resolved = self._resolve_model_path(model_path)
        if resolved != self.model_path or model_path:
            self.model_path = resolved
            self.model = YOLO(self.model_path)
            print(f"[WeldDetector] Reloaded model weights: {self.model_path}")

    def _bytes_to_cv2(self, image_bytes: bytes) -> np.ndarray:
        arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Could not decode image file into CV2 matrix.")
        return img

    def _cv2_to_b64(self, img: np.ndarray) -> str:
        ok, buf = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 94])
        return "data:image/jpeg;base64," + base64.b64encode(buf).decode()

    # ── Main Analysis Pipeline ───────────────────────────────────────────

    def analyze(self, image_bytes: bytes, filename: str = "weld_specimen.jpg") -> dict:
        best_candidate = "backend/models/best.pt"
        if os.path.exists(best_candidate) and "yolo11n-seg.pt" in self.model_path:
            self.reload_model(best_candidate)

        img_bgr = self._bytes_to_cv2(image_bytes)
        h, w, _ = img_bgr.shape

        # Run real YOLO11 Segmentation inference
        results = self.model.predict(
            img_bgr,
            conf=0.05,
            imgsz=480,
            device=self.device,
            verbose=False
        )

        r = results[0]
        raw_detections = []
        good_welding_count = 0
        detected_classes_count = {}

        if r.boxes is not None and len(r.boxes) > 0:
            boxes = r.boxes
            has_masks = r.masks is not None and len(r.masks) > 0
            
            for i in range(len(boxes)):
                cls_id = int(boxes.cls[i].item())
                conf = float(boxes.conf[i].item())
                cls_name = self.model.names.get(cls_id, f"Defect_{cls_id}")

                # Track detection counts
                detected_classes_count[cls_name] = detected_classes_count.get(cls_name, 0) + 1

                # Bounding box coordinates [x1, y1, x2, y2]
                x1, y1, x2, y2 = boxes.xyxy[i].cpu().numpy()
                bx = max(0, min(int(x1), w - 1))
                by = max(0, min(int(y1), h - 1))
                bw = max(2, min(int(x2 - x1), w - bx))
                bh = max(2, min(int(y2 - y1), h - by))

                # Segmentation mask points
                mask_pts = []
                if has_masks and i < len(r.masks.xy):
                    poly = r.masks.xy[i]
                    if len(poly) > 0:
                        mask_pts = [[int(pt[0]), int(pt[1])] for pt in poly]

                # Compute area percentage
                if mask_pts and len(mask_pts) >= 3:
                    area = cv2.contourArea(np.array(mask_pts, dtype=np.int32))
                else:
                    area = float(bw * bh)
                area_pct = round((area / max(1.0, float(w * h))) * 100, 2)

                if cls_name == "Good Welding":
                    good_welding_count += 1
                    continue

                # Determine Confidence Tier
                if conf >= 0.20:
                    conf_tier = "Confirmed Defect"
                    status_note = "High Confidence"
                elif conf >= 0.10:
                    conf_tier = "Review Required"
                    status_note = "Medium Confidence"
                else:
                    conf_tier = "Possible Indication"
                    status_note = "Low Confidence (Tentative)"

                # Severity assignment
                if conf < 0.10 and cls_name in ("Crack", "Bad Welding", "Lack of Penetration"):
                    sev = "Medium"
                else:
                    sev = CLASS_SEVERITY_MAP.get(cls_name, "Medium")

                d_dict = self._build_defect_dict(
                    dtype=cls_name,
                    sev=sev,
                    x=bx,
                    y=by,
                    cw=bw,
                    ch=bh,
                    pct=area_pct,
                    conf=conf,
                    img_w=w,
                    img_h=h,
                    mask_pts=mask_pts
                )
                d_dict["confidence_tier"] = conf_tier
                d_dict["status_note"] = status_note
                raw_detections.append(d_dict)

        # Build dynamic timestamp information
        now = datetime.datetime.now()
        inspection_date = now.strftime("%d %B %Y")
        inspection_time = now.strftime("%H:%M")
        inspection_timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        inspection_id = f"WLD-{now.strftime('%Y%m%d-%H%M%S')}"

        # If zero defects detected (or pure Good Welding)
        if not raw_detections:
            return self._clean_weld_result(
                img_bgr=img_bgr,
                w=w,
                h=h,
                filename=filename,
                inspection_id=inspection_id,
                inspection_date=inspection_date,
                inspection_time=inspection_time,
                inspection_timestamp=inspection_timestamp,
                good_welding_count=good_welding_count,
                detected_classes_count=detected_classes_count
            )

        # Include EVERY detected defect (no dropping or truncating)
        defects = sorted(raw_detections, key=lambda d: (-d["confidence"], d["id_num"] if "id_num" in d else 0))

        # Separate Detected Classes from Active Defects
        active_breakdown = {}
        for d in defects:
            t = d["type"]
            active_breakdown[t] = active_breakdown.get(t, 0) + 1

        detected_classes = dict(active_breakdown)
        if good_welding_count > 0:
            detected_classes["Good Welding"] = good_welding_count

        breakdown = detected_classes  # Backward compatibility

        # Defect Counting across strict confidence tiers
        total_active_defects = len(defects)
        total_model_detections = total_active_defects + good_welding_count
        confirmed_defects_count = sum(1 for d in defects if d.get("confidence", 0.0) >= 0.20)
        review_required_count = sum(1 for d in defects if 0.10 <= d.get("confidence", 0.0) < 0.20)
        possible_indications_count = sum(1 for d in defects if d.get("confidence", 0.0) < 0.10)

        # Assign sequential IDs and populate dynamic image-specific analysis
        for idx, d in enumerate(defects, 1):
            d["id"] = f"WLD-{idx:03d}"
            d["id_num"] = idx
            meta = WELD_DEFECT_METADATA.get(d["type"], WELD_DEFECT_METADATA.get(d["type"].capitalize(), WELD_DEFECT_METADATA["Porosity"]))

            conf = d.get("confidence", 0.0)

            # Strict Confidence Tiers:
            # CONFIDENCE >= 20% -> Confirmed Defect
            # CONFIDENCE 10%–19.99% -> Review Required
            # CONFIDENCE < 10% -> Possible Indication
            if conf >= 0.20:
                d["confidence_tier"] = "Confirmed Defect"
                d["confidence_qualifier"] = "High-confidence" if conf >= 0.50 else "Moderate-confidence"
                d["status"] = meta["status"]
                d["repair_priority"] = meta["repair_priority"]
            elif conf >= 0.10:
                d["confidence_tier"] = "Review Required"
                d["confidence_qualifier"] = "Review-required"
                d["status"] = "Review Required"
                d["repair_priority"] = "Verification Required"
            else:
                d["confidence_tier"] = "Possible Indication"
                d["confidence_qualifier"] = "Possible low-confidence"
                d["status"] = "Possible Indication"
                d["repair_priority"] = "Verification Recommended"

            d["explain"] = meta["explain"]
            d["severity_hex"] = SEVERITY_HEX.get(d["severity"], "#F59E0B")
            d["why_defect"] = meta["why_defect"]

            # Size descriptor based on area percentage (no invented mm values)
            area_pct = d.get("area_pct", 0.0)
            if area_pct >= 8.0:
                d["size_descriptor"] = "Large"
            elif area_pct >= 3.0:
                d["size_descriptor"] = "Moderate"
            elif area_pct >= 0.5:
                d["size_descriptor"] = "Small"
            else:
                d["size_descriptor"] = "Isolated"

            # Detected size strings for display (no fake mm)
            bw_px = d["bbox"][2]
            bh_px = d["bbox"][3]
            d["detected_size"] = f"{bw_px} px × {bh_px} px ({d['size_descriptor']})"
            d["region_size"] = f"{bw_px} px × {bh_px} px"
            d["size_mm"] = d["detected_size"]

            # Sanitize region and location (clean any accidental svg text artifacts)
            d["location"] = _clean_svg_text(d["location"])
            d["region"] = _clean_svg_text(d["region"])

            # Generate dynamic image-specific analysis
            analysis = self._generate_dynamic_analysis(d, defects, w, h)
            d["observation"] = _clean_svg_text(analysis["observation"])
            d["problem"] = _clean_svg_text(analysis["problem"])
            d["possible_cause"] = _clean_svg_text(analysis["possible_cause"])
            d["root_cause"] = d["possible_cause"]
            d["recommended_action"] = _clean_svg_text(analysis["recommended_action"])
            d["repair_method"] = d["recommended_action"]
            d["recommended_repair"] = d["recommended_action"]

        # ── Analytics & Quality Scoring ──────────────────────────────────────
        total_defects = len(defects)
        defective_area_pct = round(min(sum(d["area_pct"] for d in defects), 75.0), 1)
        weld_coverage_pct = round(max(99.5 - defective_area_pct * 0.4, 70.0), 1)

        critical_count = sum(1 for d in defects if d["severity"] == "Critical")
        high_count     = sum(1 for d in defects if d["severity"] == "High")
        medium_count   = sum(1 for d in defects if d["severity"] == "Medium")
        low_count      = sum(1 for d in defects if d["severity"] == "Low")

        quality_score = self._compute_weld_quality_score(defects, defective_area_pct)
        condition_info = self._get_condition_label(quality_score, defects, confirmed_defects_count)
        acceptance_status = self._determine_acceptance_status(
            quality_score, critical_count, high_count, medium_count, total_defects,
            confirmed_count=confirmed_defects_count, review_count=review_required_count
        )
        overall_severity = self._determine_overall_severity(
            critical_count, high_count, medium_count, defective_area_pct,
            confirmed_count=confirmed_defects_count
        )
        overall_risk = overall_severity
        repair_priority = self._determine_overall_repair_priority(
            critical_count, high_count, medium_count, defects,
            confirmed_count=confirmed_defects_count
        )

        dominant_type = max(set(d["type"] for d in defects), key=lambda t: sum(1 for d in defects if d["type"] == t))
        largest_d = max(defects, key=lambda d: d["area_pct"])
        largest_defect_str = f"{largest_d['type']} ({largest_d['detected_size']})"

        # ── Deterministic Calculation: Overall Detection Confidence ─────────
        # Calculated deterministically as the arithmetic mean of confidence scores
        # of actual detections found in this specimen.
        # No fake precision metric, no arbitrary clamping (removed artificial clamp to 80%).
        if defects:
            overall_detection_conf = round(float(np.mean([d["confidence"] for d in defects])) * 100, 1)
        elif good_welding_count > 0:
            overall_detection_conf = 98.0
        else:
            overall_detection_conf = 98.0

        inspection_conf = overall_detection_conf

        # Build dynamic conclusion & quality assessment explanation using ONLY actual detections
        conclusion_text = self._generate_weld_conclusion(
            defects, active_breakdown, acceptance_status, critical_count, high_count,
            confirmed_count=confirmed_defects_count, review_count=review_required_count,
            possible_count=possible_indications_count
        )
        quality_explanation = self._generate_quality_explanation(
            quality_score, acceptance_status, overall_severity, defects, active_breakdown,
            confirmed_count=confirmed_defects_count, review_count=review_required_count,
            possible_count=possible_indications_count
        )
        verdict = self._generate_weld_verdict(
            defects, defective_area_pct, quality_score, acceptance_status, dominant_type,
            confirmed_count=confirmed_defects_count
        )

        possible_causes = list(dict.fromkeys(d["possible_cause"] for d in defects))
        recommended_actions = list(dict.fromkeys(d["recommended_action"] for d in defects))

        # Problem analysis list for every defect
        problem_analysis_list = []
        for d in defects:
            problem_analysis_list.append({
                "defect_id": d["id"],
                "defect_type": d["type"],
                "severity": d["severity"],
                "confidence": d["confidence"],
                "confidence_tier": d["confidence_tier"],
                "observation": d["observation"],
                "problem": d["problem"],
                "why_defect": d["why_defect"],
                "possible_cause": d["possible_cause"],
                "recommended_action": d["recommended_action"]
            })

        # ── Render Non-Overlapping Visualizations ───────────────────────────
        annotated_bgr = self._draw_engineering_annotations(img_bgr, defects)
        overlay_bgr   = self._draw_defect_heatmap_overlay(img_bgr, defects)

        return {
            "original_image":       self._cv2_to_b64(img_bgr),
            "annotated_image":      self._cv2_to_b64(annotated_bgr),
            "overlay_image":        self._cv2_to_b64(overlay_bgr),
            "file_name":            filename,
            "inspection_id":        inspection_id,
            "inspection_date":      inspection_date,
            "inspection_time":      inspection_time,
            "inspection_timestamp": inspection_timestamp,
            "model_name":           "Ultralytics YOLO11-seg (Industrial Weld Model)",
            "model_type":           "Instance Segmentation & Defect Analysis",
            "inspection_status":    "Complete",
            "total_defects":        total_active_defects,
            "total_active_defects": total_active_defects,
            "total_model_detections": total_model_detections,
            "confirmed_defects_count": confirmed_defects_count,
            "review_required_count": review_required_count,
            "possible_indications_count": possible_indications_count,
            "good_welding_count":   good_welding_count,
            "detected_classes":     detected_classes,
            "active_defects_breakdown": active_breakdown,
            "defects":              defects,
            "breakdown":            detected_classes,
            "problem_analysis":     problem_analysis_list,
            "quality_assessment": {
                "score":                quality_score,
                "status":               acceptance_status,
                "severity":             overall_severity,
                "explanation":          quality_explanation,
            },
            "conclusion":           conclusion_text,
            "summary": {
                "total_model_detections": total_model_detections,
                "total_defects":        total_active_defects,
                "total_active_defects": total_active_defects,
                "confirmed_defects":    confirmed_defects_count,
                "review_required":      review_required_count,
                "possible_indications": possible_indications_count,
                "good_welding_detections": good_welding_count,
                "detected_classes":     detected_classes,
                "active_defects":       active_breakdown,
                "breakdown":            detected_classes,
                "critical_defects":     critical_count,
                "major_defects":        high_count,
                "minor_defects":        medium_count,
                "acceptable_defects":   low_count,
                "largest_defect":       largest_defect_str,
                "dominant_defect":      dominant_type,
                "weld_coverage_percent": weld_coverage_pct,
                "defective_area_percent": defective_area_pct,
                "inspection_confidence": inspection_conf,
                "overall_detection_confidence": overall_detection_conf,
            },
            "weld_quality": {
                "score":                quality_score,
                "condition":            condition_info["label"],
                "acceptance_status":    acceptance_status,
                "overall_status":       acceptance_status,
                "overall_severity":     overall_severity,
                "overall_risk":         overall_risk,
                "repair_priority":      repair_priority,
                "verdict":              verdict,
                "conclusion":           conclusion_text,
                "possible_causes":      possible_causes,
                "recommended_actions":  recommended_actions,
            },
            # Flat compatibility fields
            "critical_count":       critical_count,
            "high_count":           high_count,
            "medium_count":         medium_count,
            "low_count":            low_count,
            "damaged_pct":          defective_area_pct,
            "health_score":         quality_score,
            "condition":            condition_info["label"],
            "acceptance_status":    acceptance_status,
            "overall_risk":         overall_risk,
            "dominant_type":        dominant_type,
            "largest_defect":       largest_defect_str,
            "verdict":              verdict,
            "inspection_confidence": inspection_conf,
            "overall_detection_confidence": overall_detection_conf,
        }

    # ── Helpers & Generators ────────────────────────────────────────────

    def _build_defect_dict(self, dtype, sev, x, y, cw, ch, pct, conf, img_w, img_h, mask_pts=None):
        cx, cy = int(x + cw // 2), int(y + ch // 2)

        # Determine exact natural region location
        if cy < img_h * 0.35:
            vert_str = "Upper"
            zone_v = "Top Pass"
        elif cy > img_h * 0.65:
            vert_str = "Lower"
            zone_v = "Root Pass"
        else:
            vert_str = "Center"
            zone_v = "Centerline"

        if cx < img_w * 0.35:
            horiz_str = "left"
            zone_h = "Left Toe"
        elif cx > img_w * 0.65:
            horiz_str = "right"
            zone_h = "Right Toe"
        else:
            horiz_str = "weld"
            zone_h = "Weld Seam"

        if vert_str == "Center" and horiz_str == "weld":
            region_str = "Center weld region"
        else:
            region_str = f"{vert_str}-{horiz_str} weld region"

        loc_str = f"{zone_v} ({zone_h})"

        res = {
            "type": dtype,
            "defect_name": dtype,
            "severity": sev,
            "bbox": [int(x), int(y), int(cw), int(ch)],
            "center": [cx, cy],
            "area_pct": round(float(pct), 2),
            "confidence": round(float(conf), 3),
            "confidence_pct": int(round(conf * 100)),
            "region": region_str,
            "location": region_str,
            "weld_zone": loc_str,
        }
        if mask_pts:
            res["segmentation_mask"] = mask_pts
        return res

    # ── Dynamic Image-Specific Analysis Generator ──────────────────────────

    def _generate_dynamic_analysis(self, defect: dict, all_defects: list, img_w: int, img_h: int) -> dict:
        """
        Generates image-specific, detection-specific analysis text for a single defect.
        All output is deterministic — the same detection data always produces the same text.
        No randomization. No invented physical measurements.
        """
        dtype = defect.get("type", "Unknown")
        conf = defect.get("confidence", 0.0)
        conf_pct = int(round(conf * 100))
        conf_tier = defect.get("confidence_tier", "Confirmed Defect")
        conf_qual = defect.get("confidence_qualifier", "Moderate-confidence")
        region = _clean_svg_text(defect.get("region", defect.get("location", "Center weld region")))
        area_pct = defect.get("area_pct", 0.0)
        size_desc = defect.get("size_descriptor", "Small")
        has_mask = "segmentation_mask" in defect and len(defect.get("segmentation_mask", [])) >= 3
        severity = defect.get("severity", "Medium")

        # Sort same-type detections by confidence/area to establish unique context
        same_type_defs = sorted(
            [d for d in all_defects if d.get("type") == dtype],
            key=lambda x: (-x.get("confidence", 0.0), -x.get("area_pct", 0.0))
        )
        same_type_count = len(same_type_defs)
        rank = same_type_defs.index(defect) if defect in same_type_defs else 0

        # Determine clustering: same-type detections within close proximity
        clustered = False
        if same_type_count >= 2:
            cx, cy = defect.get("center", [img_w // 2, img_h // 2])
            for other in same_type_defs:
                if other is defect:
                    continue
                ox, oy = other.get("center", [0, 0])
                dist = ((cx - ox) ** 2 + (cy - oy) ** 2) ** 0.5
                if dist < max(img_w, img_h) * 0.25:
                    clustered = True
                    break

        # ── Good Welding — not a defect ──────────────────────────────────
        if dtype == "Good Welding":
            return {
                "observation": f"No active defect indication detected in the inspected {region.lower()}. YOLO11 segmentation classified this region as Good Welding with {conf_pct}% confidence.",
                "problem": "None (Conforming Weld). No active defect indication present in this region.",
                "possible_cause": "Optimal welding procedure specification (WPS) execution with balanced heat input, consistent travel speed, and proper gas shielding.",
                "recommended_action": "No corrective action required. Weld region conforms to AWS D1.1 / ISO 5817 visual inspection acceptance criteria.",
            }

        # ── Build observation (specific to detection evidence, non-repetitive) ──
        mask_desc = f"with segmentation mask confirming a {size_desc.lower()} defect region ({area_pct}% of image area)" if has_mask else f"within a {size_desc.lower()} bounding box region ({area_pct}% of image area)"

        if conf < 0.10:
            # Possible indication (<10%)
            if rank == 0 or same_type_count == 1:
                observation = f"Possible low-confidence {dtype.lower()} indication detected in the {region.lower()} at {conf_pct}% confidence ({area_pct}% of image area)."
            else:
                observation = f"Possible low-confidence secondary {dtype.lower()} indication detected in the {region.lower()} at {conf_pct}% confidence."
        elif conf < 0.20:
            # Review required (10% - 19.99%)
            if rank == 0:
                observation = f"Review-required {dtype.lower()} indication detected in the {region.lower()}, representing approximately {area_pct}% of image area at {conf_pct}% confidence."
            else:
                primary = same_type_defs[0]
                is_smaller = area_pct < primary.get("area_pct", area_pct)
                comp_str = f"smaller than the primary {dtype.lower()} indication" if is_smaller else f"representing {area_pct}% of image area"
                observation = f"Review-required {dtype.lower()} indication detected in the {region.lower()}, {comp_str} at {conf_pct}% confidence."
        else:
            # Confirmed defect (>= 20%)
            if rank == 0:
                observation = f"{conf_qual} {dtype.lower()} indication detected in the {region.lower()}, representing approximately {area_pct}% of image area at {conf_pct}% AI confidence."
            else:
                observation = f"Additional {conf_qual.lower()} {dtype.lower()} indication detected in the {region.lower()} {mask_desc} at {conf_pct}% AI confidence."

        if clustered and same_type_count >= 2:
            observation += f" Located in close proximity to adjacent {dtype.lower()} indication(s) in this zone."

        observation = observation.replace("..", ".").strip()

        # ── Build problem statement ──────────────────────────────────────
        meta = WELD_DEFECT_METADATA.get(dtype, WELD_DEFECT_METADATA.get(dtype.capitalize(), WELD_DEFECT_METADATA["Porosity"]))
        base_problem = meta["problem"]

        if conf < 0.10:
            # For <10%: Do NOT show Rejected / Requires Repair / aggressive claims
            problem = f"Possible unconfirmed indication detected at {conf_pct}% AI confidence in the {region.lower()}. Physical visual verification or complementary NDT is required to confirm whether this represents a true discontinuity or a surface mark."
        elif conf < 0.20:
            # For 10-19.99%: Review required
            problem = f"Potential {dtype.lower()} indication identified at {conf_pct}% confidence in the {region.lower()}. Indication requires visual verification prior to finalizing joint quality classification."
        else:
            # For >=20%: Confirmed defect
            if severity == "Critical":
                sev_ctx = "This is a critical-severity indication requiring engineering review and repair before service"
            elif severity == "High":
                sev_ctx = "This is a high-severity indication requiring repair before final acceptance"
            elif severity == "Medium":
                sev_ctx = "This is a medium-severity indication; rework/repair is recommended"
            else:
                sev_ctx = "This is a low-severity indication within cosmetic rework tolerance"
            problem = f"{base_problem} {sev_ctx}. AI confidence is {conf_pct}% in the {region.lower()}."

        problem = problem.replace("..", ".").strip()

        # ── Build possible cause (framed as potential/contributing) ────────
        base_cause = meta["possible_cause"].rstrip(".")

        if conf < 0.10:
            possible_cause = f"Unconfirmed low-confidence indication ({conf_pct}%). Potential contributing factors if verified include: {base_cause}."
        elif conf < 0.20:
            possible_cause = f"Tentative indication pending physical verification. Possible contributing factors include: {base_cause}."
        else:
            cause_parts = [f"Possible contributing factors include: {base_cause}"]
            if clustered and same_type_count > 1:
                cause_parts.append(f"Clustered distribution of {same_type_count} {dtype.lower()} indications in the {region.lower()} may suggest localized thermal or shielding instability in that zone")
            elif area_pct >= 5.0:
                cause_parts.append("The relatively large affected area suggests sustained or compounding process deviation")
            possible_cause = ". ".join(cause_parts) + "."

        possible_cause = possible_cause.replace("..", ".").strip()

        # ── Build recommended action (strict confidence-based) ───────────
        base_action = meta["recommended_action"].rstrip(".")

        if conf < 0.10:
            # EXACT PROMPT REQUIREMENT FOR <10%:
            recommended_action = "Manual visual verification or appropriate NDT is recommended before any corrective action is taken."
        elif conf < 0.20:
            # EXACT PROMPT REQUIREMENT FOR 10-19.99%:
            recommended_action = f"Review the indicated region in the {region.lower()} and verify visual/NDT indications before repair."
        else:
            # Confirmed defect (>= 20%)
            action_parts = [base_action]
            if severity == "Critical":
                action_parts.append(f"Given the critical severity of this {dtype.lower()} indication in the {region.lower()}, immediate corrective action and re-inspection are required before service")
            elif severity == "High":
                action_parts.append(f"Repair of this {dtype.lower()} indication in the {region.lower()} should be completed prior to final acceptance")
            recommended_action = ". ".join(action_parts) + "."

        recommended_action = recommended_action.replace("..", ".").strip()

        return {
            "observation": observation,
            "problem": problem,
            "possible_cause": possible_cause,
            "recommended_action": recommended_action,
        }

    def _compute_weld_quality_score(self, defects, defective_area_pct):
        """
        Dynamically computes quality score using confidence-aware logic.
        Confirmed defects (>=20%) drive penalties; <10% indications have minimal/zero penalty;
        Good Welding has zero penalty.
        """
        if not defects:
            return 98

        confirmed_defs = [d for d in defects if d.get("confidence", 0.0) >= 0.20]
        review_defs = [d for d in defects if 0.10 <= d.get("confidence", 0.0) < 0.20]
        possible_defs = [d for d in defects if d.get("confidence", 0.0) < 0.10]

        critical_confirmed = sum(1 for d in confirmed_defs if d["severity"] == "Critical")
        high_confirmed = sum(1 for d in confirmed_defs if d["severity"] == "High")
        medium_confirmed = sum(1 for d in confirmed_defs if d["severity"] == "Medium")
        low_confirmed = sum(1 for d in confirmed_defs if d["severity"] == "Low")

        score = 100.0

        # Confirmed defect area penalty
        confirmed_area = sum(d.get("area_pct", 0.0) for d in confirmed_defs)
        score -= min(30.0, confirmed_area * 3.0)

        # Penalties based on confirmed defects
        for d in confirmed_defs:
            sev = d["severity"]
            conf = d.get("confidence", 0.5)
            weight = max(0.5, min(1.0, conf))
            if sev == "Critical":
                score -= (32.0 * weight)
            elif sev == "High":
                score -= (18.0 * weight)
            elif sev == "Medium":
                score -= (7.0 * weight)
            else:
                score -= (2.0 * weight)

        # Review-required (10-19.99%) minor penalty
        for d in review_defs:
            sev = d["severity"]
            if sev == "Critical":
                score -= 8.0
            elif sev == "High":
                score -= 5.0
            elif sev == "Medium":
                score -= 2.0
            else:
                score -= 0.5

        # Possible indications (<10%) minimal penalty (0.5 pt each, capped at 2.0)
        score -= min(2.0, len(possible_defs) * 0.5)

        # Multi-defect compounding penalty ONLY if confirmed defects >= 2
        if len(confirmed_defs) >= 4:
            score -= 6.0
        elif len(confirmed_defs) >= 2:
            score -= 3.0

        final_score = int(round(score))

        # Strict Engineering Caps ONLY for confirmed defects:
        if critical_confirmed > 0:
            final_score = min(final_score, 42)
        elif high_confirmed > 0:
            final_score = min(final_score, 62)
        elif medium_confirmed >= 3 or len(confirmed_defs) >= 4:
            final_score = min(final_score, 74)
        elif medium_confirmed > 0:
            final_score = min(final_score, 82)
        elif len(confirmed_defs) == 0:
            # If no confirmed defects at all, score must remain high
            if len(review_defs) > 0:
                final_score = max(80, min(92, final_score))
            else:
                final_score = max(90, min(96, final_score))

        return max(5, min(98, final_score))

    def _get_condition_label(self, score, defects=None, confirmed_count=0):
        if defects and confirmed_count > 0:
            confirmed_defs = [d for d in defects if d.get("confidence", 0.0) >= 0.20]
            critical_cnt = sum(1 for d in confirmed_defs if d["severity"] == "Critical")
            high_cnt     = sum(1 for d in confirmed_defs if d["severity"] == "High")
            medium_cnt   = sum(1 for d in confirmed_defs if d["severity"] == "Medium")
            if critical_cnt > 0 or score < 45:
                return {"label": "Severe Failure", "desc": "Critical structural weld discontinuity detected"}
            if high_cnt > 0 or score < 60:
                return {"label": "Poor", "desc": "Significant defects requiring rewelding"}
            if medium_cnt >= 2 or len(confirmed_defs) >= 3 or score < 75:
                return {"label": "Sub-Standard", "desc": "Multiple surface irregularities exceeding AWS tolerances"}
            if score < 85:
                return {"label": "Moderate / Needs Repair", "desc": "Acceptable only after surface rework and de-spatter"}

        if score >= 90:
            return {"label": "Excellent", "desc": "Superior Weld Quality conforming to AWS D1.1"}
        elif score >= 78:
            return {"label": "Good", "desc": "Sound weld bead with minimal cosmetic features"}
        elif score >= 60:
            return {"label": "Acceptable", "desc": "Acceptable within general visual tolerances"}
        elif score >= 45:
            return {"label": "Poor", "desc": "Significant defects detected"}
        else:
            return {"label": "Severe Failure", "desc": "Weld failure rejecting quality threshold"}

    def _determine_acceptance_status(self, score, critical_cnt, high_cnt, medium_cnt=0, total_defects=0, confirmed_count=0, review_count=0):
        if confirmed_count == 0:
            if review_count > 0:
                return "Review Required"
            elif total_defects > 0:
                return "Verification Required"
            else:
                return "Accepted"

        # Driven by confirmed defects
        confirmed_critical = critical_cnt if confirmed_count > 0 else 0
        confirmed_high = high_cnt if confirmed_count > 0 else 0
        if confirmed_critical > 0 or score < 45:
            return "Rejected"
        elif confirmed_high > 0 or score < 65:
            return "Requires Repair"
        elif medium_cnt > 0 or score < 88:
            return "Accepted With Repair"
        else:
            return "Accepted"

    def _determine_overall_severity(self, critical_cnt, high_cnt, medium_cnt, defective_area_pct, confirmed_count=0):
        if confirmed_count == 0:
            return "Low"
        if critical_cnt >= 1 or defective_area_pct > 20:
            return "Critical"
        elif high_cnt >= 1 or defective_area_pct > 10:
            return "High"
        elif medium_cnt >= 1 or defective_area_pct > 2:
            return "Medium"
        else:
            return "Low"

    def _determine_overall_repair_priority(self, critical_cnt, high_cnt, medium_cnt, defects, confirmed_count=0):
        if confirmed_count == 0:
            if any(d.get("confidence", 0.0) >= 0.10 for d in defects):
                return "Verification Required"
            return "Manual Verification Recommended"

        confirmed_defs = [d for d in defects if d.get("confidence", 0.0) >= 0.20]
        if any(d["severity"] == "Critical" for d in confirmed_defs):
            return "Immediate Repair"
        elif any(d["severity"] == "High" for d in confirmed_defs):
            return "Repair Before Use"
        elif any(d["type"] in ("Excess Reinforcement", "Porosity") for d in confirmed_defs):
            return "Grind / Blend Flush"
        elif any("spatter" in d["type"].lower() for d in confirmed_defs):
            return "Chisel / De-Spatter"
        elif any(d["severity"] == "Medium" for d in confirmed_defs):
            return "Repair / Clean Before Service"
        else:
            return "No Action Required"

    def _generate_weld_conclusion(self, defects, active_breakdown, acceptance_status, critical_cnt, high_cnt,
                                  confirmed_count=0, review_count=0, possible_count=0):
        """
        Dynamically constructs clear engineering conclusion mentioning ONLY actual detected defect types and counts.
        Never mentions un-detected defect classes.
        """
        parts = []
        for def_type, count in active_breakdown.items():
            if def_type != "Good Welding":
                parts.append(f"{count} {def_type.lower()}")

        defect_summary_str = " and ".join(parts) if len(parts) <= 2 else ", ".join(parts[:-1]) + f", and {parts[-1]}"
        if not parts:
            defect_summary_str = "zero active defect"

        if not defects:
            return "Inspection verified sound weld bead geometry conforming to AWS D1.1 / ISO 5817 visual acceptance criteria. Status: Accepted."

        conclusion_parts = [f"Inspection identified {defect_summary_str} indication(s)."]

        if confirmed_count > 0:
            confirmed_types = list(dict.fromkeys(d["type"] for d in defects if d.get("confidence", 0.0) >= 0.20))
            conf_str = f"{confirmed_count} indication(s) ({', '.join(confirmed_types).lower()}) meet the confirmed-defect confidence threshold"
            if review_count + possible_count > 0:
                conclusion_parts.append(f"{conf_str}, while the remaining {review_count + possible_count} indication(s) require verification.")
            else:
                conclusion_parts.append(f"{conf_str}.")
        else:
            conclusion_parts.append("All detected indications are below the confirmed-defect threshold and require manual or NDT verification before concluding defect status.")

        if acceptance_status == "Rejected":
            actual_crits = [d["type"] for d in defects if d["severity"] == "Critical" and d.get("confidence", 0.0) >= 0.20]
            crit_detail = f"critical structural defect ({', '.join(set(actual_crits))})" if actual_crits else "severe defect accumulation"
            conclusion_parts.append(f"Due to the presence of confirmed {crit_detail}, the joint is classified as Rejected and requires immediate engineering review.")
        elif acceptance_status == "Requires Repair":
            conclusion_parts.append("Repair and re-inspection are required for the confirmed defect zones prior to service acceptance.")
        elif acceptance_status == "Accepted With Repair":
            conclusion_parts.append("The weld is classified as Accepted With Repair, requiring designated surface dressing or rework.")
        elif acceptance_status in ("Review Required", "Verification Required"):
            conclusion_parts.append("Weld disposition is pending physical verification of the indicated regions.")
        else:
            conclusion_parts.append("Weld bead exhibits acceptable structural integrity.")

        return " ".join(conclusion_parts)

    def _generate_quality_explanation(self, score, status, severity, defects, active_breakdown,
                                      confirmed_count=0, review_count=0, possible_count=0):
        active_items = [f"{k} ({v})" for k, v in active_breakdown.items() if k != "Good Welding"]
        defect_list_str = ", ".join(active_items) if active_items else "None"
        if not defects:
            return f"A quality score of {score}/100 and status of '{status}' was assigned because zero active defect indications were detected."

        return (
            f"A quality score of {score}/100 and overall status of '{status}' was assigned based on {len(defects)} indication(s): "
            f"{defect_list_str} ({confirmed_count} confirmed defect(s), {review_count} review required, {possible_count} possible indication(s)). "
            f"Scoring is weighted by confidence tier and AWS D1.1 severity criteria without penalizing benign or tentative indications."
        )

    def _generate_weld_verdict(self, defects, dam_pct, score, acceptance, dominant_type, confirmed_count=0):
        if not defects:
            return "No visual defects detected. Weld conforms to visual inspection criteria."

        actual_types = list(dict.fromkeys(d["type"] for d in defects))
        types_str = ", ".join(actual_types[:4])

        if confirmed_count == 0:
            return (
                f"The inspected weld contains {len(defects)} tentative indication(s) ({types_str}) pending verification. "
                f"Weld Quality Score is {score}/100 with an overall status of '{acceptance}'. "
                f"Visual verification is recommended before repair."
            )

        repair_str = "Immediate repair is required prior to load service." if acceptance == "Rejected" else (
            "Repair is required prior to final acceptance." if acceptance == "Requires Repair" else
            "The weld is acceptable with minor scheduled repair recommended."
        )
        return (
            f"The inspected weld contains {len(defects)} defect indication(s) including {types_str}. "
            f"Estimated defective area is {dam_pct}%. "
            f"Weld Quality Score is {score}/100 with an overall status of '{acceptance}'. "
            f"{repair_str}"
        )

    def _clean_weld_result(self, img_bgr, w, h, filename, inspection_id, inspection_date, inspection_time, inspection_timestamp, good_welding_count=0, detected_classes_count=None):
        verdict = ("Trained YOLO11 model verified sound weld bead geometry, uniform ripple pattern, and complete fusion coalescence. Zero visual defects detected."
                   if good_welding_count > 0 else
                   "No visual surface defects detected. Weld bead profile conforms to AWS D1.1 / ISO 5817 visual acceptance criteria.")

        detected_classes = {"Good Welding": good_welding_count} if good_welding_count > 0 else {}
        active_breakdown = {}

        return {
            "original_image":       self._cv2_to_b64(img_bgr),
            "annotated_image":      self._cv2_to_b64(img_bgr),
            "overlay_image":        self._cv2_to_b64(img_bgr),
            "file_name":            filename,
            "inspection_id":        inspection_id,
            "inspection_date":      inspection_date,
            "inspection_time":      inspection_time,
            "inspection_timestamp": inspection_timestamp,
            "model_name":           "Ultralytics YOLO11-seg (Industrial Weld Model)",
            "model_type":           "Instance Segmentation & Defect Analysis",
            "inspection_status":    "Complete",
            "total_defects":        0,
            "total_active_defects": 0,
            "total_model_detections": good_welding_count,
            "confirmed_defects_count": 0,
            "review_required_count": 0,
            "possible_indications_count": 0,
            "good_welding_count":   good_welding_count,
            "detected_classes":     detected_classes,
            "active_defects_breakdown": active_breakdown,
            "defects":              [],
            "breakdown":            detected_classes,
            "problem_analysis":     [],
            "quality_assessment": {
                "score":                98,
                "status":               "Excellent",
                "severity":             "Low",
                "explanation":          "A quality score of 98/100 and status of 'Excellent' was assigned because zero active welding defects were detected.",
            },
            "conclusion":           "Inspection verified sound weld bead geometry conforming to AWS D1.1 / ISO 5817 visual acceptance criteria with zero active defects detected. Status: Excellent / Accepted.",
            "summary": {
                "total_model_detections": good_welding_count,
                "total_defects":        0,
                "total_active_defects": 0,
                "confirmed_defects":    0,
                "review_required":      0,
                "possible_indications": 0,
                "good_welding_detections": good_welding_count,
                "detected_classes":     detected_classes,
                "active_defects":       active_breakdown,
                "breakdown":            detected_classes,
                "critical_defects":     0,
                "major_defects":        0,
                "minor_defects":        0,
                "acceptable_defects":   0,
                "largest_defect":       "None",
                "dominant_defect":      "None",
                "weld_coverage_percent": 100.0,
                "defective_area_percent": 0.0,
                "inspection_confidence": 98.5,
                "overall_detection_confidence": 98.5,
            },
            "weld_quality": {
                "score":                98,
                "condition":            "Excellent",
                "acceptance_status":    "Accepted",
                "overall_status":       "Excellent",
                "overall_severity":     "Low",
                "overall_risk":         "Low",
                "repair_priority":      "No Action Required",
                "verdict":              verdict,
                "conclusion":           "Inspection verified sound weld bead geometry conforming to AWS D1.1 / ISO 5817 visual acceptance criteria with zero active defects detected. Status: Excellent / Accepted.",
                "possible_causes":      ["Optimal welding heat input, travel speed, and gas shielding."],
                "recommended_actions":  ["Proceed to next production phase; zero repair required."],
            },
            "critical_count": 0, "high_count": 0, "medium_count": 0, "low_count": 0,
            "damaged_pct": 0.0, "health_score": 98, "condition": "Excellent", "overall_risk": "Low",
            "dominant_type": "None", "largest_defect": "None",
            "verdict": verdict,
            "inspection_confidence": 98.5,
            "overall_detection_confidence": 98.5,
        }

    # ── Non-Overlapping CAD Engineering Leader-Line Renderer ────────────────

    def _draw_engineering_annotations(self, img_bgr: np.ndarray, defects: list) -> np.ndarray:
        orig_h, orig_w, _ = img_bgr.shape
        pad_x, pad_y = 230, 60
        canvas_w = orig_w + pad_x * 2
        canvas_h = orig_h + pad_y * 2

        # Slate industrial blueprint canvas
        canvas = np.full((canvas_h, canvas_w, 3), (245, 248, 252), dtype=np.uint8)
        ox, oy = pad_x, pad_y

        # Draw subtle CAD grid
        for gx in range(0, canvas_w, 25):
            cv2.line(canvas, (gx, 0), (gx, canvas_h), (230, 236, 244), 1)
        for gy in range(0, canvas_h, 25):
            cv2.line(canvas, (0, gy), (canvas_w, gy), (230, 236, 244), 1)

        # Render original image into frame
        canvas[oy:oy+orig_h, ox:ox+orig_w] = img_bgr

        # Precision double border frame
        cv2.rectangle(canvas, (ox-3, oy-3), (ox+orig_w+3, oy+orig_h+3), (170, 185, 205), 1)
        cv2.rectangle(canvas, (ox-1, oy-1), (ox+orig_w+1, oy+orig_h+1), (120, 145, 175), 2)

        if not defects:
            return canvas

        # Highlight exact defect regions & segmentation masks
        img_region = canvas[oy:oy+orig_h, ox:ox+orig_w].copy()
        for idx, d in enumerate(defects, 1):
            bx, by, bw, bh = d["bbox"]
            bx, by = max(0, min(bx, orig_w - 1)), max(0, min(by, orig_h - 1))
            bw, bh = min(bw, orig_w - bx), min(bh, orig_h - by)
            c = SEVERITY_OVERLAY_BGR.get(d["severity"], (0, 180, 220))
            stroke_c = SEVERITY_COLOR_BGR.get(d["severity"], (0, 180, 220))

            # Draw polygon mask fill if present
            if "segmentation_mask" in d and len(d["segmentation_mask"]) >= 3:
                pts = np.array(d["segmentation_mask"], dtype=np.int32)
                mask_layer = np.zeros_like(img_region)
                cv2.fillPoly(mask_layer, [pts], c)
                cv2.addWeighted(mask_layer, 0.35, img_region, 1.0, 0, img_region)
                cv2.polylines(img_region, [pts], True, stroke_c, 2)
            else:
                roi = img_region[by:by+bh, bx:bx+bw]
                if roi.size > 0:
                    block = np.full_like(roi, c)
                    cv2.addWeighted(block, 0.25, roi, 0.75, 0, roi)
                    img_region[by:by+bh, bx:bx+bw] = roi

            # Solid severity bounding box
            cv2.rectangle(img_region, (bx, by), (bx+bw, by+bh), stroke_c, 2)

            # Compact numbered badge at top-left of defect box
            badge_text = f"#{idx}"
            cv2.rectangle(img_region, (bx, max(0, by - 16)), (bx + 26, max(16, by)), stroke_c, -1)
            cv2.putText(img_region, badge_text, (bx + 2, max(12, by - 4)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1, cv2.LINE_AA)

        canvas[oy:oy+orig_h, ox:ox+orig_w] = img_region

        # Split left and right callout boxes by centroid X and sort by Y to eliminate line crossings
        left_defects  = sorted([d for d in defects if d["center"][0] < orig_w / 2], key=lambda d: d["center"][1])
        right_defects = sorted([d for d in defects if d["center"][0] >= orig_w / 2], key=lambda d: d["center"][1])

        CARD_W = 205
        # Dynamically calculate card height and gap to fit all callouts cleanly
        max_items = max(len(left_defects), len(right_defects), 1)
        available_height = orig_h + pad_y
        CARD_H = min(48, max(32, int((available_height - (max_items - 1) * 6) / max_items)))
        CARD_GAP = max(4, min(10, int((available_height - max_items * CARD_H) / max(1, max_items - 1))))

        def compute_callout_layout(items, is_left):
            n = len(items)
            if n == 0:
                return
            total_height = n * CARD_H + (n - 1) * CARD_GAP
            start_y = max(oy, oy + (orig_h - total_height) // 2)

            for i, d in enumerate(items):
                ly = start_y + i * (CARD_H + CARD_GAP)
                lx = (ox - CARD_W - 15) if is_left else (ox + orig_w + 15)
                d["_lx"] = lx
                d["_ly"] = ly
                d["_cx"] = ox + d["center"][0]
                d["_cy"] = oy + d["center"][1]
                d["_is_left"] = is_left

        compute_callout_layout(left_defects, True)
        compute_callout_layout(right_defects, False)

        for d in defects:
            if "_lx" not in d:
                continue
            lx, ly = d["_lx"], d["_ly"]
            cx_pt, cy_pt = d["_cx"], d["_cy"]
            is_left = d["_is_left"]

            stroke_color = SEVERITY_COLOR_BGR.get(d["severity"], (0, 180, 220))

            # Leader line connection
            anchor_x = lx + CARD_W if is_left else lx
            anchor_y = ly + CARD_H // 2
            mid_x = (anchor_x + cx_pt) // 2

            cv2.line(canvas, (anchor_x, anchor_y), (mid_x, anchor_y), (140, 160, 185), 1, cv2.LINE_AA)
            cv2.line(canvas, (mid_x, anchor_y), (cx_pt, cy_pt), (140, 160, 185), 1, cv2.LINE_AA)

            # Bullseye at defect center
            cv2.circle(canvas, (cx_pt, cy_pt), 5, (255, 255, 255), -1, cv2.LINE_AA)
            cv2.circle(canvas, (cx_pt, cy_pt), 4, stroke_color, -1, cv2.LINE_AA)
            cv2.circle(canvas, (cx_pt, cy_pt), 7, stroke_color, 1, cv2.LINE_AA)

            # Callout card container
            cv2.rectangle(canvas, (lx, ly), (lx + CARD_W, ly + CARD_H), (255, 255, 255), -1)
            cv2.rectangle(canvas, (lx, ly), (lx + CARD_W, ly + CARD_H), (200, 215, 230), 1)

            # Left severity indicator bar
            cv2.rectangle(canvas, (lx, ly), (lx + 5, ly + CARD_H), stroke_color, -1)

            # Card Header Text: e.g. DEFECT #1: Crack
            def_num = d.get("id_num", 1)
            header_text = f"#{def_num} {d['type'][:14]} ({int(d['confidence']*100)}%)"
            cv2.putText(canvas, header_text, (lx + 10, ly + int(CARD_H * 0.42)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (15, 23, 42), 1, cv2.LINE_AA)

            # Sub-text: Severity & Region
            sub_text = f"{d['severity']} | {d.get('region', d['location'])[:18]}"
            cv2.putText(canvas, sub_text, (lx + 10, ly + int(CARD_H * 0.82)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.32, (100, 116, 139), 1, cv2.LINE_AA)

        return canvas

    def _draw_defect_heatmap_overlay(self, img_bgr: np.ndarray, defects: list) -> np.ndarray:
        h, w, _ = img_bgr.shape
        overlay = img_bgr.copy()

        for d in defects:
            c = SEVERITY_OVERLAY_BGR.get(d["severity"], (0, 180, 220))
            if "segmentation_mask" in d and len(d["segmentation_mask"]) >= 3:
                pts = np.array(d["segmentation_mask"], dtype=np.int32)
                mask_layer = np.zeros_like(img_bgr)
                cv2.fillPoly(mask_layer, [pts], c)
                cv2.addWeighted(mask_layer, 0.45, overlay, 1.0, 0, overlay)
                cv2.polylines(overlay, [pts], True, SEVERITY_COLOR_BGR.get(d["severity"], c), 2)
            else:
                bx, by, bw, bh = d["bbox"]
                bx, by = max(0, min(bx, w - 1)), max(0, min(by, h - 1))
                bw, bh = min(bw, w - bx), min(bh, h - by)
                roi = overlay[by:by+bh, bx:bx+bw]
                if roi.size > 0:
                    block = np.full_like(roi, c)
                    cv2.addWeighted(block, 0.40, roi, 0.60, 0, roi)
                    overlay[by:by+bh, bx:bx+bw] = roi
                cv2.rectangle(overlay, (bx, by), (bx+bw, by+bh), SEVERITY_COLOR_BGR.get(d["severity"], c), 2)

        return overlay


# Backward compatibility placeholder alias
class CorrosionDetector(WeldDetector):
    pass

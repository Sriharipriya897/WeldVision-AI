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


# ─── Welding Defect Engineering Knowledge Base & Metadata (12 Classes) ────────

WELD_DEFECT_METADATA = {
    "Slag Inclusion": {
        "severity": "High",
        "status": "Requires Repair",
        "problem": "Entrapped non-metallic solid slag particles within the weld deposit or along the fusion zone interface.",
        "why_defect": "Forms internal discontinuities that weaken the effective weld cross-section and create stress risers prone to failure.",
        "possible_cause": "Low amperage, improper welding technique, or slow travel rate allowing slag to run ahead of the weld pool (Ref: Welding Defects Manual).",
        "recommended_action": "Mechanically remove slag by grinding or other mechanical process, increase amperage and travel rate, and re-weld adhering to qualified WPS.",
        "repair_priority": "Repair Before Use",
        "explain": "Non-metallic solid material entrapped in weld metal or between weld metal and base metal.",
    },
    "Undercut": {
        "severity": "High",
        "status": "Requires Repair",
        "problem": "Groove or channel melted into base metal adjacent to weld toe or root and left unfilled by weld metal.",
        "why_defect": "Reduces parent plate thickness at high-stress transition zones and acts as severe fatigue crack initiation site.",
        "possible_cause": "High amperage, wrong electrode angle, excessive arc length, or rust on joint surface (Ref: Welding Defects Manual).",
        "recommended_action": "Set machine on scrap metal to correct parameters, clean metal before welding, and weld repair pass with smaller electrode (low hydrogen with preheat).",
        "repair_priority": "Repair Before Use",
        "explain": "Groove melted into base metal adjacent to weld toe along outer boundary.",
    },
    "Porosity": {
        "severity": "High",
        "status": "Requires Repair",
        "problem": "Porous spherical gas cavities or void cluster entrapped within the solidifying weld metal.",
        "why_defect": "Reduces effective cross-sectional density and acts as internal stress concentration points, degrading tensile and fatigue strength.",
        "possible_cause": "Atmospheric gas entrapment, moisture/grease/rust on joint faces, or inadequate shielding gas flow/drafty environment (Ref: Welding Defects Manual).",
        "recommended_action": "Mechanically grind out porous weld bead region down to sound metal, ensure dry shielded atmosphere and correct gas flow, and deposit sound repair pass.",
        "repair_priority": "Repair Before Use",
        "explain": "Gas cavity or spherical void cluster trapped during solidification detected by YOLO11 segmentation mask.",
    },
    "Incomplete Fusion": {
        "severity": "Critical",
        "status": "Rejected",
        "problem": "Lack of coalescence between adjacent weld passes or between weld metal and base metal along joint interface.",
        "why_defect": "Forms un-fused planar boundary plane causing sudden joint separation under shear or tensile stress.",
        "possible_cause": "Low amperage, steep electrode angle, fast travel speed, short arc gap, lack of preheat, electrode too small, unclean base metal, or arc off seam (Ref: Welding Defects Manual).",
        "recommended_action": "Remove defective section completely by grinding or mechanical process and re-weld adhering strictly to qualified WPS.",
        "repair_priority": "Immediate Repair",
        "explain": "Planar discontinuity along weld toe/sidewall where weld metal failed to coalesce with base metal.",
    },
    "Overlap": {
        "severity": "Medium",
        "status": "Accepted With Repair",
        "problem": "Protrusion of weld metal beyond weld toe or weld root without fusion to base metal surface (contour problem).",
        "why_defect": "Forms abrupt mechanical notch at weld toe creating stress concentration and fatigue cracking vulnerability.",
        "possible_cause": "Improper welding technique, steep electrode angle, or fast travel speed causing weld metal rollover (Ref: Welding Defects Manual).",
        "recommended_action": "Overlap is a contour problem; grind excess protruding weld metal flush to parent plate contour without gouging base metal.",
        "repair_priority": "Repair Before Use",
        "explain": "Protrusion of weld metal beyond weld toe without fusion to base plate.",
    },
    "Underfill": {
        "severity": "High",
        "status": "Requires Repair",
        "problem": "Depression on weld face or root surface extending below adjacent surface of base metal.",
        "why_defect": "Reduces effective design throat thickness of welded joint below specified engineering limits.",
        "possible_cause": "Improper welding techniques, insufficient filler metal deposition, or incorrect travel speed (Ref: Welding Defects Manual).",
        "recommended_action": "Apply proper welding techniques for weld type & position; use stripper beads before cover pass; grind and weld to fill.",
        "repair_priority": "Repair Before Use",
        "explain": "Depression on weld face or root extending below adjacent parent plate surface.",
    },
    "Spatter": {
        "severity": "Medium",
        "status": "Repair Recommended",
        "problem": "Molten metal globules expelled from welding arc scattered across weld face and adjacent base plate.",
        "why_defect": "Can mask underlying micro-cracks, interfere with non-destructive testing (NDT), impair protective coatings, and initiate localized corrosion.",
        "possible_cause": "High arc power, magnetic arc blow, damp electrodes, or improper shielding gas (Ref: Welding Defects Manual).",
        "recommended_action": "Reduce arc power and arc length, use dry electrodes, and remove spatter by mechanical process (chipping hammer, wire brush).",
        "repair_priority": "Clean / De-spatter",
        "explain": "Molten metal droplets expelled from welding arc scattered across adjacent plate surface.",
    },
    "Excessive Convexity": {
        "severity": "Medium",
        "status": "Accepted With Repair",
        "problem": "Convexity of a fillet weld face exceeding allowable code profile limits.",
        "why_defect": "Produces sharp transition notch at weld toes, creating stress concentrations that reduce fatigue strength.",
        "possible_cause": "Incompatible amperage and travel speed (excessive deposition rate with slow travel speed) (Ref: Welding Defects Manual).",
        "recommended_action": "Observe proper parameters & techniques; mechanically dress and grind convexity to blend smoothly into base metal.",
        "repair_priority": "Repair Before Use",
        "explain": "Fillet weld face profile exhibiting excessive outward curvature beyond allowable code limits.",
    },
    "Excessive Concavity": {
        "severity": "High",
        "status": "Requires Repair",
        "problem": "Concave fillet weld face profile resulting in deficient effective throat thickness.",
        "why_defect": "Reduces effective throat cross-section, leading to joint failure under shear and tensile loading.",
        "possible_cause": "Excessive arc voltage, improper travel speed, or excessive heat input sucking puddle inward (Ref: Welding Defects Manual).",
        "recommended_action": "Observe proper parameters & techniques; deposit additional weld pass to achieve required throat thickness.",
        "repair_priority": "Repair Before Use",
        "explain": "Weld face exhibiting excessive inward depression reducing effective joint throat.",
    },
    "Excessive Weld Reinforcement": {
        "severity": "Medium",
        "status": "Accepted With Repair",
        "problem": "Weld metal deposit on face or root of groove weld exceeding allowable reinforcement profile height.",
        "why_defect": "Creates abrupt geometric transitions and notch stress concentrations at weld toes, increasing fatigue vulnerability.",
        "possible_cause": "Travel speed too slow or amperage too low causing excessive crown buildup (Ref: Welding Defects Manual).",
        "recommended_action": "Set travel speed & amperage on scrap plate; remove excessive reinforcement and feather weld toes to smooth transition.",
        "repair_priority": "Repair Before Use",
        "explain": "Weld metal deposit on face or root exceeding allowable reinforcement profile height.",
    },
    "Incomplete Penetration": {
        "severity": "Critical",
        "status": "Rejected",
        "problem": "Joint penetration that is less than specified, leaving an unfilled joint root gap.",
        "why_defect": "Leaves an internal notch at root pass that drastically reduces tensile fatigue strength and promotes rapid cracking.",
        "possible_cause": "Low amperage, low preheat, tight root opening, fast travel speed, or short arc length (Ref: Welding Defects Manual).",
        "recommended_action": "Back gouge defective root pass to sound metal and back weld adhering strictly to qualified WPS.",
        "repair_priority": "Immediate Repair",
        "explain": "Unfilled gap detected at joint root due to incomplete weld penetration through joint thickness.",
    },
    "Excessive Penetration": {
        "severity": "High",
        "status": "Requires Repair",
        "problem": "Weld metal protruding excessively beyond root side of joint into interior cavity.",
        "why_defect": "Restricts internal fluid flow in piping, creates turbulence, and forms root notch stress concentrations.",
        "possible_cause": "Excessive heat input, root opening too wide, travel speed too slow, or excessively long arc (Ref: Welding Defects Manual).",
        "recommended_action": "Reduce current, narrow root opening, increase travel speed, and mechanically grind internal root protrusion flush.",
        "repair_priority": "Repair Before Use",
        "explain": "Excessive molten metal drop-through protruding past root side of joint.",
    },
    # Backward compatibility aliases
    "Excess Reinforcement": {
        "severity": "Medium",
        "status": "Accepted With Repair",
        "problem": "Weld metal deposit on face or root exceeding allowable reinforcement profile height.",
        "why_defect": "Creates abrupt geometric transitions and notch stress concentrations at weld toes.",
        "possible_cause": "Travel speed too slow or amperage too low causing excessive crown buildup.",
        "recommended_action": "Set travel speed & amperage on scrap plate; remove excessive reinforcement and feather weld toes.",
        "repair_priority": "Repair Before Use",
        "explain": "Weld metal deposit on face or root exceeding allowable reinforcement profile height.",
    },
    "Spatters": {
        "severity": "Medium",
        "status": "Repair Recommended",
        "problem": "Molten metal globules expelled from welding arc scattered across weld face and adjacent base plate.",
        "why_defect": "Can mask underlying micro-cracks and impair protective coatings.",
        "possible_cause": "High arc power, magnetic arc blow, damp electrodes, or improper shielding gas.",
        "recommended_action": "Reduce arc power and length, use dry electrodes, and remove spatter mechanically.",
        "repair_priority": "Clean / De-spatter",
        "explain": "Molten metal droplets expelled from welding arc scattered across adjacent plate surface.",
    },
    "Lack of Fusion": {
        "severity": "Critical",
        "status": "Rejected",
        "problem": "Lack of coalescence between adjacent weld passes or between weld metal and base metal.",
        "why_defect": "Forms un-fused planar boundary plane causing sudden joint separation.",
        "possible_cause": "Low amperage, steep electrode angle, fast travel speed, or lack of preheat.",
        "recommended_action": "Remove defective section completely and re-weld adhering strictly to WPS.",
        "repair_priority": "Immediate Repair",
        "explain": "Planar discontinuity along weld boundary where weld metal failed to coalesce.",
    },
    "Lack of Penetration": {
        "severity": "Critical",
        "status": "Rejected",
        "problem": "Joint penetration less than specified, leaving unfilled root gap.",
        "why_defect": "Leaves internal notch at root pass reducing fatigue strength.",
        "possible_cause": "Low amperage, tight root opening, fast travel speed, or short arc length.",
        "recommended_action": "Back gouge and back weld adhering to WPS.",
        "repair_priority": "Immediate Repair",
        "explain": "Unfilled gap at joint root due to incomplete weld penetration.",
    },
    "Good Welding": {
        "severity": "Low",
        "status": "Accepted",
        "problem": "None (Conforming Weld).",
        "why_defect": "Not a defect; conforms to standard acceptance criteria.",
        "possible_cause": "Optimal welding procedure specification (WPS) execution with balanced heat input and proper gas shielding.",
        "recommended_action": "No repair required; weld bead conforms to AWS D1.1 / ISO 5817 visual inspection criteria.",
        "repair_priority": "No Action Required",
        "explain": "Uniform bead width, smooth ripple profile, and sound metallurgical coalescence verified.",
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

# 12 Target Classes
CLASS_NAMES_12 = [
    "Slag Inclusion",
    "Undercut",
    "Porosity",
    "Incomplete Fusion",
    "Overlap",
    "Underfill",
    "Spatter",
    "Excessive Convexity",
    "Excessive Concavity",
    "Excessive Weld Reinforcement",
    "Incomplete Penetration",
    "Excessive Penetration"
]

CLASS_SEVERITY_MAP = {
    "Slag Inclusion": "High",
    "Undercut": "High",
    "Porosity": "High",
    "Incomplete Fusion": "Critical",
    "Overlap": "Medium",
    "Underfill": "High",
    "Spatter": "Medium",
    "Excessive Convexity": "Medium",
    "Excessive Concavity": "High",
    "Excessive Weld Reinforcement": "Medium",
    "Incomplete Penetration": "Critical",
    "Excessive Penetration": "High",
    # Aliases
    "Excess Reinforcement": "Medium",
    "Spatters": "Medium",
    "Lack of Fusion": "Critical",
    "Lack of Penetration": "Critical",
    "Good Welding": "Low",
}


# Configured inference thresholds
CONF_THRESHOLD = 0.25
IOU_THRESHOLD = 0.45

# ─── Centralized Visual Screening Score Bands ─────────────────────────────────
# Non-destructive demo screening bands (not certified welding acceptance criteria)
STATUS_BAND_NO_INDICATIONS = "No Significant Visual Indications Detected"  # 90–100
STATUS_BAND_REVIEW_REQUIRED = "Review Required"                             # 75–89
STATUS_BAND_SIGNIFICANT     = "Significant Indications — Detailed Review Required"  # 50–74
STATUS_BAND_HIGH_CONCERN    = "High Concern — Urgent Inspection Required"  # Below 50

# Configured severity base penalties for AI visual screening
SEVERITY_BASE_PENALTY = {
    "Critical": 32.0,
    "High":     18.0,
    "Medium":   10.0,
    "Low":      4.0
}



# ─── Main AI YOLO11 Segmentation Detector ─────────────────────────────────────

class WeldDetector(BaseDetector):
    """
    AI-Powered Weld Defect Detector using Ultralytics YOLO11 Segmentation.
    Loads real trained weights and inspects every detected defect without dropping.
    """

    def __init__(self, model_path: str = None):
        self.model_path = self._resolve_model_path(model_path)
        print(f"[WeldDetector] Loading YOLO11 segmentation weights: {self.model_path}")
        self.model = YOLO(self.model_path)
        self.device = 'cpu'
        print(f"[WeldDetector] YOLO11 model loaded successfully on device: {self.device} with {len(self.model.names)} classes")

    def _resolve_model_path(self, model_path: str = None) -> str:
        if model_path and os.path.exists(model_path):
            return str(Path(model_path).resolve())
        current_dir = Path(__file__).resolve().parent
        candidates = [
            current_dir / "models" / "best.pt",
            Path("backend/models/best.pt").resolve(),
            Path("models/best.pt").resolve(),
        ]
        for c in candidates:
            if c.exists():
                return str(c)
        raise FileNotFoundError(f"Trained model best.pt not found at {[str(c) for c in candidates]}")

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

    def _suppress_duplicate_detections(self, detections: list, iou_thresh: float = 0.45, overlap_thresh: float = 0.60) -> list:
        """
        Suppresses heavily overlapping or duplicate detections,
        keeping the higher confidence instance or the more complete segmentation.
        Prevents counting duplicate boxes or masks covering the same physical indication as separate defects.
        """
        if not detections or len(detections) <= 1:
            return detections

        # Sort descending by confidence
        sorted_dets = sorted(detections, key=lambda d: -d.get("confidence", 0.0))
        keep = []

        for d in sorted_dets:
            d_box = d["bbox"]  # [x, y, w, h]
            d_type = d["type"]
            d_cx, d_cy = d.get("center", [d_box[0] + d_box[2] // 2, d_box[1] + d_box[3] // 2])

            should_suppress = False
            for k in keep:
                k_box = k["bbox"]
                same_type = (k["type"] == d_type)

                # 1. Standard IoU & Overlap ratio
                xA = max(d_box[0], k_box[0])
                yA = max(d_box[1], k_box[1])
                xB = min(d_box[0] + d_box[2], k_box[0] + k_box[2])
                yB = min(d_box[1] + d_box[3], k_box[1] + k_box[3])

                inter_w = max(0, xB - xA)
                inter_h = max(0, yB - yA)
                inter_area = inter_w * inter_h

                k_cx, k_cy = k.get("center", [k_box[0] + k_box[2] // 2, k_box[1] + k_box[3] // 2])
                center_dist = ((d_cx - k_cx) ** 2 + (d_cy - k_cy) ** 2) ** 0.5
                diag_k = (k_box[2] ** 2 + k_box[3] ** 2) ** 0.5

                if inter_area > 0:
                    area_d = d_box[2] * d_box[3]
                    area_k = k_box[2] * k_box[3]
                    union_area = area_d + area_k - inter_area
                    iou = inter_area / float(union_area) if union_area > 0 else 0.0
                    overlap_ratio = inter_area / float(min(area_d, area_k)) if min(area_d, area_k) > 0 else 0.0

                    if same_type:
                        if iou >= iou_thresh or overlap_ratio >= overlap_thresh:
                            should_suppress = True
                            break
                    else:
                        # Cross-class duplicate suppression: if two boxes heavily cover the exact same physical indication, keep the higher confidence one
                        if iou >= 0.50 or overlap_ratio >= 0.65:
                            should_suppress = True
                            break

                # 2. Tight center proximity for small clustered spots of same type
                if same_type and center_dist < max(14, diag_k * 0.45):
                    should_suppress = True
                    break

                # Or cross-class duplicate where centers are practically identical (within 8 px) with positive overlap
                if not same_type and center_dist < 8 and inter_area > 0:
                    should_suppress = True
                    break

            if not should_suppress:
                keep.append(d)

        return keep

    # ── Main Analysis Pipeline ───────────────────────────────────────────

    def analyze(self, image_bytes: bytes, filename: str = "weld_specimen.jpg") -> dict:
        img_bgr = self._bytes_to_cv2(image_bytes)
        h, w, _ = img_bgr.shape

        # Run real YOLO11 Segmentation inference with balanced confidence and NMS settings
        results = self.model.predict(
            img_bgr,
            conf=CONF_THRESHOLD,
            iou=IOU_THRESHOLD,
            max_det=50,
            imgsz=640,
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
                if conf < CONF_THRESHOLD:
                    continue
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
                if conf >= 0.50:
                    conf_tier = "Confirmed Defect"
                    status_note = "High Confidence"
                else:
                    conf_tier = "Review Required"
                    status_note = "Medium Confidence"

                # Severity assignment
                sev = CLASS_SEVERITY_MAP.get(cls_name, "Medium")

                d_dict = self._build_defect_dict(
                    cid=cls_id,
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

        # Apply IoU and proximity deduplication to suppress redundant overlapping detections
        filtered_detections = self._suppress_duplicate_detections(raw_detections, iou_thresh=0.45, overlap_thresh=0.60)
        defects = sorted(filtered_detections, key=lambda d: (-d["confidence"], d["id_num"] if "id_num" in d else 0))

        if not defects:
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
        confirmed_defects_count = sum(1 for d in defects if d.get("confidence", 0.0) >= 0.50)
        review_required_count = sum(1 for d in defects if 0.30 <= d.get("confidence", 0.0) < 0.50)
        possible_indications_count = sum(1 for d in defects if d.get("confidence", 0.0) < 0.30)

        # Assign sequential IDs and populate dynamic image-specific analysis
        for idx, d in enumerate(defects, 1):
            d["id"] = f"WLD-{idx:03d}"
            d["id_num"] = idx
            meta = WELD_DEFECT_METADATA.get(d["type"], WELD_DEFECT_METADATA.get(d["type"].capitalize(), WELD_DEFECT_METADATA["Porosity"]))

            conf = d.get("confidence", 0.0)

            # Strict Confidence Tiers:
            # CONFIDENCE >= 50% -> Confirmed Defect
            # CONFIDENCE 30%–49.99% -> Review Required
            # CONFIDENCE < 30% -> Possible Indication
            if conf >= 0.50:
                d["confidence_tier"] = "Confirmed Defect"
                d["confidence_qualifier"] = "High-confidence" if conf >= 0.65 else "Moderate-confidence"
                d["status"] = meta["status"]
                d["repair_priority"] = meta["repair_priority"]
            elif conf >= 0.30:
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
        screening_status = self._determine_screening_status(quality_score, total_defects)
        acceptance_status = screening_status
        condition_info = self._get_condition_label(quality_score, defects)
        overall_severity = self._determine_overall_severity(
            critical_count, high_count, medium_count, defective_area_pct,
            score=quality_score, confirmed_count=confirmed_defects_count
        )
        overall_risk = overall_severity
        repair_priority = self._determine_overall_repair_priority(
            critical_count, high_count, medium_count, defects,
            score=quality_score, status=screening_status
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
            defects, active_breakdown, screening_status, critical_count, high_count,
            confirmed_count=confirmed_defects_count, review_count=review_required_count,
            possible_count=possible_indications_count, score=quality_score
        )
        quality_explanation = self._generate_quality_explanation(
            quality_score, screening_status, overall_severity, defects, active_breakdown,
            confirmed_count=confirmed_defects_count, review_count=review_required_count,
            possible_count=possible_indications_count, defective_area_pct=defective_area_pct
        )
        verdict = self._generate_weld_verdict(
            defects, defective_area_pct, quality_score, screening_status, dominant_type,
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
            "twelve_class_inspection": self._build_12_class_inspection(defects),
            "total_detected_indications": total_active_defects,
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

    def _build_12_class_inspection(self, defects: list) -> list:
        """
        Builds inspection cards ONLY for the actual detected defect classes.
        Classes with zero detections are omitted per inspection filtering rules.
        """
        if not defects:
            return []

        alias_map = {
            "Excess Reinforcement": "Excessive Weld Reinforcement",
            "Spatters": "Spatter",
            "Lack of Fusion": "Incomplete Fusion",
            "Lack of Penetration": "Incomplete Penetration"
        }

        dets_by_class = {}
        for d in defects:
            raw_cname = d.get("class_name", d.get("type", ""))
            cname = alias_map.get(raw_cname, raw_cname)
            if cname not in dets_by_class:
                dets_by_class[cname] = []
            dets_by_class[cname].append(d)

        cards = []
        for cname, class_dets in dets_by_class.items():
            if not class_dets:
                continue
            top_det = max(class_dets, key=lambda d: d.get("confidence", 0.0))
            conf_val = top_det.get("confidence", 0.0)
            conf_pct = int(round(conf_val * 100))
            
            if conf_val >= 0.50:
                status_str = "DETECTED"
                sev_tier = top_det.get("severity", CLASS_SEVERITY_MAP.get(cname, "High"))
            else:
                status_str = "DETECTED (Review Required)"
                sev_tier = "Review Required"

            obs = top_det.get("observation") or f"Localized {cname.lower()} indications identified in the weld region."
            meta = WELD_DEFECT_METADATA.get(cname, {})
            explain = meta.get("explain", f"{cname} discontinuity detected in weld.")
            causes = top_det.get("possible_cause") or meta.get("possible_cause", "Welding parameters or atmospheric conditions.")
            rec = top_det.get("recommended_action") or meta.get("recommended_action", "Visually verify the indicated region and perform NDT when required.")

            card = {
                "class_name": cname,
                "category": "detected",
                "status_type": "detected",
                "status": status_str,
                "confidence": conf_pct,
                "confidence_raw": conf_val,
                "count": len(class_dets),
                "severity": sev_tier,
                "location": top_det.get("location", top_det.get("region", "Weld region")),
                "observation": _clean_svg_text(obs),
                "explanation": explain,
                "possible_causes": _clean_svg_text(causes),
                "recommendation": _clean_svg_text(rec),
                "bbox": top_det.get("bbox"),
                "detections": class_dets
            }
            cards.append(card)

        # Sort descending by top confidence
        cards.sort(key=lambda c: -c["confidence_raw"])
        return cards

    def _build_defect_dict(self, cid, dtype, sev, x, y, cw, ch, pct, conf, img_w, img_h, mask_pts=None):
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
            "class_id": int(cid),
            "class_name": dtype,
            "type": dtype,
            "defect_name": dtype,
            "severity": sev,
            "bbox": [int(x), int(y), int(cw), int(ch)],
            "mask": mask_pts or [],
            "segmentation_mask": mask_pts or [],
            "center": [cx, cy],
            "area_pct": round(float(pct), 2),
            "area_percent": round(float(pct), 2),
            "confidence": round(float(conf), 3),
            "confidence_pct": int(round(conf * 100)),
            "region": region_str,
            "location": region_str,
            "weld_zone": loc_str,
        }
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
                "recommended_action": "No corrective action required. Weld region exhibits acceptable visual profile (AI visual screening).",
            }

        # ── Build observation (specific to detection evidence, non-repetitive) ──
        mask_desc = f"with segmentation mask confirming a {size_desc.lower()} defect region ({area_pct}% of image area)" if has_mask else f"within a {size_desc.lower()} bounding box region ({area_pct}% of image area)"

        if conf < 0.30:
            # Possible indication (<30%)
            if rank == 0 or same_type_count == 1:
                observation = f"Possible low-confidence {dtype.lower()} indication detected in the {region.lower()} at {conf_pct}% confidence ({area_pct}% of image area)."
            else:
                observation = f"Possible low-confidence secondary {dtype.lower()} indication detected in the {region.lower()} at {conf_pct}% confidence."
        elif conf < 0.50:
            # Review required (30% - 49.99%)
            if rank == 0:
                observation = f"Review-required {dtype.lower()} indication detected in the {region.lower()}, representing approximately {area_pct}% of image area at {conf_pct}% confidence."
            else:
                primary = same_type_defs[0]
                is_smaller = area_pct < primary.get("area_pct", area_pct)
                comp_str = f"smaller than the primary {dtype.lower()} indication" if is_smaller else f"representing {area_pct}% of image area"
                observation = f"Review-required {dtype.lower()} indication detected in the {region.lower()}, {comp_str} at {conf_pct}% confidence."
        else:
            # Confirmed defect (>= 50%)
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

        if conf < 0.30:
            # For <30%: Do NOT show Rejected / Requires Repair / aggressive claims
            problem = f"Possible unconfirmed indication detected at {conf_pct}% AI confidence in the {region.lower()}. Visual verification by a certified inspector is required to confirm whether this represents a true discontinuity."
        elif conf < 0.50:
            # For 30-49.99%: Review required
            problem = f"Potential {dtype.lower()} indication identified at {conf_pct}% confidence in the {region.lower()}. Indication requires visual verification prior to finalizing joint quality classification."
        else:
            # For >=50%: Confirmed defect
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

        if conf < 0.30:
            possible_cause = f"Unconfirmed low-confidence indication ({conf_pct}%). Potential contributing factors if verified include: {base_cause}."
        elif conf < 0.40:
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

        if conf < 0.30:
            recommended_action = "Manual visual verification or appropriate NDT is recommended before any corrective action is taken."
        elif conf < 0.50:
            recommended_action = f"Review the indicated region in the {region.lower()} and verify visual/NDT indications before repair."
        else:
            # Confirmed defect (>= 50%)
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
        Dynamically calculates the AI visual screening quality score from the final filtered YOLO detections.
        Penalizes score according to:
          - indication count (number of defects)
          - detection confidence
          - estimated affected area (area_pct)
          - configured severity weights (Critical > High > Medium > Low)
          - multi-defect compounding
        Does not treat low confidence as proof of a sound weld.
        Never assigns >=90 if any defect indication is detected.
        """
        if not defects:
            return 98

        num_defects = len(defects)
        total_ind_penalty = 0.0

        for d in defects:
            sev = d.get("severity", "Medium")
            base_p = SEVERITY_BASE_PENALTY.get(sev, 10.0)
            conf = float(d.get("confidence", 0.50))
            # Confidence weighting factor: scales smoothly from 0.70 at conf=0.25 to 1.0 at conf=1.0.
            # Ensures low-confidence detections still incur ~70-75% of base penalty (not ignored).
            conf_weight = 0.60 + 0.40 * max(0.0, min(1.0, conf))
            total_ind_penalty += base_p * conf_weight

        # Affected area penalty
        tot_area = sum(float(d.get("area_pct", 0.0)) for d in defects)
        area_penalty = min(20.0, tot_area * 1.5)

        # Multi-defect compounding penalty (each additional indication compounds the risk)
        multi_penalty = min(18.0, (num_defects - 1) * 3.0) if num_defects > 1 else 0.0

        total_penalty = total_ind_penalty + area_penalty + multi_penalty
        score = 100.0 - total_penalty

        # Safety & Threshold Rules:
        # 1. Any detected indication prevents classification in 90-100 band ("No Significant Visual Indications Detected")
        score = min(score, 89.0)

        # 2. Three or more indications represent significant cumulative visual concern -> max 74 (50-74 or lower)
        if num_defects >= 3:
            score = min(score, 74.0)

        # 3. Confirmed critical defect (conf >= 0.50) -> max 45 (must be in Below 50: High Concern)
        confirmed_crits = [d for d in defects if d.get("severity") == "Critical" and d.get("confidence", 0.0) >= 0.50]
        if confirmed_crits:
            score = min(score, 45.0)

        # 4. Two or more confirmed high/critical defects -> max 48
        confirmed_major = [d for d in defects if d.get("severity") in ("Critical", "High") and d.get("confidence", 0.0) >= 0.50]
        if len(confirmed_major) >= 2:
            score = min(score, 48.0)

        final_score = int(round(score))
        return max(5, min(98, final_score))

    def _determine_screening_status(self, score: int, total_defects: int = 0) -> str:
        """
        Centralized screening score bands:
          90–100: No Significant Visual Indications Detected
          75–89:  Review Required
          50–74:  Significant Indications — Detailed Review Required
          < 50:   High Concern — Urgent Inspection Required
        """
        if total_defects == 0 or score >= 90:
            return STATUS_BAND_NO_INDICATIONS
        elif score >= 75:
            return STATUS_BAND_REVIEW_REQUIRED
        elif score >= 50:
            return STATUS_BAND_SIGNIFICANT
        else:
            return STATUS_BAND_HIGH_CONCERN

    def _get_condition_label(self, score, defects=None):
        if not defects or score >= 90:
            return {"label": "Nominal", "desc": "Clean weld bead with no significant visual indications detected"}
        elif score >= 75:
            return {"label": "Review Required", "desc": "Visual indications detected requiring inspector verification"}
        elif score >= 50:
            return {"label": "Significant Indications", "desc": "Multiple or significant defect indications requiring detailed review"}
        else:
            return {"label": "High Concern", "desc": "Critical defect indications or high indication density requiring urgent inspection"}

    def _determine_acceptance_status(self, score, critical_cnt=0, high_cnt=0, medium_cnt=0, total_defects=0, **kwargs):
        """Backward-compatibility wrapper pointing directly to centralized status bands."""
        return self._determine_screening_status(score, total_defects)

    def _determine_overall_severity(self, critical_cnt, high_cnt, medium_cnt, defective_area_pct, score=100, confirmed_count=0):
        if critical_cnt >= 1 or score < 50 or defective_area_pct > 20:
            return "Critical"
        elif high_cnt >= 1 or score < 75 or defective_area_pct > 10:
            return "High"
        elif medium_cnt >= 1 or score < 90 or defective_area_pct > 2:
            return "Medium"
        else:
            return "Low"

    def _determine_overall_repair_priority(self, critical_cnt, high_cnt, medium_cnt, defects, score=100, status=""):
        if not defects:
            return "No Action Required"

        if status == STATUS_BAND_HIGH_CONCERN or score < 50 or critical_cnt > 0:
            confirmed_crits = [d for d in defects if d.get("severity") == "Critical" and d.get("confidence", 0.0) >= 0.50]
            if confirmed_crits:
                return "Immediate Repair"
            return "Urgent Inspection Required"

        if status == STATUS_BAND_SIGNIFICANT or score < 75 or high_cnt > 0:
            confirmed_high = [d for d in defects if d.get("severity") == "High" and d.get("confidence", 0.0) >= 0.50]
            if confirmed_high:
                return "Repair Before Use"
            return "Detailed Review Required"

        if status == STATUS_BAND_REVIEW_REQUIRED or score < 90:
            return "Verification Required"

        return "No Action Required"

    def _generate_weld_conclusion(self, defects, active_breakdown, acceptance_status, critical_cnt, high_cnt,
                                  confirmed_count=0, review_count=0, possible_count=0, score=100, **kwargs):
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
            return "AI visual screening identified no target defect indications in the inspected specimen. Final acceptance requires qualified inspection / CWI verification."

        conclusion_parts = [f"AI visual screening identified {defect_summary_str} indication(s) in the inspected specimen."]

        if confirmed_count > 0:
            confirmed_types = list(dict.fromkeys(d["type"] for d in defects if d.get("confidence", 0.0) >= 0.50))
            conf_str = f"{confirmed_count} indication(s) ({', '.join(confirmed_types).lower()}) meet the confirmed-defect confidence threshold (>=50%)"
            if review_count + possible_count > 0:
                conclusion_parts.append(f"{conf_str}, while {review_count + possible_count} indication(s) require inspector review/verification.")
            else:
                conclusion_parts.append(f"{conf_str}.")
        else:
            conclusion_parts.append("All detected indications are below the confirmed-defect confidence threshold (<50%) and require manual visual or NDT verification before concluding defect status.")

        # Map centralized status bands to engineering dispositions
        if acceptance_status == STATUS_BAND_HIGH_CONCERN:
            actual_crits = [d["type"] for d in defects if d["severity"] == "Critical" and d.get("confidence", 0.0) >= 0.50]
            crit_detail = f"critical discontinuity ({', '.join(set(actual_crits))})" if actual_crits else "high-density indication accumulation"
            conclusion_parts.append(f"The AI screening score of {score}/100 places this weld in the HIGH CONCERN band. Presence of {crit_detail} requires immediate engineering review and NDT verification before service.")
        elif acceptance_status == STATUS_BAND_SIGNIFICANT:
            conclusion_parts.append(f"The AI screening score of {score}/100 places this weld in the SIGNIFICANT INDICATIONS band. Detailed inspector review and targeted NDT verification are recommended before final disposition.")
        elif acceptance_status == STATUS_BAND_REVIEW_REQUIRED:
            conclusion_parts.append(f"The AI screening score of {score}/100 places this weld in the REVIEW REQUIRED band. Weld disposition is pending physical verification of the indicated regions by a qualified inspector.")
        else:
            conclusion_parts.append("Weld bead exhibits an acceptable visual profile per AI screening (score 90–100). Final acceptance requires qualified inspection / CWI verification.")

        conclusion_parts.append("This result is an AI visual screening only and does not constitute a certified weld-quality assessment or AWS D1.1 acceptance.")

        return " ".join(conclusion_parts)

    def _generate_quality_explanation(self, score, status, severity, defects, active_breakdown,
                                      confirmed_count=0, review_count=0, possible_count=0,
                                      defective_area_pct=0.0):
        active_items = [f"{k} ({v})" for k, v in active_breakdown.items() if k != "Good Welding"]
        defect_list_str = ", ".join(active_items) if active_items else "None"
        if not defects:
            return (f"AI visual screening score of {score}/100 was assigned because zero active defect indications "
                    f"were detected. Status: {status}.")

        area_note = f" Estimated defective area: {defective_area_pct:.1f}%." if defective_area_pct > 0 else ""
        return (
            f"AI visual screening score of {score}/100 (status: '{status}') was dynamically computed from "
            f"{len(defects)} indication(s): {defect_list_str} "
            f"({confirmed_count} confirmed >=50%, {review_count} review required, {possible_count} possible)."
            f"{area_note} Score is penalized by severity weight, detection confidence, affected area, and "
            f"multi-indication compounding. Score does not represent certified weld quality."
        )

    def _generate_weld_verdict(self, defects, dam_pct, score, acceptance, dominant_type, confirmed_count=0):
        if not defects:
            return "NO DEFECT INDICATIONS DETECTED. AI visual screening result — manual/CWI verification recommended."

        actual_types = list(dict.fromkeys(d["type"] for d in defects))
        types_str = ", ".join(actual_types[:4])

        if acceptance == STATUS_BAND_NO_INDICATIONS:
            return (
                f"AI screening detected {len(defects)} low-confidence indication(s) ({types_str}). "
                f"Screening score is {score}/100. Visual verification recommended before final acceptance."
            )

        if acceptance == STATUS_BAND_REVIEW_REQUIRED:
            return (
                f"The inspected weld contains {len(defects)} indication(s) ({types_str}) requiring inspector review. "
                f"AI visual screening score: {score}/100. "
                f"Physical verification of indicated regions by a qualified inspector is required before disposition."
            )

        if acceptance == STATUS_BAND_SIGNIFICANT:
            return (
                f"The inspected weld contains {len(defects)} significant indication(s) including {types_str}. "
                f"Estimated defective area: {dam_pct:.1f}%. AI screening score: {score}/100. "
                f"Detailed review and targeted NDT are recommended before acceptance."
            )

        # STATUS_BAND_HIGH_CONCERN
        action = "Immediate inspection and NDT are required before any service application."
        if confirmed_count > 0:
            confirmed_crits = [d for d in defects if d.get("severity") == "Critical" and d.get("confidence", 0) >= 0.50]
            if confirmed_crits:
                action = f"Confirmed critical indication ({confirmed_crits[0]['type']}) detected. Immediate engineering review and repair are required."
        return (
            f"HIGH CONCERN: The inspected weld contains {len(defects)} indication(s) including {types_str}. "
            f"Estimated defective area: {dam_pct:.1f}%. AI screening score: {score}/100. {action}"
        )

    def _clean_weld_result(self, img_bgr, w, h, filename, inspection_id, inspection_date, inspection_time, inspection_timestamp, good_welding_count=0, detected_classes_count=None):
        verdict = "NO TARGET DEFECT DETECTED. AI screening result — manual/CWI verification recommended."
        conclusion_str = "No active target defect indications detected in the inspected specimen (AI visual screening). Final acceptance requires qualified inspection / CWI verification."

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
                "status":               "No Target Defect Detected",
                "severity":             "Low",
                "explanation":          "A screening quality score of 98/100 was assigned because zero active defect indications were detected by the model.",
            },
            "conclusion":           conclusion_str,
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
                "condition":            "No Target Defect Detected",
                "acceptance_status":    "No Target Defect Detected",
                "overall_status":       "No Target Defect Detected",
                "overall_severity":     "Low",
                "overall_risk":         "Low",
                "repair_priority":      "No Action Required",
                "verdict":              verdict,
                "conclusion":           conclusion_str,
                "possible_causes":      ["Optimal welding heat input, travel speed, and gas shielding."],
                "recommended_actions":  ["Proceed to next inspection/production phase; visual screening clear."],
            },
            "twelve_class_inspection": self._build_12_class_inspection([]),
            "total_detected_indications": 0,
            "critical_count": 0, "high_count": 0, "medium_count": 0, "low_count": 0,
            "damaged_pct": 0.0, "health_score": 98, "condition": "No Target Defect Detected", "overall_risk": "Low",
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

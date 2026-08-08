import cv2
import numpy as np
import requests
import json

def create_sample_weld_image():
    # Create a 700x450 metallic plate texture (gray steel base)
    img = np.full((450, 700, 3), (160, 165, 170), dtype=np.uint8)

    # Add metallic texture noise
    noise = np.random.normal(0, 10, (450, 700, 3)).astype(np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    # Draw Central Weld Seam / Bead (Centerline horizontal weld pass)
    seam_y = 225
    # Heat-Affected Zone (HAZ) dark blue/tinted steel bands above and below weld seam
    cv2.rectangle(img, (50, seam_y - 60), (650, seam_y + 60), (140, 145, 155), -1)
    # Weld Bead ripples (convex curved stringer pass)
    for x in range(60, 640, 16):
        cv2.ellipse(img, (x, seam_y), (14, 38), 0, 0, 360, (190, 195, 205), -1)
        cv2.ellipse(img, (x, seam_y), (14, 38), 0, -90, 90, (120, 125, 135), 2)

    # Add Weld Defect 1: Longitudinal Crack (Centerline seam defect)
    pts = np.array([[220, seam_y - 4], [260, seam_y + 2], [310, seam_y - 3], [350, seam_y + 5]], np.int32)
    cv2.polylines(img, [pts], False, (15, 15, 25), 3)

    # Add Weld Defect 2: Porosity Clusters (Dark circular gas voids)
    for cx, cy in [(420, seam_y - 12), (435, seam_y - 8), (445, seam_y - 18), (428, seam_y + 10)]:
        cv2.circle(img, (cx, cy), 5, (10, 10, 15), -1)

    # Add Weld Defect 3: Spatter Droplets (Scattered specks on plate)
    for sx, sy in [(120, 110), (140, 130), (520, 330), (540, 310), (560, 340)]:
        cv2.circle(img, (sx, sy), 3, (40, 120, 220), -1)

    # Add Weld Defect 4: Undercut Groove (Top toe line)
    cv2.line(img, (150, seam_y - 42), (320, seam_y - 42), (25, 25, 35), 4)

    # Save sample weld defect test image
    cv2.imwrite("sample_metal_defect.jpg", img)
    print("Created sample weld defect test image: sample_metal_defect.jpg")

if __name__ == "__main__":
    create_sample_weld_image()
    
    # Test POST /api/inspect
    url = "http://127.0.0.1:8000/api/inspect"
    with open("sample_metal_defect.jpg", "rb") as f:
        response = requests.post(url, files={"file": ("sample_metal_defect.jpg", f, "image/jpeg")})
    
    if response.status_code == 200:
        data = response.json()
        print("API Welding Inspection Successful!")
        print(f"Total Defects Detected: {data['total_defects']}")
        print(f"Summary: {data['summary']}")
        print(f"Weld Quality Score: {data['weld_quality']['score']} / 100")
        print(f"Acceptance Status: {data['weld_quality']['acceptance_status']}")
        for d in data['defects']:
            print(f" - #{d['id']} {d['type']} at {d['location']} (Severity: {d['severity']}, Conf: {d['confidence']})")
        
        # Test POST /api/download-pdf
        pdf_url = "http://127.0.0.1:8000/api/download-pdf"
        pdf_resp = requests.post(pdf_url, json=data)
        if pdf_resp.status_code == 200 and pdf_resp.content.startswith(b"%PDF"):
            print("API PDF Generation Successful! PDF header verified (%PDF).")
            with open("test_report.pdf", "wb") as pdf_file:
                pdf_file.write(pdf_resp.content)
            print("Saved test PDF report: test_report.pdf")
        else:
            print(f"PDF Generation failed: {pdf_resp.status_code} {pdf_resp.text}")
    else:
        print(f"API Inspection failed: {response.status_code} {response.text}")

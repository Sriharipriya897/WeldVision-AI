import sys
from pathlib import Path
from fastapi.testclient import TestClient

backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from main import app

client = TestClient(app)

print("\n--- Testing /api/health ---")
r_health = client.get("/api/health")
print("Status:", r_health.status_code, r_health.json()["status"])

print("\n--- Testing /api/model-info ---")
r_info = client.get("/api/model-info")
classes = r_info.json()["classes"]
print("Model classes (12):", len(classes), classes)

print("\n--- Testing Clean Weld Specimen (/api/inspect) ---")
with open("dataset_12class/test/images/2ee47931-428c72c8-c6_jpg.rf.40094c65e74db145f6626ac45a431852.jpg", "rb") as f:
    r_clean = client.post("/api/inspect", files={"file": ("clean_specimen.jpg", f, "image/jpeg")})

assert r_clean.status_code == 200, f"Clean inspect failed: {r_clean.status_code}"
clean_data = r_clean.json()
print("Total defects:", clean_data["total_defects"])
print("Defect list length:", len(clean_data["defects"]))
print("Inspection cards displayed:", len(clean_data["twelve_class_inspection"]))
assert clean_data["total_defects"] == 0
assert len(clean_data["defects"]) == 0
assert len(clean_data["twelve_class_inspection"]) == 0

print("Testing Clean Weld PDF (/api/download-pdf)...")
r_clean_pdf = client.post("/api/download-pdf", json=clean_data)
assert r_clean_pdf.status_code == 200
print("Clean PDF generated:", len(r_clean_pdf.content), "bytes")

print("\n--- Testing Defective Weld Specimen with Porosity (/api/inspect) ---")
with open("dataset_12class/test/images/crack-welding-images_25_jpeg_jpg.rf.db98e9a7a69c7bc9b6a7a20e3af6efe8.jpg", "rb") as f:
    r_porosity = client.post("/api/inspect", files={"file": ("porosity_specimen.jpg", f, "image/jpeg")})

assert r_porosity.status_code == 200, f"Porosity inspect failed: {r_porosity.status_code}"
porosity_data = r_porosity.json()
print("Total defects:", porosity_data["total_defects"])
print("Defect list length:", len(porosity_data["defects"]))
print("Inspection cards displayed:", len(porosity_data["twelve_class_inspection"]))
for c in porosity_data["twelve_class_inspection"]:
    print(f"  -> Defect Card: {c['class_name']} ({c['status']}) - Conf: {c['confidence']}%, Count: {c['count']}")

assert porosity_data["total_defects"] == len(porosity_data["defects"])
assert len(porosity_data["twelve_class_inspection"]) == 1
assert porosity_data["twelve_class_inspection"][0]["class_name"] == "Porosity"

print("Testing Porosity Defect PDF (/api/download-pdf)...")
r_porosity_pdf = client.post("/api/download-pdf", json=porosity_data)
assert r_porosity_pdf.status_code == 200
print("Porosity PDF generated:", len(r_porosity_pdf.content), "bytes")

print("\n--- Testing Multi-Defect Specimen (/api/inspect) ---")
with open("dataset_12class/test/images/IMG_3621_block_1_1_png_jpg.rf.707e8c33b8fb395e32120633ab26bb95.jpg", "rb") as f:
    r_multi = client.post("/api/inspect", files={"file": ("multi_defect_specimen.jpg", f, "image/jpeg")})

assert r_multi.status_code == 200, f"Multi inspect failed: {r_multi.status_code}"
multi_data = r_multi.json()
print("Total defects:", multi_data["total_defects"])
print("Defect list length:", len(multi_data["defects"]))
print("Inspection cards displayed:", len(multi_data["twelve_class_inspection"]))
for c in multi_data["twelve_class_inspection"]:
    print(f"  -> Defect Card: {c['class_name']} ({c['status']}) - Conf: {c['confidence']}%, Count: {c['count']}")

assert multi_data["total_defects"] == len(multi_data["defects"])
detected_types = {d["type"] for d in multi_data["defects"]}
card_types = {c["class_name"] for c in multi_data["twelve_class_inspection"]}
assert detected_types == card_types, f"Mismatch: {detected_types} != {card_types}"

print("Testing Multi-Defect PDF (/api/download-pdf)...")
r_multi_pdf = client.post("/api/download-pdf", json=multi_data)
assert r_multi_pdf.status_code == 200
print("Multi-defect PDF generated:", len(r_multi_pdf.content), "bytes")

print("\n✓✓ ALL API ENDPOINT INTEGRATION TESTS PASSED! ✓✓\n")

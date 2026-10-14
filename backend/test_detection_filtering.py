import os
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from detector import WeldDetector
from pdf_generator import generate_pdf_report

detector = WeldDetector()

test_cases = [
    ('Porosity image', 'dataset_12class/test/images/crack-welding-images_25_jpeg_jpg.rf.db98e9a7a69c7bc9b6a7a20e3af6efe8.jpg'),
    ('Spatter image', 'dataset_12class/test/images/11668_2014_9832_Fig2_HTML_jpg.rf.b127c30061147cebdb4e6352f41de610.jpg'),
    ('Multi-defect image', 'dataset_12class/test/images/IMG_3621_block_1_1_png_jpg.rf.707e8c33b8fb395e32120633ab26bb95.jpg'),
    ('Clean weld image', 'dataset_12class/test/images/2ee47931-428c72c8-c6_jpg.rf.40094c65e74db145f6626ac45a431852.jpg')
]

for label, img_path in test_cases:
    full_path = Path(img_path).resolve()
    print(f"\n==================================================")
    print(f"=== Testing {label}: {full_path.name}")
    print(f"==================================================")
    with open(full_path, 'rb') as f:
        img_bytes = f.read()
    res = detector.analyze(img_bytes, filename=full_path.name)
    
    total = res['total_defects']
    defects = res['defects']
    cards = res['twelve_class_inspection']
    breakdown = res['summary']['breakdown']
    
    print(f"Total defects reported: {total}")
    print(f"Actual detections in list: {len(defects)}")
    print(f"Summary breakdown: {breakdown}")
    print(f"Displayed defect cards count: {len(cards)}")
    for c in cards:
        print(f"  -> Card: {c['class_name']} [{c['status']}], Conf={c['confidence']}%, Count={c['count']}, Loc={c['location']}")
    
    assert total == len(defects), f"Total defects mismatch: {total} != {len(defects)}"
    assert len(cards) == len(breakdown), f"Card count {len(cards)} != Breakdown count {len(breakdown)}"
    
    # Test PDF generation
    pdf_bytes = generate_pdf_report(res)
    assert len(pdf_bytes) > 1000, "PDF generation failed"
    out_pdf_path = backend_dir / f"test_{label.split()[0].lower()}_report.pdf"
    with open(out_pdf_path, 'wb') as pf:
        pf.write(pdf_bytes)
    print(f"✓ PDF report generated successfully ({len(pdf_bytes)} bytes) -> {out_pdf_path.name}")

print("\n==================================================")
print("✓✓ ALL 4 DEFECT FILTERING & REPORT TESTS PASSED! ✓✓")
print("==================================================")

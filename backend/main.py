import os
import io
import datetime
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from detector import WeldDetector, CorrosionDetector
from pdf_generator import generate_pdf_report

app = FastAPI(
    title="WeldVision AI Backend API",
    description="AI-Powered Industrial Welding Inspection and Weld Defect Analysis Platform",
    version="2.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize weld defect detector instance
detector = WeldDetector()


# ─── API Routes ───────────────────────────────────────────────────────────────

@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "system": "WeldVision AI - Industrial Welding Inspection System",
        "version": "2.0.0",
        "model_loaded": detector.model is not None,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


@app.get("/api/model-info")
def model_info():
    return {
        "model_architecture": "Ultralytics YOLO11 Segmentation (YOLO11n-seg)",
        "weights_path": str(detector.model_path),
        "classes": list(detector.model.names.values()) if hasattr(detector.model, "names") else [],
        "device": detector.device,
        "status": "ready"
    }


@app.post("/api/inspect")
async def inspect_image(file: UploadFile = File(...)):
    """
    Accepts an uploaded welded joint/bead metal image file.
    Analyzes weld defects (Crack, Porosity, Undercut, Overlap, Lack of Fusion, Lack of Penetration, Slag Inclusion, Burn Through, etc.).
    Returns engineering annotation with non-overlapping callout arrows, weld quality score, acceptance status, and defect breakdown.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image file (PNG, JPG, JPEG, WEBP).")
    
    try:
        image_bytes = await file.read()
        if not image_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        
        result = detector.analyze(image_bytes)

        # Strip internal layout keys before serializing
        _internal = {"_lx", "_ly", "_cx", "_cy", "_is_left", "items"}
        for d in result.get("defects", []):
            for k in _internal:
                d.pop(k, None)

        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Welding inspection failed: {str(e)}")


@app.post("/api/download-pdf")
async def download_pdf(data: dict = Body(...)):
    """
    Generates a professional industrial ReportLab PDF welding inspection report.
    Returns binary PDF stream for direct file download.
    """
    try:
        pdf_bytes = generate_pdf_report(data)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=WeldVision_Inspection_Report.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


# ─── Static Frontend Serving & SPA Routing ───────────────────────────────────

# Path to the compiled frontend production bundle
FRONTEND_DIST = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))

if os.path.exists(FRONTEND_DIST):
    assets_dir = os.path.join(FRONTEND_DIST, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str = ""):
        # Check if the requested file exists in dist (e.g. favicon.svg, icons.svg)
        target = os.path.join(FRONTEND_DIST, full_path) if full_path else os.path.join(FRONTEND_DIST, "index.html")
        if os.path.isfile(target):
            return FileResponse(target)
        # Otherwise fallback to index.html for client-side routing
        index_file = os.path.join(FRONTEND_DIST, "index.html")
        if os.path.isfile(index_file):
            return FileResponse(index_file)
        return JSONResponse({"status": "WeldVision AI Backend Online", "docs": "/docs"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


import io
import datetime
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse

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


@app.get("/")
def root():
    return {
        "status": "online",
        "system": "WeldVision AI - Industrial Welding Inspection System",
        "version": "2.0.0",
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

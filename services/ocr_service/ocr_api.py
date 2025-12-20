"""
Simple PaddleOCR FastAPI service for FinScribe.
This is a minimal implementation - extend as needed.
"""
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import paddleocr
from typing import Optional
import io

app = FastAPI(title="FinScribe OCR Service")

# Initialize OCR (lazy load on first request)
ocr_engine: Optional[paddleocr.PaddleOCR] = None


def get_ocr_engine():
    """Lazy initialization of OCR engine"""
    global ocr_engine
    if ocr_engine is None:
        ocr_engine = paddleocr.PaddleOCR(use_angle_cls=True, lang='en')
    return ocr_engine


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/v1/ocr")
async def ocr_endpoint(file: UploadFile = File(...)):
    """
    Extract text from uploaded image using PaddleOCR.
    
    Returns:
        JSON with 'text' field containing extracted text
    """
    try:
        # Read uploaded file
        contents = await file.read()
        image_bytes = io.BytesIO(contents)
        
        # Run OCR
        ocr = get_ocr_engine()
        result = ocr.ocr(image_bytes.read(), cls=True)
        
        # Extract text from OCR result
        text_lines = []
        if result and result[0]:
            for line in result[0]:
                if line and len(line) >= 2:
                    text_lines.append(line[1][0])  # line[1][0] is the text
        
        extracted_text = "\n".join(text_lines)
        
        return JSONResponse({
            "text": extracted_text,
            "status": "success"
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "status": "error"}
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

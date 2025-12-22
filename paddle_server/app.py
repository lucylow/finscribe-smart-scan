# paddle_server/app.py
"""
Local PaddleOCR HTTP server (FREE, no cloud).

POST /predict
multipart/form-data: image=<file>
returns JSON { regions: [...] }
"""

from fastapi import FastAPI, UploadFile, File
from paddleocr import PaddleOCR
from PIL import Image
import io

app = FastAPI(title="PaddleOCR Server")

ocr = PaddleOCR(
    use_angle_cls=True,
    lang="en",
    use_gpu=False  # set True if CUDA available
)

@app.post("/predict")
async def predict(image: UploadFile = File(...)):
    image_bytes = await image.read()
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    result = ocr.ocr(img, cls=True)

    regions = []
    for line in result:
        for box, (text, score) in line:
            x_coords = [p[0] for p in box]
            y_coords = [p[1] for p in box]
            regions.append({
                "text": text,
                "bbox": [
                    min(x_coords),
                    min(y_coords),
                    max(x_coords) - min(x_coords),
                    max(y_coords) - min(y_coords),
                ],
                "confidence": float(score),
            })

    return {"regions": regions}


"""Simple mock OCR service for demo"""
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse

app = FastAPI()

@app.post('/predict')
async def predict(file: UploadFile = File(...)):
    """Return mock OCR result"""
    return JSONResponse({
        'raw_text': """INVOICE
Invoice #: INV-2024-001
Date: 2024-01-15
Due: 2024-02-15

Vendor: TechCorp Inc.
123 Innovation Blvd, Suite 100
Cityville, CA 94000

Bill To:
Client Industries Inc.
456 Customer Avenue
New York, NY 10001

Description          Qty    Unit Price    Total
Widget A x1          1      $50.00        $50.00
Service B - Package 1  1      $100.00       $100.00
Support Plan 1 months  1      $25.00        $25.00

Subtotal: $175.00
Tax (10%): $17.50
Grand Total: $192.50""",
        'words': [
            {'text': 'INVOICE', 'bbox': [100, 50, 300, 80], 'confidence': 0.95},
            {'text': 'Invoice', 'bbox': [100, 100, 200, 130], 'confidence': 0.92},
            {'text': '#:', 'bbox': [210, 100, 240, 130], 'confidence': 0.90},
            {'text': 'INV-2024-001', 'bbox': [250, 100, 400, 130], 'confidence': 0.98},
            {'text': 'TechCorp', 'bbox': [100, 200, 250, 230], 'confidence': 0.95},
            {'text': 'Inc.', 'bbox': [260, 200, 300, 230], 'confidence': 0.93},
            {'text': 'Widget', 'bbox': [100, 400, 200, 430], 'confidence': 0.94},
            {'text': 'A', 'bbox': [210, 400, 230, 430], 'confidence': 0.96},
            {'text': '1', 'bbox': [500, 400, 520, 430], 'confidence': 0.97},
            {'text': '$50.00', 'bbox': [600, 400, 700, 430], 'confidence': 0.98},
            {'text': '$50.00', 'bbox': [800, 400, 900, 430], 'confidence': 0.98},
            {'text': 'Subtotal:', 'bbox': [600, 600, 700, 630], 'confidence': 0.95},
            {'text': '$175.00', 'bbox': [710, 600, 810, 630], 'confidence': 0.97},
            {'text': 'Tax', 'bbox': [600, 650, 650, 680], 'confidence': 0.94},
            {'text': '(10%):', 'bbox': [660, 650, 750, 680], 'confidence': 0.92},
            {'text': '$17.50', 'bbox': [760, 650, 860, 680], 'confidence': 0.96},
            {'text': 'Grand', 'bbox': [600, 700, 680, 730], 'confidence': 0.95},
            {'text': 'Total:', 'bbox': [690, 700, 760, 730], 'confidence': 0.94},
            {'text': '$192.50', 'bbox': [770, 700, 870, 730], 'confidence': 0.98},
        ],
        'latency_ms': 150
    })

@app.get('/health')
async def health():
    return {'status': 'ok'}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8001)


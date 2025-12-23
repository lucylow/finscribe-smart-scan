# frontend/mock_responses.py
def sample_response():
    return {
      "invoice_id": "mock-0001",
      "paddle": {
        "raw_text": "WALMART SUPERCENTER\nBananas 2.99\nBread 1.99\nSubtotal 4.98\nTax 0.30\nTotal 5.28",
        "words": [
            {"text":"WALMART", "bbox":[20,10,220,40], "conf":0.98},
            {"text":"Bananas", "bbox":[20,80,220,110], "conf":0.96},
            {"text":"2.99", "bbox":[300,80,360,110], "conf":0.94},
            {"text":"Bread", "bbox":[20,120,200,150], "conf":0.95},
            {"text":"1.99", "bbox":[300,120,360,150], "conf":0.93},
            {"text":"Total", "bbox":[20,220,120,250], "conf":0.99},
            {"text":"5.28", "bbox":[300,220,360,250], "conf":0.99}
        ],
        "latency_ms": 200,
        "model": "PaddleOCR-VL-finetuned"
      },
      "baseline_ocr": {
        "raw_text":"WALMART SUPERCENTER Bananas 2.99 Bread 1.99 Total 5.28",
        "latency_ms": 120,
        "model":"vanilla-paddle"
      },
      "structured_invoice": {
        "vendor": {"name":"Walmart Supercenter"},
        "invoice_date": "2024-11-15",
        "line_items":[
           {"description":"Bananas", "quantity":1, "unit_price":"2.99", "line_total":"2.99"},
           {"description":"Bread", "quantity":1, "unit_price":"1.99", "line_total":"1.99"}
        ],
        "financial_summary": {"subtotal":4.98, "tax":0.30, "grand_total":5.28}
      },
      "ernie": {
        "validated_invoice": {
          "vendor": {"name":"Walmart Supercenter"},
          "invoice_date": "2024-11-15",
          "line_items":[
              {"description":"Bananas", "quantity":1, "unit_price":"2.99", "line_total":"2.99"},
              {"description":"Bread", "quantity":1, "unit_price":"1.99", "line_total":"1.99"}
          ],
          "financial_summary":{"subtotal":4.98,"tax":0.30,"grand_total":5.28}
        },
        "validation": {"ok": True, "errors": []},
        "field_confidences": {"vendor.name":0.99, "financial_summary.grand_total":0.98},
        "latency_ms": 450
      },
      "confidence": 0.97,
      "latency_ms": {"total": 650}
    }


"""
Mock OCR backend for testing and development.
Provides deterministic mock OCR results.
"""
import time
import logging
from typing import Dict, Any

from .backend import OCRBackend, OCRResult

logger = logging.getLogger(__name__)


class MockOCRBackend(OCRBackend):
    """Mock OCR backend with deterministic fixture-driven output."""
    
    def detect(self, image_bytes: bytes) -> OCRResult:
        """
        Return deterministic mock OCR results.
        
        Args:
            image_bytes: Image data (ignored in mock)
            
        Returns:
            OCRResult with standardized structure
        """
        start_time = time.time()
        
        # Original mock data structure
        mock_tokens = [
            {"text": "INVOICE", "confidence": 0.99},
            {"text": "Invoice Number: INV-2025-001", "confidence": 0.98},
            {"text": "Date: 2025-01-15", "confidence": 0.97},
            {"text": "Acme Corporation", "confidence": 0.96},
            {"text": "123 Business St, Suite 100", "confidence": 0.94},
            {"text": "New York, NY 10001", "confidence": 0.95},
            {"text": "Bill To: Client Inc.", "confidence": 0.93},
            {"text": "456 Customer Ave", "confidence": 0.92},
            {"text": "Description | Qty | Unit Price | Total", "confidence": 0.91},
            {"text": "Consulting Services | 10 | $150.00 | $1,500.00", "confidence": 0.96},
            {"text": "Software License | 2 | $500.00 | $1,000.00", "confidence": 0.95},
            {"text": "Support Package | 1 | $250.00 | $250.00", "confidence": 0.94},
            {"text": "Subtotal: $2,750.00", "confidence": 0.97},
            {"text": "Tax (10%): $275.00", "confidence": 0.96},
            {"text": "Total: $3,025.00", "confidence": 0.98},
        ]
        
        mock_bboxes = [
            {"x": 100, "y": 50, "w": 100, "h": 20, "region_type": "header", "page_index": 0},
            {"x": 500, "y": 100, "w": 300, "h": 20, "region_type": "header", "page_index": 0},
            {"x": 500, "y": 130, "w": 200, "h": 20, "region_type": "header", "page_index": 0},
            {"x": 100, "y": 200, "w": 200, "h": 20, "region_type": "vendor", "page_index": 0},
            {"x": 100, "y": 230, "w": 250, "h": 20, "region_type": "vendor", "page_index": 0},
            {"x": 100, "y": 260, "w": 200, "h": 20, "region_type": "vendor", "page_index": 0},
            {"x": 400, "y": 200, "w": 200, "h": 20, "region_type": "client", "page_index": 0},
            {"x": 400, "y": 230, "w": 180, "h": 20, "region_type": "client", "page_index": 0},
            {"x": 100, "y": 350, "w": 500, "h": 20, "region_type": "table_header", "page_index": 0},
            {"x": 100, "y": 380, "w": 500, "h": 20, "region_type": "line_item", "page_index": 0},
            {"x": 100, "y": 410, "w": 500, "h": 20, "region_type": "line_item", "page_index": 0},
            {"x": 100, "y": 440, "w": 500, "h": 20, "region_type": "line_item", "page_index": 0},
            {"x": 400, "y": 500, "w": 200, "h": 20, "region_type": "summary", "page_index": 0},
            {"x": 400, "y": 530, "w": 200, "h": 20, "region_type": "summary", "page_index": 0},
            {"x": 400, "y": 560, "w": 200, "h": 25, "region_type": "total", "page_index": 0},
        ]
        
        # Convert to OCRResult format
        text_blocks = [token["text"] for token in mock_tokens]
        regions = []
        
        # Map bboxes to regions
        for bbox in mock_bboxes:
            # Find corresponding token text (simplified mapping)
            region_text = ""
            for token in mock_tokens:
                # Simple heuristic: match by approximate position
                if abs(bbox["y"] - 200) < 100:  # Rough matching
                    region_text = token["text"]
                    break
            
            regions.append({
                "type": bbox.get("region_type", "unknown"),
                "bbox": [bbox["x"], bbox["y"], bbox["w"], bbox["h"]],
                "text": region_text or "",
                "confidence": 0.95,  # Default confidence
                "page_index": bbox.get("page_index", 0)
            })
        
        # Extract table data from line items
        tables = []
        line_items = [token["text"] for token in mock_tokens if "|" in token["text"]]
        if line_items:
            # Parse table structure
            table_rows = []
            for item in line_items[1:]:  # Skip header
                parts = [p.strip() for p in item.split("|")]
                if len(parts) >= 4:
                    table_rows.append({
                        "description": parts[0],
                        "quantity": parts[1],
                        "unit_price": parts[2],
                        "total": parts[3]
                    })
            if table_rows:
                tables.append({
                    "type": "line_items",
                    "headers": ["Description", "Qty", "Unit Price", "Total"],
                    "rows": table_rows
                })
        
        duration = time.time() - start_time
        
        return OCRResult({
            "text": "\n".join(text_blocks),
            "regions": regions,
            "tables": tables,
            "raw": {
                "tokens": mock_tokens,
                "bboxes": mock_bboxes,
                "model_version": "PaddleOCR-VL-0.9B-mock",
                "status": "success"
            },
            "meta": {
                "backend": "mock",
                "duration": duration,
                "latency_ms": duration * 1000
            }
        })


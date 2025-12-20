import json
from typing import Dict, Any, List
from PIL import Image

class OCRService:
    """
    Mock service to simulate the PaddleOCR-VL endpoint at http://localhost:8002/v1/ocr.
    In a real-world scenario, this would make an HTTP request to the actual model service.
    """
    def __init__(self, model_url: str = "http://localhost:8002/v1/ocr"):
        self.model_url = model_url

    def process_document(self, image_path: str) -> Dict[str, Any]:
        """
        Simulates sending an image to the OCR service and getting structured output.
        
        Args:
            image_path: Path to the local image file.
            
        Returns:
            A dictionary representing the raw OCR output with bounding boxes.
        """
        # In a real implementation, we would use 'requests' to send the image file
        # to the self.model_url.
        
        # Mock OCR result structure
        mock_result = {
            "status": "success",
            "ocr_version": "PaddleOCR-VL-0.9B",
            "text_blocks": [
                {"text": "INVOICE", "box": [100, 50, 200, 70], "confidence": 0.99},
                {"text": "Invoice Number: INV-2025-001", "box": [500, 100, 800, 120], "confidence": 0.98},
                {"text": "Total: $1234.56", "box": [600, 800, 800, 820], "confidence": 0.97},
                # ... more text blocks
            ]
        }
        return mock_result

# Example usage (for testing purposes)
if __name__ == "__main__":
    # This part would typically be run in a test file
    ocr_service = OCRService()
    # Create a dummy image file for testing
    try:
        img = Image.new('RGB', (1000, 1000), color = 'white')
        img.save("dummy_invoice.png")
        
        result = ocr_service.process_document("dummy_invoice.png")
        print(json.dumps(result, indent=2))
    finally:
        import os
        if os.path.exists("dummy_invoice.png"):
            os.remove("dummy_invoice.png")

import json
from typing import Dict, Any, List

class LLMService:
    """
    Mock service to simulate the semantic parsing endpoint (Unsloth/LLaMA-Factory) 
    at http://localhost:8001/v1/infer.
    This service takes raw OCR output and converts it into structured financial data.
    """
    def __init__(self, model_url: str = "http://localhost:8001/v1/infer"):
        self.model_url = model_url

    def parse_financial_data(self, raw_ocr_output: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Simulates sending raw OCR data to the LLM for semantic parsing.
        
        Args:
            raw_ocr_output: The output from the OCR service.
            
        Returns:
            A list of structured fields extracted by the LLM.
        """
        # In a real implementation, this would send the raw_ocr_output 
        # along with a prompt to the LLM service.
        
        # Mock structured result
        structured_data = [
            {"field_name": "invoice_number", "value": "INV-2025-001", "confidence": 0.99, "source_model": "ERNIE-4.5"},
            {"field_name": "total_amount", "value": 1234.56, "confidence": 0.98, "source_model": "ERNIE-4.5"},
            {"field_name": "vendor_name", "value": "FinScribe Corp", "confidence": 0.95, "source_model": "ERNIE-4.5"},
            {"field_name": "invoice_date", "value": "2025-12-20", "confidence": 0.97, "source_model": "ERNIE-4.5"},
        ]
        return structured_data

# Example usage (for testing purposes)
if __name__ == "__main__":
    llm_service = LLMService()
    mock_ocr = {
        "status": "success",
        "ocr_version": "PaddleOCR-VL-0.9B",
        "text_blocks": [
            {"text": "INVOICE", "box": [100, 50, 200, 70], "confidence": 0.99},
            {"text": "Invoice Number: INV-2025-001", "box": [500, 100, 800, 120], "confidence": 0.98},
            {"text": "Total: $1234.56", "box": [600, 800, 800, 820], "confidence": 0.97},
        ]
    }
    
    result = llm_service.parse_financial_data(mock_ocr)
    print(json.dumps(result, indent=2))

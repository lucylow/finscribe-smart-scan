import aiohttp
import base64
import json
from typing import Dict, Any
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class VLMClientBase(ABC):
    """Base class for VLM client implementations."""
    
    @abstractmethod
    async def parse(self, ocr_payload: Dict[str, Any], image_bytes: bytes) -> Dict[str, Any]:
        """Parse OCR output into canonical structured JSON."""
        pass


class MockVLMClient(VLMClientBase):
    """Mock VLM client returning realistic invoice JSON."""
    
    async def parse(self, ocr_payload: Dict[str, Any], image_bytes: bytes) -> Dict[str, Any]:
        """Return deterministic mock VLM enrichment."""
        return {
            "status": "success",
            "model_version": "ERNIE-4.5-VL-28B-A3B-Thinking-mock",
            "structured_data": {
                "vendor_block": {
                    "name": "Acme Corporation",
                    "address": "123 Business St, Suite 100, New York, NY 10001",
                    "phone": "+1-555-123-4567",
                    "email": "billing@acme.com",
                    "confidence": 0.95
                },
                "client_info": {
                    "name": "Client Inc.",
                    "address": "456 Customer Ave",
                    "invoice_number": "INV-2025-001",
                    "invoice_date": "2025-01-15",
                    "due_date": "2025-02-15",
                    "confidence": 0.94
                },
                "line_items": [
                    {
                        "description": "Consulting Services",
                        "quantity": 10,
                        "unit_price": 150.00,
                        "total": 1500.00,
                        "confidence": 0.96
                    },
                    {
                        "description": "Software License",
                        "quantity": 2,
                        "unit_price": 500.00,
                        "total": 1000.00,
                        "confidence": 0.95
                    },
                    {
                        "description": "Support Package",
                        "quantity": 1,
                        "unit_price": 250.00,
                        "total": 250.00,
                        "confidence": 0.94
                    }
                ],
                "financial_summary": {
                    "subtotal": 2750.00,
                    "taxes": [{"type": "Sales Tax", "rate": 0.10, "amount": 275.00}],
                    "discounts": [],
                    "grand_total": 3025.00,
                    "currency": "USD"
                },
                "payment_terms": {
                    "due_date": "2025-02-15",
                    "payment_method": "Bank Transfer",
                    "notes": "Net 30 days"
                }
            },
            "validation_summary": {
                "is_valid": True,
                "math_verified": True,
                "issues": []
            },
            "confidence_scores": {
                "overall": 0.95,
                "vendor_block": 0.95,
                "client_info": 0.94,
                "line_items": 0.95,
                "financial_summary": 0.96
            },
            "latency_ms": 320,
            "token_usage": {"input": 1250, "output": 580}
        }


class ErnieVLMClient(VLMClientBase):
    """Real ERNIE 4.5 VLM client using vLLM server."""
    
    PROMPT_TEMPLATE = """You are a financial document analysis expert. Analyze this invoice and the following 
preliminary OCR data. Perform these tasks:

1. VALIDATE the extracted data against the image
2. CORRECT any errors in numbers or text
3. IDENTIFY the 5 key semantic regions:
   - Vendor block (name, address, contact)
   - Client/Invoice info (date, number, due date)
   - Line item table (description, quantity, price, total)
   - Tax & discount section
   - Grand total & payment terms
4. CHECK arithmetic consistency (sum of line items = subtotal, subtotal + tax - discounts = total)
5. EXTRACT any missing but important information

Preliminary OCR Data:
{ocr_data}

Return a JSON object with this exact structure:
{{
    "structured_data": {{
        "vendor_block": {{"name": "", "address": "", "confidence": 0.0}},
        "client_info": {{"name": "", "invoice_number": "", "invoice_date": "", "due_date": "", "confidence": 0.0}},
        "line_items": [{{"description": "", "quantity": 0, "unit_price": 0.0, "total": 0.0, "confidence": 0.0}}],
        "financial_summary": {{"subtotal": 0.0, "taxes": [], "discounts": [], "grand_total": 0.0, "currency": "USD"}},
        "payment_terms": {{}}
    }},
    "validation_summary": {{"is_valid": boolean, "math_verified": boolean, "issues": []}},
    "confidence_scores": {{"overall": 0.0}}
}}"""
    
    def __init__(self, server_url: str, timeout: int = 60):
        self.server_url = server_url
        self.timeout = timeout
    
    async def parse(self, ocr_payload: Dict[str, Any], image_bytes: bytes) -> Dict[str, Any]:
        """Send OCR data + image to ERNIE 4.5 for semantic enrichment."""
        import time
        start_time = time.time()
        
        image_data = base64.b64encode(image_bytes).decode('utf-8')
        prompt = self.PROMPT_TEMPLATE.format(ocr_data=json.dumps(ocr_payload, indent=2))
        
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}
                    },
                    {"type": "text", "text": prompt}
                ]
            }
        ]
        
        payload = {
            "model": "baidu/ERNIE-4.5-VL-28B-A3B-Thinking",
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 2048
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.server_url}/chat/completions",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    latency_ms = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        result = await response.json()
                        content = result['choices'][0]['message']['content']
                        usage = result.get('usage', {})
                        
                        try:
                            parsed = json.loads(content)
                            parsed["status"] = "success"
                            parsed["model_version"] = "ERNIE-4.5-VL-28B-A3B-Thinking"
                            parsed["latency_ms"] = latency_ms
                            parsed["token_usage"] = {
                                "input": usage.get("prompt_tokens", 0),
                                "output": usage.get("completion_tokens", 0)
                            }
                            return parsed
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse ERNIE response as JSON")
                            return {
                                "status": "partial",
                                "raw_output": content,
                                "latency_ms": latency_ms
                            }
                    else:
                        error_text = await response.text()
                        logger.error(f"ERNIE VLM error: {response.status} - {error_text}")
                        raise Exception(f"ERNIE error: {error_text}")
                        
            except aiohttp.ClientError as e:
                logger.error(f"Failed to call ERNIE VLM: {str(e)}")
                raise


class ErnieVLMService:
    """Service factory for ERNIE 4.5 VLM with model mode switching."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model_mode = config.get("model_mode", "mock")
        
        if self.model_mode == "mock":
            self.client = MockVLMClient()
        else:
            ernie_config = config.get("ernie_vl", {})
            self.client = ErnieVLMClient(
                server_url=ernie_config.get("vllm_server_url", "http://localhost:8002/v1"),
                timeout=ernie_config.get("timeout", 60)
            )
    
    async def enrich_financial_data(self, ocr_payload: Dict[str, Any], image_bytes: bytes) -> Dict[str, Any]:
        """Enrich OCR data with semantic understanding."""
        logger.info(f"Running VLM enrichment with mode: {self.model_mode}")
        return await self.client.parse(ocr_payload, image_bytes)

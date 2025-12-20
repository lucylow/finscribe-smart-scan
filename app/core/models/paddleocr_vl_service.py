import aiohttp
import base64
import json
from typing import Dict, Any
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class OCRClientBase(ABC):
    """Base class for OCR client implementations."""
    
    @abstractmethod
    async def analyze_image(self, image_bytes: bytes) -> Dict[str, Any]:
        """Analyze image and return structured OCR output."""
        pass


class MockOCRClient(OCRClientBase):
    """Mock OCR client with deterministic fixture-driven output."""
    
    async def analyze_image(self, image_bytes: bytes) -> Dict[str, Any]:
        """Return deterministic mock OCR results."""
        return {
            "status": "success",
            "model_version": "PaddleOCR-VL-0.9B-mock",
            "tokens": [
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
            ],
            "bboxes": [
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
            ],
            "regions": [
                {"type": "header", "content": "Invoice header with number and date"},
                {"type": "vendor", "content": "Vendor/seller information block"},
                {"type": "client", "content": "Client/buyer information block"},
                {"type": "table", "content": "Line items table with 3 items"},
                {"type": "summary", "content": "Financial summary with subtotal, tax, total"},
            ],
            "latency_ms": 150,
            "models_used": ["PaddleOCR-VL-0.9B"]
        }


class PaddleOCRVLClient(OCRClientBase):
    """Real PaddleOCR-VL client using vLLM server."""
    
    def __init__(self, server_url: str, timeout: int = 30, max_retries: int = 3):
        self.server_url = server_url
        self.timeout = timeout
        self.max_retries = max_retries
    
    async def analyze_image(self, image_bytes: bytes) -> Dict[str, Any]:
        """Send image to PaddleOCR-VL via vLLM and return structured output."""
        import time
        import asyncio
        
        # Validate input
        if not image_bytes or len(image_bytes) == 0:
            raise ValueError("Image bytes cannot be empty")
        
        image_data = base64.b64encode(image_bytes).decode('utf-8')
        
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}
                    },
                    {
                        "type": "text",
                        "text": "Parse this financial document. Extract all text with bounding boxes, identify semantic regions (header, vendor, client, line items, totals), and return as structured JSON."
                    }
                ]
            }
        ]
        
        payload = {
            "model": "PaddlePaddle/PaddleOCR-VL",
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": 4096
        }
        
        # Retry logic
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
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
                                try:
                                    result = await response.json()
                                    
                                    # Validate response structure
                                    if 'choices' not in result or not result['choices']:
                                        raise ValueError("Invalid response format: missing 'choices'")
                                    
                                    content = result['choices'][0]['message']['content']
                                    
                                    # Try to parse as JSON
                                    try:
                                        parsed = json.loads(content)
                                        parsed["latency_ms"] = latency_ms
                                        parsed["models_used"] = ["PaddleOCR-VL-0.9B"]
                                        parsed["status"] = "success"
                                        return parsed
                                    except json.JSONDecodeError as e:
                                        logger.warning(f"PaddleOCR-VL returned non-JSON response: {str(e)}")
                                        # Return partial result with raw output
                                        return {
                                            "status": "partial",
                                            "raw_output": content,
                                            "format": "text",
                                            "latency_ms": latency_ms,
                                            "models_used": ["PaddleOCR-VL-0.9B"],
                                            "warning": "Response could not be parsed as JSON"
                                        }
                                except (KeyError, IndexError) as e:
                                    logger.error(f"Invalid response structure: {str(e)}")
                                    raise ValueError(f"Invalid response structure: {str(e)}")
                            elif response.status == 429:
                                # Rate limit - retry with exponential backoff
                                wait_time = 2 ** attempt
                                logger.warning(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}/{self.max_retries}")
                                await asyncio.sleep(wait_time)
                                last_exception = Exception(f"Rate limit exceeded (HTTP 429)")
                                continue
                            elif response.status >= 500:
                                # Server error - retry
                                error_text = await response.text()
                                logger.warning(f"Server error {response.status}: {error_text}. Retry {attempt + 1}/{self.max_retries}")
                                if attempt < self.max_retries - 1:
                                    await asyncio.sleep(2 ** attempt)
                                    last_exception = Exception(f"Server error {response.status}: {error_text}")
                                    continue
                                else:
                                    raise Exception(f"Server error after {self.max_retries} retries: {response.status} - {error_text}")
                            else:
                                # Client error - don't retry
                                error_text = await response.text()
                                logger.error(f"PaddleOCR-VL client error: {response.status} - {error_text}")
                                raise Exception(f"Client error {response.status}: {error_text}")
                                
                    except asyncio.TimeoutError:
                        logger.warning(f"Request timeout (attempt {attempt + 1}/{self.max_retries})")
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(2 ** attempt)
                            last_exception = asyncio.TimeoutError(f"Request timeout after {self.timeout}s")
                            continue
                        else:
                            raise Exception(f"Request timeout after {self.max_retries} retries")
                            
            except aiohttp.ClientError as e:
                logger.warning(f"Network error calling PaddleOCR-VL (attempt {attempt + 1}/{self.max_retries}): {str(e)}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    last_exception = e
                    continue
                else:
                    raise Exception(f"Network error after {self.max_retries} retries: {str(e)}")
        
        # If we get here, all retries failed
        if last_exception:
            raise Exception(f"Failed to call PaddleOCR-VL after {self.max_retries} attempts: {str(last_exception)}")
        else:
            raise Exception(f"Failed to call PaddleOCR-VL after {self.max_retries} attempts")


class PaddleOCRVLService:
    """Service factory for PaddleOCR-VL with model mode switching."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model_mode = config.get("model_mode", "mock")
        
        if self.model_mode == "mock":
            self.client = MockOCRClient()
        else:
            ocr_config = config.get("paddleocr_vl", {})
            self.client = PaddleOCRVLClient(
                server_url=ocr_config.get("vllm_server_url", "http://localhost:8001/v1"),
                timeout=ocr_config.get("timeout", 30),
                max_retries=ocr_config.get("max_retries", 3)
            )
    
    async def parse_document(self, image_bytes: bytes) -> Dict[str, Any]:
        """Parse document using configured OCR client."""
        try:
            if not image_bytes or len(image_bytes) == 0:
                raise ValueError("Image bytes cannot be empty")
            
            logger.info(f"Running OCR with mode: {self.model_mode}")
            result = await self.client.analyze_image(image_bytes)
            
            # Validate result structure
            if not isinstance(result, dict):
                raise ValueError("OCR service returned invalid result type")
            
            if "status" not in result:
                result["status"] = "success"
            
            return result
        except Exception as e:
            logger.error(f"Error in OCR parse_document: {str(e)}", exc_info=True)
            raise

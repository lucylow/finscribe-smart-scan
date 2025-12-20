import aiohttp
import base64
import json
import re
from typing import Dict, Any, Optional
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
    """Real ERNIE VLM client using vLLM server. Supports ERNIE 4.5 and ERNIE 5 models."""
    
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
    
    # Supported ERNIE models with their configurations
    SUPPORTED_MODELS = {
        "ernie-5": {
            "model_name": "baidu/ERNIE-5",
            "default_max_tokens": 4096,
            "default_temperature": 0.1,
            "supports_thinking": True
        },
        "ernie-4.5-vl": {
            "model_name": "baidu/ERNIE-4.5-VL-28B-A3B-Thinking",
            "default_max_tokens": 2048,
            "default_temperature": 0.1,
            "supports_thinking": True
        },
        "ernie-4.5": {
            "model_name": "baidu/ERNIE-4.5-8B",
            "default_max_tokens": 2048,
            "default_temperature": 0.1,
            "supports_thinking": False
        }
    }
    
    def __init__(self, server_url: str, model_name: str = None, timeout: int = 60, max_retries: int = 3, enable_thinking: bool = True):
        self.server_url = server_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.enable_thinking = enable_thinking
        
        # Determine model version
        if model_name:
            self.model_name = model_name
            # Detect model version from name
            if "ernie-5" in model_name.lower() or "ERNIE-5" in model_name:
                self.model_version = "ernie-5"
            elif "ernie-4.5" in model_name.lower() or "ERNIE-4.5" in model_name:
                if "vl" in model_name.lower():
                    self.model_version = "ernie-4.5-vl"
                else:
                    self.model_version = "ernie-4.5"
            else:
                # Default to ERNIE 4.5 VL for backward compatibility
                self.model_version = "ernie-4.5-vl"
                logger.warning(f"Unknown ERNIE model '{model_name}', defaulting to ERNIE 4.5 VL")
        else:
            # Default to ERNIE 5 if available, fallback to ERNIE 4.5 VL
            self.model_version = "ernie-5"
            self.model_name = self.SUPPORTED_MODELS["ernie-5"]["model_name"]
        
        # Get model config
        model_config = self.SUPPORTED_MODELS.get(self.model_version, self.SUPPORTED_MODELS["ernie-4.5-vl"])
        self.default_max_tokens = model_config["default_max_tokens"]
        self.default_temperature = model_config["default_temperature"]
        
        logger.info(f"Initialized ERNIE VLM client with model: {self.model_name} (version: {self.model_version})")
    
    async def parse(self, ocr_payload: Dict[str, Any], image_bytes: bytes) -> Dict[str, Any]:
        """Send OCR data + image to ERNIE 4.5 for semantic enrichment."""
        import time
        import asyncio
        
        # Validate inputs
        if not image_bytes or len(image_bytes) == 0:
            raise ValueError("Image bytes cannot be empty")
        
        if not isinstance(ocr_payload, dict):
            raise ValueError("OCR payload must be a dictionary")
        
        image_data = base64.b64encode(image_bytes).decode('utf-8')
        try:
            prompt = self.PROMPT_TEMPLATE.format(ocr_data=json.dumps(ocr_payload, indent=2))
        except Exception as e:
            logger.error(f"Error formatting prompt: {str(e)}")
            raise ValueError(f"Failed to format prompt: {str(e)}")
        
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
        
        # Build payload with model-specific parameters
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.default_temperature,
            "max_tokens": self.default_max_tokens
        }
        
        # Add thinking mode for supported models if enabled
        if self.enable_thinking and self.SUPPORTED_MODELS.get(self.model_version, {}).get("supports_thinking", False):
            payload["enable_thinking"] = True
        
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
                                    usage = result.get('usage', {})
                                    
                                    try:
                                        parsed = json.loads(content)
                                        parsed["status"] = "success"
                                        parsed["model_version"] = self.model_name
                                        parsed["model_family"] = self.model_version
                                        parsed["latency_ms"] = latency_ms
                                        parsed["token_usage"] = {
                                            "input": usage.get("prompt_tokens", 0),
                                            "output": usage.get("completion_tokens", 0),
                                            "total": usage.get("total_tokens", 0)
                                        }
                                        return parsed
                                    except json.JSONDecodeError as e:
                                        logger.warning(f"Failed to parse ERNIE response as JSON: {str(e)}")
                                        # Try to extract JSON from markdown code blocks if present
                                        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
                                        if json_match:
                                            try:
                                                parsed = json.loads(json_match.group(1))
                                                parsed["status"] = "success"
                                                parsed["model_version"] = self.model_name
                                                parsed["model_family"] = self.model_version
                                                parsed["latency_ms"] = latency_ms
                                                parsed["token_usage"] = {
                                                    "input": usage.get("prompt_tokens", 0),
                                                    "output": usage.get("completion_tokens", 0),
                                                    "total": usage.get("total_tokens", 0)
                                                }
                                                return parsed
                                            except json.JSONDecodeError:
                                                pass
                                        
                                        # Return partial result if JSON extraction fails
                                        return {
                                            "status": "partial",
                                            "raw_output": content,
                                            "latency_ms": latency_ms,
                                            "model_version": self.model_name,
                                            "model_family": self.model_version,
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
                                logger.error(f"ERNIE VLM client error: {response.status} - {error_text}")
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
                logger.warning(f"Network error calling ERNIE VLM (attempt {attempt + 1}/{self.max_retries}): {str(e)}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    last_exception = e
                    continue
                else:
                    raise Exception(f"Network error after {self.max_retries} retries: {str(e)}")
        
        # If we get here, all retries failed
        if last_exception:
            raise Exception(f"Failed to call ERNIE VLM after {self.max_retries} attempts: {str(last_exception)}")
        else:
            raise Exception(f"Failed to call ERNIE VLM after {self.max_retries} attempts")


class ErnieVLMService:
    """Service factory for ERNIE VLM with model mode switching and version support."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model_mode = config.get("model_mode", "mock")
        
        if self.model_mode == "mock":
            self.client = MockVLMClient()
        else:
            ernie_config = config.get("ernie_vl", {})
            
            # Support for model version selection
            model_name = ernie_config.get("model_name")
            model_version = ernie_config.get("model_version", "auto")  # auto, ernie-5, ernie-4.5-vl, ernie-4.5
            
            # Auto-detect model version if not specified
            if model_version == "auto" and model_name:
                if "ernie-5" in model_name.lower() or "ERNIE-5" in model_name:
                    model_version = "ernie-5"
                elif "ernie-4.5" in model_name.lower() or "ERNIE-4.5" in model_name:
                    if "vl" in model_name.lower():
                        model_version = "ernie-4.5-vl"
                    else:
                        model_version = "ernie-4.5"
            
            # If no model_name specified, use version to determine default
            if not model_name:
                if model_version == "ernie-5":
                    model_name = "baidu/ERNIE-5"
                elif model_version == "ernie-4.5-vl":
                    model_name = "baidu/ERNIE-4.5-VL-28B-A3B-Thinking"
                elif model_version == "ernie-4.5":
                    model_name = "baidu/ERNIE-4.5-8B"
                else:
                    # Default to ERNIE 5, fallback to ERNIE 4.5 VL
                    model_name = "baidu/ERNIE-5"
                    logger.info("No model specified, defaulting to ERNIE 5")
            
            self.client = ErnieVLMClient(
                server_url=ernie_config.get("vllm_server_url", "http://localhost:8002/v1"),
                model_name=model_name,
                timeout=ernie_config.get("timeout", 60),
                max_retries=ernie_config.get("max_retries", 3),
                enable_thinking=ernie_config.get("enable_thinking", True)
            )
    
    async def enrich_financial_data(self, ocr_payload: Dict[str, Any], image_bytes: bytes) -> Dict[str, Any]:
        """Enrich OCR data with semantic understanding."""
        try:
            if not image_bytes or len(image_bytes) == 0:
                raise ValueError("Image bytes cannot be empty")
            
            if not isinstance(ocr_payload, dict):
                raise ValueError("OCR payload must be a dictionary")
            
            logger.info(f"Running VLM enrichment with mode: {self.model_mode}")
            result = await self.client.parse(ocr_payload, image_bytes)
            
            # Validate result structure
            if not isinstance(result, dict):
                raise ValueError("VLM service returned invalid result type")
            
            if "status" not in result:
                result["status"] = "success"
            
            return result
        except Exception as e:
            logger.error(f"Error in VLM enrich_financial_data: {str(e)}", exc_info=True)
            raise

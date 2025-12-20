import aiohttp
import base64
import json
import re
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
import logging

try:
    from .huggingface_helper import HuggingFaceHelper
except ImportError:
    # Fallback if helper not available
    HuggingFaceHelper = None

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
6. DETECT and IDENTIFY any company logos or brand marks visible in the document. Use logo recognition to cross-validate 
   and enhance confidence in the vendor name extraction. If a logo is detected, note the brand/company it represents 
   and use it to verify or correct the vendor name field.

Preliminary OCR Data:
{ocr_data}

Return a JSON object with this exact structure:
{{
    "structured_data": {{
        "vendor_block": {{"name": "", "address": "", "confidence": 0.0, "logo_detected": false, "logo_brand": null}},
        "client_info": {{"name": "", "invoice_number": "", "invoice_date": "", "due_date": "", "confidence": 0.0}},
        "line_items": [{{"description": "", "quantity": 0, "unit_price": 0.0, "total": 0.0, "confidence": 0.0}}],
        "financial_summary": {{"subtotal": 0.0, "taxes": [], "discounts": [], "grand_total": 0.0, "currency": "USD"}},
        "payment_terms": {{}}
    }},
    "validation_summary": {{"is_valid": boolean, "math_verified": boolean, "issues": []}},
    "confidence_scores": {{"overall": 0.0}},
    "logo_recognition": {{
        "detected": false,
        "brand_name": null,
        "confidence": 0.0,
        "location": "top_left|top_right|header|other",
        "description": ""
    }}
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
        
        # Get HuggingFace info if available
        self.hf_info = None
        if HuggingFaceHelper:
            try:
                self.hf_info = HuggingFaceHelper.get_model_info(self.model_name)
                logger.info(f"Model HuggingFace info: {self.hf_info.get('huggingface_url', 'N/A')}")
            except Exception as e:
                logger.debug(f"Could not get HuggingFace info: {str(e)}")
        
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
    
    async def compare_documents(
        self, 
        ocr_payload_1: Dict[str, Any], 
        image_bytes_1: bytes,
        ocr_payload_2: Dict[str, Any],
        image_bytes_2: bytes,
        comparison_type: str = "invoice_quote"
    ) -> Dict[str, Any]:
        """
        Compare two documents using ERNIE-VL's multimodal reasoning.
        Supports comparing invoices with quotes, proposals, or any related documents.
        
        Args:
            ocr_payload_1: OCR results for first document (e.g., Quote/Proposal)
            image_bytes_1: Image bytes for first document
            ocr_payload_2: OCR results for second document (e.g., Invoice)
            image_bytes_2: Image bytes for second document
            comparison_type: Type of comparison ("invoice_quote", "general", etc.)
        
        Returns:
            Comparison analysis with differences, additions, deletions, and changes
        """
        import time
        import asyncio
        
        # Validate inputs
        if not image_bytes_1 or len(image_bytes_1) == 0:
            raise ValueError("First image bytes cannot be empty")
        if not image_bytes_2 or len(image_bytes_2) == 0:
            raise ValueError("Second image bytes cannot be empty")
        
        image_data_1 = base64.b64encode(image_bytes_1).decode('utf-8')
        image_data_2 = base64.b64encode(image_bytes_2).decode('utf-8')
        
        # Build comparison prompt based on type
        if comparison_type == "invoice_quote":
            comparison_prompt = """You are a financial document analysis expert. Compare these two related documents:

DOCUMENT 1 (Quote/Proposal):
{ocr_data_1}

DOCUMENT 2 (Invoice):
{ocr_data_2}

Perform a detailed comparison:
1. Identify all line items present in both documents
2. Find additions: items in Document 2 (Invoice) but not in Document 1 (Quote)
3. Find deletions: items in Document 1 (Quote) but not in Document 2 (Invoice)
4. Detect price changes: same item but different price
5. Verify quantity changes: same item but different quantity
6. Calculate total difference between the two documents
7. Flag any discrepancies that require attention

Return a JSON object with this structure:
{{
    "comparison_summary": {{
        "total_items_document1": 0,
        "total_items_document2": 0,
        "matching_items": 0,
        "additions_count": 0,
        "deletions_count": 0,
        "price_changes_count": 0,
        "quantity_changes_count": 0,
        "total_difference": 0.0,
        "currency": "USD"
    }},
    "additions": [
        {{"description": "", "quantity": 0, "unit_price": 0.0, "total": 0.0, "reason": ""}}
    ],
    "deletions": [
        {{"description": "", "quantity": 0, "unit_price": 0.0, "total": 0.0, "reason": ""}}
    ],
    "price_changes": [
        {{
            "description": "",
            "document1_price": 0.0,
            "document2_price": 0.0,
            "difference": 0.0,
            "percentage_change": 0.0
        }}
    ],
    "quantity_changes": [
        {{
            "description": "",
            "document1_quantity": 0,
            "document2_quantity": 0,
            "difference": 0
        }}
    ],
    "matching_items": [
        {{"description": "", "quantity": 0, "unit_price": 0.0, "total": 0.0, "status": "verified"}}
    ],
    "discrepancies": [
        {{"type": "", "description": "", "severity": "low|medium|high", "recommendation": ""}}
    ],
    "overall_assessment": {{
        "status": "match|partial_match|mismatch",
        "confidence": 0.0,
        "requires_review": false,
        "summary": ""
    }}
}}"""
        else:
            comparison_prompt = """You are a document analysis expert. Compare these two documents side by side:

DOCUMENT 1:
{ocr_data_1}

DOCUMENT 2:
{ocr_data_2}

Perform a comprehensive comparison identifying:
- Common elements
- Differences in content, structure, or data
- Additions and deletions
- Value changes (if applicable)
- Any inconsistencies or discrepancies

Return a detailed JSON comparison analysis."""
        
        try:
            prompt = comparison_prompt.format(
                ocr_data_1=json.dumps(ocr_payload_1, indent=2),
                ocr_data_2=json.dumps(ocr_payload_2, indent=2)
            )
        except Exception as e:
            logger.error(f"Error formatting comparison prompt: {str(e)}")
            raise ValueError(f"Failed to format comparison prompt: {str(e)}")
        
        # Build messages with both images
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Document 1:"
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_data_1}"}
                    },
                    {
                        "type": "text",
                        "text": "Document 2:"
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_data_2}"}
                    },
                    {"type": "text", "text": prompt}
                ]
            }
        ]
        
        # Build payload
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.default_temperature,
            "max_tokens": self.default_max_tokens * 2  # Allow more tokens for comparison
        }
        
        # Add thinking mode for supported models if enabled
        if self.enable_thinking and self.SUPPORTED_MODELS.get(self.model_version, {}).get("supports_thinking", False):
            payload["enable_thinking"] = True
        
        # Retry logic (same as parse method)
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
                            timeout=aiohttp.ClientTimeout(total=self.timeout * 2)  # Longer timeout for comparison
                        ) as response:
                            latency_ms = (time.time() - start_time) * 1000
                            
                            if response.status == 200:
                                try:
                                    result = await response.json()
                                    
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
                                        parsed["comparison_type"] = comparison_type
                                        return parsed
                                    except json.JSONDecodeError as e:
                                        logger.warning(f"Failed to parse comparison response as JSON: {str(e)}")
                                        # Try to extract JSON from markdown code blocks
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
                                                parsed["comparison_type"] = comparison_type
                                                return parsed
                                            except json.JSONDecodeError:
                                                pass
                                        
                                        # Return partial result
                                        return {
                                            "status": "partial",
                                            "raw_output": content,
                                            "latency_ms": latency_ms,
                                            "model_version": self.model_name,
                                            "model_family": self.model_version,
                                            "comparison_type": comparison_type,
                                            "warning": "Response could not be parsed as JSON"
                                        }
                                except (KeyError, IndexError) as e:
                                    logger.error(f"Invalid comparison response structure: {str(e)}")
                                    raise ValueError(f"Invalid response structure: {str(e)}")
                            elif response.status == 429:
                                wait_time = 2 ** attempt
                                logger.warning(f"Rate limited during comparison, waiting {wait_time}s before retry {attempt + 1}/{self.max_retries}")
                                await asyncio.sleep(wait_time)
                                last_exception = Exception(f"Rate limit exceeded (HTTP 429)")
                                continue
                            elif response.status >= 500:
                                error_text = await response.text()
                                logger.warning(f"Server error {response.status} during comparison: {error_text}. Retry {attempt + 1}/{self.max_retries}")
                                if attempt < self.max_retries - 1:
                                    await asyncio.sleep(2 ** attempt)
                                    last_exception = Exception(f"Server error {response.status}: {error_text}")
                                    continue
                                else:
                                    raise Exception(f"Server error after {self.max_retries} retries: {response.status} - {error_text}")
                            else:
                                error_text = await response.text()
                                logger.error(f"ERNIE VLM comparison error: {response.status} - {error_text}")
                                raise Exception(f"Client error {response.status}: {error_text}")
                                
                    except asyncio.TimeoutError:
                        logger.warning(f"Comparison request timeout (attempt {attempt + 1}/{self.max_retries})")
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(2 ** attempt)
                            last_exception = asyncio.TimeoutError(f"Request timeout after {self.timeout * 2}s")
                            continue
                        else:
                            raise Exception(f"Comparison request timeout after {self.max_retries} retries")
                            
            except aiohttp.ClientError as e:
                logger.warning(f"Network error calling ERNIE VLM for comparison (attempt {attempt + 1}/{self.max_retries}): {str(e)}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    last_exception = e
                    continue
                else:
                    raise Exception(f"Network error after {self.max_retries} retries: {str(e)}")
        
        # If we get here, all retries failed
        if last_exception:
            raise Exception(f"Failed to compare documents after {self.max_retries} attempts: {str(last_exception)}")
        else:
            raise Exception(f"Failed to compare documents after {self.max_retries} attempts")


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
    
    async def compare_documents(
        self,
        ocr_payload_1: Dict[str, Any],
        image_bytes_1: bytes,
        ocr_payload_2: Dict[str, Any],
        image_bytes_2: bytes,
        comparison_type: str = "invoice_quote"
    ) -> Dict[str, Any]:
        """
        Compare two documents using ERNIE-VL's multimodal reasoning.
        This method leverages ERNIE-VL's "Thinking with Images" capability for cross-document analysis.
        """
        try:
            if not image_bytes_1 or len(image_bytes_1) == 0:
                raise ValueError("First image bytes cannot be empty")
            if not image_bytes_2 or len(image_bytes_2) == 0:
                raise ValueError("Second image bytes cannot be empty")
            
            if not isinstance(ocr_payload_1, dict):
                raise ValueError("First OCR payload must be a dictionary")
            if not isinstance(ocr_payload_2, dict):
                raise ValueError("Second OCR payload must be a dictionary")
            
            logger.info(f"Running document comparison with mode: {self.model_mode}, type: {comparison_type}")
            
            if self.model_mode == "mock":
                # Return mock comparison result for testing
                return {
                    "status": "success",
                    "model_version": "ERNIE-4.5-VL-28B-A3B-Thinking-mock",
                    "comparison_type": comparison_type,
                    "comparison_summary": {
                        "total_items_document1": 3,
                        "total_items_document2": 4,
                        "matching_items": 3,
                        "additions_count": 1,
                        "deletions_count": 0,
                        "price_changes_count": 1,
                        "quantity_changes_count": 0,
                        "total_difference": 100.00,
                        "currency": "USD"
                    },
                    "additions": [
                        {
                            "description": "Additional Service Fee",
                            "quantity": 1,
                            "unit_price": 100.00,
                            "total": 100.00,
                            "reason": "Added to invoice but not in original quote"
                        }
                    ],
                    "price_changes": [
                        {
                            "description": "Consulting Services",
                            "document1_price": 150.00,
                            "document2_price": 160.00,
                            "difference": 10.00,
                            "percentage_change": 6.67
                        }
                    ],
                    "matching_items": [
                        {
                            "description": "Software License",
                            "quantity": 2,
                            "unit_price": 500.00,
                            "total": 1000.00,
                            "status": "verified"
                        }
                    ],
                    "discrepancies": [],
                    "overall_assessment": {
                        "status": "partial_match",
                        "confidence": 0.92,
                        "requires_review": True,
                        "summary": "Most items match, but one addition and one price change detected"
                    }
                }
            
            # Use real ERNIE-VL client for comparison
            result = await self.client.compare_documents(
                ocr_payload_1, image_bytes_1,
                ocr_payload_2, image_bytes_2,
                comparison_type
            )
            
            # Validate result structure
            if not isinstance(result, dict):
                raise ValueError("VLM service returned invalid result type")
            
            if "status" not in result:
                result["status"] = "success"
            
            return result
        except Exception as e:
            logger.error(f"Error in VLM compare_documents: {str(e)}", exc_info=True)
            raise

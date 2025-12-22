"""
FinScribe OCR Service - PaddleOCR-VL Integration

This module:
1. Provides OCR client abstraction for multiple backends (mock, local, Hugging Face)
2. Integrates PaddleOCR-VL for layout-aware text extraction
3. Applies semantic layout analysis to identify document regions
4. Returns structured OCR output with bounding boxes and confidence scores

Pipeline:
  Image → OCR Backend (PaddleOCR-VL) → Semantic Layout Analysis → Structured OCR Result

Used by: app/core/document_processor.py, app/api/v1/endpoints.py
"""
import aiohttp
import base64
import json
import os
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
import logging
from PIL import Image
import io

from .paddleocr_prompts import (
    get_prompt_for_region,
    is_table_region,
    OCR_PROMPT,
    TABLE_RECOGNITION_PROMPT,
)
from .semantic_layout import SemanticLayoutAnalyzer, SemanticLayoutResult

logger = logging.getLogger(__name__)

# Try to import new OCR backend abstraction (optional)
try:
    from app.ocr.adapter import OCRBackendAdapter
    NEW_BACKEND_AVAILABLE = True
except ImportError:
    NEW_BACKEND_AVAILABLE = False
    logger.debug("New OCR backend abstraction not available, using legacy implementation")


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
    
    async def analyze_image(
        self, 
        image_bytes: bytes, 
        region_type: Optional[str] = None,
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send image to PaddleOCR-VL via vLLM and return structured output.
        
        Args:
            image_bytes: Image data to process
            region_type: Type of region (e.g., "line_items_table", "vendor_block")
                        Used to determine the appropriate task-specific prompt
            prompt: Optional custom prompt. If not provided, uses region_type to determine prompt.
        
        Returns:
            Structured OCR output
        """
        import time
        import asyncio
        
        # Validate input
        if not image_bytes or len(image_bytes) == 0:
            raise ValueError("Image bytes cannot be empty")
        
        image_data = base64.b64encode(image_bytes).decode('utf-8')
        
        # Determine the appropriate prompt
        if prompt is None:
            if region_type:
                prompt = get_prompt_for_region(region_type)
            else:
                # Default to OCR for full document parsing
                prompt = OCR_PROMPT
        
        # Build context-aware prompt message
        if is_table_region(region_type) if region_type else False:
            prompt_text = f"{prompt} Extract the table structure and return as JSON array of rows. Each row should be an object with keys matching the table headers."
        else:
            prompt_text = f"{prompt} Extract all text and structure as JSON."
        
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
                        "text": prompt_text
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
    """
    Service factory for PaddleOCR-VL with model mode switching.
    Supports task-specific prompts and mixed element processing.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model_mode = config.get("model_mode", "mock")
        
        # Check if new OCR backend should be used (via OCR_BACKEND env var)
        use_new_backend = NEW_BACKEND_AVAILABLE and os.getenv("OCR_BACKEND") is not None
        
        if use_new_backend:
            # Use new backend abstraction (paddle_local, paddle_hf, or mock)
            logger.info(f"Using new OCR backend abstraction (OCR_BACKEND={os.getenv('OCR_BACKEND')})")
            self.client = OCRBackendAdapter()
            # Override model_mode to reflect actual backend
            backend_name = os.getenv("OCR_BACKEND", "mock").lower()
            self.model_mode = backend_name if backend_name != "mock" else "mock"
        elif self.model_mode == "mock":
            self.client = MockOCRClient()
        else:
            ocr_config = config.get("paddleocr_vl", {})
            self.client = PaddleOCRVLClient(
                server_url=ocr_config.get("vllm_server_url", "http://localhost:8001/v1"),
                timeout=ocr_config.get("timeout", 30),
                max_retries=ocr_config.get("max_retries", 3)
            )
        
        # Initialize semantic layout analyzer for deep layout understanding
        self.layout_analyzer = SemanticLayoutAnalyzer()
        self.semantic_layout_enabled = config.get("semantic_layout", {}).get("enabled", True)
    
    async def parse_document(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Parse full document using configured OCR client.
        This performs initial layout analysis to detect regions.
        
        The two-stage process:
        1. Stage 1 (Layout Analysis): PP-DocLayoutV2 detects and classifies semantic regions
        2. Stage 2 (Element Recognition): PaddleOCR-VL-0.9B recognizes content and structure
        
        Returns:
            Dict with OCR results, optionally enhanced with semantic layout understanding
        """
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
            
            # Enhance with semantic layout understanding if enabled
            if self.semantic_layout_enabled:
                try:
                    layout_result = self.layout_analyzer.analyze_layout(result)
                    result["semantic_layout"] = layout_result.to_dict()
                    logger.info(f"Semantic layout analysis completed: {len(layout_result.regions)} regions detected")
                except Exception as layout_error:
                    logger.warning(f"Semantic layout analysis failed (non-critical): {str(layout_error)}")
                    # Continue without semantic layout enhancement
            
            return result
        except Exception as e:
            logger.error(f"Error in OCR parse_document: {str(e)}", exc_info=True)
            raise
    
    async def parse_region(
        self, 
        image_bytes: bytes, 
        region_type: str,
        bbox: Optional[Dict[str, int]] = None
    ) -> Dict[str, Any]:
        """
        Parse a specific region of a document with the appropriate task-specific prompt.
        
        This is used in Stage 2 of the pipeline: after layout analysis detects regions,
        each region is cropped and processed with the appropriate prompt.
        
        Args:
            image_bytes: Full document image or cropped region image
            region_type: Type of region (e.g., "line_items_table", "vendor_block")
            bbox: Optional bounding box dict with keys: x, y, w, h
        
        Returns:
            Structured output for the specific region
        """
        try:
            if not image_bytes or len(image_bytes) == 0:
                raise ValueError("Image bytes cannot be empty")
            
            # If bbox is provided, crop the image to the region
            if bbox:
                try:
                    image = Image.open(io.BytesIO(image_bytes))
                    cropped = image.crop((
                        bbox.get("x", 0),
                        bbox.get("y", 0),
                        bbox.get("x", 0) + bbox.get("w", image.width),
                        bbox.get("y", 0) + bbox.get("h", image.height)
                    ))
                    # Convert back to bytes
                    img_byte_arr = io.BytesIO()
                    cropped.save(img_byte_arr, format='PNG')
                    image_bytes = img_byte_arr.getvalue()
                except Exception as crop_error:
                    logger.warning(f"Failed to crop region, using full image: {str(crop_error)}")
            
            logger.info(f"Parsing region type '{region_type}' with prompt '{get_prompt_for_region(region_type)}'")
            
            if isinstance(self.client, PaddleOCRVLClient):
                result = await self.client.analyze_image(image_bytes, region_type=region_type)
            else:
                # Mock client doesn't support region-specific processing yet
                result = await self.client.analyze_image(image_bytes)
                # Add region metadata
                result["region_type"] = region_type
                result["prompt_used"] = get_prompt_for_region(region_type)
            
            # Validate result structure
            if not isinstance(result, dict):
                raise ValueError("OCR service returned invalid result type")
            
            if "status" not in result:
                result["status"] = "success"
            
            result["region_type"] = region_type
            result["prompt_used"] = get_prompt_for_region(region_type)
            
            return result
        except Exception as e:
            logger.error(f"Error parsing region '{region_type}': {str(e)}", exc_info=True)
            raise
    
    async def parse_document_with_semantic_layout(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Parse document with full semantic layout understanding.
        
        This method explicitly implements the two-stage process:
        1. Stage 1: Layout Analysis - Detect and classify all semantic regions with reading order
        2. Stage 2: Element Recognition - Recognize content and internal structure for each region
        
        Returns:
            Dict with semantic layout result including regions, reading order, and recognized elements
        """
        try:
            if not image_bytes or len(image_bytes) == 0:
                raise ValueError("Image bytes cannot be empty")
            
            logger.info("Running semantic layout analysis (two-stage process)")
            
            # Stage 1: Get initial OCR results (includes layout analysis from PP-DocLayoutV2)
            ocr_results = await self.parse_document(image_bytes)
            
            # Stage 2: Analyze semantic layout from OCR results
            layout_result = self.layout_analyzer.analyze_layout(ocr_results)
            
            # Return combined result
            return {
                "status": "success",
                "model_version": "PaddleOCR-VL-0.9B",
                "semantic_layout": layout_result.to_dict(),
                "raw_ocr": ocr_results,
                "processing_stages": {
                    "stage1_layout_analysis": "PP-DocLayoutV2",
                    "stage2_element_recognition": "PaddleOCR-VL-0.9B"
                }
            }
        except Exception as e:
            logger.error(f"Error in semantic layout parsing: {str(e)}", exc_info=True)
            raise
    
    async def parse_mixed_document(
        self, 
        image_bytes: bytes,
        regions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Process a document with mixed elements (text + tables) by processing each region
        with its appropriate task-specific prompt.
        
        This implements the two-stage pipeline:
        1. Layout analysis (regions should be pre-detected)
        2. Targeted element recognition for each region
        
        Args:
            image_bytes: Full document image
            regions: List of region dicts, each with:
                - type: Region type (e.g., "line_items_table", "vendor_block")
                - bbox: Optional bounding box dict with x, y, w, h
        
        Returns:
            Combined structured output with results for each region
        """
        try:
            if not image_bytes or len(image_bytes) == 0:
                raise ValueError("Image bytes cannot be empty")
            
            if not regions:
                # Fallback to full document parsing
                logger.warning("No regions provided, falling back to full document parsing")
                return await self.parse_document(image_bytes)
            
            logger.info(f"Processing mixed document with {len(regions)} regions")
            
            region_results = {}
            
            # Process each region with its appropriate prompt
            for i, region in enumerate(regions):
                region_type = region.get("type", "text")
                bbox = region.get("bbox")
                
                try:
                    result = await self.parse_region(
                        image_bytes,
                        region_type=region_type,
                        bbox=bbox
                    )
                    region_results[region_type] = result
                    logger.info(f"Successfully processed region {i+1}/{len(regions)}: {region_type}")
                except Exception as region_error:
                    logger.error(f"Failed to process region {i+1} ({region_type}): {str(region_error)}")
                    region_results[region_type] = {
                        "status": "failed",
                        "error": str(region_error),
                        "region_type": region_type
                    }
            
            # Combine results
            combined_result = {
                "status": "success",
                "model_version": "PaddleOCR-VL-0.9B",
                "regions_processed": len(regions),
                "region_results": region_results,
                "processing_strategy": "mixed_elements"
            }
            
            return combined_result
        except Exception as e:
            logger.error(f"Error processing mixed document: {str(e)}", exc_info=True)
            raise

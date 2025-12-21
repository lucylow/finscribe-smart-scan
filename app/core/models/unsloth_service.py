"""
Unsloth Inference Service

Provides a wrapper around Unsloth fine-tuned models for structured JSON extraction
from OCR text. This service acts as the reasoning/finalizer stage in the FinScribe pipeline.
"""
import os
import json
import logging
from typing import Dict, Any, Optional
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig

logger = logging.getLogger(__name__)


class UnslothService:
    """
    Service for running inference with Unsloth fine-tuned models.
    Handles loading models, tokenization, generation, and JSON extraction.
    """

    def __init__(
        self,
        model_dir: Optional[str] = None,
        device: Optional[str] = None,
        max_new_tokens: int = 512,
        temperature: float = 0.0,
    ):
        """
        Initialize Unsloth service.

        Args:
            model_dir: Path to fine-tuned Unsloth model directory. 
                       Defaults to environment variable UNSLOTH_MODEL_DIR or ./models/unsloth-finscribe
            device: Device to run inference on ('cuda' or 'cpu'). Auto-detects if None.
            max_new_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 = deterministic)
        """
        self.model_dir = model_dir or os.getenv(
            "UNSLOTH_MODEL_DIR", "./models/unsloth-finscribe"
        )
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature

        self.tokenizer = None
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load tokenizer and model from disk."""
        try:
            logger.info(f"Loading Unsloth model from {self.model_dir}")
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_dir, use_fast=True, trust_remote_code=True
            )
            
            # Load model with appropriate dtype
            dtype = torch.float16 if self.device == "cuda" else torch.float32
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_dir,
                torch_dtype=dtype,
                trust_remote_code=True,
            ).to(self.device)
            
            self.model.eval()  # Set to evaluation mode
            logger.info(f"Unsloth model loaded successfully on {self.device}")
            
        except Exception as e:
            logger.error(f"Failed to load Unsloth model: {str(e)}", exc_info=True)
            # Create a mock model for development/testing
            logger.warning("Falling back to mock mode")
            self.tokenizer = None
            self.model = None

    def _build_prompt(self, ocr_text: str, instruction: Optional[str] = None) -> str:
        """
        Build prompt from OCR text.

        Args:
            ocr_text: OCR-extracted text
            instruction: Optional custom instruction. Defaults to JSON extraction instruction.

        Returns:
            Formatted prompt string
        """
        if instruction is None:
            instruction = (
                "\n\nExtract structured JSON with vendor, invoice_number, dates, "
                "line_items (desc, qty, unit_price, line_total), and financial_summary. "
                "Output only valid JSON without any explanation."
            )
        
        # Format: OCR_TEXT: <text> <instruction>
        prompt = f"OCR_TEXT:\n{ocr_text}{instruction}"
        return prompt

    def _extract_json(self, decoded_text: str, prompt_length: int) -> Dict[str, Any]:
        """
        Extract JSON from model output.

        Args:
            decoded_text: Full decoded model output (may include prompt)
            prompt_length: Length of the input prompt

        Returns:
            Parsed JSON dictionary, or dict with error info if parsing fails
        """
        try:
            # Try to find first '{' after prompt
            json_start = decoded_text.find("{", prompt_length)
            if json_start == -1:
                # Fallback: try to find any '{'
                json_start = decoded_text.find("{")
            
            if json_start != -1:
                json_text = decoded_text[json_start:]
                # Try to find the matching closing brace
                # Simple approach: try parsing progressively
                parsed = json.loads(json_text)
                return parsed
            else:
                # No JSON found, return raw output
                return {
                    "_raw_output": decoded_text,
                    "_parse_error": True,
                    "_error_message": "No JSON found in output"
                }
        except json.JSONDecodeError as e:
            # Try to fix common JSON issues
            try:
                # Attempt to extract JSON using regex-like approach
                import re
                json_match = re.search(r'\{.*\}', decoded_text, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group())
                    return parsed
            except:
                pass
            
            # Return error info
            return {
                "_raw_output": decoded_text,
                "_parse_error": True,
                "_error_message": str(e)
            }

    def infer(
        self,
        ocr_text: str,
        instruction: Optional[str] = None,
        max_new_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Run inference on OCR text to extract structured JSON.

        Args:
            ocr_text: OCR-extracted text from document
            instruction: Optional custom instruction prompt
            max_new_tokens: Override default max_new_tokens
            temperature: Override default temperature

        Returns:
            Dictionary with parsed JSON or error information
        """
        # Use mock mode if model not loaded
        if self.model is None or self.tokenizer is None:
            logger.warning("Unsloth model not loaded, returning mock result")
            return self._mock_infer(ocr_text)

        try:
            # Build prompt
            prompt = self._build_prompt(ocr_text, instruction)
            
            # Tokenize
            inputs = self.tokenizer(
                prompt, return_tensors="pt", truncation=True, max_length=2048
            ).to(self.device)

            # Generate
            max_tokens = max_new_tokens or self.max_new_tokens
            temp = temperature if temperature is not None else self.temperature
            
            gen_config = GenerationConfig(
                temperature=temp,
                top_p=0.95,
                do_sample=(temp > 0.0),
                max_new_tokens=max_tokens,
                pad_token_id=self.tokenizer.pad_token_id or self.tokenizer.eos_token_id,
            )

            with torch.no_grad():
                outputs = self.model.generate(**inputs, generation_config=gen_config)

            # Decode
            decoded = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extract JSON
            result = self._extract_json(decoded, len(prompt))
            
            logger.info("Unsloth inference completed successfully")
            return result

        except Exception as e:
            logger.error(f"Unsloth inference failed: {str(e)}", exc_info=True)
            return {
                "_error": True,
                "_error_message": str(e),
                "_raw_input": ocr_text
            }

    def _mock_infer(self, ocr_text: str) -> Dict[str, Any]:
        """
        Mock inference for development/testing when model is not available.
        Returns a structured mock result.
        """
        return {
            "document_type": "invoice",
            "vendor": {"name": "Mock Vendor"},
            "client": {},
            "line_items": [
                {
                    "desc": "Mock Item",
                    "qty": 1,
                    "unit_price": 100.0,
                    "line_total": 100.0
                }
            ],
            "financial_summary": {
                "subtotal": 100.0,
                "tax_rate": 0.0,
                "tax_amount": 0.0,
                "grand_total": 100.0
            },
            "_mock": True,
            "_note": "Unsloth model not loaded, returned mock result"
        }

    def is_available(self) -> bool:
        """Check if model is loaded and available."""
        return self.model is not None and self.tokenizer is not None


# Global service instance
_unsloth_service: Optional[UnslothService] = None


def get_unsloth_service() -> UnslothService:
    """Get or create global Unsloth service instance."""
    global _unsloth_service
    if _unsloth_service is None:
        _unsloth_service = UnslothService()
    return _unsloth_service



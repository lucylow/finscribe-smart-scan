"""
Advanced Prompt Templates for FinScribe LLM Extraction

This module implements few-shot prompting strategies to maximize LLM performance
on structured financial data extraction tasks.
"""
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


# JSON Schema for financial document extraction
FINANCIAL_DOCUMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "document_type": {"type": "string"},
        "vendor": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "address": {"type": "string"},
                "contact": {"type": "string"}
            }
        },
        "invoice_number": {"type": "string"},
        "invoice_date": {"type": "string"},
        "due_date": {"type": "string"},
        "line_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "quantity": {"type": "number"},
                    "unit_price": {"type": "number"},
                    "line_total": {"type": "number"}
                }
            }
        },
        "financial_summary": {
            "type": "object",
            "properties": {
                "subtotal": {"type": "number"},
                "tax": {"type": "number"},
                "discount": {"type": "number"},
                "grand_total": {"type": "number"},
                "currency": {"type": "string"}
            }
        },
        "validation_notes": {"type": "string"}
    },
    "required": ["document_type", "financial_summary"]
}


def build_few_shot_prompt(
    structured_ocr_output: str,
    json_schema: Optional[Dict[str, Any]] = None
) -> str:
    """
    Build a few-shot prompt with examples for LLM extraction.
    
    This prompt includes:
    1. System instruction with JSON schema
    2. Example 1: Perfect extraction
    3. Example 2: Correction example (handling OCR flaws)
    4. Current task: The actual document to process
    
    Args:
        structured_ocr_output: Structured OCR output with semantic labels
        json_schema: Optional JSON schema (defaults to FINANCIAL_DOCUMENT_SCHEMA)
        
    Returns:
        Complete prompt string for LLM
    """
    if json_schema is None:
        json_schema = FINANCIAL_DOCUMENT_SCHEMA
    
    schema_str = json.dumps(json_schema, indent=2)
    
    # Example 1: Perfect extraction
    example1_ocr = """[KEY-VALUE]
Invoice Date: 2025-12-20
Invoice Number: INV-2025-001
Vendor: TechCorp Inc.
Total: $100.00

[TABLE]
Description | Qty | Unit Price | Total
Widget A | 2 | 10.00 | 20.00
Widget B | 3 | 15.00 | 45.00
Service Fee | 1 | 35.00 | 35.00

[KEY-VALUE]
Subtotal: $100.00
Tax: $0.00
Grand Total: $100.00"""
    
    example1_output = {
        "document_type": "invoice",
        "vendor": {"name": "TechCorp Inc."},
        "invoice_number": "INV-2025-001",
        "invoice_date": "2025-12-20",
        "line_items": [
            {"description": "Widget A", "quantity": 2, "unit_price": 10.00, "line_total": 20.00},
            {"description": "Widget B", "quantity": 3, "unit_price": 15.00, "line_total": 45.00},
            {"description": "Service Fee", "quantity": 1, "unit_price": 35.00, "line_total": 35.00}
        ],
        "financial_summary": {
            "subtotal": 100.00,
            "tax": 0.00,
            "grand_total": 100.00,
            "currency": "$"
        },
        "validation_notes": "Perfect match. All calculations verified."
    }
    
    # Example 2: Correction example (OCR flaw handling)
    example2_ocr = """[KEY-VALUE]
Invoice Date: 2025-12-20
Invoice Number: INV-2025-002
Vendor: Acme Corp
Total: $100.00

[TABLE]
Description | Qty | Unit Price | Total
Product X | 2 | 10.00 | 20.00
Product Y | 3 | 15.00 | 45.00
Service | 1 | 35.00 | 35.00

[KEY-VALUE]
Subtotal: $90.00
Tax: $9.00
Grand Total: $100.00"""
    
    example2_output = {
        "document_type": "invoice",
        "vendor": {"name": "Acme Corp"},
        "invoice_number": "INV-2025-002",
        "invoice_date": "2025-12-20",
        "line_items": [
            {"description": "Product X", "quantity": 2, "unit_price": 10.00, "line_total": 20.00},
            {"description": "Product Y", "quantity": 3, "unit_price": 15.00, "line_total": 45.00},
            {"description": "Service", "quantity": 1, "unit_price": 35.00, "line_total": 35.00}
        ],
        "financial_summary": {
            "subtotal": 90.00,
            "tax": 9.00,
            "grand_total": 99.00,  # Corrected: 90 + 9 = 99, not 100
            "currency": "$"
        },
        "validation_notes": "Corrected Grand Total from $100.00 to $99.00 (90+9) based on arithmetic validation. OCR may have misread the total."
    }
    
    # Build the complete prompt
    prompt = f"""[SYSTEM INSTRUCTION]
You are FinScribe, an expert financial data extractor. Your task is to convert the provided OCR text into a valid JSON object adhering strictly to the following schema:

{schema_str}

Rules:
1. Extract all relevant financial information from the OCR text
2. Perform arithmetic validation (e.g., subtotal + tax should equal grand_total)
3. If you detect inconsistencies, correct them and note the correction in validation_notes
4. Output ONLY valid JSON, no explanations or markdown
5. Use null for missing fields, not empty strings
6. Ensure all numbers are properly formatted (no currency symbols in numeric fields)

[FEW-SHOT EXAMPLE 1: PERFECT EXTRACTION]
OCR INPUT:
{example1_ocr}

JSON OUTPUT:
{json.dumps(example1_output, indent=2)}

[FEW-SHOT EXAMPLE 2: CORRECTION AND REASONING]
OCR INPUT:
{example2_ocr}

JSON OUTPUT:
{json.dumps(example2_output, indent=2)}

[CURRENT TASK]
OCR INPUT:
{structured_ocr_output}

JSON OUTPUT:
"""
    
    return prompt


def build_zero_shot_prompt(
    structured_ocr_output: str,
    json_schema: Optional[Dict[str, Any]] = None
) -> str:
    """
    Build a zero-shot prompt (fallback if few-shot is too long).
    
    Args:
        structured_ocr_output: Structured OCR output
        json_schema: Optional JSON schema
        
    Returns:
        Zero-shot prompt string
    """
    if json_schema is None:
        json_schema = FINANCIAL_DOCUMENT_SCHEMA
    
    schema_str = json.dumps(json_schema, indent=2)
    
    prompt = f"""Extract structured financial data from the OCR text below and output valid JSON.

Schema:
{schema_str}

OCR Text:
{structured_ocr_output}

Output only valid JSON:"""
    
    return prompt


def extract_json_schema_from_prompt(prompt: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON schema from prompt (for validation).
    
    Args:
        prompt: Prompt string containing schema
        
    Returns:
        Extracted JSON schema or None
    """
    try:
        # Look for schema section
        if "schema:" in prompt.lower():
            schema_start = prompt.lower().find("schema:")
            schema_section = prompt[schema_start:].split("\n\n")[0]
            # Try to extract JSON
            json_start = schema_section.find("{")
            if json_start != -1:
                json_end = schema_section.rfind("}") + 1
                schema_str = schema_section[json_start:json_end]
                return json.loads(schema_str)
    except Exception as e:
        logger.warning(f"Could not extract schema from prompt: {e}")
    
    return None


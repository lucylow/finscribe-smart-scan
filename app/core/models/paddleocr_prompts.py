"""
PaddleOCR-VL Task-Specific Prompts

This module defines the core task prompts for PaddleOCR-VL as documented in the
official transformers library. These prompts instruct the model to perform
specific types of element recognition on document images.

Reference: https://github.com/PaddlePaddle/PaddleOCR
"""

# Core task prompts as defined in official PaddleOCR-VL documentation
OCR_PROMPT = "OCR:"
TABLE_RECOGNITION_PROMPT = "Table Recognition:"
FORMULA_RECOGNITION_PROMPT = "Formula Recognition:"
CHART_RECOGNITION_PROMPT = "Chart Recognition:"

# Mapping from region types to appropriate prompts
REGION_TO_PROMPT = {
    # Text regions
    "header": OCR_PROMPT,
    "vendor": OCR_PROMPT,
    "client": OCR_PROMPT,
    "vendor_block": OCR_PROMPT,
    "client_info": OCR_PROMPT,
    "footer": OCR_PROMPT,
    "summary": OCR_PROMPT,
    "total": OCR_PROMPT,
    "text": OCR_PROMPT,
    "text_block": OCR_PROMPT,
    
    # Table regions
    "table": TABLE_RECOGNITION_PROMPT,
    "line_items_table": TABLE_RECOGNITION_PROMPT,
    "line_item": TABLE_RECOGNITION_PROMPT,
    "table_header": TABLE_RECOGNITION_PROMPT,
    "table_body": TABLE_RECOGNITION_PROMPT,
    
    # Specialized regions (for future use)
    "formula": FORMULA_RECOGNITION_PROMPT,
    "chart": CHART_RECOGNITION_PROMPT,
    "graph": CHART_RECOGNITION_PROMPT,
}

# Default prompt for unknown region types
DEFAULT_PROMPT = OCR_PROMPT


def get_prompt_for_region(region_type: str) -> str:
    """
    Get the appropriate PaddleOCR-VL prompt for a given region type.
    
    Args:
        region_type: The type of document region (e.g., "line_items_table", "vendor_block")
        
    Returns:
        The task-specific prompt string (e.g., "Table Recognition:", "OCR:")
    """
    return REGION_TO_PROMPT.get(region_type.lower(), DEFAULT_PROMPT)


def is_table_region(region_type: str) -> bool:
    """
    Check if a region type requires table recognition.
    
    Args:
        region_type: The type of document region
        
    Returns:
        True if the region should use Table Recognition prompt
    """
    return get_prompt_for_region(region_type) == TABLE_RECOGNITION_PROMPT


def build_prompt_message(prompt: str, additional_context: str = None) -> str:
    """
    Build a complete prompt message for PaddleOCR-VL.
    
    Args:
        prompt: The task-specific prompt (e.g., "Table Recognition:")
        additional_context: Optional additional instructions for fine-tuned models
        
    Returns:
        Complete prompt message string
    """
    if additional_context:
        return f"{prompt} {additional_context}"
    return prompt



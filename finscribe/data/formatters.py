"""
Financial instruction formatters for PaddleOCR-VL fine-tuning
Converts cropped regions into instruction-response pairs
"""

import json
from typing import Dict, Any, List, Union
from PIL import Image

# Import prompt system for consistent prompt usage
try:
    from app.core.models.paddleocr_prompts import get_prompt_for_region
except ImportError:
    # Fallback if not available
    def get_prompt_for_region(region_type: str) -> str:
        if "table" in region_type.lower():
            return "Table Recognition:"
        return "OCR:"


def build_instruction_sample(
    image: Image.Image,
    region_type: str,
    target: Union[Dict[str, Any], List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """
    Builds a PaddleOCR-VL instruction sample in the format expected by
    the model's instruction tuning pipeline.
    
    Uses the task-specific prompt system to automatically select the correct
    prompt based on region type (e.g., "Table Recognition:" for tables,
    "OCR:" for text regions).
    
    Args:
        image: PIL Image of the cropped semantic region
        region_type: Type of region (vendor_block, line_items_table, etc.)
        target: Ground truth data to extract (dict or list for tables)
        
    Returns:
        Dictionary with 'images' and 'messages' keys compatible with
        PaddleOCR-VL's instruction format
        
    Example:
        >>> image = Image.open("table_crop.png")
        >>> target = [{"description": "Item 1", "quantity": 1, "unit_price": 100}]
        >>> sample = build_instruction_sample(image, "line_items_table", target)
        >>> sample["messages"][0]["content"][1]["text"]
        'Table Recognition:'
    """
    # Get the appropriate prompt for this region type
    prompt = get_prompt_for_region(region_type)
    
    # Handle table regions (expect list of rows)
    if "table" in region_type.lower() or prompt == "Table Recognition:":
        # Target should be a list of rows or dict with 'rows' key
        if isinstance(target, dict) and "rows" in target:
            response = json.dumps(target["rows"], ensure_ascii=False, indent=None)
        elif isinstance(target, list):
            response = json.dumps(target, ensure_ascii=False, indent=None)
        else:
            # Convert dict to list format if needed
            response = json.dumps([target], ensure_ascii=False, indent=None)
    else:
        # Text regions (expect dict)
        # Ensure target is a dict
        if not isinstance(target, dict):
            target = {"content": target}
        response = json.dumps(target, ensure_ascii=False, indent=None)
    
    return {
        "images": [image],
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt},
                ],
            },
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": response}
                ],
            },
        ],
    }


def format_vendor_block(vendor_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formats vendor block data into canonical structure.
    
    Args:
        vendor_data: Raw vendor information
        
    Returns:
        Normalized vendor block dict
    """
    return {
        "vendor_name": vendor_data.get("name", ""),
        "address": vendor_data.get("address", ""),
        "city": vendor_data.get("city", ""),
        "state": vendor_data.get("state", ""),
        "postal_code": vendor_data.get("postal_code", ""),
        "country": vendor_data.get("country", ""),
        "phone": vendor_data.get("phone", ""),
        "email": vendor_data.get("email", ""),
        "tax_id": vendor_data.get("tax_id", ""),
    }


def format_line_items_table(items: list) -> list:
    """
    Formats line items into canonical table structure.
    Supports both simple numeric values and CurrencyAmount objects.
    
    Args:
        items: List of line item dictionaries
        
    Returns:
        List of normalized line item rows with consistent structure
        
    Example:
        >>> items = [{"description": "Service", "quantity": 1, "unit_price": 100}]
        >>> formatted = format_line_items_table(items)
        >>> formatted[0]["description"]
        'Service'
    """
    formatted = []
    for item in items:
        # Handle unit_price (can be number or CurrencyAmount dict)
        unit_price = item.get("unit_price", 0.0)
        if isinstance(unit_price, dict):
            unit_price = unit_price.get("amount", 0.0)
        
        # Handle line_total (can be number or CurrencyAmount dict)
        line_total = item.get("line_total", item.get("total", 0.0))
        if isinstance(line_total, dict):
            line_total = line_total.get("amount", 0.0)
        
        formatted.append({
            "description": item.get("description", ""),
            "quantity": item.get("quantity", 0),
            "unit_price": float(unit_price),
            "line_total": float(line_total),
            # Include currency if available
            **({"currency": item.get("currency")} if item.get("currency") else {}),
        })
    return formatted


def format_totals_section(totals_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formats totals section into canonical structure.
    
    Args:
        totals_data: Raw totals information
        
    Returns:
        Normalized totals dict
    """
    return {
        "subtotal": totals_data.get("subtotal", 0.0),
        "tax": totals_data.get("tax", totals_data.get("tax_total", 0.0)),
        "discount": totals_data.get("discount", totals_data.get("discount_total", 0.0)),
        "grand_total": totals_data.get("grand_total", totals_data.get("total", 0.0)),
        "currency": totals_data.get("currency", "USD"),
    }


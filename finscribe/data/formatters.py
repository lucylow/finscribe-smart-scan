"""
Financial instruction formatters for PaddleOCR-VL fine-tuning
Converts cropped regions into instruction-response pairs
"""

import json
from typing import Dict, Any
from PIL import Image


def build_instruction_sample(
    image: Image.Image,
    region_type: str,
    target: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Builds a PaddleOCR-VL instruction sample in the format expected by
    the model's instruction tuning pipeline.
    
    Args:
        image: PIL Image of the cropped semantic region
        region_type: Type of region (vendor_block, line_items_table, etc.)
        target: Ground truth data to extract (dict or list for tables)
        
    Returns:
        Dictionary with 'images' and 'messages' keys compatible with
        PaddleOCR-VL's instruction format
    """
    # For table regions, use "Table Recognition:" prompt
    # For text regions, use "OCR:" prompt
    if region_type == "line_items_table":
        prompt = "Table Recognition:"
        # Target should be a list of rows or dict with 'rows' key
        if isinstance(target, dict) and "rows" in target:
            response = json.dumps(target["rows"], ensure_ascii=False)
        elif isinstance(target, list):
            response = json.dumps(target, ensure_ascii=False)
        else:
            # Convert dict to list format if needed
            response = json.dumps([target], ensure_ascii=False)
    else:
        prompt = "OCR:"
        # Ensure target is a dict
        if not isinstance(target, dict):
            target = {"content": target}
        response = json.dumps(target, ensure_ascii=False)
    
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
    
    Args:
        items: List of line item dictionaries
        
    Returns:
        List of normalized line item rows
    """
    formatted = []
    for item in items:
        formatted.append({
            "description": item.get("description", ""),
            "quantity": item.get("quantity", 0),
            "unit_price": item.get("unit_price", 0.0),
            "line_total": item.get("line_total", item.get("total", 0.0)),
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


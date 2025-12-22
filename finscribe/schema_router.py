"""
Schema-aware routing for document parsing.

Groups OCR regions by layout zones and applies schema-based field extraction.
"""

from typing import Dict, List, Any, Optional
from .schemas import DocumentSchema, infer_doc_type, get_schema_for_doc_type
import logging

logger = logging.getLogger(__name__)


def group_regions_by_layout(regions: List[Dict[str, Any]], image_height: Optional[int] = None) -> Dict[str, List[Dict[str, Any]]]:
    """
    Group OCR regions by layout zones (header, table, footer).
    
    Args:
        regions: List of OCR regions with 'bbox' field
        image_height: Optional image height for better footer detection
        
    Returns:
        Dictionary with keys: 'header', 'table', 'footer'
    """
    buckets = {"header": [], "table": [], "footer": []}
    
    if not regions:
        return buckets
    
    # Use image height if provided, otherwise estimate from max y coordinate
    if image_height is None:
        max_y = max((r.get("bbox", [0, 0, 0, 0])[1] + r.get("bbox", [0, 0, 0, 0])[3] 
                    for r in regions if len(r.get("bbox", [])) >= 4), default=800)
        image_height = max_y
    
    # Heuristic thresholds
    header_threshold = image_height * 0.3  # Top 30% is header
    footer_threshold = image_height * 0.7  # Bottom 30% is footer
    
    for region in regions:
        bbox = region.get("bbox", [])
        if len(bbox) < 2:
            continue
        
        y = bbox[1]  # Top y coordinate
        
        # Check if region has explicit layout annotation
        layout = region.get("layout", "").lower()
        
        if layout == "table":
            buckets["table"].append(region)
        elif y < header_threshold:
            buckets["header"].append(region)
        elif y > footer_threshold:
            buckets["footer"].append(region)
        else:
            # Middle region - assume table if no explicit layout
            buckets["table"].append(region)
    
    return buckets


def extract_fields_by_schema(
    regions: List[Dict[str, Any]],
    schema: DocumentSchema,
    image_height: Optional[int] = None
) -> Dict[str, Any]:
    """
    Extract fields from regions using schema-based routing.
    
    Args:
        regions: List of OCR regions
        schema: DocumentSchema to use for extraction
        image_height: Optional image height
        
    Returns:
        Dictionary with extracted fields
    """
    # Group regions by layout
    layout_groups = group_regions_by_layout(regions, image_height)
    
    extracted = {}
    
    # Extract fields for each region type
    for region_type in ["header", "table", "footer"]:
        regions_in_type = layout_groups.get(region_type, [])
        fields_for_type = schema.get_fields_by_region(region_type)
        
        for field_spec in fields_for_type:
            # Try to match field using regex if available
            for region in regions_in_type:
                text = region.get("text", "")
                
                if field_spec.matches(text):
                    # Extract value from text
                    value = _extract_field_value(text, field_spec)
                    if value:
                        extracted[field_spec.name] = {
                            "value": value,
                            "confidence": region.get("confidence", 0.5),
                            "region_type": region_type,
                            "source_text": text
                        }
                        break
    
    return extracted


def _extract_field_value(text: str, field_spec: Any) -> Optional[str]:
    """
    Extract field value from text using regex.
    
    Args:
        text: Text to extract from
        field_spec: FieldSpec with regex pattern
        
    Returns:
        Extracted value or None
    """
    if not field_spec.regex:
        return text.strip()
    
    import re
    match = re.search(field_spec.regex, text, re.IGNORECASE)
    if match:
        # Return the first capture group if available, otherwise the full match
        if match.groups():
            return match.group(1).strip()
        return match.group(0).strip()
    
    return None


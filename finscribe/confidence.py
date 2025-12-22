"""
Confidence-weighted aggregation for field extraction.

Provides aggregation logic to combine multiple field extraction candidates
based on confidence scores.
"""

from typing import List, Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def aggregate_fields(fields: List[Dict[str, Any]]) -> Tuple[Any, float]:
    """
    Aggregate multiple field candidates using confidence-weighted voting.
    
    Args:
        fields: List of field dictionaries, each with 'value' and 'confidence'
                Example: [{"value": "INV-123", "confidence": 0.9}, ...]
        
    Returns:
        Tuple of (best_value, normalized_confidence)
    """
    if not fields:
        return None, 0.0
    
    if len(fields) == 1:
        field = fields[0]
        return field.get("value"), field.get("confidence", 0.5)
    
    # Group by value and sum confidence scores
    scores = {}
    
    for field in fields:
        value = field.get("value")
        if value is None:
            continue
        
        # Normalize value for comparison (convert to string, lowercase if text-like)
        normalized_value = str(value).strip()
        
        # For numeric values, try to normalize formatting
        try:
            # Try to parse as number and normalize
            float_val = float(normalized_value.replace(",", "").replace("$", ""))
            normalized_value = str(float_val)
        except (ValueError, AttributeError):
            # Not numeric, use as-is but normalize case
            normalized_value = normalized_value.lower()
        
        conf = field.get("confidence", 0.5)
        
        # Sum confidence scores for identical values
        if normalized_value in scores:
            scores[normalized_value]["confidence_sum"] += conf
            scores[normalized_value]["count"] += 1
        else:
            scores[normalized_value] = {
                "value": value,  # Keep original value
                "confidence_sum": conf,
                "count": 1
            }
    
    if not scores:
        return None, 0.0
    
    # Find value with highest confidence sum
    best_normalized = max(scores.items(), key=lambda x: x[1]["confidence_sum"])[0]
    best_entry = scores[best_normalized]
    
    # Calculate normalized confidence (0-1 scale, accounting for count)
    # Confidence is sum of confidences, normalized by number of candidates
    num_candidates = len(fields)
    normalized_conf = min(1.0, best_entry["confidence_sum"] / num_candidates)
    
    # Boost confidence if multiple sources agree
    if best_entry["count"] > 1:
        agreement_boost = min(0.1, best_entry["count"] * 0.02)
        normalized_conf = min(1.0, normalized_conf + agreement_boost)
    
    return best_entry["value"], normalized_conf


def aggregate_invoice_totals(regions: List[Dict[str, Any]]) -> Tuple[Optional[float], float]:
    """
    Extract and aggregate invoice total amounts from OCR regions.
    
    Args:
        regions: List of OCR regions with 'text' and 'confidence'
        
    Returns:
        Tuple of (total_amount, confidence)
    """
    import re
    
    total_patterns = [
        r"(?:total|grand\s+total|amount\s+due|balance\s+due)[\s:]*\$?\s*([\d,]+\.?\d*)",
        r"^\$?\s*([\d,]+\.?\d*)\s*$",  # Standalone amounts in footer
    ]
    
    candidates = []
    
    for region in regions:
        text = region.get("text", "")
        confidence = region.get("confidence", 0.5)
        
        # Try each pattern
        for pattern in total_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                try:
                    amount_str = match.group(1).replace(",", "")
                    amount = float(amount_str)
                    if amount > 0:  # Only positive amounts
                        candidates.append({
                            "value": amount,
                            "confidence": confidence,
                            "source_text": text
                        })
                        break  # Found a match, don't try other patterns
                except (ValueError, AttributeError):
                    continue
    
    if not candidates:
        return None, 0.0
    
    # Aggregate candidates
    best_value, conf = aggregate_fields(candidates)
    return best_value, conf


def aggregate_field_candidates(
    field_name: str,
    candidates: List[Dict[str, Any]],
    field_type: str = "text"
) -> Dict[str, Any]:
    """
    Aggregate field candidates with type-specific handling.
    
    Args:
        field_name: Name of the field
        candidates: List of candidate dictionaries with 'value' and 'confidence'
        field_type: Type of field ('text', 'number', 'date', 'currency')
        
    Returns:
        Dictionary with 'value', 'confidence', and metadata
    """
    if not candidates:
        return {
            "value": None,
            "confidence": 0.0,
            "field_name": field_name,
            "source_count": 0
        }
    
    # Type-specific normalization
    if field_type == "number":
        # Normalize numeric values
        normalized_candidates = []
        for cand in candidates:
            try:
                value = cand.get("value")
                if isinstance(value, str):
                    # Remove currency symbols, commas
                    cleaned = value.replace("$", "").replace(",", "").strip()
                    num_value = float(cleaned)
                else:
                    num_value = float(value)
                normalized_candidates.append({
                    **cand,
                    "value": num_value
                })
            except (ValueError, TypeError):
                continue
        candidates = normalized_candidates if normalized_candidates else candidates
    
    # Aggregate
    best_value, confidence = aggregate_fields(candidates)
    
    return {
        "value": best_value,
        "confidence": confidence,
        "field_name": field_name,
        "source_count": len(candidates),
        "field_type": field_type
    }


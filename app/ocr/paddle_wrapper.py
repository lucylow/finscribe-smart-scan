"""
PaddleOCR-VL Wrapper with Semantic Block Filtering

This module provides enhanced OCR output structuring and filtering to improve
LLM extraction accuracy by:
1. Filtering low-confidence text blocks
2. Identifying and labeling semantic block types (table, key-value, text)
3. Discarding boilerplate content (T&Cs, marketing text)
4. Structuring output for optimal LLM consumption
"""
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


def get_structured_ocr_output(ocr_result: Dict[str, Any], min_confidence: float = 0.85) -> str:
    """
    Filter and structure OCR output for LLM consumption.
    
    This function filters OCR results to include only relevant semantic blocks
    (tables, key-value pairs, high-confidence text) and discards boilerplate
    content that confuses the LLM.
    
    Args:
        ocr_result: OCR result dictionary with regions, text, confidence scores
        min_confidence: Minimum confidence threshold for including text blocks
        
    Returns:
        Structured, filtered OCR text with semantic labels
    """
    relevant_blocks = []
    
    try:
        # Extract regions from OCR result
        regions = ocr_result.get("regions", [])
        tables = ocr_result.get("tables", [])
        raw_text = ocr_result.get("text", "")
        
        # Process tables first (high priority)
        if tables:
            for table in tables:
                if isinstance(table, dict):
                    table_text = _extract_table_text(table)
                    if table_text:
                        relevant_blocks.append(f"[TABLE]\n{table_text}")
                elif isinstance(table, list):
                    # Handle table as list of rows
                    table_text = _format_table_rows(table)
                    if table_text:
                        relevant_blocks.append(f"[TABLE]\n{table_text}")
        
        # Process regions (text blocks with bounding boxes)
        for region in regions:
            if not isinstance(region, dict):
                continue
            
            # Filter 1: Confidence Score
            confidence = region.get("confidence", 0.0)
            if confidence < min_confidence:
                continue
            
            # Filter 2: Semantic Type
            region_type = region.get("type", "unknown").lower()
            text = region.get("text", "").strip()
            
            if not text:
                continue
            
            # Filter 3: Discard boilerplate (large unstructured text blocks)
            if region_type == "text" and len(text) > 500:
                # Heuristic: if it's a large text block, check if it looks like boilerplate
                if _is_boilerplate(text):
                    continue
            
            # Categorize and label the block
            if region_type in ["table", "key-value", "list"]:
                relevant_blocks.append(f"[{region_type.upper()}]\n{text}")
            elif region_type in ["header", "footer"]:
                # Include headers/footers only if they contain key information
                if _contains_key_information(text):
                    relevant_blocks.append(f"[{region_type.upper()}]\n{text}")
            elif confidence >= 0.90:  # High confidence text blocks
                relevant_blocks.append(f"[TEXT]\n{text}")
        
        # If no structured regions found, fall back to raw text with filtering
        if not relevant_blocks and raw_text:
            # Split into lines and filter
            lines = raw_text.split("\n")
            filtered_lines = []
            for line in lines:
                line = line.strip()
                if line and len(line) > 3:  # Filter very short lines
                    filtered_lines.append(line)
            
            if filtered_lines:
                relevant_blocks.append(f"[TEXT]\n" + "\n".join(filtered_lines[:50]))  # Limit to 50 lines
        
        # Join the filtered, semantically labeled blocks
        structured_output = "\n\n".join(relevant_blocks)
        
        logger.info(f"Structured OCR output: {len(relevant_blocks)} blocks, {len(structured_output)} chars")
        return structured_output
        
    except Exception as e:
        logger.error(f"Error structuring OCR output: {e}", exc_info=True)
        # Fallback to raw text
        return ocr_result.get("text", "")


def _extract_table_text(table: Dict[str, Any]) -> str:
    """Extract text from table structure."""
    try:
        if "rows" in table:
            rows = table["rows"]
            return _format_table_rows(rows)
        elif "data" in table:
            return _format_table_rows(table["data"])
        elif "text" in table:
            return table["text"]
        else:
            return str(table)
    except Exception as e:
        logger.warning(f"Error extracting table text: {e}")
        return ""


def _format_table_rows(rows: List[Any]) -> str:
    """Format table rows as structured text."""
    try:
        formatted_rows = []
        for row in rows:
            if isinstance(row, list):
                # Join row cells with pipe separator
                formatted_rows.append(" | ".join(str(cell) for cell in row))
            elif isinstance(row, dict):
                # Extract values from dict row
                values = [str(v) for v in row.values()]
                formatted_rows.append(" | ".join(values))
            else:
                formatted_rows.append(str(row))
        return "\n".join(formatted_rows)
    except Exception as e:
        logger.warning(f"Error formatting table rows: {e}")
        return ""


def _is_boilerplate(text: str) -> bool:
    """
    Heuristic to detect boilerplate content (T&Cs, marketing text).
    
    Args:
        text: Text to check
        
    Returns:
        True if text appears to be boilerplate
    """
    text_lower = text.lower()
    
    # Common boilerplate indicators
    boilerplate_keywords = [
        "terms and conditions",
        "terms of service",
        "privacy policy",
        "all rights reserved",
        "copyright",
        "confidential",
        "proprietary",
        "this document contains",
        "unauthorized use",
        "for more information",
        "visit our website",
        "follow us on",
        "subscribe to",
        "marketing",
        "promotional"
    ]
    
    # Check if text contains multiple boilerplate keywords
    keyword_count = sum(1 for keyword in boilerplate_keywords if keyword in text_lower)
    
    # If more than 2 keywords found, likely boilerplate
    if keyword_count >= 2:
        return True
    
    # Check for very long sentences (common in legal text)
    sentences = text.split(".")
    if len(sentences) > 0:
        avg_sentence_length = sum(len(s) for s in sentences) / len(sentences)
        if avg_sentence_length > 150:  # Very long sentences suggest legal/boilerplate
            return True
    
    return False


def _contains_key_information(text: str) -> bool:
    """
    Check if header/footer contains key financial information.
    
    Args:
        text: Header or footer text
        
    Returns:
        True if text contains relevant financial information
    """
    text_lower = text.lower()
    
    # Key information indicators
    key_indicators = [
        "invoice",
        "bill",
        "receipt",
        "date",
        "total",
        "amount",
        "due",
        "payment",
        "vendor",
        "customer",
        "invoice number",
        "invoice #",
        "account",
        "balance"
    ]
    
    # If contains any key indicator, it's relevant
    return any(indicator in text_lower for indicator in key_indicators)


def filter_ocr_by_confidence(ocr_result: Dict[str, Any], min_confidence: float = 0.85) -> Dict[str, Any]:
    """
    Filter OCR results by confidence score.
    
    Args:
        ocr_result: Original OCR result
        min_confidence: Minimum confidence threshold
        
    Returns:
        Filtered OCR result with only high-confidence regions
    """
    try:
        filtered_result = ocr_result.copy()
        regions = filtered_result.get("regions", [])
        
        # Filter regions by confidence
        filtered_regions = [
            r for r in regions
            if isinstance(r, dict) and r.get("confidence", 0.0) >= min_confidence
        ]
        
        filtered_result["regions"] = filtered_regions
        
        # Rebuild text from filtered regions
        filtered_text = "\n".join(
            r.get("text", "") for r in filtered_regions
            if r.get("text", "").strip()
        )
        
        if filtered_text:
            filtered_result["text"] = filtered_text
        
        logger.info(f"Filtered OCR: {len(regions)} -> {len(filtered_regions)} regions")
        return filtered_result
        
    except Exception as e:
        logger.error(f"Error filtering OCR by confidence: {e}", exc_info=True)
        return ocr_result


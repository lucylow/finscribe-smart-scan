"""
Safe JSON parser utility for extracting JSON from LLM outputs.
Handles common issues like markdown code blocks, extra text, etc.
"""
import json
import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def safe_json_parse(text: str, fallback: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Safely parse JSON from text that may contain extra content.
    
    Args:
        text: Text that may contain JSON
        fallback: Optional fallback dict if parsing fails
        
    Returns:
        Parsed JSON dictionary, or fallback if parsing fails
    """
    if not text or not isinstance(text, str):
        return fallback or {}
    
    # Try direct JSON parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try to extract JSON from markdown code blocks
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try to find first { ... } block
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass
    
    # Try to find last { ... } block (sometimes there's extra text after)
    json_matches = list(re.finditer(r'\{[\s\S]*\}', text))
    if json_matches:
        for match in reversed(json_matches):
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                continue
    
    logger.warning(f"Failed to parse JSON from text: {text[:200]}...")
    return fallback or {}


"""Safe JSON parsing utilities"""
import json
import re
from typing import Dict, Any, Optional


def safe_json_parse(s: str) -> Dict[str, Any]:
    """
    Extract JSON from a string that may contain text + JSON.
    
    Handles cases where LLM returns:
    - Plain JSON: {"key": "value"}
    - Text + JSON: "Here's the result: {\"key\": \"value\"}"
    - JSON wrapped in markdown: ```json\n{"key": "value"}\n```
    
    Args:
        s: Input string that may contain JSON
        
    Returns:
        Parsed JSON dictionary
        
    Raises:
        ValueError: If no valid JSON found
    """
    if not s or not isinstance(s, str):
        raise ValueError("Input must be a non-empty string")
    
    # Try direct parse first
    try:
        return json.loads(s.strip())
    except json.JSONDecodeError:
        pass
    
    # Try to find JSON in markdown code blocks
    json_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
    match = re.search(json_block_pattern, s, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try to find JSON object in text (look for { ... })
    json_obj_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    matches = re.findall(json_obj_pattern, s, re.DOTALL)
    
    # Try each match, return the first valid JSON
    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue
    
    # Last resort: try to extract anything that looks like JSON
    # Find the first { and last } and try to parse
    first_brace = s.find('{')
    last_brace = s.rfind('}')
    
    if first_brace >= 0 and last_brace > first_brace:
        try:
            return json.loads(s[first_brace:last_brace + 1])
        except json.JSONDecodeError:
            pass
    
    raise ValueError(f"Could not extract valid JSON from string: {s[:200]}...")


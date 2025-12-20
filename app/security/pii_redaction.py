"""PII redaction utilities."""
import re
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

# Patterns for common PII
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
PHONE_PATTERN = re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b')
SSN_PATTERN = re.compile(r'\b\d{3}-?\d{2}-?\d{4}\b')
CREDIT_CARD_PATTERN = re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b')


def redact_text(text: str, patterns: List[re.Pattern] = None) -> str:
    """
    Redact PII from text using regex patterns.
    
    Args:
        text: Text to redact
        patterns: List of regex patterns (defaults to common PII patterns)
    
    Returns:
        Redacted text
    """
    if patterns is None:
        patterns = [EMAIL_PATTERN, PHONE_PATTERN, SSN_PATTERN, CREDIT_CARD_PATTERN]
    
    redacted = text
    for pattern in patterns:
        redacted = pattern.sub("[REDACTED]", redacted)
    
    return redacted


def redact_dict(data: Dict[str, Any], fields_to_redact: List[str] = None) -> Dict[str, Any]:
    """
    Redact PII from dictionary fields.
    
    Args:
        data: Dictionary to redact
        fields_to_redact: List of field names to redact (defaults to common PII fields)
    
    Returns:
        Redacted dictionary
    """
    if fields_to_redact is None:
        fields_to_redact = [
            "email", "phone", "ssn", "credit_card", "account_number",
            "tax_id", "bank_account", "routing_number"
        ]
    
    redacted = data.copy()
    
    for key, value in redacted.items():
        if isinstance(value, dict):
            redacted[key] = redact_dict(value, fields_to_redact)
        elif isinstance(value, list):
            redacted[key] = [
                redact_dict(item, fields_to_redact) if isinstance(item, dict)
                else redact_text(str(item)) if isinstance(item, str) and key.lower() in [f.lower() for f in fields_to_redact]
                else item
                for item in value
            ]
        elif isinstance(value, str):
            key_lower = key.lower()
            if any(field.lower() in key_lower for field in fields_to_redact):
                redacted[key] = redact_text(value)
            else:
                # Still check for PII patterns
                redacted[key] = redact_text(value)
    
    return redacted


def should_redact(data: Dict[str, Any], redaction_enabled: bool = False) -> bool:
    """
    Determine if data should be redacted.
    
    Args:
        data: Data dictionary
        redaction_enabled: Whether redaction is enabled via configuration
    
    Returns:
        True if redaction should be applied
    """
    import os
    redaction_enabled = redaction_enabled or os.getenv("PII_REDACTION_ENABLED", "false").lower() == "true"
    return redaction_enabled


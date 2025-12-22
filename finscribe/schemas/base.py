"""
Base schema definitions for document parsing.

Defines field specifications and document schemas with region contracts.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Any
import re


@dataclass
class FieldSpec:
    """Specification for a document field."""
    name: str
    required: bool
    region_type: str  # header | table | footer
    regex: Optional[str] = None
    description: Optional[str] = None
    
    def matches(self, text: str) -> bool:
        """Check if text matches this field's regex pattern."""
        if self.regex:
            return bool(re.search(self.regex, text, re.IGNORECASE))
        return False


@dataclass
class DocumentSchema:
    """Schema definition for a document type."""
    doc_type: str
    fields: List[FieldSpec]
    
    def get_fields_by_region(self, region_type: str) -> List[FieldSpec]:
        """Get all fields for a specific region type."""
        return [f for f in self.fields if f.region_type == region_type]
    
    def get_required_fields(self) -> List[FieldSpec]:
        """Get all required fields."""
        return [f for f in self.fields if f.required]
    
    def get_field_by_name(self, name: str) -> Optional[FieldSpec]:
        """Get field specification by name."""
        for field in self.fields:
            if field.name == name:
                return field
        return None


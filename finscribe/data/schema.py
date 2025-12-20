"""
Dataset schema definitions for PaddleOCR-VL instruction tuning
"""

from typing import Dict, List, Any
from PIL import Image

# Type alias for instruction samples compatible with HuggingFace / ERNIEKit
InstructionSample = Dict[str, Any]

# Supported semantic region types
REGION_TYPES = [
    "vendor_block",
    "client_info",
    "line_items_table",
    "tax_section",
    "totals_section",
]


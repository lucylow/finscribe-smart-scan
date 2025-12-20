"""
Training modules for PaddleOCR-VL fine-tuning
"""

from .collate import collate_fn, IGNORE_INDEX
from .model import load_model
from .lora import apply_lora

__all__ = ["collate_fn", "IGNORE_INDEX", "load_model", "apply_lora"]


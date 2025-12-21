"""
Dataset preparation modules for PaddleOCR-VL fine-tuning
"""

from .schema import InstructionSample
from .formatters import build_instruction_sample
from .build_dataset import build_dataset

__all__ = ["InstructionSample", "build_instruction_sample", "build_dataset"]



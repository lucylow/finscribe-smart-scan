"""
Synthetic financial document generator for training data
"""

from .generator import generate_invoice
from .renderer import render_invoice
from .export import export_sample

__all__ = ["generate_invoice", "render_invoice", "export_sample"]


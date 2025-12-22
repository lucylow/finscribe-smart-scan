"""
FinScribe ETL Pipeline - Production-ready Extract-Transform-Load system

This module provides a complete ETL pipeline for financial document processing:
- Multi-source ingestion (local, S3/MinIO, email, bytes)
- Image preprocessing (deskew, denoise, contrast enhancement)
- Multi-backend OCR (PaddleOCR, HuggingFace, external)
- Semantic parsing (VLM + heuristic fallback)
- Data normalization (dates, currency)
- Validation (arithmetic, business rules)
- Structured persistence (Postgres + MinIO)
"""

__version__ = "1.0.0"


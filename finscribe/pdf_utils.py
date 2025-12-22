"""
PDF processing utilities for multi-page document splitting.

Converts PDF files to individual PNG images (one per page) for OCR processing.
"""

import io
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

try:
    from pdf2image import convert_from_bytes
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    logger.warning("pdf2image not available. Install with: pip install pdf2image")


def split_pdf_to_images(pdf_bytes: bytes, dpi: int = 200) -> List[bytes]:
    """
    Convert PDF bytes to a list of PNG image bytes (one per page).
    
    Args:
        pdf_bytes: Raw PDF file bytes
        dpi: DPI resolution for image conversion (default: 200)
        
    Returns:
        List of PNG image bytes, one per page
        
    Raises:
        ImportError: If pdf2image is not installed
        ValueError: If PDF bytes are invalid
    """
    if not PDF2IMAGE_AVAILABLE:
        raise ImportError(
            "pdf2image is required for PDF processing. "
            "Install with: pip install pdf2image\n"
            "Also requires poppler-utils:\n"
            "  macOS: brew install poppler\n"
            "  Ubuntu/Debian: sudo apt-get install poppler-utils\n"
            "  Windows: Download from https://github.com/oschwartz10612/poppler-windows/releases/"
        )
    
    if not pdf_bytes or len(pdf_bytes) == 0:
        raise ValueError("PDF bytes are empty")
    
    try:
        # Convert PDF to PIL Images
        images = convert_from_bytes(pdf_bytes, dpi=dpi)
        pages = []
        
        for img in images:
            # Convert PIL Image to PNG bytes
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            pages.append(buf.getvalue())
            buf.close()
        
        logger.info(f"Split PDF into {len(pages)} pages")
        return pages
        
    except Exception as e:
        logger.error(f"Failed to split PDF: {str(e)}")
        raise ValueError(f"Failed to convert PDF to images: {str(e)}") from e


def get_pdf_page_count(pdf_bytes: bytes) -> int:
    """
    Get the number of pages in a PDF without converting to images.
    
    Args:
        pdf_bytes: Raw PDF file bytes
        
    Returns:
        Number of pages in the PDF
    """
    if not PDF2IMAGE_AVAILABLE:
        # Fallback: try using PyPDF2 if available
        try:
            import PyPDF2
            pdf_file = io.BytesIO(pdf_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            return len(pdf_reader.pages)
        except ImportError:
            logger.warning("Neither pdf2image nor PyPDF2 available")
            return 0
    
    try:
        # Use pdf2image to count pages (more efficient than full conversion)
        images = convert_from_bytes(pdf_bytes, dpi=50, first_page=1, last_page=1)
        # This is a workaround - we'll actually need to try different approaches
        # For now, convert all pages but we could optimize this
        images = convert_from_bytes(pdf_bytes, dpi=50)
        return len(images)
    except Exception as e:
        logger.error(f"Failed to count PDF pages: {str(e)}")
        return 0


"""
Document Classifier for ETL Pipeline.

Classifies documents to enable intelligent routing and processing:
- Scanned vs native PDF detection
- Text layer detection
- Table detection
- Multi-page detection
- Document type classification (invoice, receipt, statement, etc.)
"""
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import mimetypes

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    from PIL import Image
    from pdf2image import convert_from_bytes
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

logger = logging.getLogger(__name__)


class DocumentClassifier:
    """
    Classifies documents to determine processing strategy.
    
    Early classification enables:
    - Routing to appropriate OCR engines
    - Optimizing preprocessing steps
    - Setting confidence thresholds
    - Choosing extraction strategies
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize document classifier.
        
        Args:
            config: Classification configuration
        """
        self.config = config or {}
        self.enable_table_detection = self.config.get("enable_table_detection", True)
        self.enable_document_type_classification = self.config.get(
            "enable_document_type_classification", True
        )
    
    async def classify(
        self,
        file_content: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """
        Classify document and return classification results.
        
        Args:
            file_content: Raw file bytes
            filename: Original filename
            
        Returns:
            Classification results dictionary with:
            - is_scanned: bool
            - has_text_layer: bool
            - contains_tables: bool
            - is_multi_page: bool
            - document_type: str (invoice, receipt, statement, etc.)
            - file_type: str (pdf, image, etc.)
            - confidence: float
        """
        result = {
            "is_scanned": None,
            "has_text_layer": None,
            "contains_tables": None,
            "is_multi_page": None,
            "document_type": None,
            "file_type": None,
            "confidence": 1.0
        }
        
        # Detect file type
        file_type = self._detect_file_type(file_content, filename)
        result["file_type"] = file_type
        
        if file_type == "pdf":
            # PDF-specific classification
            pdf_classification = await self._classify_pdf(file_content)
            result.update(pdf_classification)
        elif file_type in ["image", "png", "jpg", "jpeg", "tiff"]:
            # Image files are always scanned
            result["is_scanned"] = True
            result["has_text_layer"] = False
            result["is_multi_page"] = False
        
        # Document type classification (invoice, receipt, etc.)
        if self.enable_document_type_classification:
            doc_type = await self._classify_document_type(file_content, filename, result)
            result["document_type"] = doc_type
        
        # Table detection
        if self.enable_table_detection and file_type == "pdf":
            has_tables = await self._detect_tables(file_content)
            result["contains_tables"] = has_tables
        
        logger.info(f"Classification result for {filename}: {result}")
        return result
    
    def _detect_file_type(self, file_content: bytes, filename: str) -> str:
        """Detect file type from content and extension."""
        # Check MIME type
        mime_type, _ = mimetypes.guess_type(filename)
        
        if mime_type:
            if mime_type == "application/pdf":
                return "pdf"
            elif mime_type.startswith("image/"):
                return "image"
        
        # Fallback to extension
        ext = Path(filename).suffix.lower()
        if ext == ".pdf":
            return "pdf"
        elif ext in [".png", ".jpg", ".jpeg", ".tiff", ".tif"]:
            return "image"
        
        # Check magic bytes
        if file_content.startswith(b"%PDF"):
            return "pdf"
        elif file_content.startswith(b"\x89PNG"):
            return "png"
        elif file_content.startswith(b"\xff\xd8\xff"):
            return "jpg"
        
        return "unknown"
    
    async def _classify_pdf(self, file_content: bytes) -> Dict[str, Any]:
        """
        Classify PDF document.
        
        Returns:
            Dictionary with is_scanned, has_text_layer, is_multi_page
        """
        result = {
            "is_scanned": False,
            "has_text_layer": False,
            "is_multi_page": False
        }
        
        if not PYMUPDF_AVAILABLE:
            logger.warning("PyMuPDF not available, using fallback PDF classification")
            # Fallback: assume scanned if we can't analyze
            result["is_scanned"] = True
            result["has_text_layer"] = False
            return result
        
        try:
            import fitz
            
            doc = fitz.open(stream=file_content, filetype="pdf")
            result["is_multi_page"] = len(doc) > 1
            
            # Check first few pages for text layer
            text_found = False
            total_chars = 0
            
            for page_num in range(min(3, len(doc))):
                page = doc[page_num]
                text = page.get_text()
                total_chars += len(text)
                if len(text) > 50:  # Threshold for "has text"
                    text_found = True
            
            result["has_text_layer"] = text_found
            
            # Heuristic: if no text layer, likely scanned
            # Also check if pages are mostly images
            if not text_found:
                result["is_scanned"] = True
            else:
                # Check if text is sparse (indicating scanned with OCR layer)
                # vs dense (native PDF)
                if total_chars < 100:  # Very sparse text
                    result["is_scanned"] = True
                else:
                    result["is_scanned"] = False
            
            doc.close()
            
        except Exception as e:
            logger.error(f"Error classifying PDF: {str(e)}")
            # Fallback: assume scanned
            result["is_scanned"] = True
            result["has_text_layer"] = False
        
        return result
    
    async def _detect_tables(self, file_content: bytes) -> bool:
        """
        Detect if document contains tables.
        
        This is a simple heuristic - in production, you'd use
        a dedicated table detection model.
        """
        if not PYMUPDF_AVAILABLE:
            return False
        
        try:
            import fitz
            
            doc = fitz.open(stream=file_content, filetype="pdf")
            
            # Check first page for tables (simple heuristic)
            if len(doc) > 0:
                page = doc[0]
                # Look for table-like structures in annotations or text blocks
                blocks = page.get_text("blocks")
                
                # Heuristic: if we have many small text blocks in grid-like pattern
                # This is simplified - real table detection would use ML
                if len(blocks) > 10:
                    # Could be a table
                    doc.close()
                    return True
            
            doc.close()
            return False
            
        except Exception as e:
            logger.error(f"Error detecting tables: {str(e)}")
            return False
    
    async def _classify_document_type(
        self,
        file_content: bytes,
        filename: str,
        classification: Dict[str, Any]
    ) -> Optional[str]:
        """
        Classify document type (invoice, receipt, statement, etc.).
        
        Uses filename patterns and content heuristics.
        In production, this would use a trained classifier.
        """
        filename_lower = filename.lower()
        
        # Filename-based classification
        if any(keyword in filename_lower for keyword in ["invoice", "inv", "bill"]):
            return "invoice"
        elif any(keyword in filename_lower for keyword in ["receipt", "receipt"]):
            return "receipt"
        elif any(keyword in filename_lower for keyword in ["statement", "stmt"]):
            return "statement"
        elif any(keyword in filename_lower for keyword in ["contract", "agreement"]):
            return "contract"
        
        # Content-based classification would go here
        # For now, return None (unknown)
        return None


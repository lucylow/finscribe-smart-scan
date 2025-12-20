"""
Vanilla PaddleOCR pipeline wrapper for comparison in Streamlit demo.
Uses standard PaddleOCR without fine-tuning.
"""
import cv2
import numpy as np
from typing import Dict, Any, Optional
import sys
import os

# Try to import PaddleOCR, fallback to mock if not available
try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False
    print("Warning: PaddleOCR not available. Using mock implementation.")


class VanillaPaddleOCR:
    """Wrapper for vanilla PaddleOCR for comparison"""
    
    def __init__(self):
        """Initialize vanilla PaddleOCR"""
        if PADDLEOCR_AVAILABLE:
            self.ocr = PaddleOCR(
                use_angle_cls=True,
                lang='en',
                show_log=False
            )
        else:
            self.ocr = None
    
    def process_document(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Process document using vanilla PaddleOCR.
        
        Args:
            image: OpenCV image (BGR format)
            
        Returns:
            Structured results dictionary
        """
        if not PADDLEOCR_AVAILABLE or self.ocr is None:
            return self._mock_process(image)
        
        # Run OCR
        result = self.ocr.ocr(image, cls=True)
        
        # Format results
        return self._format_results(result, image)
    
    def _format_results(self, ocr_result: list, original_image: np.ndarray) -> Dict[str, Any]:
        """
        Format vanilla OCR results to match our structure.
        
        Args:
            ocr_result: Raw PaddleOCR result
            original_image: Original image for visualization
            
        Returns:
            Formatted result dictionary
        """
        # Extract text blocks
        text_blocks = []
        all_text = []
        
        if ocr_result and len(ocr_result) > 0:
            for page_result in ocr_result:
                if page_result:
                    for line in page_result:
                        if line:
                            bbox, (text, confidence) = line
                            text_blocks.append({
                                'text': text,
                                'bbox': [bbox[0][0], bbox[0][1], bbox[2][0], bbox[2][1]],
                                'confidence': confidence
                            })
                            all_text.append(text)
        
        # Try to extract basic structure from text
        structured_data = self._extract_basic_structure(all_text)
        
        # Build validation result (basic)
        validation = {
            'is_valid': True,  # Vanilla OCR doesn't do validation
            'overall_confidence': self._calculate_avg_confidence(text_blocks),
            'arithmetic_checks': {
                'subtotal_validation': {
                    'is_valid': False,  # Vanilla doesn't validate
                    'difference': None
                }
            },
            'errors': [],
            'warnings': ['Vanilla OCR does not perform financial validation'],
            'confidence_scores': {tb['text']: tb['confidence'] for tb in text_blocks[:5]}
        }
        
        return {
            'status': 'success',
            'data': structured_data,
            'validation': validation,
            'metadata': {
                'processing_time': 0.0,  # Would need timing
                'regions': [{'type': 'text', 'text': text} for text in all_text[:5]],
                'text_blocks': text_blocks
            },
            'visualization': self._create_visualization(original_image, text_blocks)
        }
    
    def _extract_basic_structure(self, all_text: list) -> Dict[str, Any]:
        """
        Try to extract basic structure from text.
        This is a simple heuristic-based extraction.
        """
        text_str = ' '.join(all_text).lower()
        
        # Try to find invoice number
        invoice_number = None
        for text in all_text:
            if 'invoice' in text.lower() and any(c.isdigit() for c in text):
                # Extract number-like pattern
                import re
                numbers = re.findall(r'[A-Z]{0,3}-?\d+', text.upper())
                if numbers:
                    invoice_number = numbers[0]
                    break
        
        # Try to find totals
        total = None
        for text in all_text:
            if 'total' in text.lower():
                import re
                amounts = re.findall(r'\$?[\d,]+\.?\d{0,2}', text)
                if amounts:
                    try:
                        total = float(amounts[-1].replace('$', '').replace(',', ''))
                        break
                    except ValueError:
                        pass
        
        return {
            'vendor': {'name': None},
            'client': {
                'invoice_number': invoice_number,
                'dates': {}
            },
            'line_items': [],
            'financial_summary': {
                'grand_total': total if total else 0.0,
                'subtotal': 0.0,
                'currency': 'USD'
            }
        }
    
    def _calculate_avg_confidence(self, text_blocks: list) -> float:
        """Calculate average confidence from text blocks"""
        if not text_blocks:
            return 0.0
        confidences = [tb.get('confidence', 0.0) for tb in text_blocks]
        return sum(confidences) / len(confidences) if confidences else 0.0
    
    def _create_visualization(self, image: np.ndarray, text_blocks: list) -> np.ndarray:
        """
        Create visualization with bounding boxes.
        """
        vis_image = image.copy()
        
        # Draw bounding boxes
        for block in text_blocks[:20]:  # Limit to first 20 blocks
            bbox = block.get('bbox', [])
            if len(bbox) == 4:
                x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
                cv2.rectangle(vis_image, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        return vis_image
    
    def _mock_process(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Mock processing when PaddleOCR is not available.
        Returns a basic structure for demo purposes.
        """
        return {
            'status': 'success',
            'data': {
                'vendor': {'name': 'Mock Vendor'},
                'client': {
                    'invoice_number': 'MOCK-001',
                    'dates': {}
                },
                'line_items': [],
                'financial_summary': {
                    'grand_total': 0.0,
                    'subtotal': 0.0,
                    'currency': 'USD'
                }
            },
            'validation': {
                'is_valid': False,
                'overall_confidence': 0.5,
                'arithmetic_checks': {
                    'subtotal_validation': {
                        'is_valid': False,
                        'difference': None
                    }
                },
                'errors': ['PaddleOCR not installed - using mock results'],
                'warnings': [],
                'confidence_scores': {}
            },
            'metadata': {
                'processing_time': 0.0,
                'regions': [],
                'text_blocks': []
            },
            'visualization': image.copy()
        }

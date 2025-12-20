"""
Fine-tuned PaddleOCR-VL pipeline wrapper for Streamlit demo.
Integrates with the existing FinancialDocumentProcessor.
"""
import cv2
import numpy as np
import asyncio
from typing import Dict, Any, Optional
import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.core.document_processor import FinancialDocumentProcessor
from app.config.settings import load_config


class FineTunedInvoiceAnalyzer:
    """Wrapper for the fine-tuned PaddleOCR-VL pipeline"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the fine-tuned model pipeline.
        
        Args:
            config: Optional configuration dict. If not provided, uses default config.
        """
        self.config = config or load_config()
        # Force model mode to use actual models (not mock) for demo
        # You can set MODEL_MODE environment variable to override
        self.config['model_mode'] = os.getenv('MODEL_MODE', self.config.get('model_mode', 'mock'))
        self.processor = FinancialDocumentProcessor(self.config)
    
    def process_document(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Process a document image through the fine-tuned pipeline.
        
        Args:
            image: OpenCV image (BGR format)
            
        Returns:
            Structured results dictionary with data, validation, and metadata
        """
        # Convert numpy array to bytes
        success, buffer = cv2.imencode('.jpg', image)
        if not success:
            raise ValueError("Failed to encode image")
        image_bytes = buffer.tobytes()
        
        # Run async processor in sync context
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Process document
        result = loop.run_until_complete(
            self.processor.process_document(image_bytes, "demo_invoice.jpg", model_type="fine_tuned")
        )
        
        # Transform result to demo format
        return self._format_results(result, image)
    
    def _format_results(self, processor_result: Dict[str, Any], original_image: np.ndarray) -> Dict[str, Any]:
        """
        Format the processor result into the demo's expected structure.
        
        Args:
            processor_result: Result from FinancialDocumentProcessor
            original_image: Original image for visualization
            
        Returns:
            Formatted result dictionary
        """
        if not processor_result.get('success', False):
            # Return error structure
            return {
                'status': 'error',
                'error': processor_result.get('error', 'Unknown error'),
                'data': {},
                'validation': {
                    'is_valid': False,
                    'errors': [processor_result.get('error', 'Processing failed')],
                    'overall_confidence': 0.0
                },
                'visualization': original_image
            }
        
        structured = processor_result.get('structured_output', {})
        validation = processor_result.get('validation', {})
        extracted_fields = processor_result.get('extracted_data', [])
        
        # Build data structure
        data = {
            'vendor': structured.get('vendor_block', {}),
            'client': structured.get('client_info', {}),
            'line_items': structured.get('line_items', []),
            'financial_summary': structured.get('financial_summary', {})
        }
        
        # Build validation structure
        validation_result = {
            'is_valid': validation.get('is_valid', False),
            'overall_confidence': self._calculate_overall_confidence(extracted_fields),
            'arithmetic_checks': {
                'subtotal_validation': {
                    'is_valid': validation.get('math_ok', False),
                    'difference': validation.get('issues', [])
                }
            },
            'errors': validation.get('issues', []),
            'warnings': [],
            'confidence_scores': self._extract_confidence_scores(extracted_fields)
        }
        
        # Create visualization
        visualization = self._create_visualization(original_image, structured, extracted_fields)
        
        return {
            'status': 'success',
            'data': data,
            'validation': validation_result,
            'metadata': {
                'processing_time': processor_result.get('metadata', {}).get('processing_time_ms', 0) / 1000.0,
                'regions': self._extract_regions(structured),
                'model_version': processor_result.get('metadata', {}).get('model_versions', {})
            },
            'visualization': visualization
        }
    
    def _calculate_overall_confidence(self, extracted_fields: list) -> float:
        """Calculate overall confidence from extracted fields"""
        if not extracted_fields:
            return 0.0
        confidences = [f.get('confidence', 0.0) for f in extracted_fields if isinstance(f.get('confidence'), (int, float))]
        return sum(confidences) / len(confidences) if confidences else 0.0
    
    def _extract_confidence_scores(self, extracted_fields: list) -> Dict[str, float]:
        """Extract confidence scores by field type"""
        scores = {}
        for field in extracted_fields:
            field_name = field.get('field_name', 'unknown')
            confidence = field.get('confidence', 0.0)
            if isinstance(confidence, (int, float)):
                scores[field_name] = confidence
        return scores
    
    def _extract_regions(self, structured: Dict[str, Any]) -> list:
        """Extract region information from structured data"""
        regions = []
        if structured.get('vendor_block'):
            regions.append({
                'type': 'vendor',
                'text': structured['vendor_block'].get('name', '')
            })
        if structured.get('client_info'):
            regions.append({
                'type': 'client',
                'text': structured['client_info'].get('invoice_number', '')
            })
        if structured.get('line_items'):
            regions.append({
                'type': 'line_items',
                'text': f"{len(structured['line_items'])} items"
            })
        return regions
    
    def _create_visualization(self, image: np.ndarray, structured: Dict[str, Any], extracted_fields: list) -> np.ndarray:
        """
        Create a simple visualization of the extracted data.
        In a full implementation, this would draw bounding boxes.
        """
        # For now, return the original image
        # In production, you'd use the visualizer utility to draw boxes
        return image.copy()

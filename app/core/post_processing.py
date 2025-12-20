"""
Phase 3: Post-Processing Intelligence

A robust FinancialDocumentProcessor that transforms raw, layout-aware OCR output
into validated, structured financial data. This layer ensures reliability and
demonstrates the practical utility of the fine-tuned model.
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from decimal import Decimal, ROUND_HALF_UP
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BoundingBox:
    """Represents a bounding box with coordinates and confidence"""
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float = 1.0
    
    @property
    def center(self) -> Tuple[float, float]:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)
    
    @property
    def area(self) -> float:
        return (self.x2 - self.x1) * (self.y2 - self.y1)
    
    def distance_to(self, other: 'BoundingBox') -> float:
        """Calculate Euclidean distance between box centers"""
        x1, y1 = self.center
        x2, y2 = other.center
        return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    
    def is_near(self, other: 'BoundingBox', threshold: float = 50.0) -> bool:
        """Check if two boxes are spatially close"""
        return self.distance_to(other) < threshold


@dataclass
class TextElement:
    """Represents a single text element with semantic information"""
    text: str
    bbox: BoundingBox
    element_type: str  # 'text', 'table_cell', 'header', 'footer'
    confidence: float = 1.0
    
    @property
    def is_numeric(self) -> bool:
        """Check if text appears to be a monetary amount or quantity"""
        # Patterns for currency: $100.00, €1.234,56, £1,000.50
        currency_pattern = r'^[$€£¥₹₩]\s*[\d,]+(\.\d{2})?$'
        # Patterns for numbers: 100.00, 1,234.56, (1.000,50)
        number_pattern = r'^[\(\-]?\s*[\d,]+([\.\,]\d{2,3})?[\)]?$'
        return bool(re.match(currency_pattern, self.text.strip()) or 
                   re.match(number_pattern, self.text.strip()))
    
    @property
    def is_date(self) -> bool:
        """Check if text appears to be a date"""
        date_patterns = [
            r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}',  # MM-DD-YYYY
            r'\d{4}[-/]\d{1,2}[-/]\d{1,2}',    # YYYY-MM-DD
            r'\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}'  # DD Mon YYYY
        ]
        return any(re.search(pattern, self.text, re.IGNORECASE) for pattern in date_patterns)
    
    @property
    def is_total_keyword(self) -> bool:
        """Check if text contains total-related keywords"""
        total_keywords = {'total', 'amount', 'sum', 'balance', 'grand', 'final', 'due'}
        text_lower = self.text.lower()
        return any(keyword in text_lower for keyword in total_keywords)


@dataclass
class DocumentRegion:
    """Represents a semantic region in the document"""
    region_type: str  # 'vendor', 'client', 'line_items', 'tax', 'totals'
    elements: List[TextElement]
    bbox: BoundingBox
    
    def get_text(self, delimiter: str = ' ') -> str:
        """Get concatenated text of all elements in region"""
        return delimiter.join(elem.text for elem in self.elements)
    
    def find_element_by_keyword(self, keywords: List[str]) -> Optional[TextElement]:
        """Find element containing specific keywords"""
        for elem in self.elements:
            elem_lower = elem.text.lower()
            if any(keyword.lower() in elem_lower for keyword in keywords):
                return elem
        return None


class FinancialDocumentPostProcessor:
    """
    Main class for post-processing OCR results into structured financial data.
    Implements layout analysis, business rule validation, and data structuring.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._default_config()
        self.currency_symbols = {'$', '€', '£', '¥', '₹', '₩'}
        self.date_formats = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d']
        
    def _default_config(self) -> Dict:
        """Default configuration for document processing"""
        return {
            'region_threshold': 50.0,  # Pixel threshold for region grouping
            'numeric_tolerance': 0.01,  # Tolerance for numerical comparisons
            'min_confidence': 0.7,      # Minimum confidence for text elements
            'currency_precision': 2,    # Decimal places for currency
            'validation': {
                'validate_arithmetic': True,
                'validate_dates': True,
                'check_duplicates': True,
                'enforce_positive': True
            }
        }
    
    def extract_financial_structure(self, ocr_results: Dict) -> Dict:
        """
        Main pipeline: Convert raw OCR results into validated structured data.
        
        Args:
            ocr_results: Dictionary containing OCR output from PaddleOCR-VL
                        with bounding boxes, text, and confidence scores.
        
        Returns:
            Dict: Structured financial data with validation results.
        """
        logger.info("Starting financial document processing pipeline")
        
        try:
            # 1. Parse OCR results into structured elements
            text_elements = self._parse_ocr_results(ocr_results)
            
            # 2. Identify semantic regions using layout coordinates
            document_regions = self._identify_semantic_regions(text_elements)
            
            # 3. Extract structured data from each region
            structured_data = self._extract_region_data(document_regions)
            
            # 4. Apply business rules and validation
            validation_results = self._validate_financial_data(structured_data)
            
            # 5. Enrich with metadata and confidence scores
            final_output = self._create_final_output(structured_data, validation_results)
            
            logger.info("Document processing completed successfully")
            return final_output
            
        except Exception as e:
            logger.error(f"Error processing document: {e}", exc_info=True)
            return self._create_error_output(str(e))
    
    def _parse_ocr_results(self, ocr_results: Dict) -> List[TextElement]:
        """Convert raw OCR output into structured TextElement objects"""
        elements = []
        
        # PaddleOCR-VL output structure may vary - handle different formats
        if 'pages' in ocr_results:
            # Structured output from fine-tuned model
            for page in ocr_results['pages']:
                for element in page.get('elements', []):
                    bbox = BoundingBox(
                        x1=element.get('bbox', [0, 0, 0, 0])[0],
                        y1=element.get('bbox', [0, 0, 0, 0])[1],
                        x2=element.get('bbox', [0, 0, 0, 0])[2],
                        y2=element.get('bbox', [0, 0, 0, 0])[3],
                        confidence=element.get('confidence', 1.0)
                    )
                    
                    text_elem = TextElement(
                        text=element.get('text', ''),
                        bbox=bbox,
                        element_type=element.get('type', 'text'),
                        confidence=element.get('confidence', 1.0)
                    )
                    
                    if text_elem.confidence >= self.config['min_confidence']:
                        elements.append(text_elem)
        
        elif 'text_regions' in ocr_results:
            # Alternative OCR output format
            for region in ocr_results['text_regions']:
                bbox = BoundingBox(
                    x1=region.get('coordinates', {}).get('x1', 0),
                    y1=region.get('coordinates', {}).get('y1', 0),
                    x2=region.get('coordinates', {}).get('x2', 0),
                    y2=region.get('coordinates', {}).get('y2', 0)
                )
                
                text_elem = TextElement(
                    text=region.get('text', ''),
                    bbox=bbox,
                    element_type='text',
                    confidence=region.get('confidence', 1.0)
                )
                
                if text_elem.confidence >= self.config['min_confidence']:
                    elements.append(text_elem)
        
        elif 'bboxes' in ocr_results and 'tokens' in ocr_results:
            # PaddleOCR-VL service format (from paddleocr_vl_service.py)
            tokens = ocr_results.get('tokens', [])
            bboxes = ocr_results.get('bboxes', [])
            
            # Match tokens with bboxes by index
            for i, token in enumerate(tokens):
                bbox_data = bboxes[i] if i < len(bboxes) else {}
                
                # Handle different bbox formats: [x, y, w, h] or {x, y, w, h}
                if isinstance(bbox_data, dict):
                    x = bbox_data.get('x', 0)
                    y = bbox_data.get('y', 0)
                    w = bbox_data.get('w', 0)
                    h = bbox_data.get('h', 0)
                    x1, y1 = x, y
                    x2, y2 = x + w, y + h
                elif isinstance(bbox_data, list) and len(bbox_data) >= 4:
                    x1, y1, x2, y2 = bbox_data[0], bbox_data[1], bbox_data[2], bbox_data[3]
                else:
                    # Fallback: use token position if available
                    x1, y1, x2, y2 = 0, 0, 0, 0
                
                bbox = BoundingBox(
                    x1=float(x1),
                    y1=float(y1),
                    x2=float(x2),
                    y2=float(y2),
                    confidence=token.get('confidence', 1.0)
                )
                
                text_elem = TextElement(
                    text=token.get('text', ''),
                    bbox=bbox,
                    element_type=bbox_data.get('region_type', 'text'),
                    confidence=token.get('confidence', 1.0)
                )
                
                if text_elem.confidence >= self.config['min_confidence']:
                    elements.append(text_elem)
        
        elif 'text_blocks' in ocr_results:
            # Alternative format with text_blocks
            for block in ocr_results['text_blocks']:
                box = block.get('box', [0, 0, 0, 0])
                bbox = BoundingBox(
                    x1=float(box[0]),
                    y1=float(box[1]),
                    x2=float(box[2]),
                    y2=float(box[3]),
                    confidence=block.get('confidence', 1.0)
                )
                
                text_elem = TextElement(
                    text=block.get('text', ''),
                    bbox=bbox,
                    element_type='text',
                    confidence=block.get('confidence', 1.0)
                )
                
                if text_elem.confidence >= self.config['min_confidence']:
                    elements.append(text_elem)
        
        logger.info(f"Parsed {len(elements)} text elements from OCR results")
        return elements
    
    def _identify_semantic_regions(self, elements: List[TextElement]) -> Dict[str, DocumentRegion]:
        """
        Use layout coordinates and content analysis to identify 5 key semantic regions.
        Implements rule-based spatial analysis enhanced with content hints.
        """
        regions = {}
        
        # Sort elements by Y then X coordinate (top-to-bottom, left-to-right reading order)
        sorted_elements = sorted(elements, key=lambda e: (e.bbox.y1, e.bbox.x1))
        
        # Initialize region groups
        vendor_elements = []
        client_elements = []
        line_item_elements = []
        tax_elements = []
        total_elements = []
        
        # Page dimensions for relative positioning
        if elements:
            all_x = [e.bbox.x2 for e in elements]
            all_y = [e.bbox.y2 for e in elements]
            page_width = max(all_x) if all_x else 1000
            page_height = max(all_y) if all_y else 1400
        else:
            page_width, page_height = 1000, 1400
        
        # Rule 1: Vendor block is typically top-left quadrant
        vendor_quadrant = page_width * 0.5, page_height * 0.3
        for elem in sorted_elements:
            if elem.bbox.center[0] < vendor_quadrant[0] and elem.bbox.center[1] < vendor_quadrant[1]:
                vendor_elements.append(elem)
        
        # Rule 2: Client/Invoice info is often top-right or near vendor
        client_keywords = ['invoice', 'bill to', 'client', 'customer', 'invoice no', 'date', 'due']
        for elem in sorted_elements:
            elem_lower = elem.text.lower()
            if (elem.bbox.center[0] > page_width * 0.5 or 
                any(keyword in elem_lower for keyword in client_keywords)):
                if elem not in vendor_elements:
                    client_elements.append(elem)
        
        # Rule 3: Line item table is typically large, centered area with numeric columns
        # Look for elements that form tabular structures
        numeric_elements = [e for e in sorted_elements if e.is_numeric]
        if numeric_elements:
            # Find cluster of numeric elements (likely the table)
            table_y_start = min(e.bbox.y1 for e in numeric_elements)
            table_y_end = max(e.bbox.y2 for e in numeric_elements)
            
            for elem in sorted_elements:
                if table_y_start <= elem.bbox.center[1] <= table_y_end:
                    # Check if element is near numeric elements (in table)
                    if any(elem.bbox.is_near(num_elem.bbox) for num_elem in numeric_elements[:10]):
                        if elem not in vendor_elements + client_elements:
                            line_item_elements.append(elem)
        
        # Rule 4: Tax & discount section is usually below line items, contains % or keywords
        tax_keywords = ['tax', 'vat', 'gst', 'discount', 'subtotal']
        for elem in sorted_elements:
            elem_lower = elem.text.lower()
            if any(keyword in elem_lower for keyword in tax_keywords):
                if elem not in line_item_elements + vendor_elements + client_elements:
                    tax_elements.append(elem)
        
        # Rule 5: Grand total is typically bottom-right, contains "Total" or large amount
        total_area_x_start = page_width * 0.6
        total_area_y_start = page_height * 0.7
        
        for elem in sorted_elements:
            if (elem.bbox.center[0] > total_area_x_start and 
                elem.bbox.center[1] > total_area_y_start):
                if elem not in tax_elements + line_item_elements:
                    total_elements.append(elem)
            elif elem.is_total_keyword and elem.is_numeric:
                total_elements.append(elem)
        
        # Create DocumentRegion objects
        regions['vendor'] = self._create_region('vendor', vendor_elements)
        regions['client'] = self._create_region('client', client_elements)
        regions['line_items'] = self._create_region('line_items', line_item_elements)
        regions['tax'] = self._create_region('tax', tax_elements)
        regions['totals'] = self._create_region('totals', total_elements)
        
        logger.info(f"Identified semantic regions: {list(regions.keys())}")
        return regions
    
    def _create_region(self, region_type: str, elements: List[TextElement]) -> DocumentRegion:
        """Create a DocumentRegion from elements, calculating overall bounding box"""
        if not elements:
            return DocumentRegion(region_type, [], BoundingBox(0, 0, 0, 0))
        
        x1 = min(e.bbox.x1 for e in elements)
        y1 = min(e.bbox.y1 for e in elements)
        x2 = max(e.bbox.x2 for e in elements)
        y2 = max(e.bbox.y2 for e in elements)
        
        bbox = BoundingBox(x1, y1, x2, y2)
        return DocumentRegion(region_type, elements, bbox)
    
    def _extract_region_data(self, regions: Dict[str, DocumentRegion]) -> Dict:
        """Extract structured data from each semantic region"""
        structured_data = {
            'vendor': self._extract_vendor_data(regions.get('vendor')),
            'client': self._extract_client_data(regions.get('client')),
            'line_items': self._extract_line_items(regions.get('line_items')),
            'taxes': self._extract_tax_data(regions.get('tax')),
            'totals': self._extract_total_data(regions.get('totals')),
            'metadata': self._extract_metadata(regions)
        }
        
        return structured_data
    
    def _extract_vendor_data(self, region: DocumentRegion) -> Dict:
        """Extract vendor information from vendor region"""
        if not region or not region.elements:
            return {}
        
        vendor_text = region.get_text('\n')
        
        # Simple parsing - in production, use more sophisticated NLP or regex
        vendor_data = {
            'raw_text': vendor_text,
            'name': '',
            'address': '',
            'contact': {},
            'confidence': sum(e.confidence for e in region.elements) / len(region.elements) if region.elements else 0
        }
        
        # Extract potential name (first line often contains name)
        lines = vendor_text.split('\n')
        if lines:
            vendor_data['name'] = lines[0]
        
        # Look for email and phone patterns
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        phone_pattern = r'\b[\d\(\)\s\-\+]{10,}\b'
        
        for elem in region.elements:
            text = elem.text
            if re.search(email_pattern, text):
                vendor_data['contact']['email'] = text
            elif re.search(phone_pattern, text.replace(' ', '')):
                vendor_data['contact']['phone'] = text
        
        return vendor_data
    
    def _extract_client_data(self, region: DocumentRegion) -> Dict:
        """Extract client and invoice metadata"""
        if not region or not region.elements:
            return {}
        
        client_data = {
            'invoice_number': '',
            'dates': {},
            'client_name': '',
            'raw_text': region.get_text('\n')
        }
        
        # Look for invoice number patterns
        invoice_patterns = [
            r'(?:invoice|inv|bill|order)[\s\#\:\-]*([A-Z0-9\-]+)',
            r'([A-Z]{2,}\d{4,})',
            r'(\d{4,}\-\d{2,})'
        ]
        
        # Look for date patterns
        date_pattern = r'\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})\b'
        
        for elem in region.elements:
            text = elem.text.lower()
            
            # Check for invoice number
            for pattern in invoice_patterns:
                match = re.search(pattern, elem.text, re.IGNORECASE)
                if match and not client_data['invoice_number']:
                    client_data['invoice_number'] = match.group(1).strip()
            
            # Check for dates
            date_match = re.search(date_pattern, elem.text)
            if date_match:
                date_str = date_match.group(1)
                # Parse and categorize date
                for date_format in self.date_formats:
                    try:
                        parsed_date = datetime.strptime(date_str, date_format)
                        date_key = 'invoice_date' if 'date' in text else 'due_date' if 'due' in text else 'date'
                        client_data['dates'][date_key] = parsed_date.strftime('%Y-%m-%d')
                        break
                    except ValueError:
                        continue
            
            # Client name might be a longer text not matching other patterns
            if len(elem.text) > 3 and not elem.is_numeric and not date_match:
                if not any(keyword in text for keyword in ['invoice', 'date', 'due', 'number', 'no']):
                    client_data['client_name'] = elem.text
        
        return client_data
    
    def _extract_line_items(self, region: DocumentRegion) -> List[Dict]:
        """Extract structured line items from table region"""
        if not region or len(region.elements) < 2:
            return []
        
        # Group elements by rows based on Y-coordinate
        rows = {}
        for elem in region.elements:
            row_key = round(elem.bbox.center[1] / 10) * 10  # Group by similar Y
            if row_key not in rows:
                rows[row_key] = []
            rows[row_key].append(elem)
        
        # Sort rows by Y position
        sorted_rows = sorted(rows.items())
        line_items = []
        
        # Assume first row might be headers
        headers = []
        if sorted_rows:
            # Sort elements in first row by X position
            first_row_elems = sorted(sorted_rows[0][1], key=lambda e: e.bbox.x1)
            headers = [e.text.lower() for e in first_row_elems]
        
        # Process remaining rows as data
        for row_key, row_elems in sorted_rows[1:]:  # Skip header row
            sorted_elems = sorted(row_elems, key=lambda e: e.bbox.x1)
            
            if len(sorted_elems) >= 3:  # Need at least description, qty, price
                item = {}
                
                # Map elements to headers if available
                for i, elem in enumerate(sorted_elems):
                    if i < len(headers):
                        header = headers[i]
                    else:
                        header = f'column_{i}'
                    
                    # Clean and parse values
                    if elem.is_numeric:
                        # Extract numeric value
                        clean_text = re.sub(r'[^\d\.,\-]', '', elem.text)
                        try:
                            # Handle different decimal separators
                            if ',' in clean_text and '.' in clean_text:
                                # 1.234,56 format
                                clean_text = clean_text.replace('.', '').replace(',', '.')
                            elif ',' in clean_text:
                                # European format
                                clean_text = clean_text.replace(',', '.')
                            
                            item[header] = float(clean_text)
                        except ValueError:
                            item[header] = elem.text
                    else:
                        item[header] = elem.text
                
                if item:  # Only add if we extracted meaningful data
                    # Calculate line total if we have quantity and price
                    if 'quantity' in item and 'price' in item:
                        if isinstance(item['quantity'], (int, float)) and isinstance(item['price'], (int, float)):
                            item['line_total'] = round(item['quantity'] * item['price'], 2)
                    elif 'unit price' in item and 'total' in item:
                        # Alternative header names
                        qty_key = next((k for k in item.keys() if 'qty' in k.lower() or 'quantity' in k.lower()), None)
                        if qty_key:
                            if isinstance(item[qty_key], (int, float)) and isinstance(item['unit price'], (int, float)):
                                item['line_total'] = round(item[qty_key] * item['unit price'], 2)
                    
                    line_items.append(item)
        
        return line_items
    
    def _extract_tax_data(self, region: DocumentRegion) -> Dict:
        """Extract tax and discount information"""
        if not region or not region.elements:
            return {}
        
        tax_data = {
            'tax_rate': 0.0,
            'tax_amount': 0.0,
            'discount_rate': 0.0,
            'discount_amount': 0.0,
            'subtotal': 0.0
        }
        
        for elem in region.elements:
            text = elem.text.lower()
            
            # Look for tax rate (usually contains %)
            if '%' in text and ('tax' in text or 'vat' in text or 'gst' in text):
                # Extract percentage
                rate_match = re.search(r'(\d+\.?\d*)%', text)
                if rate_match:
                    tax_data['tax_rate'] = float(rate_match.group(1))
            
            # Look for amounts
            if elem.is_numeric:
                clean_amount = self._extract_numeric_value(elem.text)
                
                if 'tax' in text or 'vat' in text or 'gst' in text:
                    tax_data['tax_amount'] = clean_amount
                elif 'discount' in text:
                    tax_data['discount_amount'] = clean_amount
                elif 'sub' in text or 'subtotal' in text:
                    tax_data['subtotal'] = clean_amount
        
        return tax_data
    
    def _extract_total_data(self, region: DocumentRegion) -> Dict:
        """Extract total amounts and payment terms"""
        if not region or not region.elements:
            return {}
        
        total_data = {
            'grand_total': 0.0,
            'amount_due': 0.0,
            'currency': '',
            'payment_terms': '',
            'raw_text': region.get_text('\n')
        }
        
        # Find the largest numeric value (likely grand total)
        numeric_elements = [e for e in region.elements if e.is_numeric]
        if numeric_elements:
            # Sort by value (extract numeric part)
            numeric_elements.sort(
                key=lambda e: self._extract_numeric_value(e.text),
                reverse=True
            )
            total_data['grand_total'] = self._extract_numeric_value(numeric_elements[0].text)
            
            # Determine currency from the total element
            for char in numeric_elements[0].text:
                if char in self.currency_symbols:
                    total_data['currency'] = char
                    break
        
        # Look for payment terms keywords
        terms_keywords = ['net', 'days', 'due', 'payment', 'terms', 'upon receipt']
        terms_elements = []
        for elem in region.elements:
            if any(keyword in elem.text.lower() for keyword in terms_keywords):
                terms_elements.append(elem)
        
        if terms_elements:
            total_data['payment_terms'] = ' '.join(e.text for e in terms_elements)
        
        return total_data
    
    def _extract_metadata(self, regions: Dict[str, DocumentRegion]) -> Dict:
        """Extract overall document metadata"""
        return {
            'region_count': len(regions),
            'total_elements': sum(len(r.elements) for r in regions.values() if r),
            'processing_timestamp': datetime.now().isoformat(),
            'region_types': list(regions.keys())
        }
    
    def _extract_numeric_value(self, text: str) -> float:
        """Extract numeric value from text, handling currency symbols and separators"""
        # Remove currency symbols and extra characters
        clean = re.sub(r'[^\d\.,\-]', '', text)
        
        if not clean:
            return 0.0
        
        # Handle different decimal separators
        if ',' in clean and '.' in clean:
            # Format like 1.234,56
            clean = clean.replace('.', '').replace(',', '.')
        elif ',' in clean:
            # European format or thousand separator
            if clean.count(',') == 1 and len(clean.split(',')[-1]) == 2:
                # Probably decimal comma
                clean = clean.replace(',', '.')
            else:
                # Probably thousand separator
                clean = clean.replace(',', '')
        
        try:
            return float(clean)
        except ValueError:
            return 0.0
    
    def _validate_financial_data(self, data: Dict) -> Dict:
        """
        Apply business rules and validation to extracted data.
        Returns validation results with confidence scores.
        """
        validation = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'confidence_scores': {},
            'arithmetic_checks': {}
        }
        
        # 1. Validate arithmetic relationships
        if self.config['validation']['validate_arithmetic']:
            self._validate_arithmetic(data, validation)
        
        # 2. Validate date consistency
        if self.config['validation']['validate_dates']:
            self._validate_dates(data, validation)
        
        # 3. Check for duplicates
        if self.config['validation']['check_duplicates']:
            self._check_duplicates(data, validation)
        
        # 4. Calculate confidence scores
        self._calculate_confidence(data, validation)
        
        validation['is_valid'] = len(validation['errors']) == 0
        
        return validation
    
    def _validate_arithmetic(self, data: Dict, validation: Dict):
        """Validate arithmetic relationships between amounts"""
        line_items = data.get('line_items', [])
        taxes = data.get('taxes', {})
        totals = data.get('totals', {})
        
        # Check 1: Line item calculations
        for i, item in enumerate(line_items):
            if 'quantity' in item and 'price' in item and 'line_total' in item:
                expected = item['quantity'] * item['price']
                actual = item['line_total']
                tolerance = self.config['numeric_tolerance']
                
                if abs(expected - actual) > tolerance:
                    validation['errors'].append(
                        f"Line item {i+1}: Calculated total ({expected:.2f}) "
                        f"doesn't match extracted total ({actual:.2f})"
                    )
        
        # Check 2: Subtotal + Tax - Discount = Grand Total
        subtotal = taxes.get('subtotal', 0)
        tax_amount = taxes.get('tax_amount', 0)
        discount_amount = taxes.get('discount_amount', 0)
        grand_total = totals.get('grand_total', 0)
        
        calculated_total = subtotal + tax_amount - discount_amount
        tolerance = self.config['numeric_tolerance']
        
        validation['arithmetic_checks']['subtotal_validation'] = {
            'calculated': calculated_total,
            'extracted': grand_total,
            'difference': abs(calculated_total - grand_total),
            'is_valid': abs(calculated_total - grand_total) <= tolerance
        }
        
        if abs(calculated_total - grand_total) > tolerance:
            validation['errors'].append(
                f"Arithmetic mismatch: Subtotal ({subtotal:.2f}) + Tax ({tax_amount:.2f}) "
                f"- Discount ({discount_amount:.2f}) = {calculated_total:.2f}, "
                f"but Grand Total is {grand_total:.2f}"
            )
    
    def _validate_dates(self, data: Dict, validation: Dict):
        """Validate date consistency"""
        dates = data.get('client', {}).get('dates', {})
        
        # Check if invoice date is before due date
        invoice_date_str = dates.get('invoice_date')
        due_date_str = dates.get('due_date')
        
        if invoice_date_str and due_date_str:
            try:
                invoice_date = datetime.strptime(invoice_date_str, '%Y-%m-%d')
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
                
                if due_date < invoice_date:
                    validation['errors'].append(
                        f"Due date ({due_date_str}) is before invoice date ({invoice_date_str})"
                    )
                
                # Check if dates are in the future (might be okay for proforma)
                today = datetime.now()
                if invoice_date > today:
                    validation['warnings'].append(
                        f"Invoice date ({invoice_date_str}) is in the future"
                    )
                    
            except ValueError:
                validation['warnings'].append("Could not parse dates for validation")
    
    def _check_duplicates(self, data: Dict, validation: Dict):
        """Check for potential duplicate line items"""
        line_items = data.get('line_items', [])
        
        seen_descriptions = set()
        for i, item in enumerate(line_items):
            description = item.get('description', '')
            if description and description in seen_descriptions:
                validation['warnings'].append(
                    f"Possible duplicate line item: '{description}'"
                )
            seen_descriptions.add(description)
    
    def _calculate_confidence(self, data: Dict, validation: Dict):
        """Calculate confidence scores for different data sections"""
        confidence_scores = {}
        
        # Vendor confidence
        vendor = data.get('vendor', {})
        confidence_scores['vendor'] = vendor.get('confidence', 0.5)
        
        # Client confidence based on completeness
        client = data.get('client', {})
        client_score = 0.0
        if client.get('invoice_number'):
            client_score += 0.3
        if client.get('dates', {}).get('invoice_date'):
            client_score += 0.3
        if client.get('client_name'):
            client_score += 0.2
        confidence_scores['client'] = client_score
        
        # Line items confidence
        line_items = data.get('line_items', [])
        if line_items:
            avg_item_confidence = 0.7  # Base confidence
            # Higher confidence if we have many items with calculated totals
            valid_items = sum(1 for item in line_items if 'line_total' in item)
            if valid_items > 0:
                avg_item_confidence = 0.5 + (valid_items / len(line_items)) * 0.5
            confidence_scores['line_items'] = avg_item_confidence
        else:
            confidence_scores['line_items'] = 0.0
        
        # Arithmetic validation confidence
        arith_check = validation['arithmetic_checks'].get('subtotal_validation', {})
        if arith_check.get('is_valid', False):
            confidence_scores['arithmetic'] = 0.9
        else:
            # Lower confidence based on magnitude of error
            error = arith_check.get('difference', 0)
            if error == 0:
                confidence_scores['arithmetic'] = 0.5
            else:
                confidence_scores['arithmetic'] = max(0.1, 0.5 - min(error / 100, 0.4))
        
        validation['confidence_scores'] = confidence_scores
        
        # Overall confidence (weighted average)
        weights = {'vendor': 0.1, 'client': 0.2, 'line_items': 0.4, 'arithmetic': 0.3}
        overall = sum(confidence_scores.get(k, 0) * weights.get(k, 0) for k in weights)
        validation['overall_confidence'] = overall
    
    def _create_final_output(self, data: Dict, validation: Dict) -> Dict:
        """Create the final structured output with validation results"""
        return {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'data': {
                'vendor': data.get('vendor', {}),
                'client': data.get('client', {}),
                'line_items': data.get('line_items', []),
                'financial_summary': {
                    'subtotal': data.get('taxes', {}).get('subtotal', 0),
                    'tax': {
                        'rate': data.get('taxes', {}).get('tax_rate', 0),
                        'amount': data.get('taxes', {}).get('tax_amount', 0)
                    },
                    'discount': {
                        'rate': data.get('taxes', {}).get('discount_rate', 0),
                        'amount': data.get('taxes', {}).get('discount_amount', 0)
                    },
                    'grand_total': data.get('totals', {}).get('grand_total', 0),
                    'currency': data.get('totals', {}).get('currency', ''),
                    'payment_terms': data.get('totals', {}).get('payment_terms', '')
                }
            },
            'validation': validation,
            'metadata': data.get('metadata', {}),
            'version': '1.0'
        }
    
    def _create_error_output(self, error_message: str) -> Dict:
        """Create error output when processing fails"""
        return {
            'success': False,
            'timestamp': datetime.now().isoformat(),
            'error': error_message,
            'data': {},
            'validation': {
                'is_valid': False,
                'errors': [error_message],
                'warnings': [],
                'confidence_scores': {},
                'overall_confidence': 0.0
            },
            'metadata': {},
            'version': '1.0'
        }
    
    def process_ocr_output(self, ocr_results: Dict) -> Dict:
        """Public interface for processing OCR results"""
        return self.extract_financial_structure(ocr_results)


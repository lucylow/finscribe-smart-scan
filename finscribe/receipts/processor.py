"""
Receipt Processor for extracting structured data from receipt images.
Integrates with PaddleOCR-VL and the existing document processing pipeline.
"""

import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
import cv2
import numpy as np
from PIL import Image
import logging

logger = logging.getLogger(__name__)

class ReceiptProcessor:
    """Specialized processor for receipt documents"""
    
    def __init__(self, paddleocr_service=None):
        self.paddleocr = paddleocr_service
        self.receipt_types = ['grocery', 'restaurant', 'retail', 'gas', 'pharmacy']
        
    def detect_receipt_type(self, ocr_text: str) -> str:
        """Detect the type of receipt based on content"""
        text_lower = ocr_text.lower()
        
        if any(word in text_lower for word in ['burger', 'pizza', 'restaurant', 'menu', 'tip']):
            return 'restaurant'
        elif any(word in text_lower for word in ['grocery', 'supermarket', 'walmart', 'target', 'kroger']):
            return 'grocery'
        elif any(word in text_lower for word in ['pharmacy', 'rx', 'prescription', 'cvs', 'walgreens']):
            return 'pharmacy'
        elif any(word in text_lower for word in ['gas', 'petrol', 'fuel', 'station']):
            return 'gas'
        else:
            return 'retail'
    
    def extract_receipt_data(self, ocr_results: Dict[str, Any]) -> Dict:
        """Extract structured data from OCR results"""
        if not ocr_results:
            return {"error": "No OCR results provided"}
        
        # Extract text lines from OCR results
        lines = self._extract_lines_from_ocr(ocr_results)
        
        if not lines:
            return {"error": "No text detected"}
        
        # Parse receipt structure
        receipt_data = self._parse_receipt_structure(lines)
        
        # Add receipt type detection
        full_text = ' '.join([line['text'] for line in lines])
        receipt_data['receipt_type'] = self.detect_receipt_type(full_text)
        
        return receipt_data
    
    def _extract_lines_from_ocr(self, ocr_results: Dict[str, Any]) -> List[Dict]:
        """Extract text lines with positions from OCR results"""
        lines = []
        
        # Handle different OCR output formats
        if 'tokens' in ocr_results and 'bboxes' in ocr_results:
            # PaddleOCR-VL format
            tokens = ocr_results.get('tokens', [])
            bboxes = ocr_results.get('bboxes', [])
            
            for i, token in enumerate(tokens):
                if isinstance(token, dict):
                    text = token.get('text', '')
                    confidence = token.get('confidence', 0.9)
                else:
                    text = str(token)
                    confidence = 0.9
                
                bbox = bboxes[i] if i < len(bboxes) else {}
                
                # Calculate center
                if isinstance(bbox, dict):
                    x = bbox.get('x', 0)
                    y = bbox.get('y', 0)
                    w = bbox.get('w', 0)
                    h = bbox.get('h', 0)
                    center_x = x + w / 2
                    center_y = y + h / 2
                    bbox_list = [[x, y], [x+w, y], [x+w, y+h], [x, y+h]]
                else:
                    center_x = 0
                    center_y = 0
                    bbox_list = []
                
                lines.append({
                    'text': text,
                    'bbox': bbox_list,
                    'center': (center_x, center_y),
                    'confidence': confidence
                })
        
        elif 'regions' in ocr_results:
            # Alternative format with regions
            for region in ocr_results.get('regions', []):
                if isinstance(region, dict) and 'content' in region:
                    text = region.get('content', '')
                    lines.append({
                        'text': text,
                        'bbox': [],
                        'center': (0, 0),
                        'confidence': 0.9
                    })
        
        # Sort lines by vertical position (top to bottom)
        lines.sort(key=lambda x: x['center'][1] if x['center'][1] > 0 else 0)
        
        return lines
    
    def _parse_receipt_structure(self, lines: List[Dict]) -> Dict:
        """Parse receipt structure from OCR lines"""
        receipt_data = {
            'merchant_info': {},
            'transaction_info': {},
            'items': [],
            'totals': {},
            'payment_info': {},
            'raw_lines': lines
        }
        
        if len(lines) < 2:
            return receipt_data
        
        # Group lines by vertical regions
        header_end = len(lines) // 3
        header_lines = lines[:header_end]
        
        footer_start = int(len(lines) * 0.8)
        footer_lines = lines[footer_start:]
        
        middle_lines = lines[header_end:footer_start]
        
        # Parse header for merchant info
        receipt_data['merchant_info'] = self._parse_merchant_info(header_lines)
        
        # Parse transaction info from header
        receipt_data['transaction_info'] = self._parse_transaction_info(header_lines)
        
        # Parse items from middle section
        receipt_data['items'] = self._parse_items(middle_lines)
        
        # Parse totals from middle/footer
        receipt_data['totals'] = self._parse_totals(middle_lines + footer_lines)
        
        # Parse payment info from footer
        receipt_data['payment_info'] = self._parse_payment_info(footer_lines)
        
        return receipt_data
    
    def _parse_merchant_info(self, lines: List[Dict]) -> Dict:
        """Extract merchant information"""
        merchant_info = {
            'name': '',
            'address': '',
            'phone': ''
        }
        
        # Look for merchant name (usually first non-empty line)
        for line in lines[:5]:
            text = line['text'].strip()
            if text and len(text) > 2:
                merchant_info['name'] = text
                break
        
        # Look for address patterns
        address_pattern = r'\d+\s+[A-Za-z\s]+(?:STREET|ST|AVENUE|AVE|ROAD|RD|BOULEVARD|BLVD)'
        phone_pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        
        for line in lines:
            text = line['text']
            
            # Check for address
            if re.search(address_pattern, text, re.IGNORECASE):
                merchant_info['address'] = text
            
            # Check for phone
            phone_match = re.search(phone_pattern, text)
            if phone_match:
                merchant_info['phone'] = phone_match.group()
        
        return merchant_info
    
    def _parse_transaction_info(self, lines: List[Dict]) -> Dict:
        """Extract transaction information"""
        transaction_info = {
            'date': '',
            'time': '',
            'receipt_number': '',
            'cashier': '',
            'register': ''
        }
        
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{2,4}',
            r'\d{4}-\d{2}-\d{2}',
            r'\d{1,2}-[A-Za-z]{3}-\d{2,4}'
        ]
        
        time_pattern = r'\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)?'
        
        for line in lines:
            text = line['text'].upper()
            
            # Look for date
            for pattern in date_patterns:
                date_match = re.search(pattern, text)
                if date_match:
                    transaction_info['date'] = date_match.group()
                    break
            
            # Look for time
            time_match = re.search(time_pattern, text, re.IGNORECASE)
            if time_match:
                transaction_info['time'] = time_match.group()
            
            # Look for receipt number
            if 'RECEIPT' in text or 'REC#' in text or 'NO.' in text:
                numbers = re.findall(r'\d+', text)
                if numbers:
                    transaction_info['receipt_number'] = numbers[-1]
            
            # Look for cashier/register
            if 'CASHIER' in text:
                cashier_match = re.search(r'CASHIER[:\s]*([A-Z0-9]+)', text)
                if cashier_match:
                    transaction_info['cashier'] = cashier_match.group(1)
            
            if 'REGISTER' in text or 'REG#' in text:
                register_match = re.search(r'REG(?:ISTER)?[:\s#]*([A-Z0-9]+)', text)
                if register_match:
                    transaction_info['register'] = register_match.group(1)
        
        return transaction_info
    
    def _parse_items(self, lines: List[Dict]) -> List[Dict]:
        """Parse line items from receipt"""
        items = []
        
        # Find the items section
        item_section_start = -1
        
        for i, line in enumerate(lines):
            text = line['text'].upper()
            
            if 'QTY' in text or ('ITEM' in text and 'PRICE' in text):
                item_section_start = i + 1
                break
        
        if item_section_start == -1:
            # Try to find items by pattern matching
            for i, line in enumerate(lines):
                text = line['text']
                if re.search(r'\$\d+\.\d{2}', text):
                    item_section_start = i
                    break
        
        if item_section_start == -1:
            return items
        
        # Parse items until we hit totals
        i = item_section_start
        while i < len(lines):
            line = lines[i]
            text = line['text']
            
            if not text.strip():
                i += 1
                continue
            
            if self._is_total_line(text):
                break
            
            item = self._parse_single_item(text, line.get('bbox', []))
            if item:
                items.append(item)
            
            i += 1
        
        return items
    
    def _parse_single_item(self, text: str, bbox: List) -> Optional[Dict]:
        """Parse a single line item"""
        text = ' '.join(text.split())
        
        # Look for price at the end
        price_match = re.search(r'(\$\d+\.\d{2})$', text)
        if not price_match:
            price_match = re.search(r'(\d+\.\d{2})$', text)
        
        if price_match:
            price = float(price_match.group(1).replace('$', ''))
            item_text = text[:price_match.start()].strip()
            
            # Try to extract quantity
            qty_match = re.search(r'(\d+)\s*[Xx@]\s*$', item_text)
            if qty_match:
                quantity = int(qty_match.group(1))
                description = item_text[:qty_match.start()].strip()
            else:
                qty_match = re.match(r'^(\d+)\s+', item_text)
                if qty_match:
                    quantity = int(qty_match.group(1))
                    description = item_text[qty_match.end():].strip()
                else:
                    quantity = 1
                    description = item_text
            
            return {
                'description': description,
                'quantity': quantity,
                'unit_price': round(price / quantity, 2) if quantity > 0 else price,
                'total': price,
                'bbox': bbox
            }
        
        return None
    
    def _is_total_line(self, text: str) -> bool:
        """Check if line contains total information"""
        total_keywords = ['TOTAL', 'SUBTOTAL', 'TAX', 'BALANCE', 'AMOUNT', 'CHANGE']
        text_upper = text.upper()
        return any(keyword in text_upper for keyword in total_keywords)
    
    def _parse_totals(self, lines: List[Dict]) -> Dict:
        """Parse total amounts from receipt"""
        totals = {
            'subtotal': 0.0,
            'tax': 0.0,
            'total': 0.0,
            'discount': 0.0
        }
        
        for line in lines:
            text = line['text'].upper()
            
            if 'SUBTOTAL' in text:
                amount = self._extract_amount(text)
                if amount:
                    totals['subtotal'] = amount
            elif 'TAX' in text or 'VAT' in text or 'GST' in text:
                amount = self._extract_amount(text)
                if amount:
                    totals['tax'] = amount
            elif 'TOTAL' in text and 'SUBTOTAL' not in text:
                amount = self._extract_amount(text)
                if amount:
                    totals['total'] = amount
            elif 'DISCOUNT' in text or 'SAVINGS' in text:
                amount = self._extract_amount(text)
                if amount:
                    totals['discount'] = amount
        
        return totals
    
    def _parse_payment_info(self, lines: List[Dict]) -> Dict:
        """Parse payment information"""
        payment_info = {
            'method': '',
            'amount_tendered': 0.0,
            'change': 0.0
        }
        
        for line in lines:
            text = line['text'].upper()
            
            payment_methods = ['CASH', 'VISA', 'MASTERCARD', 'AMEX', 'DEBIT', 'CREDIT']
            for method in payment_methods:
                if method in text:
                    payment_info['method'] = method
                    break
            
            if 'TENDERED' in text or 'CASH' in text:
                amount = self._extract_amount(text)
                if amount:
                    payment_info['amount_tendered'] = amount
            
            if 'CHANGE' in text:
                amount = self._extract_amount(text)
                if amount:
                    payment_info['change'] = amount
        
        return payment_info
    
    def _extract_amount(self, text: str) -> Optional[float]:
        """Extract monetary amount from text"""
        patterns = [
            r'\$(\d+\.\d{2})',
            r'(\d+\.\d{2})',
            r'\$(\d+)',
            r'(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        
        return None
    
    def validate_receipt(self, receipt_data: Dict) -> Dict:
        """Validate receipt data consistency"""
        validation = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'arithmetic_checks': {}
        }
        
        items = receipt_data.get('items', [])
        totals = receipt_data.get('totals', {})
        
        # Calculate subtotal from items
        calculated_subtotal = sum(item.get('total', 0) for item in items)
        extracted_subtotal = totals.get('subtotal', 0)
        
        # Check subtotal consistency
        if calculated_subtotal > 0 and extracted_subtotal > 0:
            diff = abs(calculated_subtotal - extracted_subtotal)
            if diff > 0.01:  # Tolerance of 1 cent
                validation['errors'].append(
                    f"Subtotal mismatch: Calculated ${calculated_subtotal:.2f}, "
                    f"Extracted ${extracted_subtotal:.2f}"
                )
                validation['is_valid'] = False
        
        # Check total consistency
        extracted_total = totals.get('total', 0)
        tax = totals.get('tax', 0)
        discount = totals.get('discount', 0)
        
        if extracted_total > 0 and extracted_subtotal > 0:
            calculated_total = extracted_subtotal + tax - discount
            diff = abs(calculated_total - extracted_total)
            
            validation['arithmetic_checks']['total_check'] = {
                'calculated': calculated_total,
                'extracted': extracted_total,
                'difference': diff,
                'is_valid': diff <= 0.01
            }
            
            if diff > 0.01:
                validation['warnings'].append(
                    f"Total calculation mismatch: Expected ${calculated_total:.2f}, "
                    f"Found ${extracted_total:.2f}"
                )
        
        # Check for missing critical information
        if not receipt_data.get('merchant_info', {}).get('name'):
            validation['warnings'].append("Missing merchant name")
        
        if not receipt_data.get('transaction_info', {}).get('date'):
            validation['warnings'].append("Missing transaction date")
        
        if len(items) == 0:
            validation['warnings'].append("No items found on receipt")
        
        return validation
    
    def process_receipt_from_ocr(self, ocr_results: Dict[str, Any]) -> Dict:
        """Complete pipeline for processing receipt from OCR results"""
        # Extract data
        receipt_data = self.extract_receipt_data(ocr_results)
        
        if 'error' in receipt_data:
            return {
                'success': False,
                'error': receipt_data['error'],
                'timestamp': datetime.now().isoformat()
            }
        
        # Validate
        validation = self.validate_receipt(receipt_data)
        
        # Create final output
        output = {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'receipt_type': receipt_data.get('receipt_type', 'unknown'),
            'data': {
                'merchant_info': receipt_data.get('merchant_info', {}),
                'transaction_info': receipt_data.get('transaction_info', {}),
                'items': receipt_data.get('items', []),
                'totals': receipt_data.get('totals', {}),
                'payment_info': receipt_data.get('payment_info', {})
            },
            'validation': validation,
            'metadata': {
                'total_items': len(receipt_data.get('items', [])),
                'total_amount': receipt_data.get('totals', {}).get('total', 0)
            }
        }
        
        return output



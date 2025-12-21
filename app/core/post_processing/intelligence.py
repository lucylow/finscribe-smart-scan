"""
Post-Processing Intelligence Layer for Financial Document Extraction

This module implements the intelligent post-processing layer that extracts
structured financial data from OCR results using layout understanding and
business rules. It identifies semantic regions and applies domain-specific
logic to extract vendor info, line items, totals, etc.
"""

import re
import json
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class FinancialPostProcessor:
    """
    Intelligent post-processor that extracts structured financial data
    from OCR results using layout coordinates and business rules.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.currency_patterns = {
            'USD': r'\$|USD|US\$',
            'EUR': r'€|EUR|EU€',
            'GBP': r'£|GBP',
            'JPY': r'¥|JPY|JP¥',
        }
        self.date_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
            r'\d{2}-\d{2}-\d{4}',  # MM-DD-YYYY
            r'\d{1,2}/\d{1,2}/\d{4}',  # M/D/YYYY
        ]
    
    def extract_financial_structure(self, ocr_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main extraction function that processes OCR results into structured financial data.
        
        Args:
            ocr_results: Raw OCR output from PaddleOCR-VL
            
        Returns:
            Structured financial data dictionary
        """
        # Extract tokens and bounding boxes
        tokens = ocr_results.get('tokens', [])
        bboxes = ocr_results.get('bboxes', [])
        regions = ocr_results.get('regions', [])
        
        # Step 1: Identify semantic regions using layout coordinates
        semantic_regions = self._identify_semantic_regions(tokens, bboxes, regions)
        
        # Step 2: Extract vendor information
        vendor_data = self._extract_vendor_block(semantic_regions.get('vendor', []))
        
        # Step 3: Extract client and invoice metadata
        invoice_info = self._extract_invoice_info(semantic_regions.get('header', []))
        
        # Step 4: Extract line items table
        line_items = self._extract_line_items(semantic_regions.get('table', []))
        
        # Step 5: Extract financial summary (totals, tax, etc.)
        financial_summary = self._extract_financial_summary(
            semantic_regions.get('summary', []),
            semantic_regions.get('total', [])
        )
        
        # Step 6: Validate and normalize
        normalized_data = self._normalize_and_validate({
            'vendor': vendor_data,
            'invoice_info': invoice_info,
            'line_items': line_items,
            'financial_summary': financial_summary
        })
        
        return normalized_data
    
    def _identify_semantic_regions(
        self,
        tokens: List[Dict],
        bboxes: List[Dict],
        regions: List[Dict]
    ) -> Dict[str, List[Dict]]:
        """
        Identify semantic regions based on bounding boxes and region types.
        
        Returns:
            Dictionary mapping region types to their tokens/bboxes
        """
        semantic_regions = {
            'header': [],
            'vendor': [],
            'client': [],
            'table': [],
            'summary': [],
            'total': []
        }
        
        # Group tokens by region type
        for i, bbox in enumerate(bboxes):
            region_type = bbox.get('region_type', 'unknown')
            if region_type in semantic_regions:
                token_idx = bbox.get('token_index', i)
                if token_idx < len(tokens):
                    semantic_regions[region_type].append({
                        'token': tokens[token_idx],
                        'bbox': bbox
                    })
        
        # Also use explicit region information if available
        for region in regions:
            region_type = region.get('type', '').lower()
            if region_type in semantic_regions:
                semantic_regions[region_type].append({
                    'content': region.get('content', ''),
                    'bbox': region.get('bbox', {})
                })
        
        return semantic_regions
    
    def _extract_vendor_block(self, vendor_tokens: List[Dict]) -> Dict[str, Any]:
        """Extract vendor information from vendor block tokens."""
        vendor_data = {
            'name': None,
            'address': None,
            'contact': {}
        }
        
        # Combine all text from vendor tokens
        vendor_text = ' '.join([
            t.get('token', {}).get('text', '') if isinstance(t, dict) and 'token' in t else str(t)
            for t in vendor_tokens
        ])
        
        # Extract company name (usually first line or largest text)
        lines = vendor_text.split('\n')
        if lines:
            vendor_data['name'] = lines[0].strip()
        
        # Extract address (look for street address patterns)
        address_pattern = r'\d+\s+[\w\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr)'
        address_match = re.search(address_pattern, vendor_text, re.IGNORECASE)
        if address_match:
            vendor_data['address'] = address_match.group(0)
        
        # Extract phone and email
        phone_pattern = r'[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}'
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        
        phone_match = re.search(phone_pattern, vendor_text)
        if phone_match:
            vendor_data['contact']['phone'] = phone_match.group(0)
        
        email_match = re.search(email_pattern, vendor_text)
        if email_match:
            vendor_data['contact']['email'] = email_match.group(0)
        
        return vendor_data
    
    def _extract_invoice_info(self, header_tokens: List[Dict]) -> Dict[str, Any]:
        """Extract invoice number, date, and due date from header."""
        invoice_info = {
            'invoice_number': None,
            'issue_date': None,
            'due_date': None
        }
        
        # Combine header text
        header_text = ' '.join([
            t.get('token', {}).get('text', '') if isinstance(t, dict) and 'token' in t else str(t)
            for t in header_tokens
        ])
        
        # Extract invoice number
        invoice_patterns = [
            r'Invoice\s*[#:]?\s*([A-Z0-9\-]+)',
            r'INV[#:]?\s*([A-Z0-9\-]+)',
            r'Invoice\s*Number[:\s]+([A-Z0-9\-]+)'
        ]
        for pattern in invoice_patterns:
            match = re.search(pattern, header_text, re.IGNORECASE)
            if match:
                invoice_info['invoice_number'] = match.group(1)
                break
        
        # Extract dates
        for pattern in self.date_patterns:
            matches = re.findall(pattern, header_text)
            if matches:
                if not invoice_info['issue_date']:
                    invoice_info['issue_date'] = matches[0]
                elif not invoice_info['due_date'] and len(matches) > 1:
                    invoice_info['due_date'] = matches[1]
        
        return invoice_info
    
    def _extract_line_items(self, table_tokens: List[Dict]) -> List[Dict[str, Any]]:
        """
        Extract line items from table region.
        This is the most complex extraction as it requires table structure understanding.
        """
        line_items = []
        
        # Combine table text
        table_text = ' '.join([
            t.get('token', {}).get('text', '') if isinstance(t, dict) and 'token' in t else str(t)
            for t in table_tokens
        ])
        
        # Try to parse as structured table
        # Look for pipe-separated or tab-separated values
        lines = table_text.split('\n')
        
        for line in lines:
            # Skip header rows
            if any(keyword in line.lower() for keyword in ['description', 'qty', 'quantity', 'price', 'total', 'amount']):
                continue
            
            # Try to parse line item
            # Pattern: description | quantity | unit_price | total
            parts = re.split(r'\s*\|\s*|\s{2,}|\t+', line.strip())
            
            if len(parts) >= 3:
                try:
                    description = parts[0].strip()
                    quantity = self._parse_number(parts[1]) if len(parts) > 1 else 1.0
                    unit_price = self._parse_number(parts[2]) if len(parts) > 2 else 0.0
                    line_total = self._parse_number(parts[3]) if len(parts) > 3 else (quantity * unit_price)
                    
                    line_items.append({
                        'description': description,
                        'quantity': float(quantity),
                        'unit_price': float(unit_price),
                        'line_total': float(line_total)
                    })
                except (ValueError, IndexError):
                    continue
        
        return line_items
    
    def _extract_financial_summary(
        self,
        summary_tokens: List[Dict],
        total_tokens: List[Dict]
    ) -> Dict[str, Any]:
        """Extract subtotal, tax, discount, and grand total."""
        financial_summary = {
            'subtotal': None,
            'tax_total': None,
            'discount_total': None,
            'grand_total': None,
            'currency': 'USD'
        }
        
        # Combine all summary text
        summary_text = ' '.join([
            t.get('token', {}).get('text', '') if isinstance(t, dict) and 'token' in t else str(t)
            for t in summary_tokens + total_tokens
        ])
        
        # Extract currency
        for currency, pattern in self.currency_patterns.items():
            if re.search(pattern, summary_text):
                financial_summary['currency'] = currency
                break
        
        # Extract subtotal
        subtotal_patterns = [
            r'Subtotal[:\s]+([\d,]+\.?\d*)',
            r'Sub-total[:\s]+([\d,]+\.?\d*)',
            r'Sub\s+Total[:\s]+([\d,]+\.?\d*)'
        ]
        for pattern in subtotal_patterns:
            match = re.search(pattern, summary_text, re.IGNORECASE)
            if match:
                financial_summary['subtotal'] = self._parse_number(match.group(1))
                break
        
        # Extract tax
        tax_patterns = [
            r'Tax[:\s]+\(?(\d+\.?\d*)%?\)?[:\s]+([\d,]+\.?\d*)',
            r'Tax\s+Total[:\s]+([\d,]+\.?\d*)',
            r'VAT[:\s]+([\d,]+\.?\d*)'
        ]
        for pattern in tax_patterns:
            match = re.search(pattern, summary_text, re.IGNORECASE)
            if match:
                financial_summary['tax_total'] = self._parse_number(match.group(-1))
                break
        
        # Extract discount
        discount_patterns = [
            r'Discount[:\s]+([\d,]+\.?\d*)',
            r'Discount\s+Total[:\s]+([\d,]+\.?\d*)'
        ]
        for pattern in discount_patterns:
            match = re.search(pattern, summary_text, re.IGNORECASE)
            if match:
                financial_summary['discount_total'] = self._parse_number(match.group(1))
                break
        
        # Extract grand total (usually the largest number or explicitly labeled)
        total_patterns = [
            r'Total[:\s]+([\d,]+\.?\d*)',
            r'Grand\s+Total[:\s]+([\d,]+\.?\d*)',
            r'Amount\s+Due[:\s]+([\d,]+\.?\d*)'
        ]
        for pattern in total_patterns:
            match = re.search(pattern, summary_text, re.IGNORECASE)
            if match:
                financial_summary['grand_total'] = self._parse_number(match.group(1))
                break
        
        return financial_summary
    
    def _parse_number(self, text: str) -> Decimal:
        """Parse number from text, removing currency symbols and commas."""
        # Remove currency symbols and commas
        cleaned = re.sub(r'[^\d\.\-]', '', str(text))
        try:
            return Decimal(cleaned)
        except:
            return Decimal('0')
    
    def _normalize_and_validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize and validate extracted data."""
        normalized = data.copy()
        
        # Validate arithmetic: subtotal + tax - discount = grand_total
        financial = normalized.get('financial_summary', {})
        line_items = normalized.get('line_items', [])
        
        # Calculate expected subtotal from line items
        calculated_subtotal = sum(item.get('line_total', 0) for item in line_items)
        
        # If we have both calculated and extracted subtotals, prefer calculated
        if calculated_subtotal > 0:
            financial['subtotal'] = float(calculated_subtotal)
        
        # Validate totals match
        subtotal = financial.get('subtotal', 0) or 0
        tax = financial.get('tax_total', 0) or 0
        discount = financial.get('discount_total', 0) or 0
        grand_total = financial.get('grand_total', 0) or 0
        
        expected_total = subtotal + tax - discount
        
        # Add validation flags
        normalized['validation'] = {
            'arithmetic_valid': abs(expected_total - grand_total) < 0.01,
            'expected_total': float(expected_total),
            'extracted_total': float(grand_total),
            'difference': float(abs(expected_total - grand_total))
        }
        
        return normalized



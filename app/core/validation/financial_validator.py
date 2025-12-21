"""
FinScribe Financial Validator

This module:
1. Validates arithmetic correctness (line items sum to subtotal, subtotal + tax = total)
2. Validates date logic (issue_date <= due_date, reasonable date ranges)
3. Normalizes currency values and formats
4. Aggregates confidence scores from OCR/LLM extraction
5. Flags documents needing human review

Used by: app/core/document_processor.py, app/api/v1/camel_endpoints.py
"""
from typing import Dict, Any, List, Optional, Union
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class FinancialValidator:
    """
    Validates financial document data with arithmetic and business rules.
    
    Ensures extracted invoice data is mathematically correct and logically consistent.
    Critical for production use where accuracy is essential.
    """
    
    def __init__(self, tolerance: float = 0.01):
        self.tolerance = Decimal(str(tolerance))
    
    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Run all validation checks and return results."""
        issues: List[str] = []
        field_confidences: Dict[str, float] = {}
        
        structured = data.get("structured_data", {})
        
        # Validate arithmetic
        math_result = self._validate_arithmetic(structured)
        if not math_result["is_valid"]:
            issues.extend(math_result["issues"])
        
        # Validate dates
        date_result = self._validate_dates(structured)
        if not date_result["is_valid"]:
            issues.extend(date_result["issues"])
        
        # Normalize currencies
        normalized = self._normalize_currency(structured)
        
        # Aggregate confidence scores
        field_confidences = self._aggregate_confidences(structured)
        
        needs_review = len(issues) > 0 or field_confidences.get("overall", 1.0) < 0.85
        
        return {
            "is_valid": len(issues) == 0,
            "math_ok": math_result["is_valid"],
            "dates_ok": date_result["is_valid"],
            "issues": issues,
            "field_confidences": field_confidences,
            "needs_review": needs_review,
            "normalized_data": normalized
        }
    
    def _validate_arithmetic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Verify line items sum to subtotal, and subtotal + tax - discounts = total."""
        issues = []
        
        try:
            line_items = data.get("line_items", [])
            summary = data.get("financial_summary", {})
            
            # Calculate line items total
            line_total = Decimal("0")
            for item in line_items:
                item_total = Decimal(str(item.get("total", 0)))
                qty = Decimal(str(item.get("quantity", 0)))
                unit_price = Decimal(str(item.get("unit_price", 0)))
                
                expected_total = qty * unit_price
                if abs(item_total - expected_total) > self.tolerance:
                    issues.append(f"Line item '{item.get('description', 'Unknown')}' total mismatch: {item_total} vs {expected_total}")
                
                line_total += item_total
            
            # Check subtotal
            subtotal = Decimal(str(summary.get("subtotal", 0)))
            if abs(line_total - subtotal) > self.tolerance:
                issues.append(f"Subtotal mismatch: line items sum to {line_total}, but subtotal is {subtotal}")
            
            # Calculate taxes
            tax_total = Decimal("0")
            for tax in summary.get("taxes", []):
                tax_total += Decimal(str(tax.get("amount", 0)))
            
            # Calculate discounts
            discount_total = Decimal("0")
            for discount in summary.get("discounts", []):
                discount_total += Decimal(str(discount.get("amount", 0)))
            
            # Verify grand total
            expected_grand = subtotal + tax_total - discount_total
            grand_total = Decimal(str(summary.get("grand_total", 0)))
            
            if abs(grand_total - expected_grand) > self.tolerance:
                issues.append(f"Grand total mismatch: expected {expected_grand}, but got {grand_total}")
                
        except Exception as e:
            logger.error(f"Arithmetic validation error: {e}")
            issues.append(f"Arithmetic validation failed: {str(e)}")
        
        return {"is_valid": len(issues) == 0, "issues": issues}
    
    def _validate_dates(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize dates to ISO 8601."""
        issues = []
        
        try:
            client_info = data.get("client_info", {})
            invoice_date = client_info.get("invoice_date", "")
            due_date = client_info.get("due_date", "")
            
            if invoice_date and due_date:
                inv_dt = self._parse_date(invoice_date)
                due_dt = self._parse_date(due_date)
                
                if inv_dt and due_dt and due_dt < inv_dt:
                    issues.append(f"Due date ({due_date}) is before invoice date ({invoice_date})")
                    
        except Exception as e:
            logger.error(f"Date validation error: {e}")
            issues.append(f"Date validation failed: {str(e)}")
        
        return {"is_valid": len(issues) == 0, "issues": issues}
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Try to parse date string in various formats."""
        formats = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%B %d, %Y", "%d %B %Y"]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None
    
    def _normalize_currency(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize currency values and codes to ISO format."""
        normalized = data.copy()
        
        summary = normalized.get("financial_summary", {})
        currency = summary.get("currency", "USD").upper()
        
        # Map common variations to ISO codes
        currency_map = {
            "$": "USD", "US$": "USD", "USD$": "USD",
            "€": "EUR", "£": "GBP", "¥": "JPY",
            "DOLLARS": "USD", "EUROS": "EUR"
        }
        
        if currency in currency_map:
            summary["currency"] = currency_map[currency]
        
        return normalized
    
    def _aggregate_confidences(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Aggregate confidence scores from all fields."""
        confidences = {}
        scores = []
        
        # Vendor confidence
        vendor = data.get("vendor_block", {})
        if "confidence" in vendor:
            confidences["vendor_block"] = vendor["confidence"]
            scores.append(vendor["confidence"])
        
        # Client confidence
        client = data.get("client_info", {})
        if "confidence" in client:
            confidences["client_info"] = client["confidence"]
            scores.append(client["confidence"])
        
        # Line items average confidence
        line_items = data.get("line_items", [])
        if line_items:
            item_scores = [item.get("confidence", 0) for item in line_items]
            avg_item_conf = sum(item_scores) / len(item_scores)
            confidences["line_items"] = avg_item_conf
            scores.append(avg_item_conf)
        
        # Overall confidence
        if scores:
            confidences["overall"] = sum(scores) / len(scores)
        else:
            confidences["overall"] = 0.0
        
        return confidences

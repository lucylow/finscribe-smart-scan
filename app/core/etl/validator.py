"""
Document Validator for ETL Pipeline.

Validates extracted data using:
- Arithmetic validation (subtotal + tax = total)
- Logical validation (dates, ranges, consistency)
- Statistical validation (outlier detection)
- Business rule validation
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)


class DocumentValidator:
    """
    Validates extracted financial document data.
    
    Validation is critical for financial ETL - errors here
    can cause downstream issues and compliance problems.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize validator.
        
        Args:
            config: Validation configuration including tolerances
        """
        self.config = config or {}
        self.arithmetic_tolerance = self.config.get("arithmetic_tolerance", 0.01)
        self.enable_statistical_validation = self.config.get(
            "enable_statistical_validation", False
        )
        self.enable_business_rules = self.config.get("enable_business_rules", True)
    
    async def validate(
        self,
        structured_data: Dict[str, Any],
        canonical_schema: Dict[str, Any],
        ocr_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Validate extracted data.
        
        Args:
            structured_data: Extracted structured data
            canonical_schema: Canonical schema data
            ocr_results: Optional raw OCR results for context
            
        Returns:
            Validation results with:
            - is_valid: bool
            - errors: List[str]
            - warnings: List[str]
            - validation_details: Dict with per-rule results
        """
        result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "validation_details": {}
        }
        
        # Run validation rules
        arithmetic_result = self._validate_arithmetic(canonical_schema)
        result["validation_details"]["arithmetic"] = arithmetic_result
        if not arithmetic_result["passed"]:
            result["is_valid"] = False
            result["errors"].extend(arithmetic_result["errors"])
        
        logical_result = self._validate_logical(canonical_schema)
        result["validation_details"]["logical"] = logical_result
        if not logical_result["passed"]:
            result["is_valid"] = False
            result["errors"].extend(logical_result["errors"])
        result["warnings"].extend(logical_result["warnings"])
        
        if self.enable_statistical_validation:
            statistical_result = await self._validate_statistical(
                canonical_schema, ocr_results
            )
            result["validation_details"]["statistical"] = statistical_result
            result["warnings"].extend(statistical_result["warnings"])
        
        if self.enable_business_rules:
            business_result = self._validate_business_rules(canonical_schema)
            result["validation_details"]["business_rules"] = business_result
            if not business_result["passed"]:
                result["is_valid"] = False
                result["errors"].extend(business_result["errors"])
            result["warnings"].extend(business_result["warnings"])
        
        logger.info(
            f"Validation {'passed' if result['is_valid'] else 'failed'}: "
            f"{len(result['errors'])} errors, {len(result['warnings'])} warnings"
        )
        
        return result
    
    def _validate_arithmetic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate arithmetic relationships.
        
        Checks:
        - subtotal + tax ≈ total
        - sum(line_items) ≈ subtotal
        """
        result = {
            "passed": True,
            "errors": [],
            "warnings": []
        }
        
        total = self._safe_float(data.get("total", 0))
        subtotal = self._safe_float(data.get("subtotal"))
        tax = self._safe_float(data.get("tax", 0))
        line_items = data.get("line_items", [])
        
        # Check: subtotal + tax ≈ total
        if subtotal is not None:
            expected_total = subtotal + tax
            difference = abs(total - expected_total)
            
            if difference > self.arithmetic_tolerance:
                error_msg = (
                    f"Arithmetic mismatch: subtotal ({subtotal}) + tax ({tax}) = "
                    f"{expected_total}, but total is {total} (difference: {difference})"
                )
                result["errors"].append(error_msg)
                result["passed"] = False
            elif difference > self.arithmetic_tolerance * 0.5:
                # Warning for smaller differences
                result["warnings"].append(
                    f"Minor arithmetic difference: {difference}"
                )
        
        # Check: sum(line_items) ≈ subtotal
        if line_items and subtotal is not None:
            line_items_sum = sum(
                self._safe_float(item.get("amount", item.get("total", 0)))
                for item in line_items
            )
            
            difference = abs(subtotal - line_items_sum)
            if difference > self.arithmetic_tolerance:
                error_msg = (
                    f"Line items sum ({line_items_sum}) does not match "
                    f"subtotal ({subtotal}) (difference: {difference})"
                )
                result["errors"].append(error_msg)
                result["passed"] = False
        
        return result
    
    def _validate_logical(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate logical constraints.
        
        Checks:
        - Dates are valid and reasonable
        - Amounts are non-negative
        - Currency is consistent
        - Required fields are present
        """
        result = {
            "passed": True,
            "errors": [],
            "warnings": []
        }
        
        # Validate dates
        date_str = data.get("date")
        if date_str:
            try:
                # Try to parse date
                date_obj = self._parse_date(date_str)
                if date_obj:
                    # Check date is not in future
                    if date_obj > datetime.now():
                        result["warnings"].append(
                            f"Invoice date is in the future: {date_str}"
                        )
                    
                    # Check date is not too old (e.g., > 10 years)
                    years_ago = (datetime.now() - date_obj).days / 365.25
                    if years_ago > 10:
                        result["warnings"].append(
                            f"Invoice date is very old: {date_str} ({years_ago:.1f} years ago)"
                        )
            except Exception as e:
                result["errors"].append(f"Invalid date format: {date_str}")
                result["passed"] = False
        
        # Validate amounts are non-negative
        total = self._safe_float(data.get("total", 0))
        if total < 0:
            result["errors"].append(f"Total amount is negative: {total}")
            result["passed"] = False
        
        subtotal = self._safe_float(data.get("subtotal"))
        if subtotal is not None and subtotal < 0:
            result["errors"].append(f"Subtotal is negative: {subtotal}")
            result["passed"] = False
        
        tax = self._safe_float(data.get("tax", 0))
        if tax < 0:
            result["errors"].append(f"Tax is negative: {tax}")
            result["passed"] = False
        
        # Validate line items
        line_items = data.get("line_items", [])
        for i, item in enumerate(line_items):
            amount = self._safe_float(item.get("amount", item.get("total", 0)))
            if amount < 0:
                result["warnings"].append(
                    f"Line item {i+1} has negative amount: {amount}"
                )
        
        # Check required fields
        required_fields = ["total", "currency"]
        for field in required_fields:
            if field not in data or data[field] is None:
                result["errors"].append(f"Required field missing: {field}")
                result["passed"] = False
        
        return result
    
    async def _validate_statistical(
        self,
        data: Dict[str, Any],
        ocr_results: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Statistical validation (outlier detection).
        
        This would compare against historical data patterns.
        For now, it's a placeholder.
        """
        result = {
            "passed": True,
            "warnings": []
        }
        
        # Placeholder for statistical validation
        # In production, this would:
        # 1. Compare amounts against vendor historical data
        # 2. Detect unusual patterns
        # 3. Flag outliers for review
        
        return result
    
    def _validate_business_rules(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate business-specific rules.
        
        Examples:
        - Tax rate validation
        - Payment terms validation
        - Vendor-specific rules
        """
        result = {
            "passed": True,
            "errors": [],
            "warnings": []
        }
        
        # Validate tax calculation
        subtotal = self._safe_float(data.get("subtotal"))
        tax = self._safe_float(data.get("tax", 0))
        total = self._safe_float(data.get("total", 0))
        
        if subtotal is not None and subtotal > 0 and tax > 0:
            tax_rate = tax / subtotal
            # Check if tax rate is reasonable (e.g., 0-30%)
            if tax_rate > 0.30:
                result["warnings"].append(
                    f"Unusually high tax rate: {tax_rate*100:.1f}%"
                )
            elif tax_rate < 0:
                result["errors"].append("Tax rate is negative")
                result["passed"] = False
        
        # Validate invoice ID format (if present)
        invoice_id = data.get("invoice_id")
        if invoice_id:
            # Check for reasonable length
            if len(str(invoice_id)) > 50:
                result["warnings"].append(
                    f"Invoice ID is unusually long: {len(invoice_id)} characters"
                )
        
        return result
    
    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert value to float."""
        if value is None:
            return None
        
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            # Remove currency symbols and commas
            cleaned = value.replace(',', '').replace('$', '').strip()
            try:
                return float(cleaned)
            except ValueError:
                return None
        
        return None
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime object."""
        if not date_str:
            return None
        
        # Try common formats
        formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%m-%d-%Y",
            "%d/%m/%Y",
            "%Y-%m-%dT%H:%M:%S",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None


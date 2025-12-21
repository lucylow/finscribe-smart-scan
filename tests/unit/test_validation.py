"""Unit tests for validation module."""
import pytest
from decimal import Decimal
from app.core.validation.financial_validator import FinancialValidator


class TestFinancialValidator:
    """Tests for FinancialValidator."""
    
    def test_validate_arithmetic_valid(self, sample_result_data):
        """Test arithmetic validation with valid data."""
        validator = FinancialValidator()
        data = {
            "structured_data": {
                "line_items": [
                    {"description": "Item 1", "quantity": 2, "unit_price": 100.0, "total": 200.0},
                    {"description": "Item 2", "quantity": 1, "unit_price": 300.0, "total": 300.0}
                ],
                "financial_summary": {
                    "subtotal": 500.0,
                    "taxes": [{"amount": 50.0}],
                    "discounts": [],
                    "grand_total": 550.0,
                    "currency": "USD"
                }
            }
        }
        
        result = validator.validate(data)
        assert result["is_valid"] is True
        assert result["math_ok"] is True
    
    def test_validate_arithmetic_invalid_subtotal(self):
        """Test arithmetic validation with invalid subtotal."""
        validator = FinancialValidator()
        data = {
            "structured_data": {
                "line_items": [
                    {"description": "Item 1", "quantity": 2, "unit_price": 100.0, "total": 200.0}
                ],
                "financial_summary": {
                    "subtotal": 300.0,  # Should be 200.0
                    "taxes": [],
                    "discounts": [],
                    "grand_total": 300.0,
                    "currency": "USD"
                }
            }
        }
        
        result = validator.validate(data)
        assert result["is_valid"] is False
        assert result["math_ok"] is False
        assert len(result["issues"]) > 0
    
    def test_validate_arithmetic_invalid_total(self):
        """Test arithmetic validation with invalid grand total."""
        validator = FinancialValidator()
        data = {
            "structured_data": {
                "line_items": [
                    {"description": "Item 1", "quantity": 1, "unit_price": 100.0, "total": 100.0}
                ],
                "financial_summary": {
                    "subtotal": 100.0,
                    "taxes": [{"amount": 10.0}],
                    "discounts": [],
                    "grand_total": 150.0,  # Should be 110.0
                    "currency": "USD"
                }
            }
        }
        
        result = validator.validate(data)
        assert result["is_valid"] is False
        assert result["math_ok"] is False
    
    def test_validate_dates(self):
        """Test date validation."""
        validator = FinancialValidator()
        data = {
            "structured_data": {
                "client_info": {
                    "invoice_date": "2025-01-01",
                    "due_date": "2025-01-15"
                }
            }
        }
        
        result = validator.validate(data)
        assert result["dates_ok"] is True
    
    def test_validate_dates_invalid(self):
        """Test date validation with invalid dates."""
        validator = FinancialValidator()
        data = {
            "structured_data": {
                "client_info": {
                    "invoice_date": "2025-01-15",
                    "due_date": "2025-01-01"  # Due date before invoice date
                }
            }
        }
        
        result = validator.validate(data)
        assert result["dates_ok"] is False
        assert len(result["issues"]) > 0
    
    def test_normalize_currency(self):
        """Test currency normalization."""
        validator = FinancialValidator()
        data = {
            "structured_data": {
                "financial_summary": {
                    "currency": "$",  # Should normalize to USD
                    "subtotal": 100.0,
                    "taxes": [],
                    "discounts": [],
                    "grand_total": 100.0
                }
            }
        }
        
        result = validator.validate(data)
        normalized = result["normalized_data"]
        assert normalized["financial_summary"]["currency"] == "USD"



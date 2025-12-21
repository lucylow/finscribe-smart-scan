"""
Structured JSON Schema for Multi-Currency Financial Documents

This module defines the canonical JSON structure for financial documents,
with support for multi-currency invoices, line items, and mixed document elements.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from decimal import Decimal
import json


@dataclass
class CurrencyAmount:
    """Represents a monetary amount with currency information."""
    amount: float
    currency: str  # ISO 4217 currency code (e.g., "USD", "EUR", "GBP")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "amount": self.amount,
            "currency": self.currency,
            "formatted": f"{self.currency} {self.amount:,.2f}"
        }


@dataclass
class VendorInfo:
    """Vendor/seller information block."""
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    tax_id: Optional[str] = None
    website: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class ClientInfo:
    """Client/buyer information block."""
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    tax_id: Optional[str] = None
    purchase_order: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class LineItem:
    """Individual line item in an invoice table."""
    description: str
    quantity: float
    unit_price: CurrencyAmount
    line_total: CurrencyAmount
    sku: Optional[str] = None
    tax_rate: Optional[float] = None
    discount: Optional[CurrencyAmount] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "description": self.description,
            "quantity": self.quantity,
            "unit_price": self.unit_price.to_dict(),
            "line_total": self.line_total.to_dict(),
        }
        if self.sku:
            result["sku"] = self.sku
        if self.tax_rate is not None:
            result["tax_rate"] = self.tax_rate
        if self.discount:
            result["discount"] = self.discount.to_dict()
        return result


@dataclass
class FinancialSummary:
    """Financial summary section with totals."""
    subtotal: CurrencyAmount
    tax: Optional[CurrencyAmount] = None
    discount: Optional[CurrencyAmount] = None
    shipping: Optional[CurrencyAmount] = None
    grand_total: CurrencyAmount = None
    currency: Optional[str] = None  # Primary currency for the document
    
    def __post_init__(self):
        if self.grand_total is None:
            # Calculate grand total if not provided
            total = self.subtotal.amount
            if self.tax:
                total += self.tax.amount
            if self.discount:
                total -= self.discount.amount
            if self.shipping:
                total += self.shipping.amount
            self.grand_total = CurrencyAmount(
                amount=total,
                currency=self.subtotal.currency
            )
        if self.currency is None:
            self.currency = self.subtotal.currency
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "subtotal": self.subtotal.to_dict(),
            "grand_total": self.grand_total.to_dict(),
            "currency": self.currency,
        }
        if self.tax:
            result["tax"] = self.tax.to_dict()
        if self.discount:
            result["discount"] = self.discount.to_dict()
        if self.shipping:
            result["shipping"] = self.shipping.to_dict()
        return result


@dataclass
class InvoiceDocument:
    """Complete structured invoice document."""
    invoice_number: str
    invoice_date: str
    due_date: Optional[str] = None
    vendor: Optional[VendorInfo] = None
    client: Optional[ClientInfo] = None
    line_items: List[LineItem] = None
    financial_summary: Optional[FinancialSummary] = None
    notes: Optional[str] = None
    terms: Optional[str] = None
    payment_method: Optional[str] = None
    
    def __post_init__(self):
        if self.line_items is None:
            self.line_items = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to canonical JSON structure."""
        result = {
            "invoice_number": self.invoice_number,
            "invoice_date": self.invoice_date,
        }
        
        if self.due_date:
            result["due_date"] = self.due_date
        if self.vendor:
            result["vendor_block"] = self.vendor.to_dict()
        if self.client:
            result["client_info"] = self.client.to_dict()
        if self.line_items:
            result["line_items"] = [item.to_dict() for item in self.line_items]
        if self.financial_summary:
            result["financial_summary"] = self.financial_summary.to_dict()
        if self.notes:
            result["notes"] = self.notes
        if self.terms:
            result["terms"] = self.terms
        if self.payment_method:
            result["payment_method"] = self.payment_method
        
        return result
    
    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


def parse_currency_string(amount_str: str, default_currency: str = "USD") -> CurrencyAmount:
    """
    Parse a currency string (e.g., "$1,234.56", "EUR 500.00") into CurrencyAmount.
    
    Args:
        amount_str: String representation of amount with optional currency
        default_currency: Default currency if not specified in string
        
    Returns:
        CurrencyAmount object
    """
    # Common currency symbols mapping
    currency_symbols = {
        "$": "USD",
        "€": "EUR",
        "£": "GBP",
        "¥": "JPY",
        "₹": "INR",
        "A$": "AUD",
        "C$": "CAD",
    }
    
    # Remove whitespace and common separators
    cleaned = amount_str.strip().replace(",", "")
    
    # Try to detect currency
    currency = default_currency
    amount_value = None
    
    # Check for currency codes (3-letter ISO codes)
    for code in ["USD", "EUR", "GBP", "JPY", "INR", "AUD", "CAD", "CNY", "CHF"]:
        if code in cleaned.upper():
            currency = code
            # Extract number after currency code
            parts = cleaned.upper().split(code)
            if len(parts) > 1:
                try:
                    amount_value = float(parts[1].strip())
                    break
                except ValueError:
                    pass
    
    # Check for currency symbols
    if amount_value is None:
        for symbol, code in currency_symbols.items():
            if cleaned.startswith(symbol):
                currency = code
                try:
                    amount_value = float(cleaned.replace(symbol, "").strip())
                    break
                except ValueError:
                    pass
    
    # If no currency detected, try to parse as number
    if amount_value is None:
        # Remove all non-numeric characters except decimal point and minus
        numeric_str = "".join(c for c in cleaned if c.isdigit() or c in ".-")
        try:
            amount_value = float(numeric_str)
        except ValueError:
            raise ValueError(f"Could not parse amount from: {amount_str}")
    
    return CurrencyAmount(amount=amount_value, currency=currency)


def validate_multi_currency_consistency(document: InvoiceDocument) -> Dict[str, Any]:
    """
    Validate that multi-currency documents have consistent currency handling.
    
    Args:
        document: InvoiceDocument to validate
        
    Returns:
        Validation result with warnings/errors
    """
    issues = []
    warnings = []
    
    # Collect all currencies used
    currencies = set()
    
    if document.financial_summary:
        currencies.add(document.financial_summary.currency)
        currencies.add(document.financial_summary.subtotal.currency)
        if document.financial_summary.tax:
            currencies.add(document.financial_summary.tax.currency)
        if document.financial_summary.grand_total:
            currencies.add(document.financial_summary.grand_total.currency)
    
    for item in document.line_items:
        currencies.add(item.unit_price.currency)
        currencies.add(item.line_total.currency)
        if item.discount:
            currencies.add(item.discount.currency)
    
    # Check for multi-currency scenarios
    if len(currencies) > 1:
        warnings.append(f"Document contains multiple currencies: {', '.join(currencies)}")
        warnings.append("Ensure all amounts are properly converted or clearly labeled")
    
    # Check for currency consistency within line items
    for i, item in enumerate(document.line_items):
        if item.unit_price.currency != item.line_total.currency:
            issues.append(
                f"Line item {i+1}: Unit price currency ({item.unit_price.currency}) "
                f"does not match line total currency ({item.line_total.currency})"
            )
    
    return {
        "is_valid": len(issues) == 0,
        "currencies_detected": list(currencies),
        "is_multi_currency": len(currencies) > 1,
        "issues": issues,
        "warnings": warnings,
    }



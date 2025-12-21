"""
Example: Using the Finance Data Layer

This demonstrates the complete finance processing pipeline:
1. Parse OCR output → Invoice objects
2. Validate with math + business rules
3. Store at each ETL stage
4. Export for active learning
5. Compute metrics
"""
from app.core.finance_processor import FinanceProcessor
from app.models.finance import Invoice, Money, Vendor, LineItem
from app.validation.finance_validator import validate_invoice
from app.metrics.finance_metrics import compute_invoice_metrics, compare_metrics
from decimal import Decimal


def example_1_simple_processing():
    """Example: Process an invoice from OCR output."""
    processor = FinanceProcessor()
    
    # Simulate OCR output
    ocr_json = {
        "invoice_id": "INV-001",
        "invoice_date": "2024-01-15",
        "vendor": {
            "name": "Acme Corp",
            "address": "123 Main St",
            "tax_id": "TAX-123"
        },
        "line_items": [
            {
                "description": "Widget A",
                "quantity": "2",
                "unit_price": "10.00",
                "total": "20.00",
                "currency": "USD"
            },
            {
                "description": "Widget B",
                "quantity": "3",
                "unit_price": "15.00",
                "total": "45.00",
                "currency": "USD"
            }
        ],
        "subtotal": "65.00",
        "tax": "6.50",
        "total": "71.50",
        "currency": "USD",
        "confidence": 0.95
    }
    
    # Process the invoice
    result = processor.process_invoice(ocr_json, export_for_training=True)
    
    print("Processing Result:")
    print(f"  Status: {result['status']}")
    print(f"  Validation: {'PASSED' if result['validation']['passed'] else 'FAILED'}")
    if result['validation']['errors']:
        print(f"  Errors: {result['validation']['errors']}")
    print(f"  Confidence: {result['confidence']}")
    
    return result


def example_2_manual_validation():
    """Example: Create and validate an Invoice manually."""
    # Create invoice using Pydantic models
    invoice = Invoice(
        invoice_id="INV-002",
        invoice_date="2024-01-20",
        vendor=Vendor(
            name="Tech Solutions Inc",
            address="456 Tech Ave",
            tax_id="TAX-456"
        ),
        line_items=[
            LineItem(
                description="Service A",
                quantity=Decimal("1"),
                unit_price=Money(value=Decimal("100.00"), currency="USD"),
                total=Money(value=Decimal("100.00"), currency="USD")
            ),
            LineItem(
                description="Service B",
                quantity=Decimal("2"),
                unit_price=Money(value=Decimal("50.00"), currency="USD"),
                total=Money(value=Decimal("100.00"), currency="USD")
            )
        ],
        subtotal=Money(value=Decimal("200.00"), currency="USD"),
        tax=Money(value=Decimal("20.00"), currency="USD"),
        total=Money(value=Decimal("220.00"), currency="USD"),
        confidence=0.92
    )
    
    # Validate
    validation = validate_invoice(invoice)
    
    print("\nManual Validation:")
    print(f"  Passed: {validation.passed}")
    if validation.errors:
        print(f"  Errors: {validation.errors}")
    if validation.warnings:
        print(f"  Warnings: {validation.warnings}")
    
    return invoice, validation


def example_3_metrics():
    """Example: Compute aggregate metrics."""
    processor = FinanceProcessor()
    
    # Process multiple invoices
    invoices = []
    for i in range(5):
        ocr_json = {
            "invoice_id": f"INV-{i:03d}",
            "invoice_date": "2024-01-15",
            "vendor": {"name": f"Vendor {i}"},
            "line_items": [
                {
                    "description": "Item",
                    "quantity": "1",
                    "unit_price": "100.00",
                    "total": "100.00",
                    "currency": "USD"
                }
            ],
            "subtotal": "100.00",
            "tax": "10.00",
            "total": "110.00",
            "currency": "USD",
            "confidence": 0.9 + (i * 0.01)
        }
        result = processor.process_invoice(ocr_json)
        invoices.append(result)
    
    # Compute metrics
    metrics = processor.get_metrics(invoices)
    
    print("\nAggregate Metrics:")
    print(f"  Total Documents: {metrics['total_docs']}")
    print(f"  Validation Pass Rate: {metrics['validation_pass_rate']:.1%}")
    print(f"  Average Confidence: {metrics['avg_confidence']:.3f}")
    print(f"  Total Value: ${metrics['total_value']:.2f} {metrics['currency']}")
    
    return metrics


def example_4_comparison():
    """Example: Compare metrics before/after improvements."""
    # Simulate before metrics
    before_metrics = {
        "total_docs": 100,
        "validation_pass_rate": 0.75,
        "avg_confidence": 0.82,
        "error_rate": 0.25
    }
    
    # Simulate after metrics (after fine-tuning)
    after_metrics = {
        "total_docs": 100,
        "validation_pass_rate": 0.92,
        "avg_confidence": 0.91,
        "error_rate": 0.08
    }
    
    comparison = compare_metrics(before_metrics, after_metrics)
    
    print("\nBefore/After Comparison:")
    print(f"  Pass Rate Improvement: +{comparison['pass_rate_improvement_pct']:.1f}%")
    print(f"  Confidence Improvement: +{comparison['confidence_improvement']:.3f}")
    print(f"  Error Rate Reduction: -{comparison['error_rate_reduction']:.1%}")
    
    return comparison


if __name__ == "__main__":
    print("=" * 60)
    print("Finance Data Layer Examples")
    print("=" * 60)
    
    # Run examples
    example_1_simple_processing()
    example_2_manual_validation()
    example_3_metrics()
    example_4_comparison()
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


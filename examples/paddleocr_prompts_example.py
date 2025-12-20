"""
Example: Using PaddleOCR-VL Task-Specific Prompts

This example demonstrates:
1. Using region-specific prompts for different document elements
2. Processing mixed documents (text + tables)
3. Structuring multi-currency invoice output
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, Any, List

# Import the new modules
from app.core.models.paddleocr_vl_service import PaddleOCRVLService
from app.core.models.paddleocr_prompts import get_prompt_for_region, is_table_region
from app.core.models.invoice_schema import (
    InvoiceDocument,
    LineItem,
    CurrencyAmount,
    VendorInfo,
    ClientInfo,
    FinancialSummary,
    parse_currency_string,
    validate_multi_currency_consistency
)
from app.config.settings import load_config


async def example_1_basic_region_processing():
    """Example 1: Process individual regions with appropriate prompts."""
    print("\n=== Example 1: Basic Region Processing ===\n")
    
    config = load_config()
    service = PaddleOCRVLService(config)
    
    # Simulate reading a document
    # In production, this would be actual image bytes
    image_bytes = b"fake_image_data"
    
    # Process a table region (uses "Table Recognition:" prompt)
    print("Processing line items table...")
    table_result = await service.parse_region(
        image_bytes=image_bytes,
        region_type="line_items_table"
    )
    print(f"Prompt used: {table_result.get('prompt_used')}")
    print(f"Region type: {table_result.get('region_type')}")
    
    # Process a text region (uses "OCR:" prompt)
    print("\nProcessing vendor block...")
    vendor_result = await service.parse_region(
        image_bytes=image_bytes,
        region_type="vendor_block"
    )
    print(f"Prompt used: {vendor_result.get('prompt_used')}")
    print(f"Region type: {vendor_result.get('region_type')}")


async def example_2_mixed_document_processing():
    """Example 2: Process document with mixed elements."""
    print("\n=== Example 2: Mixed Document Processing ===\n")
    
    config = load_config()
    service = PaddleOCRVLService(config)
    
    # Simulate detected regions from layout analysis
    regions = [
        {
            "type": "header",
            "bbox": {"x": 0, "y": 0, "w": 800, "h": 100}
        },
        {
            "type": "vendor_block",
            "bbox": {"x": 50, "y": 120, "w": 300, "h": 150}
        },
        {
            "type": "client_info",
            "bbox": {"x": 400, "y": 120, "w": 300, "h": 150}
        },
        {
            "type": "line_items_table",
            "bbox": {"x": 50, "y": 300, "w": 700, "h": 400}
        },
        {
            "type": "financial_summary",
            "bbox": {"x": 500, "y": 750, "w": 250, "h": 100}
        }
    ]
    
    image_bytes = b"fake_image_data"
    
    print(f"Processing document with {len(regions)} regions...")
    result = await service.parse_mixed_document(
        image_bytes=image_bytes,
        regions=regions
    )
    
    print(f"\nProcessing strategy: {result.get('processing_strategy')}")
    print(f"Regions processed: {result.get('regions_processed')}")
    
    # Show prompts used for each region
    print("\nPrompts used per region:")
    for region_type, region_result in result.get("region_results", {}).items():
        prompt = region_result.get("prompt_used", "unknown")
        status = region_result.get("status", "unknown")
        print(f"  {region_type}: {prompt} (status: {status})")


def example_3_multi_currency_invoice():
    """Example 3: Create and validate multi-currency invoice structure."""
    print("\n=== Example 3: Multi-Currency Invoice Structure ===\n")
    
    # Create a multi-currency invoice
    invoice = InvoiceDocument(
        invoice_number="INV-2025-001",
        invoice_date="2025-01-15",
        due_date="2025-02-15",
        vendor=VendorInfo(
            name="Global Services Inc.",
            address="123 International Blvd",
            city="New York",
            state="NY",
            postal_code="10001",
            country="USA",
            email="billing@globalservices.com"
        ),
        client=ClientInfo(
            name="European Client Ltd.",
            address="456 Business Ave",
            city="London",
            postal_code="SW1A 1AA",
            country="UK",
            purchase_order="PO-2025-042"
        ),
        line_items=[
            LineItem(
                description="US Consulting Services",
                quantity=10,
                unit_price=CurrencyAmount(amount=150.00, currency="USD"),
                line_total=CurrencyAmount(amount=1500.00, currency="USD")
            ),
            LineItem(
                description="European Software License",
                quantity=2,
                unit_price=CurrencyAmount(amount=500.00, currency="EUR"),
                line_total=CurrencyAmount(amount=1000.00, currency="EUR")
            ),
            LineItem(
                description="UK Support Package",
                quantity=1,
                unit_price=CurrencyAmount(amount=250.00, currency="GBP"),
                line_total=CurrencyAmount(amount=250.00, currency="GBP")
            )
        ],
        financial_summary=FinancialSummary(
            subtotal=CurrencyAmount(amount=2750.00, currency="USD"),  # Converted total
            tax=CurrencyAmount(amount=275.00, currency="USD"),
            grand_total=CurrencyAmount(amount=3025.00, currency="USD")
        ),
        notes="All amounts converted to USD at time of invoice",
        terms="Net 30"
    )
    
    # Convert to JSON
    json_output = invoice.to_json(indent=2)
    print("Structured Invoice JSON:")
    print(json_output)
    
    # Validate multi-currency consistency
    print("\n=== Multi-Currency Validation ===\n")
    validation = validate_multi_currency_consistency(invoice)
    
    print(f"Is valid: {validation['is_valid']}")
    print(f"Currencies detected: {', '.join(validation['currencies_detected'])}")
    print(f"Is multi-currency: {validation['is_multi_currency']}")
    
    if validation['warnings']:
        print("\nWarnings:")
        for warning in validation['warnings']:
            print(f"  ⚠️  {warning}")
    
    if validation['issues']:
        print("\nIssues:")
        for issue in validation['issues']:
            print(f"  ❌ {issue}")


def example_4_currency_parsing():
    """Example 4: Parse currency strings from OCR output."""
    print("\n=== Example 4: Currency String Parsing ===\n")
    
    # Simulate OCR output with various currency formats
    ocr_amounts = [
        "$1,234.56",
        "EUR 500.00",
        "£250.00",
        "¥10,000",
        "INR 50,000.00",
        "1500.00"  # No currency specified, defaults to USD
    ]
    
    print("Parsing currency strings from OCR output:")
    for amount_str in ocr_amounts:
        try:
            parsed = parse_currency_string(amount_str)
            print(f"  '{amount_str}' → {parsed.currency} {parsed.amount:,.2f}")
        except ValueError as e:
            print(f"  '{amount_str}' → Error: {e}")


def example_5_prompt_mapping():
    """Example 5: Demonstrate region type to prompt mapping."""
    print("\n=== Example 5: Region Type to Prompt Mapping ===\n")
    
    test_regions = [
        "vendor_block",
        "client_info",
        "header",
        "line_items_table",
        "table",
        "financial_summary",
        "formula",
        "chart",
        "unknown_region"
    ]
    
    print("Region Type → Prompt Mapping:")
    for region_type in test_regions:
        prompt = get_prompt_for_region(region_type)
        is_table = is_table_region(region_type)
        print(f"  {region_type:20} → {prompt:25} (table: {is_table})")


async def example_6_finetuning_data_structure():
    """Example 6: Structure fine-tuning data with proper prompts."""
    print("\n=== Example 6: Fine-Tuning Data Structure ===\n")
    
    from finscribe.data.formatters import build_instruction_sample
    from PIL import Image
    import io
    
    # Create a dummy image for demonstration
    dummy_image = Image.new('RGB', (100, 100), color='white')
    
    # Example 1: Table recognition training sample
    print("Table Recognition Training Sample:")
    table_target = [
        {
            "description": "Consulting Services",
            "quantity": 10,
            "unit_price": {"amount": 150.00, "currency": "USD"},
            "line_total": {"amount": 1500.00, "currency": "USD"}
        },
        {
            "description": "Software License",
            "quantity": 2,
            "unit_price": {"amount": 500.00, "currency": "USD"},
            "line_total": {"amount": 1000.00, "currency": "USD"}
        }
    ]
    
    table_sample = build_instruction_sample(
        image=dummy_image,
        region_type="line_items_table",
        target=table_target
    )
    
    print(f"  Prompt: {table_sample['messages'][0]['content'][1]['text']}")
    print(f"  Response type: {type(table_sample['messages'][1]['content'][0]['text'])}")
    print(f"  Response preview: {table_sample['messages'][1]['content'][0]['text'][:100]}...")
    
    # Example 2: OCR training sample
    print("\nOCR Training Sample:")
    vendor_target = {
        "name": "Acme Corporation",
        "address": "123 Business St",
        "city": "New York",
        "state": "NY",
        "postal_code": "10001"
    }
    
    ocr_sample = build_instruction_sample(
        image=dummy_image,
        region_type="vendor_block",
        target=vendor_target
    )
    
    print(f"  Prompt: {ocr_sample['messages'][0]['content'][1]['text']}")
    print(f"  Response type: {type(ocr_sample['messages'][1]['content'][0]['text'])}")
    print(f"  Response preview: {ocr_sample['messages'][1]['content'][0]['text'][:100]}...")


async def main():
    """Run all examples."""
    print("=" * 60)
    print("PaddleOCR-VL Task-Specific Prompts Examples")
    print("=" * 60)
    
    # Run synchronous examples
    example_3_multi_currency_invoice()
    example_4_currency_parsing()
    example_5_prompt_mapping()
    
    # Run async examples
    await example_1_basic_region_processing()
    await example_2_mixed_document_processing()
    await example_6_finetuning_data_structure()
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())


# PaddleOCR-VL Task-Specific Prompts Implementation Guide

This guide explains how to use the task-specific prompt system for PaddleOCR-VL in FinScribe AI, including handling multi-currency invoices and mixed document elements.

## Overview

PaddleOCR-VL uses fixed, task-specific prompts (not conversational prompts) to instruct the model on what to extract from document images. This implementation follows the official PaddleOCR documentation and supports:

- **Text Recognition (OCR)**: `"OCR:"` - For standard text extraction
- **Table Recognition**: `"Table Recognition:"` - For structured table parsing
- **Formula Recognition**: `"Formula Recognition:"` - For mathematical formulas
- **Chart Recognition**: `"Chart Recognition:"` - For chart data extraction

## Two-Stage Processing Pipeline

### Stage 1: Layout Analysis
Before using task-specific prompts, the system uses layout analysis (PP-DocLayoutV2) to detect and classify regions on the page:
- Text blocks (header, vendor, client info)
- Tables (line items)
- Other elements (logos, signatures, etc.)

### Stage 2: Targeted Element Recognition
Each detected region is cropped and passed to PaddleOCR-VL-0.9B with the appropriate task prompt:
- Text regions → `"OCR:"` prompt
- Table regions → `"Table Recognition:"` prompt

## Usage Examples

### Basic Usage: Full Document Parsing

```python
from app.core.models.paddleocr_vl_service import PaddleOCRVLService
from app.config.settings import load_config

config = load_config()
service = PaddleOCRVLService(config)

# Read document image
with open("invoice.pdf", "rb") as f:
    image_bytes = f.read()

# Parse full document (uses default OCR prompt)
result = await service.parse_document(image_bytes)
```

### Region-Specific Processing

```python
# Process a specific region with appropriate prompt
result = await service.parse_region(
    image_bytes=image_bytes,
    region_type="line_items_table",  # Automatically uses "Table Recognition:" prompt
    bbox={"x": 100, "y": 300, "w": 500, "h": 400}
)

# For text regions, uses "OCR:" prompt
vendor_result = await service.parse_region(
    image_bytes=image_bytes,
    region_type="vendor_block",  # Automatically uses "OCR:" prompt
    bbox={"x": 50, "y": 100, "w": 300, "h": 150}
)
```

### Mixed Elements Processing

For documents with both text and tables on the same page:

```python
# After layout analysis, you have detected regions
regions = [
    {
        "type": "vendor_block",
        "bbox": {"x": 50, "y": 100, "w": 300, "h": 150}
    },
    {
        "type": "line_items_table",
        "bbox": {"x": 100, "y": 300, "w": 500, "h": 400}
    },
    {
        "type": "financial_summary",
        "bbox": {"x": 400, "y": 750, "w": 200, "h": 100}
    }
]

# Process all regions with appropriate prompts
result = await service.parse_mixed_document(
    image_bytes=image_bytes,
    regions=regions
)

# Result contains structured output for each region
print(result["region_results"]["line_items_table"])  # Table data
print(result["region_results"]["vendor_block"])       # Vendor info
```

## Multi-Currency Invoice Structure

### JSON Schema

The `invoice_schema.py` module provides a structured format for multi-currency invoices:

```python
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

# Example: Multi-currency invoice
invoice = InvoiceDocument(
    invoice_number="INV-2025-001",
    invoice_date="2025-01-15",
    vendor=VendorInfo(
        name="Global Corp",
        address="123 Business St",
        city="New York",
        country="USA"
    ),
    line_items=[
        LineItem(
            description="Consulting Services",
            quantity=10,
            unit_price=CurrencyAmount(amount=150.00, currency="USD"),
            line_total=CurrencyAmount(amount=1500.00, currency="USD")
        ),
        LineItem(
            description="European License",
            quantity=2,
            unit_price=CurrencyAmount(amount=500.00, currency="EUR"),
            line_total=CurrencyAmount(amount=1000.00, currency="EUR")
        )
    ],
    financial_summary=FinancialSummary(
        subtotal=CurrencyAmount(amount=2500.00, currency="USD"),  # Converted
        tax=CurrencyAmount(amount=250.00, currency="USD"),
        grand_total=CurrencyAmount(amount=2750.00, currency="USD")
    )
)

# Convert to JSON
json_output = invoice.to_json(indent=2)

# Validate multi-currency consistency
validation = validate_multi_currency_consistency(invoice)
print(validation["warnings"])  # Will warn about multiple currencies
```

### Parsing Currency Strings

```python
# Automatically detect currency from string
amount1 = parse_currency_string("$1,234.56")  # USD 1234.56
amount2 = parse_currency_string("EUR 500.00")  # EUR 500.00
amount3 = parse_currency_string("£250.00")     # GBP 250.00
```

## Fine-Tuning Data Structure

For fine-tuning PaddleOCR-VL on financial documents, structure your training data as instruction-response pairs:

```python
from finscribe.data.formatters import build_instruction_sample
from PIL import Image

# Example: Table recognition training sample
image = Image.open("cropped_table.png")
target_data = [
    {
        "description": "Consulting Services",
        "quantity": 10,
        "unit_price": {"amount": 150.00, "currency": "USD"},
        "line_total": {"amount": 1500.00, "currency": "USD"}
    },
    # ... more rows
]

instruction_sample = build_instruction_sample(
    image=image,
    region_type="line_items_table",  # Uses "Table Recognition:" prompt
    target=target_data
)

# instruction_sample contains:
# {
#     "images": [image],
#     "messages": [
#         {
#             "role": "user",
#             "content": [
#                 {"type": "image", "image": image},
#                 {"type": "text", "text": "Table Recognition:"}
#             ]
#         },
#         {
#             "role": "assistant",
#             "content": [
#                 {"type": "text", "text": "[JSON array of rows]"}
#             ]
#         }
#     ]
# }
```

## Region Type to Prompt Mapping

| Region Type | Prompt Used | Use Case |
|------------|-------------|----------|
| `vendor_block`, `client_info`, `header`, `footer` | `"OCR:"` | Text extraction |
| `line_items_table`, `table`, `table_body` | `"Table Recognition:"` | Structured table parsing |
| `formula` | `"Formula Recognition:"` | Mathematical formulas |
| `chart`, `graph` | `"Chart Recognition:"` | Chart data extraction |

## Best Practices

1. **Always use region-specific prompts**: Don't use a generic prompt for all regions. Let the system determine the appropriate prompt based on region type.

2. **Handle multi-currency carefully**: 
   - Validate currency consistency
   - Convert currencies when necessary
   - Clearly label all amounts with their currency

3. **Process regions individually**: For best results, crop regions and process them separately with appropriate prompts rather than processing the entire document at once.

4. **Structure JSON output consistently**: Use the `invoice_schema.py` classes to ensure consistent JSON structure across all documents.

5. **Fine-tune with real data**: Use your actual financial documents to create fine-tuning datasets, ensuring the model learns your specific document formats and requirements.

## Integration with Document Processor

The `FinancialDocumentProcessor` automatically uses these prompts when processing documents:

```python
from app.core.document_processor import FinancialDocumentProcessor

processor = FinancialDocumentProcessor()

result = await processor.process_document(
    file_content=image_bytes,
    filename="invoice.pdf",
    model_type="fine_tuned"
)

# The processor:
# 1. Uses PaddleOCR-VL for layout analysis
# 2. Processes each region with appropriate prompt
# 3. Structures output using invoice_schema
# 4. Validates multi-currency consistency
```

## Troubleshooting

### Issue: Model returns unstructured text instead of JSON
**Solution**: Ensure you're using the correct prompt (`"Table Recognition:"` for tables, `"OCR:"` for text) and that your fine-tuned model was trained to output structured JSON.

### Issue: Multi-currency amounts are inconsistent
**Solution**: Use `validate_multi_currency_consistency()` to detect issues and ensure all amounts are properly converted or labeled.

### Issue: Mixed elements not processing correctly
**Solution**: Ensure layout analysis correctly detects and classifies regions before passing them to `parse_mixed_document()`.

## References

- [PaddleOCR Official Repository](https://github.com/PaddlePaddle/PaddleOCR)
- [PaddleOCR-VL Documentation](https://aistudio.baidu.com/paddleocr)
- [Transformers Library PaddleOCR Examples](https://huggingface.co/PaddlePaddle/PaddleOCR-VL)


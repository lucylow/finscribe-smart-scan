# PaddleOCR-VL Task-Specific Prompts Implementation Summary

## Overview

This implementation adds proper task-specific prompt support for PaddleOCR-VL in FinScribe AI, following the official PaddleOCR documentation. The system now correctly uses fixed prompts (`"OCR:"`, `"Table Recognition:"`, etc.) instead of conversational prompts, and includes comprehensive support for multi-currency invoices and mixed document elements.

## What Was Implemented

### 1. Task-Specific Prompt System (`app/core/models/paddleocr_prompts.py`)

**Purpose**: Centralized prompt management following PaddleOCR-VL's official prompt system.

**Key Features**:
- Core task prompts: `OCR:`, `Table Recognition:`, `Formula Recognition:`, `Chart Recognition:`
- Automatic region-to-prompt mapping
- Helper functions for prompt selection

**Usage**:
```python
from app.core.models.paddleocr_prompts import get_prompt_for_region

prompt = get_prompt_for_region("line_items_table")  # Returns "Table Recognition:"
```

### 2. Multi-Currency Invoice Schema (`app/core/models/invoice_schema.py`)

**Purpose**: Structured JSON schema for financial documents with multi-currency support.

**Key Features**:
- `CurrencyAmount` class for amounts with currency codes
- `InvoiceDocument` dataclass for complete invoice structure
- `LineItem`, `VendorInfo`, `ClientInfo`, `FinancialSummary` classes
- Currency string parsing (`parse_currency_string()`)
- Multi-currency validation (`validate_multi_currency_consistency()`)

**Usage**:
```python
from app.core.models.invoice_schema import InvoiceDocument, CurrencyAmount, LineItem

invoice = InvoiceDocument(
    invoice_number="INV-001",
    invoice_date="2025-01-15",
    line_items=[
        LineItem(
            description="Service",
            quantity=1,
            unit_price=CurrencyAmount(amount=100.00, currency="USD"),
            line_total=CurrencyAmount(amount=100.00, currency="USD")
        )
    ]
)
json_output = invoice.to_json()
```

### 3. Enhanced PaddleOCR-VL Service (`app/core/models/paddleocr_vl_service.py`)

**Purpose**: Updated service to use task-specific prompts and support mixed element processing.

**New Methods**:
- `parse_region()`: Process individual regions with appropriate prompts
- `parse_mixed_document()`: Process documents with multiple element types (text + tables)

**Key Improvements**:
- Automatic prompt selection based on region type
- Region cropping support for targeted processing
- Mixed element handling strategy

**Usage**:
```python
# Process a specific region
result = await service.parse_region(
    image_bytes=image_bytes,
    region_type="line_items_table",  # Uses "Table Recognition:" prompt
    bbox={"x": 100, "y": 300, "w": 500, "h": 400}
)

# Process mixed document
regions = [
    {"type": "vendor_block", "bbox": {...}},
    {"type": "line_items_table", "bbox": {...}}
]
result = await service.parse_mixed_document(image_bytes, regions)
```

### 4. Updated Formatters (`finscribe/data/formatters.py`)

**Purpose**: Enhanced fine-tuning data formatters to use the new prompt system.

**Improvements**:
- Integration with `paddleocr_prompts` module
- Better handling of CurrencyAmount objects
- Consistent prompt usage across all formatters

### 5. Documentation and Examples

**Files Created**:
- `PADDLEOCR_PROMPTS_GUIDE.md`: Comprehensive usage guide
- `examples/paddleocr_prompts_example.py`: Practical examples
- `PADDLEOCR_IMPLEMENTATION_SUMMARY.md`: This file

## Architecture: Two-Stage Processing Pipeline

### Stage 1: Layout Analysis
- Uses PP-DocLayoutV2 (or similar) to detect and classify regions
- Identifies: text blocks, tables, logos, etc.
- Outputs: List of regions with bounding boxes and types

### Stage 2: Targeted Element Recognition
- Each detected region is cropped
- Passed to PaddleOCR-VL-0.9B with appropriate task prompt:
  - Text regions → `"OCR:"` prompt
  - Table regions → `"Table Recognition:"` prompt
- Model outputs structured JSON for each region

## Region Type to Prompt Mapping

| Region Type | Prompt | Use Case |
|------------|--------|----------|
| `vendor_block`, `client_info`, `header` | `"OCR:"` | Text extraction |
| `line_items_table`, `table` | `"Table Recognition:"` | Structured table parsing |
| `formula` | `"Formula Recognition:"` | Mathematical formulas |
| `chart` | `"Chart Recognition:"` | Chart data extraction |

## Multi-Currency Support

### Features
- ISO 4217 currency code support (USD, EUR, GBP, etc.)
- Currency string parsing from OCR output
- Multi-currency validation and warnings
- Consistent JSON structure across all currencies

### Example Multi-Currency Invoice
```json
{
  "invoice_number": "INV-2025-001",
  "line_items": [
    {
      "description": "US Service",
      "unit_price": {"amount": 100.00, "currency": "USD"},
      "line_total": {"amount": 100.00, "currency": "USD"}
    },
    {
      "description": "European License",
      "unit_price": {"amount": 500.00, "currency": "EUR"},
      "line_total": {"amount": 500.00, "currency": "EUR"}
    }
  ],
  "financial_summary": {
    "grand_total": {"amount": 600.00, "currency": "USD"}
  }
}
```

## Mixed Elements Strategy

For documents containing both text and tables on the same page:

1. **Layout Analysis**: Detect all regions and their types
2. **Region Processing**: Process each region individually with appropriate prompt
3. **Result Combination**: Merge results from all regions into structured output

**Benefits**:
- Better accuracy (each region uses optimal prompt)
- Handles complex layouts
- Supports fine-tuning on specific region types

## Fine-Tuning Integration

The prompt system integrates seamlessly with fine-tuning:

1. **Training Data Structure**: Use `build_instruction_sample()` to create training pairs
2. **Prompt Consistency**: All samples use correct task-specific prompts
3. **Target Output**: Structured JSON matching `invoice_schema.py` format

**Example Training Sample**:
```python
sample = build_instruction_sample(
    image=cropped_table_image,
    region_type="line_items_table",  # Uses "Table Recognition:" prompt
    target=[{"description": "...", "quantity": 1, ...}]
)
```

## Testing

Run the example script to see all features in action:

```bash
python examples/paddleocr_prompts_example.py
```

This demonstrates:
- Region-specific processing
- Mixed document handling
- Multi-currency invoice creation
- Currency string parsing
- Prompt mapping
- Fine-tuning data structure

## Integration Points

### With Document Processor
The `FinancialDocumentProcessor` can now:
- Use region-specific prompts automatically
- Process mixed documents efficiently
- Output structured multi-currency JSON

### With Fine-Tuning Pipeline
The `finscribe/data/formatters.py` now:
- Uses consistent prompts across all training samples
- Supports multi-currency line items
- Generates properly structured JSON targets

## Next Steps

1. **Layout Analysis Integration**: Connect with PP-DocLayoutV2 or similar for automatic region detection
2. **Fine-Tuning**: Use the new prompt system in your fine-tuning pipeline
3. **Currency Conversion**: Add automatic currency conversion for multi-currency invoices
4. **Validation**: Enhance validation rules for multi-currency scenarios

## References

- [PaddleOCR Official Repository](https://github.com/PaddlePaddle/PaddleOCR)
- [PaddleOCR-VL Documentation](https://aistudio.baidu.com/paddleocr)
- [ISO 4217 Currency Codes](https://www.iso.org/iso-4217-currency-codes.html)

## Files Modified/Created

### New Files
- `app/core/models/paddleocr_prompts.py` - Prompt system
- `app/core/models/invoice_schema.py` - Multi-currency schema
- `PADDLEOCR_PROMPTS_GUIDE.md` - Usage guide
- `examples/paddleocr_prompts_example.py` - Examples
- `PADDLEOCR_IMPLEMENTATION_SUMMARY.md` - This file

### Modified Files
- `app/core/models/paddleocr_vl_service.py` - Added region processing and prompt support
- `finscribe/data/formatters.py` - Integrated prompt system

## Key Benefits

1. **Correct Prompt Usage**: Follows official PaddleOCR-VL documentation
2. **Better Accuracy**: Task-specific prompts improve recognition quality
3. **Multi-Currency Support**: Handles international invoices properly
4. **Mixed Elements**: Processes complex documents with text + tables
5. **Fine-Tuning Ready**: Structured for effective model fine-tuning
6. **Type Safety**: Dataclasses provide structure and validation


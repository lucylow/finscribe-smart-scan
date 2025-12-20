# Structured Financial Data Output Guide

This guide explains how FinScribe AI generates structured financial data output using PaddleOCR-VL, following the two-stage pipeline architecture for optimal document understanding and data extraction.

## Overview

PaddleOCR-VL excels at converting visual document layouts into machine-readable, structured formats. This is crucial for automated data extraction from financial documents like invoices, receipts, and financial statements.

## Output Formats

FinScribe AI supports **two complementary output formats** that work together:

| Output Type | Description | Use Case |
| :--- | :--- | :--- |
| **JSON** | Structured output containing text content, bounding box coordinates, element types (text, table, figure), and hierarchical relationships | Perfect for programmatic use. A parsed income statement's "Revenue" line item would be tagged with its value, label, and position in the document. |
| **Markdown** | A formatted, human-readable version that visually preserves the document's layout, such as headings, paragraphs, and tables | Useful for quick verification and review. It clearly shows how the model interprets table structures and headings. |
| **Combined Outputs** | The post-processing module combines layout analysis and recognition results to generate both JSON and Markdown formats simultaneously | Enables you to validate the extracted data (via Markdown) and feed the structured fields directly into a database or application (via JSON). |

## Architecture: Two-Stage Pipeline

The system implements a two-stage pipeline as detailed in the official PaddlePaddle architecture:

### Stage 1: Layout Analysis with PP-DocLayoutV2

This stage uses a detection model to identify and classify all semantic regions on a page:
- **Text blocks** (headers, vendor info, client info)
- **Tables** (line items, financial summaries)
- **Other elements** (logos, signatures, etc.)

Crucially, it also predicts the correct **reading order**, which is vital for understanding multi-column layouts common in financial reports.

### Stage 2: Element Recognition with PaddleOCR-VL-0.9B

Each region identified in Stage 1 is processed by the Vision-Language Model. This is where the model:
- Reads the content
- Understands its *internal* structure
- Recognizes individual cells, headers, and their relationships

For example, it doesn't just see a "table" region; it recognizes individual cells, headers, and their relationships.

### Final Post-Processing

The outputs from both stages are aggregated. The system combines:
- **Spatial relationships** (from layout analysis)
- **Recognized text and structure** (from the VLM)

To build the final **JSON and Markdown outputs**.

## Usage Examples

### Basic Usage: Standard Processing

```python
from app.core.document_processor import FinancialDocumentProcessor

processor = FinancialDocumentProcessor()

# Process document (returns JSON in structured_output, Markdown in markdown_output)
result = await processor.process_document(file_content, "invoice.pdf")

# Access JSON structured data
json_data = result.get("structured_output", {})
vendor_name = json_data.get("vendor_block", {}).get("name")

# Access Markdown for human review
markdown = result.get("markdown_output", "")
print(markdown)  # View formatted output
```

### Advanced Usage: Combined Output Method

For explicit control over both formats:

```python
# Get both JSON and Markdown in a structured response
combined_result = await processor.process_document_with_combined_output(
    file_content, 
    "invoice.pdf"
)

# Access both formats
json_output = combined_result.get("json", {})
markdown_output = combined_result.get("markdown", "")

# JSON contains structured data
line_items = json_output.get("data", {}).get("line_items", [])

# Markdown is ready for display/review
print(markdown_output)
```

### Direct Post-Processing Usage

If you already have OCR results and want to generate structured output:

```python
from app.core.post_processing import FinancialDocumentPostProcessor

post_processor = FinancialDocumentPostProcessor()

# Generate combined JSON + Markdown
combined = post_processor.generate_combined_output(ocr_results)

# Or generate individually
json_data = post_processor.extract_financial_structure(ocr_results)
markdown_text = post_processor.generate_markdown(json_data)
```

## JSON Output Structure

The JSON output follows this structure:

```json
{
  "success": true,
  "timestamp": "2025-01-15T10:30:00",
  "data": {
    "vendor": {
      "name": "Acme Corporation",
      "address": "123 Business St",
      "contact": {
        "email": "contact@acme.com",
        "phone": "+1-555-0123"
      },
      "confidence": 0.96
    },
    "client": {
      "invoice_number": "INV-2025-001",
      "invoice_date": "2025-01-15",
      "due_date": "2025-02-15",
      "client_name": "Client Inc."
    },
    "line_items": [
      {
        "description": "Consulting Services",
        "quantity": 10,
        "unit_price": 150.00,
        "line_total": 1500.00
      }
    ],
    "financial_summary": {
      "subtotal": 2750.00,
      "tax": {
        "rate": 10.0,
        "amount": 275.00
      },
      "grand_total": 3025.00,
      "currency": "$",
      "payment_terms": "Net 30"
    }
  },
  "validation": {
    "is_valid": true,
    "confidence_scores": {
      "vendor": 0.96,
      "client": 0.94,
      "line_items": 0.95,
      "arithmetic": 0.98
    },
    "overall_confidence": 0.96
  },
  "metadata": {
    "region_count": 5,
    "total_elements": 45,
    "processing_timestamp": "2025-01-15T10:30:00"
  }
}
```

## Markdown Output Example

The Markdown output provides a human-readable view:

```markdown
# Financial Document

**Processed:** 2025-01-15T10:30:00

## Vendor Information

**Name:** Acme Corporation
**Address:** 123 Business St, Suite 100
**Email:** contact@acme.com
**Phone:** +1-555-0123

## Invoice Information

**Invoice Number:** INV-2025-001
**Client:** Client Inc.
**Invoice Date:** 2025-01-15
**Due Date:** 2025-02-15

## Line Items

| Description | Quantity | Unit Price | Line Total |
| --- | --- | --- | --- |
| Consulting Services | 10 | $150.00 | $1,500.00 |
| Software License | 2 | $500.00 | $1,000.00 |

## Financial Summary

**Subtotal:** $2,750.00
**Tax (10%):** $275.00

### Grand Total: $3,025.00

**Payment Terms:** Net 30

## Validation Results

**Status:** ✅ Valid

### Confidence Scores
- **Vendor:** 96.0%
- **Client:** 94.0%
- **Line Items:** 95.0%

**Overall Confidence:** 96.0%
```

## Key Features

### 1. Semantic Understanding

The system goes beyond simple text extraction to provide **semantic understanding**:
- Recognizes "Total" as a monetary value
- Checks arithmetic consistency
- Identifies relationships between fields

### 2. Multi-Currency Support

Handles various currency formats:
- `$100.00` (USD)
- `€1.234,56` (European format)
- `£1,000.50` (GBP)
- `¥1000` (JPY)

### 3. Validation & Confidence Scores

Each extraction includes:
- **Confidence scores** per field
- **Arithmetic validation** (line totals, grand totals)
- **Date consistency checks**
- **Overall confidence** metric

### 4. Hierarchical Structure

The output preserves document hierarchy:
- Document → Regions → Elements
- Tables → Rows → Cells
- Financial Summary → Components

## API Integration

### REST API Response

When using the `/api/v1/analyze` endpoint, the response includes:

```json
{
  "status": "completed",
  "result_id": "doc-123",
  "data": {
    "structured_output": { /* JSON data */ },
    "markdown_output": "# Financial Document\n\n...",
    "validation": { /* validation results */ }
  },
  "downloads": {
    "json": "/api/v1/results/doc-123/download?format=json",
    "markdown": "/api/v1/results/doc-123/download?format=markdown"
  }
}
```

### Download Formats

You can download results in different formats:
- `GET /api/v1/results/{result_id}/download?format=json` - JSON format
- `GET /api/v1/results/{result_id}/download?format=markdown` - Markdown format

## Best Practices

### 1. Use Combined Outputs for Validation

Always use both JSON and Markdown:
- **JSON** for programmatic processing
- **Markdown** for human verification

### 2. Check Confidence Scores

Review confidence scores before using extracted data:
```python
validation = result.get("validation", {})
confidence = validation.get("overall_confidence", 0)

if confidence < 0.8:
    # Flag for manual review
    pass
```

### 3. Validate Arithmetic

The system automatically validates arithmetic, but you should also check:
```python
validation = result.get("validation", {})
if not validation.get("is_valid"):
    errors = validation.get("errors", [])
    # Handle errors
```

### 4. Handle Partial Results

Some documents may return partial results:
```python
if result.get("metadata", {}).get("partial_results"):
    # Some processing steps may have failed
    # Check individual confidence scores
    pass
```

## Fine-Tuning Considerations

For fine-tuning PaddleOCR-VL to output specific structured data:

1. **Training Data Format**: Create instruction-response pairs where the response is structured JSON
   ```
   Prompt: "Extract all line items into a JSON array"
   Response: [{"description": "Item A", "qty": 2, "unit_price": 50.0}, ...]
   ```

2. **Focus on Table Recognition**: Fine-tune specifically for table parsing if your documents contain complex financial tables

3. **Document Type Specialization**: Consider fine-tuning for specific document types (invoices, receipts, balance sheets) for better accuracy

## Performance Considerations

- **Layout Analysis**: Fast, typically < 100ms
- **Element Recognition**: Depends on document complexity, typically 200-500ms
- **Post-Processing**: Very fast, typically < 50ms
- **Total Pipeline**: Usually completes in < 1 second for standard invoices

## Troubleshooting

### Low Confidence Scores

If confidence scores are low:
1. Check document image quality
2. Verify document type matches training data
3. Review validation errors for specific issues

### Missing Fields

If expected fields are missing:
1. Check if field exists in Markdown output (may be extraction issue)
2. Review raw OCR output for text presence
3. Consider document-specific fine-tuning

### Arithmetic Validation Failures

If arithmetic checks fail:
1. Review line item calculations
2. Check for currency symbol mismatches
3. Verify tax/discount calculations

## Next Steps

- Review [PADDLEOCR_PROMPTS_GUIDE.md](./PADDLEOCR_PROMPTS_GUIDE.md) for task-specific prompts
- Check [FINETUNING_GUIDE.md](./FINETUNING_GUIDE.md) for fine-tuning instructions
- See [HACKATHON_STRATEGY.md](./HACKATHON_STRATEGY.md) for hackathon submission planning


# PaddleOCR-VL Structured Financial Data Output: Technical Guide

## Overview

For your PaddleOCR-VL fine-tuning project, achieving structured financial data output is central to the model's design. The system is built to turn the visual layout of a document into a machine-readable, structured format, which is crucial for automated data extraction from financial documents.

PaddleOCR-VL excels at this by first understanding a document's layout and then applying this knowledge to recognize and categorize elements like text and tables, which are key components of financial statements and invoices.

## Output Types

The table below summarizes the types of structured data the system can produce:

| Output Type | Description | Financial Document Application |
| :--- | :--- | :--- |
| **JSON** | Structured output containing text content, bounding box coordinates, element types (e.g., text, table, figure), and their hierarchical relationships. | Perfect for programmatic use. A parsed income statement's "Revenue" line item would be tagged with its value, label, and position in the document. |
| **Markdown** | A formatted, human-readable version that visually preserves the document's layout, such as headings, paragraphs, and tables. | Useful for quick verification and review. It clearly shows how the model interprets table structures and headings. |
| **Combined Outputs** | In practice, the model's **post-processing module** combines layout analysis and recognition results to generate both JSON and Markdown formats simultaneously, providing the best of both worlds. | Enables you to validate the extracted data (via Markdown) and feed the structured fields directly into a database or application (via JSON). |

## Architecture: Two-Stage Pipeline

The architecture, as detailed in the official PaddlePaddle report, is a two-stage pipeline. Understanding this is key to effective fine-tuning.

### Stage 1: Layout Analysis with PP-DocLayoutV2

This stage uses a detection model to identify and classify all semantic regions on a page (text blocks, tables, formulas). Crucially, it also predicts the correct reading order, which is vital for understanding multi-column layouts common in financial reports.

**What it does:**
- Identifies **text blocks** (headers, vendor info, client info, line item descriptions)
- Detects **tables** (line items tables, financial summaries, balance sheets)
- Recognizes **other elements** (logos, signatures, footnotes)
- Determines **reading order** for proper document flow understanding

**Implementation in FinScribe:**
```python
# Layout analysis happens automatically in the OCR pipeline
# The PaddleOCR-VL system handles this internally
ocr_results = await ocr_service.process_document(image)
# ocr_results contains layout information including:
# - Region types (text, table, figure)
# - Bounding boxes
# - Reading order
```

### Stage 2: Element Recognition with PaddleOCR-VL-0.9B

Each region identified in Stage 1 is processed by the Vision-Language Model. This is where the model reads the content and understands its *internal* structure. For example, it doesn't just see a "table" region; it recognizes individual cells, headers, and their relationships.

**What it does:**
- Reads text content within each region
- Understands semantic structure (e.g., table cells, headers, data relationships)
- Extracts structured information (e.g., line items as JSON objects)
- Recognizes context and relationships between elements

**Implementation in FinScribe:**
```python
from app.core.post_processing import FinancialDocumentPostProcessor

post_processor = FinancialDocumentPostProcessor()

# Process OCR results to extract structured data
structured_data = post_processor.extract_financial_structure(ocr_results)

# This returns structured JSON with:
# - Vendor information
# - Client information
# - Line items (array of structured objects)
# - Financial summary (totals, taxes, discounts)
# - Validation results
```

### Final Post-Processing

The outputs from both stages are aggregated. The system combines the spatial relationships (from layout analysis) with the recognized text and structure (from the VLM) to build the final **JSON and Markdown outputs**.

**Implementation in FinScribe:**
```python
# Generate combined output (JSON + Markdown simultaneously)
combined = post_processor.generate_combined_output(ocr_results)

# Returns:
# {
#   'json': { /* structured JSON data */ },
#   'markdown': "# Financial Document\n\n...",
#   'metadata': {
#     'timestamp': '...',
#     'version': '1.0',
#     'formats': ['json', 'markdown'],
#     'success': True
#   }
# }
```

## Key Practical Considerations

Research and real-world applications highlight several factors crucial for getting reliable, structured data from financial documents.

### The Challenge of Financial Documents

Financial PDFs are often unstructured and contain complex layouts with:
- **Dense tables** with nested structures
- **Multi-language content** (e.g., invoices with multiple languages)
- **Handwritten notes** or annotations
- **Multi-column layouts** (e.g., balance sheets with multiple periods)
- **Complex formatting** (merged cells, rotated text, etc.)

A study by OCBC Bank found that using a modular pipeline with a compact VLM for specific sections can be **8.8 times more accurate** than feeding entire documents to a large model. This validates the two-stage approach used by PaddleOCR-VL.

### Beyond Simple Text Extraction

The ultimate goal is **semantic understanding** that converts raw text into meaningful, validated data:
- Recognizing "Total" as a monetary value (not just text)
- Checking arithmetic consistency (line totals = sum of line items)
- Identifying field relationships (invoice number → invoice date → due date)
- Understanding context (discounts, taxes, shipping)

**Example in FinScribe:**
```python
# The post-processor performs semantic understanding:
structured_data = post_processor.extract_financial_structure(ocr_results)

# This includes:
# - Arithmetic validation (checks if totals are correct)
# - Confidence scores for each extraction
# - Error detection (missing fields, invalid values)
# - Relationship mapping (vendor → invoice → line items → totals)
```

### Quality of Output

In practical business applications, structured output for an invoice includes:
- **Detailed nested JSON** for vendor info, line items, tax breakdowns
- **Confidence scores** for each extracted field
- **Fraud detection flags** (e.g., suspicious amounts, duplicate invoices)
- **Validation results** (arithmetic checks, date consistency)

**FinScribe Implementation:**
```python
{
  "data": {
    "vendor": {
      "name": "Acme Corp",
      "confidence": 0.96  # High confidence
    },
    "line_items": [
      {
        "description": "Consulting",
        "quantity": 10,
        "unit_price": 150.00,
        "line_total": 1500.00,
        "confidence": 0.94
      }
    ],
    "financial_summary": {
      "subtotal": 2750.00,
      "tax": {"rate": 10.0, "amount": 275.00},
      "grand_total": 3025.00
    }
  },
  "validation": {
    "is_valid": True,
    "confidence_scores": {
      "vendor": 0.96,
      "line_items": 0.95,
      "arithmetic": 0.98  # Arithmetic checks passed
    },
    "arithmetic_checks": {
      "line_items_total": {
        "is_valid": True,
        "calculated": 2750.00,
        "extracted": 2750.00,
        "difference": 0.00
      }
    }
  }
}
```

## Preparing Your Fine-Tuning Dataset for Structure

To train PaddleOCR-VL to output the specific structured data you need, your training examples must reflect the desired output format.

### Instruction-Response Pairs

This involves creating instruction-response pairs where the **response** is the structured output (like JSON) for a given document image and task prompt.

**Example Training Pair:**
```json
{
  "instruction": "<invoice_image> Extract all line items into a JSON array.",
  "output": "[{\"description\": \"Item A\", \"qty\": 2, \"unit_price\": 50.0, \"line_total\": 100.0}, {\"description\": \"Item B\", \"qty\": 1, \"unit_price\": 75.0, \"line_total\": 75.0}]"
}
```

**Another Example:**
```json
{
  "instruction": "<balance_sheet_image> Extract the financial summary including total assets, total liabilities, and equity.",
  "output": "{\"total_assets\": 1000000.0, \"total_liabilities\": 600000.0, \"equity\": 400000.0}"
}
```

### Task-Specific Fine-Tuning

A question on the official ERNIE GitHub repository confirms that fine-tuning supports specific tasks like "Table Recognition". This means you can focus your training to make the model exceptionally good at parsing complex financial tables.

**FinScribe Training Approach:**
```python
# In finscribe/training/instruction_pairs.py
# You can create specialized training pairs for table recognition:

table_recognition_pairs = [
    {
        "instruction": "Extract the line items table from this invoice as JSON.",
        "output": "[{\"description\": \"...\", \"qty\": ..., \"price\": ...}]",
        "task_type": "table_recognition",
        "document_type": "invoice"
    }
]
```

### Document Type Specialization

To effectively plan your hackathon submission, it would be helpful to know which specific financial document type you plan to focus your model on first:

1. **Multi-currency commercial invoices** - Complex line items, tax calculations, multiple currencies
2. **Balance sheets** - Multi-column tables, hierarchical account structures
3. **Income statements** - Revenue/expense categorization, period comparisons
4. **Receipts** - Simple structure, but with handwritten notes and various formats

This will help define:
- The exact structure of your training data
- Expected JSON output schema
- Validation rules specific to that document type
- Success metrics for evaluation

## Implementation in FinScribe AI

### Code Structure

```
app/core/
├── document_processor.py      # Main processor (uses OCR + post-processing)
└── post_processing.py          # Structured output generation (JSON + Markdown)

finscribe/training/
└── instruction_pairs.py        # Training data generation for fine-tuning
```

### Usage Examples

#### Example 1: Standard Processing (Automatic Markdown)

```python
from app.core.document_processor import FinancialDocumentProcessor

processor = FinancialDocumentProcessor()

# Process document (returns JSON in structured_output, Markdown in markdown_output)
result = await processor.process_document(file_content, "invoice.pdf")

# Access JSON structured data
json_data = result.get("structured_output", {})
vendor_name = json_data.get("data", {}).get("vendor", {}).get("name")

# Access Markdown for human review
markdown = result.get("markdown_output", "")
print(markdown)  # View formatted output
```

#### Example 2: Explicit Combined Output

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

#### Example 3: Direct Post-Processing

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

## JSON Output Schema

The JSON output follows a structured schema designed for financial documents:

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
      "dates": {
        "invoice_date": "2025-01-15",
        "due_date": "2025-02-15"
      },
      "client_name": "Client Inc."
    },
    "line_items": [
      {
        "description": "Consulting Services",
        "quantity": 10,
        "unit_price": 150.00,
        "line_total": 1500.00,
        "confidence": 0.95
      }
    ],
    "financial_summary": {
      "subtotal": 2750.00,
      "tax": {
        "rate": 10.0,
        "amount": 275.00
      },
      "discount": {
        "rate": 0.0,
        "amount": 0.00
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
    "overall_confidence": 0.96,
    "arithmetic_checks": {
      "line_items_total": {
        "is_valid": true,
        "calculated": 2750.00,
        "extracted": 2750.00,
        "difference": 0.00
      },
      "grand_total": {
        "is_valid": true,
        "calculated": 3025.00,
        "extracted": 3025.00,
        "difference": 0.00
      }
    },
    "errors": [],
    "warnings": []
  },
  "metadata": {
    "region_count": 5,
    "total_elements": 45,
    "processing_timestamp": "2025-01-15T10:30:00",
    "output_formats": ["json", "markdown"]
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
- **Arithmetic:** 98.0%

**Overall Confidence:** 96.0%

### Arithmetic Validation
- ✅ **Line Items Total:**
  - Calculated: 2,750.00
  - Extracted: 2,750.00
  - Difference: 0.00
- ✅ **Grand Total:**
  - Calculated: 3,025.00
  - Extracted: 3,025.00
  - Difference: 0.00
```

## Best Practices for Fine-Tuning

### 1. Focus on Specific Document Types

Start with one document type (e.g., invoices) and create specialized training data:
- Consistent JSON schema
- Document-type-specific validation rules
- High-quality examples with accurate labels

### 2. Use Structured Output in Training

Always use structured JSON in your training responses:
```python
# Good: Structured output
output = {
    "line_items": [
        {"description": "Item A", "qty": 2, "price": 50.0}
    ]
}

# Bad: Unstructured text
output = "Item A, 2 units, $50 each"
```

### 3. Include Confidence and Validation

Train the model to include confidence scores and validation in output:
```python
{
    "data": { /* extracted data */ },
    "validation": {
        "confidence_scores": { /* per-field confidence */ },
        "arithmetic_checks": { /* validation results */ }
    }
}
```

### 4. Leverage Combined Outputs

Use both JSON and Markdown in your evaluation:
- JSON for automated testing and validation
- Markdown for human review and quality assurance

## Performance Considerations

Based on the two-stage pipeline architecture:

- **Layout Analysis (Stage 1)**: Fast, typically < 100ms
- **Element Recognition (Stage 2)**: Depends on document complexity, typically 200-500ms per region
- **Post-Processing**: Very fast, typically < 50ms
- **Total Pipeline**: Usually completes in < 1 second for standard invoices

For complex documents with many regions, processing time scales linearly with the number of regions identified in Stage 1.

## Next Steps

1. **Define Your Target Document Type**: Choose the specific financial document type for your hackathon submission
2. **Create Training Data**: Generate instruction-response pairs with structured JSON outputs
3. **Fine-Tune the Model**: Use the training data to fine-tune PaddleOCR-VL for your specific use case
4. **Evaluate Performance**: Test with real-world documents and measure accuracy
5. **Iterate**: Refine training data based on evaluation results

For more information:
- See [STRUCTURED_OUTPUT_GUIDE.md](./STRUCTURED_OUTPUT_GUIDE.md) for implementation details
- Check [FINETUNING_GUIDE.md](./FINETUNING_GUIDE.md) for fine-tuning instructions
- Review [PADDLEOCR_PROMPTS_GUIDE.md](./PADDLEOCR_PROMPTS_GUIDE.md) for task-specific prompts
- See [HACKATHON_STRATEGY.md](./HACKATHON_STRATEGY.md) for hackathon submission planning


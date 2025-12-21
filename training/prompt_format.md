# Prompt Engineering Guide for FinScribe

This document explains the prompt design strategy for fine-tuning PaddleOCR-VL on financial documents.

## Overview

Our fine-tuning approach uses **task-specific prompts** that guide the model to extract structured information from financial documents. The prompts are designed to leverage PaddleOCR-VL's layout understanding capabilities (via PP-DocLayoutV2) while ensuring accurate semantic extraction.

## Core Prompt Philosophy

1. **Region-Aware Instructions**: Different semantic regions (vendor block, line items table, financial summary) require different extraction strategies
2. **Structured Output Format**: Prompts explicitly request JSON output to ensure consistency
3. **Layout Context**: Prompts reference spatial relationships ("table", "header", "footer") to leverage the model's layout understanding
4. **Completeness Guidance**: Instructions emphasize extracting all relevant fields, not just visible text

## Prompt Templates by Region Type

### 1. Full Document OCR Prompt (Default)

```
Extract all text and layout information from this financial document. 
Identify semantic regions including: vendor information, client details, 
invoice metadata (number, date, due date), line items table, and financial summary (subtotal, tax, total).
Return structured JSON with bounding boxes for each detected element.
```

**Use Case**: Initial document parsing when region boundaries are unknown.

### 2. Vendor Block Extraction

```
Extract vendor information from this document region. Look for:
- Vendor name (company name)
- Vendor address (street, city, state, zip, country)
- Vendor contact information (phone, email, website)
- Vendor tax ID or registration number (if present)

Return as JSON object with keys: name, address, contact, tax_id.
Include bounding boxes for each extracted field.
```

**Target Region**: Top-left or top section of invoice.

### 3. Line Items Table Extraction

```
Extract the line items table from this document region. Each row should contain:
- Description or item name
- Quantity (numeric value)
- Unit price (currency value)
- Line total (quantity × unit price)

Identify table headers and ensure proper row/column alignment.
Return as JSON array of objects, each with keys: description, quantity, unit_price, line_total.
Include bounding boxes for the entire table and each cell.
```

**Target Region**: Central section of invoice containing itemized list.

### 4. Financial Summary Extraction

```
Extract financial summary information from this document region. Look for:
- Subtotal (sum of line items before tax/discount)
- Discount amount (if applicable)
- Tax rate and tax amount
- Shipping/Handling charges (if applicable)
- Grand total (final amount due)

Ensure numeric values are correctly parsed (handle currency symbols, commas, decimal points).
Return as JSON object with keys: subtotal, discount, tax_rate, tax_amount, shipping, grand_total, currency.
```

**Target Region**: Bottom section or footer area of invoice.

### 5. Invoice Metadata Extraction

```
Extract invoice metadata from this document region. Look for:
- Invoice number (may be labeled as "Invoice #", "Invoice No.", "INV", etc.)
- Issue date (date invoice was created)
- Due date (payment deadline, if present)
- Purchase order number (PO number, if present)
- Payment terms (e.g., "Net 30", "Due on receipt")

Return as JSON object with keys: invoice_number, issue_date, due_date, po_number, payment_terms.
Parse dates in standard format (YYYY-MM-DD).
```

**Target Region**: Header section, often near invoice number.

## Prompt Construction in Code

Prompts are dynamically constructed based on the region type and task:

```python
# From app/core/models/paddleocr_prompts.py

def get_prompt_for_region(region_type: str) -> str:
    """Get task-specific prompt based on region type."""
    prompts = {
        "vendor_block": VENDOR_EXTRACTION_PROMPT,
        "line_items_table": LINE_ITEMS_EXTRACTION_PROMPT,
        "financial_summary": FINANCIAL_SUMMARY_PROMPT,
        "invoice_metadata": INVOICE_METADATA_PROMPT,
        "client_block": CLIENT_EXTRACTION_PROMPT,
    }
    return prompts.get(region_type, DEFAULT_OCR_PROMPT)
```

## Training Data Format

During fine-tuning, prompts are paired with expected JSON outputs:

**Input (Instruction)**:
```
Extract vendor information from this document region...
```

**Output (Completion)**:
```json
{
  "vendor": {
    "name": "TechCorp Inc.",
    "address": {
      "street": "123 Innovation Drive",
      "city": "San Francisco",
      "state": "CA",
      "zip": "94105",
      "country": "USA"
    },
    "contact": {
      "phone": "+1-415-555-0100",
      "email": "contact@techcorp.com"
    }
  }
}
```

## Key Design Decisions

### 1. Explicit JSON Structure Requests

**Rationale**: By explicitly requesting JSON output, we guide the model to produce structured data that's easy to parse and validate programmatically.

**Implementation**: All prompts end with "Return as JSON..." instructions.

### 2. Region-Specific Prompts

**Rationale**: Different document regions have different extraction challenges:
- Vendor blocks: Free-form text with varying layouts
- Line items tables: Requires understanding table structure (rows/columns)
- Financial summary: Numeric extraction with validation (sums must match)

**Implementation**: Semantic layout analysis first identifies regions, then region-specific prompts are applied.

### 3. Bounding Box Inclusion

**Rationale**: Bounding boxes enable:
- Visual verification of extraction accuracy
- Post-processing validation (checking spatial relationships)
- Active learning (highlighting incorrectly extracted regions)

**Implementation**: All prompts request bounding box information for extracted fields.

### 4. Numeric Normalization Guidance

**Rationale**: Financial documents use various numeric formats (currency symbols, commas, decimal points). Explicit instructions help the model handle these variations.

**Example Prompt Addition**:
```
Ensure numeric values are correctly parsed (handle currency symbols, commas, decimal points).
Parse amounts as floating-point numbers without currency symbols.
```

## Prompt Refinement Process

1. **Initial Prompts**: Created based on domain knowledge and document structure
2. **Validation**: Tested on diverse invoice samples
3. **Error Analysis**: Identified common extraction failures
4. **Iterative Refinement**: Updated prompts to address specific failure modes
5. **A/B Testing**: Compared different phrasings to optimize extraction accuracy

## Best Practices

1. **Be Specific**: Vague instructions lead to inconsistent outputs. Specify exact field names and formats.
2. **Handle Edge Cases**: Mention common variations (e.g., "Invoice #", "Invoice No.", "INV")
3. **Request Validation**: Ask the model to verify extracted data makes sense (e.g., "Ensure line totals equal quantity × unit price")
4. **Format Guidelines**: Specify output format clearly (JSON structure, date formats, numeric precision)

## Example: Complete Extraction Workflow

```python
# 1. Full document analysis
full_ocr_prompt = DEFAULT_OCR_PROMPT
layout_result = await ocr_client.analyze_image(image_bytes, prompt=full_ocr_prompt)

# 2. Identify semantic regions
regions = semantic_layout_analyzer.analyze_layout(layout_result)

# 3. Extract region-specific data
for region in regions:
    region_prompt = get_prompt_for_region(region.type)
    region_image = crop_image(image_bytes, region.bbox)
    region_data = await ocr_client.analyze_image(region_image, prompt=region_prompt)

# 4. Aggregate results
structured_output = aggregate_regions(region_data_list)
```

## Future Improvements

1. **Few-Shot Examples**: Include example input-output pairs in prompts for in-context learning
2. **Chain-of-Thought**: Add reasoning steps for complex extractions (e.g., "First identify the table structure, then extract each row")
3. **Multi-Language Support**: Adapt prompts for different languages (translate field names and instructions)
4. **Error Recovery**: Add prompts for handling ambiguous cases (e.g., "If date format is unclear, extract as-is and flag for review")



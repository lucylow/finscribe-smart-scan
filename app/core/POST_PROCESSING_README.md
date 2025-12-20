# Phase 3: Post-Processing Intelligence

## Overview

The `FinancialDocumentPostProcessor` is a robust post-processing layer that transforms raw, layout-aware OCR output into validated, structured financial data. This module implements:

1. **Layout Analysis**: Uses bounding box coordinates to identify semantic regions
2. **Business Rules**: Applies domain-specific rules for financial documents
3. **Validation**: Validates arithmetic relationships and data consistency
4. **Structured Output**: Produces clean, validated JSON ready for integration

## Features

### 1. Semantic Region Identification

The processor identifies 5 key semantic regions using spatial analysis:

- **Vendor Block**: Top-left quadrant, contains vendor information
- **Client Block**: Top-right or near vendor, contains invoice/client metadata
- **Line Items**: Centered table area with numeric columns
- **Tax Section**: Below line items, contains tax/discount information
- **Totals**: Bottom-right area, contains grand total and payment terms

### 2. Business Rule Validation

- **Arithmetic Validation**: 
  - Line item totals (quantity × price = line_total)
  - Grand total calculation (subtotal + tax - discount = grand_total)
  
- **Date Validation**:
  - Invoice date before due date
  - Future date warnings
  
- **Duplicate Detection**:
  - Identifies potential duplicate line items

### 3. Confidence Scoring

Calculates confidence scores for:
- Vendor information
- Client/invoice metadata
- Line items
- Arithmetic validation
- Overall document confidence

## Usage

### Basic Usage

```python
from app.core.post_processing import FinancialDocumentPostProcessor

# Initialize processor
processor = FinancialDocumentPostProcessor()

# Process OCR results
result = processor.process_ocr_output(ocr_results)

# Check results
if result['success']:
    data = result['data']
    validation = result['validation']
    print(f"Confidence: {validation['overall_confidence']:.2%}")
```

### With Custom Configuration

```python
config = {
    'region_threshold': 50.0,
    'numeric_tolerance': 0.01,
    'min_confidence': 0.7,
    'validation': {
        'validate_arithmetic': True,
        'validate_dates': True,
        'check_duplicates': True,
        'enforce_positive': True
    }
}

processor = FinancialDocumentPostProcessor(config=config)
```

### Integration with Document Processor

The post-processing layer is automatically integrated into the `FinancialDocumentProcessor` pipeline. It runs after OCR and can supplement or replace VLM output.

To enable/disable in configuration:

```python
config = {
    "post_processing": {
        "enabled": True,
        "region_threshold": 50.0,
        "numeric_tolerance": 0.01,
        # ... other settings
    }
}
```

## Input Format

The processor accepts OCR results in multiple formats:

### Format 1: PaddleOCR-VL Service Format
```python
{
    'tokens': [
        {'text': 'Invoice', 'confidence': 0.99},
        # ...
    ],
    'bboxes': [
        {'x': 100, 'y': 50, 'w': 100, 'h': 20, 'region_type': 'header'},
        # ...
    ]
}
```

### Format 2: Pages Format
```python
{
    'pages': [{
        'elements': [
            {
                'text': 'Invoice',
                'bbox': [100, 50, 200, 70],
                'type': 'text',
                'confidence': 0.99
            }
        ]
    }]
}
```

### Format 3: Text Blocks Format
```python
{
    'text_blocks': [
        {
            'text': 'Invoice',
            'box': [100, 50, 200, 70],
            'confidence': 0.99
        }
    ]
}
```

## Output Format

```json
{
  "success": true,
  "timestamp": "2024-01-15T10:30:00",
  "data": {
    "vendor": {
      "name": "Tech Solutions Inc.",
      "address": "123 Innovation St...",
      "contact": {
        "email": "info@tech.com",
        "phone": "+1-555-0123"
      },
      "confidence": 0.95
    },
    "client": {
      "invoice_number": "INV-2024-001",
      "dates": {
        "invoice_date": "2024-01-15",
        "due_date": "2024-02-14"
      },
      "client_name": "ABC Corp"
    },
    "line_items": [
      {
        "description": "Software License",
        "quantity": 5,
        "price": 100.00,
        "line_total": 500.00
      }
    ],
    "financial_summary": {
      "subtotal": 500.00,
      "tax": {
        "rate": 7.0,
        "amount": 35.00
      },
      "discount": {
        "rate": 0.0,
        "amount": 0.00
      },
      "grand_total": 535.00,
      "currency": "$",
      "payment_terms": "Net 30 days"
    }
  },
  "validation": {
    "is_valid": true,
    "errors": [],
    "warnings": [],
    "confidence_scores": {
      "vendor": 0.95,
      "client": 0.85,
      "line_items": 0.92,
      "arithmetic": 0.98
    },
    "overall_confidence": 0.93,
    "arithmetic_checks": {
      "subtotal_validation": {
        "calculated": 535.00,
        "extracted": 535.00,
        "difference": 0.0,
        "is_valid": true
      }
    }
  },
  "metadata": {
    "region_count": 5,
    "total_elements": 24,
    "processing_timestamp": "2024-01-15T10:30:00"
  },
  "version": "1.0"
}
```

## Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `region_threshold` | 50.0 | Pixel threshold for region grouping |
| `numeric_tolerance` | 0.01 | Tolerance for numerical comparisons |
| `min_confidence` | 0.7 | Minimum confidence for text elements |
| `currency_precision` | 2 | Decimal places for currency |
| `validation.validate_arithmetic` | True | Enable arithmetic validation |
| `validation.validate_dates` | True | Enable date validation |
| `validation.check_duplicates` | True | Enable duplicate detection |
| `validation.enforce_positive` | True | Enforce positive amounts |

## Error Handling

The processor gracefully handles errors and returns structured error output:

```python
{
    "success": False,
    "timestamp": "2024-01-15T10:30:00",
    "error": "Error message",
    "data": {},
    "validation": {
        "is_valid": False,
        "errors": ["Error message"],
        "warnings": [],
        "confidence_scores": {},
        "overall_confidence": 0.0
    }
}
```

## Testing

Run the example to see the processor in action:

```bash
python examples/post_processing_example.py
```

## Architecture

```
OCR Results (Raw)
    ↓
Parse OCR Results → TextElement[] with BoundingBoxes
    ↓
Identify Semantic Regions → DocumentRegion[]
    ↓
Extract Region Data → Structured Data Dict
    ↓
Validate Financial Data → Validation Results
    ↓
Create Final Output → Validated JSON
```

## Benefits

1. **Reliability**: Validates extracted data against business rules
2. **Confidence Scoring**: Provides confidence metrics for each data section
3. **Error Detection**: Identifies arithmetic mismatches and inconsistencies
4. **Flexible Input**: Handles multiple OCR output formats
5. **Production Ready**: Includes logging, error handling, and comprehensive validation

## Integration Points

The post-processing layer integrates with:

- **PaddleOCR-VL Service**: Processes OCR output with bounding boxes
- **Financial Validator**: Can supplement existing validation
- **Document Processor**: Automatically runs in the processing pipeline
- **Active Learning**: Can contribute to active learning datasets

## Future Enhancements

- Machine learning-based region classification
- Multi-currency support with automatic detection
- Advanced table parsing with column detection
- Support for multi-page documents
- Custom business rule configuration


# Receipt Processing Guide

This guide explains how to use the receipt processing capabilities added to FinScribe Smart Scan.

## Overview

The receipt processing module extends FinScribe to handle receipts using PaddleOCR-VL. It provides:

- **Automatic Receipt Detection**: Detects receipts and applies specialized processing
- **Structured Data Extraction**: Extracts merchant info, items, totals, and payment details
- **Receipt Type Classification**: Identifies receipt types (grocery, restaurant, retail, gas, pharmacy)
- **Data Validation**: Validates arithmetic consistency and data completeness
- **Synthetic Data Generation**: Generates training data for fine-tuning

## Quick Start

### 1. Generate Synthetic Receipt Dataset

```bash
# Generate 1000 receipts for training
python examples/receipt_generation_example.py
```

Or programmatically:

```python
from finscribe.receipts import SyntheticReceiptGenerator

generator = SyntheticReceiptGenerator()
dataset = generator.generate_dataset(
    num_receipts=1000,
    output_dir="./receipt_dataset"
)
```

### 2. Process Receipts via API

Receipts are automatically detected and processed when uploaded:

```bash
# Upload a receipt (same endpoint as invoices)
curl -X POST "http://localhost:8000/api/v1/analyze" \
  -F "files=@receipt.jpg" \
  -F "mode=sync"
```

The response will include:
- `document_type: "receipt"` in metadata
- `receipt_data` with receipt-specific structure
- `receipt_type` (grocery, restaurant, etc.)

### 3. Fine-tune PaddleOCR-VL for Receipts

```bash
python -m finscribe.receipts.finetune \
    --dataset_path ./receipt_dataset \
    --output_dir ./fine_tuned_receipt_model \
    --epochs 5 \
    --batch_size 4 \
    --learning_rate 2e-4
```

## Receipt Data Structure

### Input: Receipt Image
Upload any receipt image (JPG, PNG, PDF) through the standard API.

### Output: Structured Receipt Data

```json
{
  "success": true,
  "document_id": "uuid",
  "metadata": {
    "document_type": "receipt",
    "receipt_type": "grocery"
  },
  "receipt_data": {
    "receipt_type": "grocery",
    "data": {
      "merchant_info": {
        "name": "Walmart",
        "address": "123 Main St",
        "phone": "(555) 123-4567"
      },
      "transaction_info": {
        "date": "01/15/2025",
        "time": "02:30 PM",
        "receipt_number": "REC-20250115-1234",
        "cashier": "C5",
        "register": "R12"
      },
      "items": [
        {
          "description": "Organic Apples",
          "quantity": 2,
          "unit_price": 2.99,
          "total": 5.98
        }
      ],
      "totals": {
        "subtotal": 25.50,
        "tax": 2.04,
        "total": 27.54,
        "discount": 0.0
      },
      "payment_info": {
        "method": "VISA",
        "amount_tendered": 27.54,
        "change": 0.0
      }
    },
    "validation": {
      "is_valid": true,
      "errors": [],
      "warnings": []
    }
  },
  "structured_output": {
    "document_type": "receipt",
    "merchant_info": { ... },
    "line_items": [ ... ],
    "financial_summary": { ... }
  }
}
```

## Supported Receipt Types

1. **Grocery Receipts**
   - Supermarkets, grocery stores
   - Multiple items with quantities
   - Tax calculations

2. **Restaurant Receipts**
   - Restaurants, cafes, fast food
   - Menu items, tips
   - Service charges

3. **Retail Receipts**
   - General retail stores
   - Product descriptions
   - Warranty information

4. **Gas Station Receipts**
   - Fuel purchases
   - Gallons/liters
   - Pump numbers

5. **Pharmacy Receipts**
   - Prescription information
   - Insurance details
   - Medical codes

## Integration Details

### Automatic Detection

The system automatically detects receipts by:
1. Running OCR on the document
2. Analyzing text patterns and structure
3. Checking for receipt-specific keywords
4. Applying receipt processing if detected

### Processing Pipeline

```
Document Upload
    ↓
OCR (PaddleOCR-VL)
    ↓
Receipt Detection
    ↓
Receipt Processing (if detected)
    ├─ Extract merchant info
    ├─ Extract transaction details
    ├─ Parse line items
    ├─ Extract totals
    ├─ Extract payment info
    └─ Validate data
    ↓
Standard Processing (if not receipt)
    └─ Invoice processing
    ↓
Combined Output
```

### Configuration

Receipt processing can be configured in `app/config/receipt_config.yaml`:

```yaml
processing:
  detect_receipt_type: true
  validate_arithmetic: true
  extract_line_items: true
  extract_payment_info: true
  min_confidence: 0.7
```

Or via environment variables:

```bash
export RECEIPT_PROCESSING_ENABLED=true
export RECEIPT_MIN_CONFIDENCE=0.7
```

## Fine-tuning for Receipts

### Dataset Format

The generator creates instruction-response pairs:

```json
{
  "instruction": "<image>\nExtract all line items from the receipt.",
  "response": "[{\"description\": \"Item\", \"quantity\": 2, \"unit_price\": 10.99, \"total\": 21.98}]"
}
```

### Training

```bash
python -m finscribe.receipts.finetune \
    --dataset_path ./receipt_dataset \
    --output_dir ./fine_tuned_receipt_model \
    --epochs 5 \
    --batch_size 4 \
    --learning_rate 2e-4
```

### Using Fine-tuned Model

Update your configuration to use the fine-tuned model:

```yaml
paddleocr_vl:
  model_path: "./fine_tuned_receipt_model"
```

## Validation

The receipt processor validates:

1. **Arithmetic Consistency**
   - Subtotal matches sum of line items
   - Total matches subtotal + tax - discount

2. **Data Completeness**
   - Merchant name present
   - Transaction date present
   - At least one line item found

3. **Payment Validation**
   - Payment method detected
   - Change calculation verified

## Examples

### Python Example

```python
from app.core.document_processor import processor

# Process a receipt
with open("receipt.jpg", "rb") as f:
    file_content = f.read()

result = await processor.process_document(file_content, "receipt.jpg")

if result.get("metadata", {}).get("document_type") == "receipt":
    receipt = result["receipt_data"]
    print(f"Merchant: {receipt['data']['merchant_info']['name']}")
    print(f"Total: ${receipt['data']['totals']['total']:.2f}")
    print(f"Items: {len(receipt['data']['items'])}")
```

### API Example

```bash
# Upload receipt
curl -X POST "http://localhost:8000/api/v1/analyze" \
  -F "files=@receipt.jpg" \
  -F "mode=sync" \
  | jq '.metadata.document_type'

# Response: "receipt"
```

## Troubleshooting

### Receipt Not Detected

If a receipt is not being detected:
1. Check OCR quality - ensure text is readable
2. Verify receipt has typical receipt structure
3. Check logs for detection attempts

### Low Accuracy

To improve accuracy:
1. Fine-tune on your specific receipt types
2. Generate more synthetic data
3. Adjust confidence thresholds in config

### Validation Errors

If validation fails:
1. Check arithmetic calculations manually
2. Verify OCR extracted correct numbers
3. Review validation warnings in response

## Best Practices

1. **Generate Diverse Training Data**
   - Include all receipt types
   - Vary layouts and formats
   - Include different quality levels

2. **Fine-tune for Your Use Case**
   - Use receipts similar to your target domain
   - Include edge cases
   - Validate on real receipts

3. **Monitor Performance**
   - Track detection accuracy
   - Monitor validation errors
   - Collect feedback for active learning

## Next Steps

1. Generate synthetic receipt dataset
2. Fine-tune PaddleOCR-VL on your data
3. Test with real receipts
4. Iterate based on results

For more details, see:
- `finscribe/receipts/README.md` - Module documentation
- `examples/receipt_generation_example.py` - Generation example
- `app/config/receipt_config.yaml` - Configuration options


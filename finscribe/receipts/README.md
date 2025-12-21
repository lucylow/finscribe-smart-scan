# Receipt Processing Module

This module provides receipt-specific processing capabilities for FinScribe Smart Scan, extending the system to handle receipts using PaddleOCR-VL.

## Features

- **Synthetic Receipt Generation**: Generate diverse, realistic receipt images for training
- **Receipt Processing**: Extract structured data from receipt images
- **Receipt Type Detection**: Automatically classify receipts (grocery, restaurant, retail, gas, pharmacy)
- **Data Validation**: Validate receipt data consistency and arithmetic
- **Fine-tuning Support**: Prepare datasets and fine-tune PaddleOCR-VL for receipt understanding

## Module Structure

```
finscribe/receipts/
├── __init__.py          # Module exports
├── generator.py         # Synthetic receipt generation
├── processor.py         # Receipt data extraction and processing
├── finetune.py          # Fine-tuning script for receipts
└── README.md           # This file
```

## Quick Start

### 1. Generate Synthetic Receipt Dataset

```python
from finscribe.receipts import SyntheticReceiptGenerator

# Initialize generator
generator = SyntheticReceiptGenerator()

# Generate 1000 receipts
dataset = generator.generate_dataset(
    num_receipts=1000,
    output_dir="./receipt_dataset"
)
```

### 2. Process a Receipt

The receipt processor is automatically integrated into the document processor. When you upload a receipt, it will be automatically detected and processed:

```python
from app.core.document_processor import processor

# Process a receipt (same API as invoices)
result = await processor.process_document(file_content, "receipt.jpg")

# Check if it's a receipt
if result.get("metadata", {}).get("document_type") == "receipt":
    receipt_data = result.get("receipt_data")
    print(f"Receipt type: {receipt_data.get('receipt_type')}")
    print(f"Merchant: {receipt_data['data']['merchant_info']['name']}")
    print(f"Total: ${receipt_data['data']['totals']['total']}")
```

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

### Generated Receipt Metadata

```json
{
  "receipt_id": "REC-20250115-1234",
  "merchant_name": "Walmart",
  "merchant_address": "123 Main St",
  "merchant_phone": "(555) 123-4567",
  "transaction_date": "01/15/2025",
  "transaction_time": "02:30 PM",
  "cashier_id": "C5",
  "register_id": "R12",
  "items": [
    {
      "description": "Organic Apples",
      "quantity": 2,
      "unit_price": 2.99,
      "discount": 0.0,
      "total": 5.98
    }
  ],
  "subtotal": 25.50,
  "tax_rate": 0.08,
  "tax_amount": 2.04,
  "discount_total": 0.0,
  "total_paid": 27.54,
  "payment_method": "VISA",
  "change_given": 0.0,
  "currency": "$",
  "receipt_type": "grocery"
}
```

### Processed Receipt Output

```json
{
  "success": true,
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
      "receipt_number": "1234",
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
}
```

## Configuration

Receipt processing can be configured via `app/config/receipt_config.yaml`:

```yaml
processing:
  detect_receipt_type: true
  validate_arithmetic: true
  extract_line_items: true
  extract_payment_info: true
  min_confidence: 0.7
```

## Integration with Document Processor

The receipt processor is automatically integrated into the main document processor. When processing a document:

1. OCR is performed using PaddleOCR-VL
2. The system attempts to detect if the document is a receipt
3. If detected as a receipt, receipt-specific processing is applied
4. If not a receipt, standard invoice processing continues

This allows the system to handle both invoices and receipts seamlessly.

## Supported Receipt Types

- **Grocery**: Supermarkets, grocery stores
- **Restaurant**: Restaurants, cafes, fast food
- **Retail**: General retail stores
- **Gas**: Gas stations, fuel receipts
- **Pharmacy**: Pharmacy receipts, prescriptions

## Fine-tuning for Receipts

The fine-tuning script prepares instruction-response pairs in the format expected by PaddleOCR-VL:

```json
{
  "instruction": "<image>\nExtract all line items from the receipt.",
  "response": "[{\"description\": \"Item 1\", \"quantity\": 2, \"unit_price\": 10.99, \"total\": 21.98}]"
}
```

This teaches the model to follow domain-specific commands for receipt understanding.

## Validation

The receipt processor includes validation checks:

- **Arithmetic Validation**: Verifies subtotals and totals match line items
- **Data Completeness**: Checks for missing critical information
- **Consistency Checks**: Validates payment method and change calculations

## Examples

See the `examples/` directory for:
- Receipt generation examples
- Processing examples
- Fine-tuning examples

## Dependencies

- `faker`: For generating realistic merchant data
- `Pillow`: For image generation
- `opencv-python`: For image processing
- `numpy`: For numerical operations
- `pyyaml`: For configuration management

## License

Part of the FinScribe Smart Scan project.



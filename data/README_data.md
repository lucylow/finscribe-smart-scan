# Dataset Documentation: FinScribe Training Data

This document describes the dataset format, structure, and preparation process for training the FinScribe financial document parser.

## Dataset Overview

The FinScribe training dataset consists of:

1. **Synthetic Financial Documents**: 5,000+ computer-generated invoices, receipts, and statements with perfect ground truth annotations
2. **Real Anonymized Samples**: 500+ real financial documents (anonymized) for validation and fine-tuning
3. **Active Learning Data**: User corrections from production deployments (continuously updated)

## Dataset Structure

```
data/
├── raw_samples/                    # Example input images (PDFs/PNGs)
│   ├── invoices/                   # Sample invoice images
│   ├── receipts/                   # Sample receipt images
│   └── statements/                 # Sample bank statement images
├── synthetic_generator.py          # Script for generating synthetic training data
├── unsloth_train.jsonl            # Training dataset (instruction-response pairs)
├── unsloth_val.jsonl              # Validation dataset
├── active_learning_seed.jsonl     # Seed data for active learning
├── active_learning.jsonl          # Production corrections (continuously updated)
└── dataset_info.json              # Dataset metadata and statistics
```

## Data Format

### Instruction-Response Pairs (JSONL Format)

Each line in the training dataset is a JSON object with the following structure:

```json
{
  "instruction": "Validate and return JSON only",
  "input": "OCR_TEXT:\nVendor: TechCorp Inc.\nInvoice #: INV-2024-001\nDate: 2024-03-15\nItems: Widget A 2x50.00 Total 100.00\nSubtotal: 100.00\nTax: 10.00\nTotal: 110.00",
  "output": "{\"document_type\":\"invoice\",\"vendor\":{\"name\":\"TechCorp Inc.\"},\"invoice_number\":\"INV-2024-001\",\"issue_date\":\"2024-03-15\",\"line_items\":[{\"description\":\"Widget A\",\"quantity\":2,\"unit_price\":50.0,\"line_total\":100.0}],\"financial_summary\":{\"subtotal\":100.0,\"tax_rate\":0.1,\"tax_amount\":10.0,\"grand_total\":110.0,\"currency\":\"USD\"}}"
}
```

**Fields Explained:**

- `instruction`: Task instruction for the model (typically "Validate and return JSON only" for invoice parsing)
- `input`: OCR-extracted text or image prompt (format varies based on model)
- `output`: Ground truth structured JSON matching the target schema

### Ground Truth Schema

The output JSON follows this canonical schema:

```json
{
  "document_type": "invoice" | "receipt" | "statement" | "purchase_order",
  "vendor": {
    "name": "string",
    "address": {
      "street": "string",
      "city": "string",
      "state": "string",
      "zip": "string",
      "country": "string"
    },
    "contact": {
      "phone": "string",
      "email": "string",
      "website": "string"
    },
    "tax_id": "string"
  },
  "client": {
    "name": "string",
    "address": { /* same structure as vendor.address */ },
    "contact": { /* same structure as vendor.contact */ }
  },
  "invoice_number": "string",
  "issue_date": "YYYY-MM-DD",
  "due_date": "YYYY-MM-DD",
  "po_number": "string",
  "payment_terms": "string",
  "line_items": [
    {
      "description": "string",
      "sku": "string",
      "quantity": 2.0,
      "unit_price": 50.0,
      "discount": 0.0,
      "tax_rate": 0.1,
      "line_total": 100.0,
      "bbox": [x, y, width, height]
    }
  ],
  "financial_summary": {
    "subtotal": 100.0,
    "discount": 0.0,
    "tax_rate": 0.1,
    "tax_amount": 10.0,
    "shipping": 0.0,
    "grand_total": 110.0,
    "currency": "USD"
  },
  "metadata": {
    "processing_date": "YYYY-MM-DDTHH:MM:SSZ",
    "model_version": "string",
    "confidence_score": 0.95
  }
}
```

## Synthetic Data Generation

### Overview

Synthetic data is generated using `ml/synthetic_invoice_generator/` tools to create diverse, realistic financial documents with perfect ground truth annotations.

### Generation Process

1. **Template Selection**: Randomly select from multiple invoice/receipt templates
2. **Data Filling**: Use `faker` library to generate realistic vendor names, addresses, item descriptions
3. **Layout Variation**: Apply different layouts (single-column, multi-column, tabular)
4. **Rendering**: Use `reportlab` or similar to generate PDF/image with annotations
5. **Annotation Export**: Export ground truth JSON with bounding boxes

### Key Variations

- **Layouts**: 10+ different invoice templates (modern, classic, minimal, detailed)
- **Fonts**: Multiple font families and sizes to simulate real-world variation
- **Languages**: Primarily English, with some multi-language samples
- **Vendors**: 100+ synthetic vendor profiles with realistic addresses and contact info
- **Item Types**: Diverse product/service descriptions (tech, retail, services, manufacturing)
- **Numeric Variations**: Different currency formats, decimal precision, number formatting

### Running the Generator

```bash
# Generate 1000 synthetic invoices
python ml/synthetic_invoice_generator/src/data_generator.py \
  --output-dir data/synthetic \
  --count 1000 \
  --template-set all \
  --format jsonl

# Generate with augmentation (skew, noise, blur)
python ml/synthetic_invoice_generator/src/data_generator.py \
  --output-dir data/synthetic \
  --count 500 \
  --augment true \
  --augmentation-intensity medium
```

## Real Data Preparation

### Anonymization Process

Real financial documents are anonymized before inclusion in training data:

1. **PII Removal**: Replace real names, addresses, phone numbers with synthetic equivalents
2. **Invoice Number Masking**: Replace invoice numbers with pattern-preserving placeholders
3. **Amount Normalization**: Scale amounts to random values (preserving relative relationships)
4. **Date Shifting**: Shift dates by random offset (preserving relative timing)

### Annotation Guidelines

For real documents, annotations are created manually following these guidelines:

1. **Completeness**: All visible fields must be annotated
2. **Accuracy**: Values must match exactly what appears in the document
3. **Confidence**: Mark uncertain fields with confidence scores
4. **Bounding Boxes**: Include pixel coordinates for each field (for visual validation)
5. **Validation Flags**: Mark documents with known inconsistencies (e.g., arithmetic errors in source document)

## Active Learning Data

### Purpose

Active learning data captures user corrections from production deployments, enabling continuous model improvement.

### Collection Process

1. **Low-Confidence Flagging**: Documents with low-confidence extractions are flagged for review
2. **User Corrections**: Users correct extracted fields via web interface
3. **Correction Export**: Corrections are exported to `active_learning.jsonl` format
4. **Retraining**: Periodically retrain model with accumulated corrections

### Format

```json
{
  "job_id": "job_abc123",
  "ocr_payload": { /* original OCR output */ },
  "vlm_response": { /* original model prediction */ },
  "user_correction": {
    "invoice_number": "INV-2024-001",
    "line_items": [
      { "description": "Corrected Item Name", "quantity": 2, ... }
    ]
  },
  "created_at": "2024-03-15T10:30:00Z",
  "correction_reason": "OCR misread character"
}
```

## Dataset Statistics

### Current Dataset Size

- **Training Examples**: 5,200+ instruction-response pairs
- **Validation Examples**: 500+ pairs
- **Test Examples**: 500+ pairs (separate from validation)
- **Active Learning Examples**: Continuously growing (currently ~200 corrections)

### Distribution

- **Document Types**: 60% invoices, 25% receipts, 10% statements, 5% purchase orders
- **Source**: 90% synthetic, 10% real (anonymized)
- **Quality**: High-quality scans (60%), phone photos (30%), low-quality scans (10%)

## Data Augmentation

During training, the following augmentations are applied to improve robustness:

1. **Geometric Transformations**:
   - Rotation: ±5 degrees
   - Scaling: 0.9x to 1.1x
   - Translation: ±10 pixels

2. **Image Quality Variations**:
   - Gaussian noise: σ = 0.01 to 0.05
   - Gaussian blur: kernel size 3-5
   - Contrast adjustment: 0.8x to 1.2x
   - Brightness adjustment: 0.8x to 1.2x

3. **Document-Specific Augmentations**:
   - Skew simulation (rotated scans)
   - Compression artifacts (JPEG quality 60-90)
   - Resolution variations (150-300 DPI)

**Note**: Augmentations are applied on-the-fly during training, not pre-computed.

## Data Validation

### Quality Checks

Before inclusion in training data, each example is validated:

1. **Schema Validation**: JSON output matches canonical schema
2. **Type Checking**: Numeric fields are numbers, dates are valid ISO format
3. **Arithmetic Consistency**: Line totals = quantity × unit_price, grand_total = subtotal + tax
4. **Completeness**: Required fields are present (vendor name, invoice number, etc.)
5. **Confidence Scores**: All fields have associated confidence scores

### Validation Script

```bash
# Validate training dataset
python finscribe/data/validate_dataset.py \
  --input data/unsloth_train.jsonl \
  --schema data/schema.json \
  --output data/validation_report.json
```

## Dataset Usage

### Training

```bash
# Use dataset for fine-tuning
python phase2_finetuning/train_finetune_enhanced.py \
  --config phase2_finetuning/finetune_config.yaml \
  --train-file data/unsloth_train.jsonl \
  --val-file data/unsloth_val.jsonl
```

### Evaluation

```bash
# Evaluate on test set
python ml/examples/evaluate_model.py \
  --test-dir data/test_dataset \
  --model-path ./finetuned_model \
  --output evaluation/results.json
```

## Privacy and Licensing

### Privacy Considerations

- **Real Documents**: All real documents are anonymized (PII removed)
- **Synthetic Data**: Safe to share publicly (no real business information)
- **Active Learning**: User corrections are anonymized before inclusion

### Licensing

- **Synthetic Data**: MIT License (freely shareable)
- **Real Data**: Proprietary (for internal use only, cannot be shared)
- **Annotations**: MIT License (annotation format and schema are open)

## Contributing Data

To contribute additional training data:

1. **Synthetic Data**: Use the generator scripts in `ml/synthetic_invoice_generator/`
2. **Real Data**: Follow anonymization guidelines, submit via pull request
3. **Corrections**: Active learning corrections are automatically collected (with user consent)

## Future Improvements

1. **Dataset Expansion**: Target 10,000+ training examples
2. **Multi-Language**: Add Spanish, French, German, Chinese samples
3. **Document Diversity**: More purchase orders, bank statements, tax documents
4. **Edge Cases**: Add more challenging examples (handwritten, poor quality, unusual layouts)
5. **Domain-Specific**: Industry-specific invoices (construction, healthcare, legal services)


# Semantic Understanding Training Guide

This guide explains how to train PaddleOCR-VL to understand semantic structure and logic in financial documents—not just extract text.

## Overview

Instead of training the model to simply extract text, we use **instruction fine-tuning** to teach it to:
- Understand document structure
- Extract specific fields on demand
- Parse complete documents into structured JSON
- Reconstruct tables in various formats
- Perform logical reasoning (arithmetic validation)
- Summarize complex documents

## Key Concepts

### Instruction Fine-Tuning

Each training example consists of:
- **Input (Prompt)**: An image + a specific instruction/question
- **Target Output (Completion)**: A structured response (JSON, CSV, or text)

The model learns to complete the task described in the instruction, not just extract raw text.

### Completion-Only Training

During training, we mask the prompt tokens (set them to -100) so the loss is calculated **only on the assistant's response**. This prevents the model from "forgetting" how to follow instructions.

## Quick Start

### Step 1: Generate Synthetic Invoices

First, generate synthetic invoice data with ground truth:

```bash
cd synthetic_invoice_generator
python generate_dataset.py
```

This creates:
- Invoice images in `output/images/`
- Ground truth JSON files in `output/ground_truth/`
- Training manifest in `output/training_manifest.json`

### Step 2: Create Semantic Instruction Pairs

Generate diverse instruction-completion pairs from your synthetic data:

```bash
cd phase2_finetuning
python create_semantic_instruction_pairs.py \
    --manifest ../synthetic_invoice_generator/output/training_manifest.json \
    --output semantic_instruction_pairs.jsonl
```

This creates a JSONL file with multiple instruction types per invoice.

### Step 3: Train the Model

Fine-tune PaddleOCR-VL with your semantic instruction pairs:

```bash
python train_finetune_enhanced.py \
    --config finetune_config.yaml \
    --dataset semantic_instruction_pairs.jsonl
```

## Instruction Types

The generator creates 5 types of instruction pairs:

### 1. Field Extraction

**Purpose**: Extract specific key fields on demand

**Example Prompt**: `"Extract the 'Vendor Name' and 'Invoice Total' from this document."`

**Example Output**:
```json
{
  "field": "Vendor Name",
  "value": "ABC Corporation"
}
```

**Use Case**: When you need only specific information, not the entire document.

### 2. Full JSON Parsing

**Purpose**: Parse entire document into structured JSON

**Example Prompt**: `"Parse this entire invoice into a JSON object with keys for vendor, date, line_items, and totals."`

**Example Output**:
```json
{
  "document_type": "invoice",
  "invoice_number": "INV-12345",
  "vendor": {
    "name": "ABC Corp",
    "address": "..."
  },
  "line_items": [...],
  "totals": {
    "subtotal": 130.00,
    "grand_total": 143.00
  }
}
```

**Use Case**: Complete document parsing for downstream processing.

### 3. Table Reconstruction

**Purpose**: Convert tables to structured formats (CSV/JSON)

**Example Prompt**: `"Convert this financial table to CSV format, preserving all headers and row data."`

**Example Output (CSV)**:
```csv
Description,Quantity,Unit Price,Line Total
"Widget A",2,50.00,100.00
"Widget B",1,30.00,30.00
```

**Example Output (JSON)**:
```json
[
  {
    "description": "Widget A",
    "quantity": 2,
    "unit_price": 50.00,
    "line_total": 100.00
  }
]
```

**Use Case**: Extracting tabular data for analysis or import into spreadsheets.

### 4. Logical Reasoning

**Purpose**: Verify arithmetic and validate consistency

**Example Prompt**: `"Verify the arithmetic on this invoice. Check if subtotal + tax equals total."`

**Example Output**:
```json
{
  "subtotal_correct": true,
  "tax_correct": true,
  "total_correct": false,
  "calculated_total": 145.00,
  "ground_truth_total": 143.00,
  "line_items_valid": true
}
```

**Use Case**: Quality assurance and fraud detection.

### 5. Summarization

**Purpose**: Provide concise summaries of complex data

**Example Prompt**: `"Summarize this invoice by listing the vendor name, invoice total, and number of line items."`

**Example Output**:
```json
{
  "vendor": "ABC Corporation",
  "invoice_number": "INV-12345",
  "total_amount": "$143.00",
  "number_of_items": 2,
  "payment_terms": "Net 30"
}
```

**Use Case**: Quick document overviews and reporting.

## Advanced Usage

### Generate Specific Instruction Types

Only generate certain instruction types:

```bash
python create_semantic_instruction_pairs.py \
    --manifest training_manifest.json \
    --output semantic_data.jsonl \
    --include-types field_extraction full_json_parsing
```

### Limit Samples Per Invoice

For large datasets, randomly sample pairs per invoice:

```bash
python create_semantic_instruction_pairs.py \
    --manifest training_manifest.json \
    --output semantic_data.jsonl \
    --samples-per-invoice 5
```

### Process Directory Instead of Manifest

If you have separate directories:

```bash
python create_semantic_instruction_pairs.py \
    --ground-truth-dir ../synthetic_invoice_generator/output/ground_truth \
    --images-dir ../synthetic_invoice_generator/output/images \
    --output semantic_data.jsonl
```

## Training Configuration

Edit `finetune_config.yaml` to adjust training parameters:

```yaml
training:
  learning_rate: 2.0e-5      # Critical: start conservative
  per_device_train_batch_size: 8
  num_train_epochs: 5
  max_sequence_length: 2048   # Must fit your longest JSON output
```

### Key Parameters

- **Learning Rate**: Most critical. Start at 2e-5, adjust based on loss stability.
- **Batch Size**: Increase as GPU memory allows (4, 8, 16).
- **Max Sequence Length**: Must accommodate full JSON output (2048+ recommended).

## Data Format

Each line in the JSONL file follows this structure:

```json
{
  "image": "path/to/invoice_image.png",
  "conversations": [
    {
      "role": "human",
      "content": "<image>\nExtract the 'Vendor Name' from this document."
    },
    {
      "role": "assistant",
      "content": "{\"field\": \"Vendor Name\", \"value\": \"ABC Corporation\"}"
    }
  ],
  "instruction_type": "field_extraction",
  "field_name": "Vendor Name"
}
```

## Completion-Only Training

The training script automatically masks prompt tokens so the model only learns from the assistant's response. This is handled by the `CompletionOnlyTrainer` class which:

1. Identifies where the assistant response starts (using tokenizer special tokens)
2. Masks all tokens before that point (sets to -100)
3. Calculates loss only on the response tokens

## Evaluation

After training, evaluate your model on:

1. **Field Extraction Accuracy**: Can it extract specific fields correctly?
2. **JSON Parsing Completeness**: Does it capture all required fields?
3. **Table Structure Accuracy**: Are tables reconstructed correctly?
4. **Arithmetic Validation**: Can it verify calculations?
5. **Summarization Quality**: Are summaries accurate and concise?

## Best Practices

1. **Start Simple**: Begin with field extraction before moving to full JSON parsing.
2. **Consistency**: Use clear, consistent naming for JSON keys (e.g., always `"invoice_number"`, not sometimes `"inv_no"`).
3. **Quality Over Quantity**: 1,000 perfectly aligned pairs are better than 10,000 messy ones.
4. **Diverse Prompts**: Use multiple prompt templates per instruction type for better generalization.
5. **Monitor Loss**: Watch for loss spikes or NaN values—reduce learning rate if needed.

## Troubleshooting

### Model outputs incomplete JSON

- Increase `max_sequence_length` in config
- Check that your longest expected output fits within the limit

### Training loss is unstable

- Reduce learning rate (try 1e-5)
- Increase batch size or gradient accumulation steps
- Add more warmup steps

### Model doesn't follow instructions

- Ensure completion-only training is working (check that prompt tokens are masked)
- Verify your instruction pairs have clear, consistent formats
- Add more diverse prompt templates

### Out of memory errors

- Reduce batch size
- Enable gradient checkpointing
- Use quantization (4-bit or 8-bit)
- Reduce image resolution

## Next Steps

1. Generate diverse synthetic invoices covering your use cases
2. Create semantic instruction pairs with all 5 types
3. Train with conservative hyperparameters
4. Evaluate on held-out test set
5. Iterate: adjust prompts, add more data, tune hyperparameters

## References

- [PaddleOCR-VL Documentation](https://github.com/PaddlePaddle/PaddleOCR)
- [Instruction Fine-Tuning Best Practices](https://huggingface.co/docs/transformers/training)
- [LoRA Fine-Tuning Guide](https://huggingface.co/docs/peft/conceptual_guides/lora)


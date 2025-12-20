# FinScribe Unsloth Demo Dataset

This folder contains a minimal, runnable dataset for the FinScribe + Unsloth demo.

## Files

- `unsloth_train.jsonl` — Supervised fine-tuning dataset (10 examples)
- `unsloth_val.jsonl` — Validation dataset (2 examples)
- `active_learning_seed.jsonl` — Seed data for human-in-the-loop corrections

## Format

Each record contains:
- `prompt`: OCR-extracted text (instruction input)
- `completion`: Structured JSON ground truth (target output)

Example:
```json
{
  "prompt": "OCR_TEXT:\nVendor: TechCorp Inc.\nInvoice #: INV-2024-001\n...",
  "completion": "{\"document_type\":\"invoice\",\"vendor\":{\"name\":\"TechCorp Inc.\"},...}"
}
```

## Usage

1. **Fine-tune Unsloth model:**
   ```bash
   ./scripts/train_unsloth.sh
   ```

2. **Use in Streamlit UI:**
   - Upload documents
   - Correct parsed JSON outputs
   - Save corrections to `active_learning.jsonl`

3. **Retrain with corrections:**
   - Merge `active_learning.jsonl` into training dataset
   - Run training script again to improve model

## Notes

- This dataset is synthetic and safe for demos and hackathons
- For production, you'll want 100+ high-quality examples
- The active learning seed contains intentionally noisy OCR to simulate real-world scenarios


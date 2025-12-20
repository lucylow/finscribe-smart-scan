# FinScribe-VL-Financial-INT8

## Model Description

FinScribe-VL is a fine-tuned version of PaddleOCR-VL-0.9B specialized for structured extraction of financial documents (invoices, statements, receipts). The model has been optimized through Supervised Fine-Tuning (SFT) with completion-only loss masking and is quantized to INT8 for efficient deployment.

## Architecture

- **Base Model**: PaddleOCR-VL-0.9B
- **Fine-tuning Method**: Supervised Fine-Tuning (SFT) with LoRA
- **Quantization**: INT8 (ONNX Runtime)
- **Attention**: Flash Attention 2 (training), default (inference)

## Training Data

- **8,000 synthetic invoices** generated with perfect arithmetic
- **1,200 anonymized real invoices** from financial document corpus
- **5 semantic regions per document**:
  - Vendor block
  - Client/invoice info
  - Line items table
  - Tax section
  - Totals section

## Training Configuration

- **Epochs**: 4
- **Batch Size**: 4 per device (effective: 16 with gradient accumulation)
- **Learning Rate**: 2e-5
- **Optimizer**: AdamW
- **Mixed Precision**: bfloat16
- **LoRA Rank**: 16

## Intended Use

- Invoice parsing and data extraction
- Accounting automation
- Expense analysis and categorization
- Financial document digitization

## Performance

### Quantitative Metrics

| Metric | Base PaddleOCR-VL | FinScribe-VL | FinScribe-VL-INT8 |
|--------|-------------------|--------------|-------------------|
| Field Accuracy | 76.8% | 94.2% | 93.6% |
| Table TEDS | 68.2 | 91.7 | 90.9 |
| Numeric Accuracy | 82.1% | 97.3% | 96.8% |
| Validation Pass Rate | 54.7% | 96.8% | 95.9% |
| Latency (ms/page) | 310 | 340 | 128 |
| VRAM (GB) | 7.2 | 7.6 | 2.9 |

### Key Improvements

- **+17.4%** field extraction accuracy
- **+23.5** TEDS score improvement
- **+15.2%** numeric accuracy
- **+42.1%** validation pass rate
- **2.6x** faster inference with INT8 quantization
- **60%** VRAM reduction with quantization

## Limitations

- Not certified for legal or tax compliance
- Performance degrades on handwritten documents
- Requires high-quality input images (minimum 300 DPI recommended)
- May struggle with non-standard invoice formats
- Currency support limited to training data currencies

## Ethical Considerations

- Model trained on synthetic and anonymized data
- No PII (Personally Identifiable Information) in training data
- Users should validate extracted data for critical financial operations

## Citation

If you use this model, please cite:

```bibtex
@software{finscribe_vl,
  title={FinScribe-VL: Fine-tuned PaddleOCR-VL for Financial Document Intelligence},
  author={FinScribe Team},
  year={2025},
  url={https://github.com/finscribe/paddleocr-vl-finetune}
}
```

## License

MIT License

## Contact

For questions, issues, or contributions, please open an issue on the project repository.


# Synthetic Invoice Dataset Generator

A comprehensive system for generating synthetic invoice datasets with realistic variations for training PaddleOCR-VL and other document understanding models.

## Features

- **Multiple Layout Templates**: Classic, modern, compact, multi-column, receipt-style, and multi-page layouts
- **Multi-language Support**: Generate invoices in multiple languages (English, German, French, Spanish, Japanese, Chinese)
- **Currency Variations**: Support for USD, EUR, GBP, JPY, CNY
- **Complexity Levels**: Simple (1-5 items), medium (6-15 items), complex (16-30 items, multi-page)
- **Realistic Augmentation**: Image augmentation to simulate scanned documents with rotation, blur, noise, folds, and other artifacts
- **Ground Truth Generation**: Complete JSON annotations for training
- **Scalable Generation**: Batch processing for thousands of invoices

## Installation

1. Install dependencies:

```bash
cd synthetic_invoice_generator
pip install -r requirements.txt
```

Note: Some optional dependencies (like `imgaug`) provide enhanced augmentation features but the system will work with basic augmentations if they're not available.

## Configuration

Edit `config/config.yaml` to customize:

- Number of invoices to generate
- Batch size for processing
- Layout types to use
- Languages and currencies
- Complexity levels
- Augmentation settings

## Usage

### Generate Full Dataset

```bash
python generate_dataset.py
```

This will:
1. Generate synthetic invoices as PDFs
2. Convert PDFs to images
3. Apply augmentations (if enabled)
4. Create training manifest with ground truth

### Output Structure

```
output/
├── pdfs/              # Generated PDF invoices
├── images/            # Converted PNG images (one per page)
├── ground_truth/      # JSON metadata for each invoice
├── augmented/         # Augmented image variants
├── metadata/          # Batch metadata files
├── training_manifest.json  # Complete training manifest
└── dataset_summary.json    # Dataset statistics
```

### Ground Truth Format

Each invoice has a corresponding JSON file with complete metadata:

```json
{
  "invoice_id": "INV-2024-000001",
  "issue_date": "2024-01-15",
  "due_date": "2024-02-14",
  "currency": "USD",
  "language": "en_US",
  "layout_type": "classic_left",
  "vendor": {
    "name": "Tech Solutions LLC",
    "address": "123 Main St",
    ...
  },
  "client": {...},
  "items": [...],
  "subtotal": 8500.00,
  "tax_total": 1615.00,
  "grand_total": 10115.00,
  ...
}
```

## Training Manifest

The `training_manifest.json` file contains all training pairs:

```json
[
  {
    "invoice_id": "INV-2024-000001",
    "pdf_path": "./output/pdfs/INV-2024-000001.pdf",
    "image_path": "./output/images/INV-2024-000001/INV-2024-000001_page_1.png",
    "ground_truth_path": "./output/ground_truth/INV-2024-000001.json",
    "page_num": 1,
    "is_augmented": false
  },
  ...
]
```

## Customization

### Adding New Layouts

1. Add layout name to `config/config.yaml` under `variations.layouts`
2. Implement layout method in `SyntheticInvoiceGenerator` class:
   ```python
   def _create_your_layout(self, invoice_data: InvoiceMetadata, filename: str):
       # Your layout implementation
   ```
3. Add case to `generate_single_invoice` method

### Adding Languages

1. Add locale to `config/config.yaml` under `variations.languages`
2. Ensure Faker supports the locale (install language packs if needed)
3. Optionally add custom fonts in `config/fonts/` for better rendering

### Custom Augmentations

Modify `src/augmentation.py` to add custom augmentation effects:

```python
def your_custom_augmentation(self, image: np.ndarray) -> np.ndarray:
    # Your augmentation logic
    return augmented_image
```

## Integration with PaddleOCR-VL

The generated dataset can be directly used for PaddleOCR-VL fine-tuning:

1. Use `training_manifest.json` to iterate over training samples
2. Load images from `image_path`
3. Load ground truth from `ground_truth_path`
4. Format according to PaddleOCR-VL training requirements

Example conversion:

```python
from src.utils import PDFProcessor

# Load training manifest
with open('output/training_manifest.json') as f:
    manifest = json.load(f)

# Convert to PaddleOCR-VL format
for pair in manifest:
    with open(pair['ground_truth_path']) as f:
        metadata = json.load(f)
    
    gt = PDFProcessor.create_paddleocr_vl_ground_truth(
        metadata,
        pair['image_path']
    )
    # Use gt for training
```

## Performance

- Generation speed: ~10-20 invoices/second (depending on complexity)
- Average PDF size: 50-200 KB
- Image size: ~2-5 MB per page (200 DPI PNG)
- Recommended: Use batch processing for large datasets (5000+ invoices)

## Troubleshooting

### Font Issues

If you see font warnings, you can:
- Install system fonts or add custom fonts to `config/fonts/`
- The system will fall back to default fonts automatically

### Memory Issues

For large datasets:
- Reduce batch size in config
- Process in smaller chunks
- Clear intermediate files periodically

### Missing Dependencies

Install optional dependencies for full features:
```bash
pip install imgaug  # Enhanced augmentation
```

## License

Part of the FinScribe AI project.


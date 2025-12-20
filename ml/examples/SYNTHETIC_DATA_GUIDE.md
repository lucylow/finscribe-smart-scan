# Synthetic Invoice Data Generation Guide

This guide demonstrates how to generate high-quality synthetic training data for PaddleOCR-VL and other document understanding models using Python.

## 🎯 Why Synthetic Data?

- **No Copyright Issues**: Completely generated data avoids legal concerns
- **Unlimited Scale**: Generate thousands of variations quickly
- **Controlled Diversity**: Systematically vary layouts, fonts, and content
- **Ground Truth Included**: Perfect annotations for training

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd examples
pip install -r requirements_synthetic_data.txt
```

### 2. Generate Your First Batch

```bash
# Generate 100 invoices (default)
python synthetic_invoice_generator_example.py

# Generate 500 invoices with custom output
python synthetic_invoice_generator_example.py --count 500 --output ./my_dataset

# Generate with only classic layout
python synthetic_invoice_generator_example.py --count 50 --layouts classic
```

### 3. Check Output

```
synthetic_invoices/
├── pdfs/                    # Generated PDF invoices
│   ├── INV-2024-00001.pdf
│   ├── INV-2024-00002.pdf
│   └── ...
├── annotations/             # Ground truth JSON files
│   ├── INV-2024-00001.json
│   ├── INV-2024-00002.json
│   └── ...
├── training_manifest.json   # Complete training manifest
└── dataset_summary.json     # Dataset statistics
```

## 📋 Workflow Overview

The script follows the recommended workflow:

1. **Generate Structured Data** → Uses `Faker` to create realistic invoice content
2. **Design Visual Layouts** → Uses `ReportLab` to create different PDF layouts
3. **Render to PDF** → Outputs high-fidelity PDF documents
4. **Create Annotations** → Generates JSON ground truth files

## 🛠️ How It Works

### Data Generation (Faker)

The `InvoiceDataGenerator` class uses Faker to create:
- Company names and addresses
- Invoice IDs, dates, and metadata
- Product descriptions and line items
- Realistic pricing and tax calculations
- Multiple currencies (USD, EUR, GBP, JPY, CNY)

### PDF Generation (ReportLab)

The `InvoicePDFGenerator` class creates two layout styles:

1. **Classic Layout**: Traditional invoice with vendor/client side-by-side
2. **Modern Layout**: Compact, streamlined design

Both layouts include:
- Professional styling
- Complete line item tables
- Tax calculations
- Totals section

### Ground Truth Format

Each invoice has a corresponding JSON annotation:

```json
{
  "invoice_id": "INV-2024-00001",
  "pdf_path": "pdfs/INV-2024-00001.pdf",
  "layout_type": "classic",
  "metadata": {
    "issue_date": "2024-01-15",
    "due_date": "2024-02-14",
    "currency": "USD",
    "vendor": {
      "name": "Tech Solutions LLC",
      "address": "123 Main St, City, State 12345",
      "email": "contact@techsolutions.com",
      "phone": "+1-555-0123"
    },
    "client": {
      "name": "Acme Corporation",
      "address": "456 Oak Ave, City, State 67890",
      "email": "billing@acme.com"
    },
    "items": [
      {
        "description": "Software License: Enterprise Package",
        "quantity": 5,
        "unit_price": 1200.00,
        "tax_rate": 10.0,
        "subtotal": 6000.00,
        "tax_amount": 600.00,
        "total": 6600.00
      }
    ],
    "subtotal": 6000.00,
    "tax_total": 600.00,
    "grand_total": 6600.00
  }
}
```

## 📊 Training Manifest

The `training_manifest.json` file provides a complete index:

```json
[
  {
    "invoice_id": "INV-2024-00001",
    "pdf_path": "pdfs/INV-2024-00001.pdf",
    "annotation_path": "annotations/INV-2024-00001.json",
    "layout": "classic",
    "currency": "USD",
    "total": 6600.00
  }
]
```

## 🔧 Customization

### Adding New Layouts

1. Add a new method to `InvoicePDFGenerator`:
```python
def generate_custom_layout(self, invoice: InvoiceData, output_path: Path):
    # Your custom layout implementation
    pass
```

2. Add the layout name to the `generate()` method
3. Include it in the `--layouts` argument

### Changing Data Generation

Modify `InvoiceDataGenerator` to:
- Add new product categories
- Change pricing ranges
- Add custom fields
- Support additional locales

### Multi-language Support

Faker supports many locales. Generate invoices in different languages:

```bash
# German invoices
python synthetic_invoice_generator_example.py --locale de_DE

# French invoices
python synthetic_invoice_generator_example.py --locale fr_FR

# Japanese invoices
python synthetic_invoice_generator_example.py --locale ja_JP
```

## 📈 Scaling Up

### Generate Large Datasets

For thousands of invoices, process in batches:

```python
# Generate 10,000 invoices in batches
for batch in range(10):
    start = batch * 1000
    output = f"./dataset_batch_{batch}"
    generate_synthetic_invoices(
        count=1000,
        output_dir=Path(output),
        layouts=['classic', 'modern']
    )
```

### Performance Tips

- **Batch Processing**: Process invoices in chunks to manage memory
- **Parallel Generation**: Use multiprocessing for faster generation
- **Selective Augmentation**: Only augment a subset for training diversity

## 🔗 Integration with PaddleOCR-VL

### Convert to Training Format

Use the training manifest to convert to PaddleOCR-VL format:

```python
import json
from pathlib import Path

# Load manifest
with open('training_manifest.json') as f:
    manifest = json.load(f)

# Convert each sample
for sample in manifest:
    # Load annotation
    with open(sample['annotation_path']) as f:
        annotation = json.load(f)
    
    # Format for PaddleOCR-VL
    # (Format depends on your specific training pipeline)
    training_sample = {
        'image': sample['pdf_path'],
        'ground_truth': annotation['metadata']
    }
    # Add to training dataset
```

### Using PP-StructureV3 for Validation

You can use PaddleOCR's PP-StructureV3 to:
1. Parse your generated PDFs
2. Cross-check annotations
3. Generate additional layout information

## 🎨 Extending to Other Documents

The same principles apply to other financial documents:

### Income Statements
- Generate revenue, expenses, and profit data
- Create standard financial statement layouts
- Include multiple periods for comparison

### Balance Sheets
- Generate assets, liabilities, equity
- Create multi-section layouts
- Include notes and disclosures

### Receipts
- Simpler structure (fewer line items)
- Compact layouts
- Multiple vendor styles

## 📚 Key Takeaways

1. **Start Simple**: Begin with 100-500 invoices to test your pipeline
2. **Introduce Variance**: Systematically vary layouts, fonts, and content
3. **Validate Quality**: Check that generated data matches real-world patterns
4. **Scale Gradually**: Increase dataset size as you validate the approach
5. **Document Everything**: Keep track of generation parameters for reproducibility

## 🔍 Next Steps

1. **Generate Initial Dataset**: Start with 1000 invoices
2. **Validate Format**: Ensure annotations match your training pipeline
3. **Add Augmentation**: Apply image transformations (rotation, noise, etc.)
4. **Test Training**: Use a small subset to test your training pipeline
5. **Scale Up**: Generate larger datasets as needed

## 📖 Additional Resources

- [Faker Documentation](https://faker.readthedocs.io/)
- [ReportLab User Guide](https://www.reportlab.com/docs/reportlab-userguide.pdf)
- [PaddleOCR-VL Documentation](https://github.com/PaddlePaddle/PaddleOCR)

## 💡 Tips for Hackathon Projects

- **Focus on Quality**: 1000 well-designed invoices > 10,000 poor ones
- **Document Your Process**: Explain your synthetic data generation in your presentation
- **Show Diversity**: Demonstrate different layouts, currencies, and languages
- **Validate Realism**: Compare synthetic invoices to real examples
- **Iterate Quickly**: Use the script to rapidly generate test datasets

---

**Happy Generating! 🚀**


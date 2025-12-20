# Invoice Type Enhancements

## Overview

The synthetic invoice generator has been enhanced to support diverse invoice types and challenge-based categorization, based on the comprehensive document diversity guide.

## New Features

### 1. Invoice Type Support

The generator now supports four distinct invoice types:

#### Commercial Invoice
- **Purpose**: Cross-border shipment of goods
- **Key Fields**:
  - HS Codes (6-10 digit product classification codes)
  - Incoterms (FOB, CIF, EXW, DDP, CFR, CPT)
  - Country of origin
  - Customs value
- **Characteristics**: Most detailed, complex table layouts with multi-level headers
- **Generation Method**: `generate_commercial_invoice_items()`

#### Service Invoice
- **Purpose**: Services, consulting, SaaS
- **Key Fields**:
  - Service descriptions (longer, more detailed)
  - Hourly/project rates
  - Contract numbers
  - Duration/hours
- **Characteristics**: Simpler layout, descriptive text rather than tabular data
- **Generation Method**: `generate_service_invoice_items()`

#### Proforma Invoice
- **Purpose**: Preliminary quotation or estimate
- **Key Fields**: Similar to commercial invoice but clearly marked "PROFORMA"
- **Characteristics**: Invoice ID prefixed with "PROFORMA-" for identification
- **Generation Method**: Uses standard invoice generation with proforma marking

#### Industry-Specific Invoice
- **Purpose**: Industry-specific formats (construction, healthcare, retail, freelancing, etc.)
- **Key Fields**:
  - Industry classification
  - Project codes
  - Industry-specific terminology
- **Characteristics**: High variability, branded designs, unconventional layouts
- **Generation Method**: Uses standard invoice generation with industry tagging

### 2. Challenge-Based Categorization

Each invoice is automatically categorized by the layout challenge it presents:

#### Challenge Categories

1. **complex_table**: Multi-level headers, merged cells, nested structures
   - Triggered by: Commercial invoices, invoices with 15+ items

2. **key_value**: Scattered fields, key-value pair extraction
   - Default category for standard invoices

3. **visual_noise**: Heavy branding, signatures, stamps, watermarks
   - Triggered by: Industry-specific invoices

4. **multi_page**: Key information (totals) not on first page
   - Triggered by: 25+ items, multi-page layout type

5. **dense_data**: High information density, complex calculations
   - Triggered by: 10+ items in medium complexity

6. **multi_currency**: Multiple currencies or languages
   - Triggered by: Non-standard currencies or non-English languages (30% chance)

### 3. Enhanced Metadata

The `InvoiceMetadata` dataclass now includes:

```python
invoice_type: str  # commercial, service, proforma, industry_specific
challenge_category: str  # complex_table, key_value, visual_noise, etc.

# Commercial invoice fields
hs_codes: Optional[List[str]]
incoterms: str
country_of_origin: str
customs_value: float

# Industry-specific fields
industry: str
contract_number: str
project_code: str
```

### 4. Configuration Updates

The `config.yaml` file now supports:

```yaml
invoice_types:
  commercial:
    weight: 0.30
    description: "Cross-border shipment invoices with HS codes, Incoterms, customs value"
  service:
    weight: 0.25
    description: "Service invoices with hourly/project rates, contract numbers"
  proforma:
    weight: 0.15
    description: "Preliminary quotations/estimates marked as Proforma"
  industry_specific:
    weight: 0.30
    description: "Industry-specific invoices (construction, healthcare, retail, etc.)"

challenge_categories:
  - complex_table
  - key_value
  - visual_noise
  - multi_page
  - dense_data
  - multi_currency
```

### 5. Enhanced Dataset Summary

The dataset summary now includes:

- Invoice type distribution (count and percentage for each type)
- Challenge category distribution (count and percentage for each category)
- Full breakdown in `dataset_summary.json`

## Usage

### Generating Invoices with Specific Types

The invoice type is automatically selected based on the configured distribution:

```python
from synthetic_invoice_generator.src.data_generator import SyntheticInvoiceGenerator

generator = SyntheticInvoiceGenerator()
pdf_path, metadata = generator.generate_single_invoice(1)

print(f"Invoice type: {metadata['invoice_type']}")
print(f"Challenge category: {metadata['challenge_category']}")

if metadata['invoice_type'] == 'commercial':
    print(f"HS Codes: {metadata['hs_codes']}")
    print(f"Incoterms: {metadata['incoterms']}")
```

### Filtering by Challenge Category

When generating training data, you can filter by challenge category:

```python
# Generate batch and filter
all_invoices = generator.generate_batch(1, 1000)

# Get complex table examples
complex_table_invoices = [
    inv for inv in all_invoices 
    if inv['metadata']['challenge_category'] == 'complex_table'
]
```

## Integration with Training Pipeline

### For PaddleOCR-VL Fine-Tuning

1. **Balanced Dataset**: Use invoice type distribution to ensure balanced training data
2. **Hard Sample Mining**: Use challenge categories to identify difficult cases
3. **Category-Specific Evaluation**: Evaluate model performance by challenge category
4. **Targeted Training**: Focus additional training on weak challenge categories

### Instruction Pair Generation

When creating instruction-response pairs, include invoice type and challenge category in metadata:

```python
instruction_pair = {
    "image": "path/to/invoice.png",
    "conversations": [...],
    "metadata": {
        "invoice_type": "commercial",
        "challenge_category": "complex_table",
        "has_hs_codes": True,
        "has_customs_data": True
    }
}
```

## Next Steps

1. **Layout Enhancements**: Create specialized layouts for commercial invoices with HS code tables
2. **Visual Noise Simulation**: Add branded templates, logos, and stamps for industry-specific invoices
3. **Multi-Currency Support**: Implement dual-currency layouts for international invoices
4. **Financial Statements**: Add support for Income Statements, Balance Sheets, and Cash Flow Statements

## References

- See `DOCUMENT_DIVERSITY_GUIDE.md` for comprehensive format diversity information
- See `config/config.yaml` for configuration options
- See `src/data_generator.py` for implementation details


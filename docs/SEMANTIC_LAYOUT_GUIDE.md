# Semantic Layout Understanding Guide

## Overview

PaddleOCR-VL is designed to move far beyond simple text extraction and achieve **"deep structural and semantic understanding of a document's layout"**. This is crucial for the Financial Statement & Invoice Analyzer, as it must comprehend relationships between headers, values, tables, and their order to produce accurate structured data.

## 🏗️ Two-Stage Architecture

PaddleOCR-VL's architecture decomposes document parsing into two specialized stages to achieve superior layout understanding efficiently:

| Stage | Core Component | Primary Function for Semantic Layout |
| :--- | :--- | :--- |
| **Stage 1: Layout Analysis** | **PP-DocLayoutV2** (RT-DETR detector + Pointer Network) | 1. **Detects and classifies** all semantic regions (text blocks, tables, formulas, images)<br>2. **Predicts the correct reading order** for these elements, which is vital for understanding multi-column documents like financial reports |
| **Stage 2: Element Recognition** | **PaddleOCR-VL-0.9B** (Vision-Language Model) | Takes the cropped image of each element from Stage 1 and **recognizes its specific content and internal structure**, such as text within a paragraph or cells within a table |

This two-stage approach allows each part to specialize. The layout model focuses purely on geometry and order, while the VLM focuses on content recognition, together enabling a holistic understanding of the document.

## 💡 What This Means for Financial Document Analysis

This architecture directly enables the features needed for financial document processing:

### From "Text Soup" to Structured Data

The system doesn't output a stream of text. It provides a structured representation of the entire document, often as JSON or Markdown, where each element is tagged with its type (text, table), content, and position. For example, it could distinguish a table cell containing the numeric `"Subtotal"` from a header cell labeled `"Subtotal"` based on layout and context.

### Handling Complex Layouts

It excels at challenging tasks like:
- Parsing tables with merged cells
- Understanding the flow of multi-column financial statements
- Ignoring visual noise like stamps or logos by correctly classifying them

### Foundation for Fine-Tuning

When you fine-tune the **PaddleOCR-VL-0.9B model**, you build upon this pre-existing, powerful understanding of document semantics. You're teaching it to apply these skills with even higher precision to the specific language, formats, and structures found in invoices and balance sheets.

## 📊 Structured Output Format

The semantic layout analyzer produces structured output that captures the document's semantic structure:

```json
{
  "pages": [{
    "text_blocks": [
      {"text": "INVOICE", "type": "title", "bbox": [50, 20, 200, 50], "reading_order": 0},
      {"text": "Invoice #: INV-2023-001", "type": "field", "bbox": [400, 20, 600, 50], "reading_order": 1}
    ],
    "tables": [{
      "html": "<table><tr><td>Item</td><td>Qty</td><td>Price</td></tr>...",
      "bbox": [50, 200, 550, 400],
      "structure": {
        "num_rows": 4,
        "num_cols": 4,
        "has_header": true
      },
      "reading_order": 2
    }],
    "images": [
      {"type": "company_logo", "bbox": [400, 50, 500, 150], "reading_order": 3}
    ]
  }],
  "regions": [
    {
      "type": "title",
      "bbox": {"x1": 50, "y1": 20, "x2": 200, "y2": 50},
      "reading_order": 0,
      "confidence": 0.99
    }
  ],
  "reading_order": [0, 1, 2, 3]
}
```

## 🔧 Implementation in FinScribe

### Basic Usage

```python
from app.core.models.paddleocr_vl_service import PaddleOCRVLService
from app.config.settings import load_config

config = load_config()
service = PaddleOCRVLService(config)

# Read document image
with open("invoice.pdf", "rb") as f:
    image_bytes = f.read()

# Parse with semantic layout understanding
result = await service.parse_document_with_semantic_layout(image_bytes)

# Access semantic layout
semantic_layout = result["semantic_layout"]
regions = semantic_layout["regions"]
reading_order = semantic_layout["reading_order"]
```

### Standard Document Parsing (with semantic layout enhancement)

```python
# Standard parsing (automatically includes semantic layout if enabled)
result = await service.parse_document(image_bytes)

# Check if semantic layout is available
if "semantic_layout" in result:
    layout = result["semantic_layout"]
    print(f"Detected {len(layout['regions'])} semantic regions")
    print(f"Reading order: {layout['reading_order']}")
```

### Region-Specific Processing

```python
# Process a specific region with appropriate prompt (Stage 2)
result = await service.parse_region(
    image_bytes=image_bytes,
    region_type="line_items_table",
    bbox={"x": 50, "y": 200, "w": 500, "h": 200}
)
```

### Mixed Document Processing

```python
# Process document with pre-detected regions
regions = [
    {"type": "vendor_block", "bbox": {"x": 100, "y": 100, "w": 300, "h": 150}},
    {"type": "line_items_table", "bbox": {"x": 100, "y": 300, "w": 500, "h": 200}},
    {"type": "financial_summary", "bbox": {"x": 400, "y": 550, "w": 200, "h": 100}}
]

result = await service.parse_mixed_document(image_bytes, regions)
```

## 🎯 Key Features

### 1. Reading Order Prediction

The layout analyzer predicts the correct reading order for multi-column documents. This is crucial for financial statements where information flows in a specific sequence:

```python
# Regions are automatically sorted by reading order
for region in semantic_layout["regions"]:
    print(f"Order {region['reading_order']}: {region['type']}")
```

### 2. Semantic Region Classification

The system classifies regions into semantic types:
- `text_block`: Standard text paragraphs
- `table` / `line_items_table`: Structured tabular data
- `formula`: Mathematical formulas
- `image`: Logos, signatures, stamps
- `title`: Document titles
- `header` / `footer`: Page headers and footers
- `vendor_block`: Vendor/seller information
- `client_block`: Client/buyer information
- `financial_summary`: Totals, taxes, subtotals

### 3. Internal Structure Recognition

For tables, the system recognizes:
- Number of rows and columns
- Header rows
- Cell relationships
- Merged cells (when available)

### 4. Bounding Box Precision

Each region and element has precise bounding box coordinates, enabling:
- Accurate region cropping
- Spatial relationship analysis
- Overlap detection
- Multi-column document handling

## 🔬 Fine-Tuning Strategy

To win the "Best PaddleOCR-VL Fine-Tune" prize, you can build on this foundation:

### 1. Focus Your Fine-Tuning

Since the layout analysis (PP-DocLayoutV2) is already robust, your fine-tuning efforts should target the **PaddleOCR-VL-0.9B** model. Train it to become an expert in recognizing and structuring the specific elements of financial documents.

### 2. Design Domain-Specific Prompts

Use the model's instruction-following capability. For example, you can design prompts that ask the fine-tuned model to `"Extract all line items and calculate the total tax"` from an invoice image, leveraging its semantic understanding to perform the task.

### 3. Leverage Semantic Layout in Training

When creating training data, use the semantic layout information:
- Group related elements by region
- Preserve reading order
- Use region types as context for extraction tasks

## 📁 Module Structure

The semantic layout understanding is implemented in:

- **`app/core/models/semantic_layout.py`**: Core semantic layout analyzer
  - `SemanticLayoutAnalyzer`: Main analyzer class
  - `SemanticRegion`: Represents detected regions (Stage 1)
  - `RecognizedElement`: Represents recognized content (Stage 2)
  - `SemanticLayoutResult`: Complete structured output

- **`app/core/models/paddleocr_vl_service.py`**: Enhanced service with semantic layout integration
  - `parse_document_with_semantic_layout()`: Full two-stage processing
  - `parse_document()`: Standard parsing with optional semantic layout enhancement

## ⚙️ Configuration

Enable or disable semantic layout analysis in your config:

```python
config = {
    "semantic_layout": {
        "enabled": True  # Enable semantic layout understanding
    },
    "paddleocr_vl": {
        "vllm_server_url": "http://localhost:8001/v1",
        "timeout": 30,
        "max_retries": 3
    }
}
```

## 🚀 Next Steps

1. **Test with Real Documents**: Process sample invoices and financial statements to see semantic layout in action
2. **Analyze Reading Order**: Verify that multi-column documents are processed in the correct order
3. **Fine-Tune Prompts**: Use semantic region information to create better extraction prompts
4. **Validate Structure**: Use the structured output to validate extracted financial data

## 📚 References

- [PaddleOCR-VL Documentation](https://github.com/PaddlePaddle/PaddleOCR)
- [PP-DocLayoutV2 Architecture](https://github.com/PaddlePaddle/PaddleOCR/tree/release/2.7/ppstructure)
- [PaddleOCR-VL-0.9B Model Card](https://huggingface.co/PaddlePaddle/PaddleOCR-VL)


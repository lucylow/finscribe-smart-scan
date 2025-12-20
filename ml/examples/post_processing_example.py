"""
Example usage of the Post-Processing Intelligence Layer (Phase 3)

This demonstrates how the FinancialDocumentPostProcessor transforms raw OCR output
into validated, structured financial data.
"""

import json
from app.core.post_processing import FinancialDocumentPostProcessor


def example_usage():
    """Example of how to use the FinancialDocumentPostProcessor"""
    
    # Sample OCR output (simplified for example)
    # This matches the format from PaddleOCR-VL service
    sample_ocr_output = {
        'status': 'success',
        'model_version': 'PaddleOCR-VL-0.9B',
        'tokens': [
            {'text': 'Tech Solutions Inc.', 'confidence': 0.95},
            {'text': '123 Innovation Street', 'confidence': 0.94},
            {'text': 'San Francisco, CA 94105', 'confidence': 0.93},
            {'text': 'Invoice #: INV-2024-001', 'confidence': 0.98},
            {'text': 'Date: 01/15/2024', 'confidence': 0.97},
            {'text': 'Due Date: 02/14/2024', 'confidence': 0.96},
            {'text': 'Bill To: ABC Corporation', 'confidence': 0.95},
            {'text': 'Description', 'confidence': 0.91},
            {'text': 'Qty', 'confidence': 0.91},
            {'text': 'Unit Price', 'confidence': 0.91},
            {'text': 'Total', 'confidence': 0.91},
            {'text': 'Software License', 'confidence': 0.92},
            {'text': '5', 'confidence': 0.99},
            {'text': '$100.00', 'confidence': 0.97},
            {'text': '$500.00', 'confidence': 0.96},
            {'text': 'Subtotal:', 'confidence': 0.94},
            {'text': '$500.00', 'confidence': 0.96},
            {'text': 'Tax (7%):', 'confidence': 0.95},
            {'text': '$35.00', 'confidence': 0.97},
            {'text': 'Grand Total:', 'confidence': 0.98},
            {'text': '$535.00', 'confidence': 0.97},
        ],
        'bboxes': [
            {'x': 50, 'y': 50, 'w': 150, 'h': 20, 'region_type': 'vendor', 'page_index': 0},
            {'x': 50, 'y': 80, 'w': 200, 'h': 20, 'region_type': 'vendor', 'page_index': 0},
            {'x': 50, 'y': 110, 'w': 250, 'h': 20, 'region_type': 'vendor', 'page_index': 0},
            {'x': 400, 'y': 50, 'w': 200, 'h': 20, 'region_type': 'header', 'page_index': 0},
            {'x': 400, 'y': 80, 'w': 150, 'h': 20, 'region_type': 'header', 'page_index': 0},
            {'x': 400, 'y': 110, 'w': 180, 'h': 20, 'region_type': 'header', 'page_index': 0},
            {'x': 400, 'y': 150, 'w': 200, 'h': 20, 'region_type': 'client', 'page_index': 0},
            {'x': 50, 'y': 200, 'w': 100, 'h': 20, 'region_type': 'table_header', 'page_index': 0},
            {'x': 200, 'y': 200, 'w': 50, 'h': 20, 'region_type': 'table_header', 'page_index': 0},
            {'x': 300, 'y': 200, 'w': 100, 'h': 20, 'region_type': 'table_header', 'page_index': 0},
            {'x': 450, 'y': 200, 'w': 80, 'h': 20, 'region_type': 'table_header', 'page_index': 0},
            {'x': 50, 'y': 230, 'w': 150, 'h': 20, 'region_type': 'line_item', 'page_index': 0},
            {'x': 200, 'y': 230, 'w': 30, 'h': 20, 'region_type': 'line_item', 'page_index': 0},
            {'x': 300, 'y': 230, 'w': 80, 'h': 20, 'region_type': 'line_item', 'page_index': 0},
            {'x': 450, 'y': 230, 'w': 80, 'h': 20, 'region_type': 'line_item', 'page_index': 0},
            {'x': 300, 'y': 300, 'w': 100, 'h': 20, 'region_type': 'summary', 'page_index': 0},
            {'x': 450, 'y': 300, 'w': 80, 'h': 20, 'region_type': 'summary', 'page_index': 0},
            {'x': 300, 'y': 330, 'w': 120, 'h': 20, 'region_type': 'summary', 'page_index': 0},
            {'x': 450, 'y': 330, 'w': 80, 'h': 20, 'region_type': 'summary', 'page_index': 0},
            {'x': 300, 'y': 360, 'w': 150, 'h': 25, 'region_type': 'total', 'page_index': 0},
            {'x': 450, 'y': 360, 'w': 80, 'h': 25, 'region_type': 'total', 'page_index': 0},
        ]
    }
    
    # Initialize processor
    processor = FinancialDocumentPostProcessor()
    
    # Process the OCR output
    result = processor.process_ocr_output(sample_ocr_output)
    
    # Output structured JSON
    print("=" * 80)
    print("POST-PROCESSING INTELLIGENCE OUTPUT")
    print("=" * 80)
    print(json.dumps(result, indent=2))
    
    # Check validation results
    if result['success']:
        print("\n" + "=" * 80)
        print("VALIDATION SUMMARY")
        print("=" * 80)
        print(f"Validation passed: {result['validation']['is_valid']}")
        print(f"Overall confidence: {result['validation']['overall_confidence']:.2%}")
        
        if result['validation']['errors']:
            print("\nErrors found:")
            for error in result['validation']['errors']:
                print(f"  - {error}")
        
        if result['validation']['warnings']:
            print("\nWarnings:")
            for warning in result['validation']['warnings']:
                print(f"  - {warning}")
        
        # Display extracted data summary
        print("\n" + "=" * 80)
        print("EXTRACTED DATA SUMMARY")
        print("=" * 80)
        data = result['data']
        
        if data.get('vendor', {}).get('name'):
            print(f"Vendor: {data['vendor']['name']}")
        
        if data.get('client', {}).get('invoice_number'):
            print(f"Invoice Number: {data['client']['invoice_number']}")
        
        if data.get('client', {}).get('dates', {}).get('invoice_date'):
            print(f"Invoice Date: {data['client']['dates']['invoice_date']}")
        
        line_items = data.get('line_items', [])
        print(f"\nLine Items: {len(line_items)}")
        for i, item in enumerate(line_items, 1):
            desc = item.get('description', item.get('column_0', 'N/A'))
            qty = item.get('quantity', item.get('qty', 'N/A'))
            price = item.get('price', item.get('unit price', 'N/A'))
            total = item.get('line_total', item.get('total', 'N/A'))
            print(f"  {i}. {desc} - Qty: {qty}, Price: {price}, Total: {total}")
        
        summary = data.get('financial_summary', {})
        print(f"\nFinancial Summary:")
        print(f"  Subtotal: ${summary.get('subtotal', 0):,.2f}")
        print(f"  Tax ({summary.get('tax', {}).get('rate', 0)}%): ${summary.get('tax', {}).get('amount', 0):,.2f}")
        print(f"  Grand Total: {summary.get('currency', '$')}{summary.get('grand_total', 0):,.2f}")
    else:
        print(f"\nProcessing failed: {result.get('error')}")


if __name__ == "__main__":
    example_usage()


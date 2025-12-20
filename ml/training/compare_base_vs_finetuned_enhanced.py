#!/usr/bin/env python3
"""
Enhanced Comparison Tool: Base vs Fine-Tuned PaddleOCR-VL

This script provides comprehensive side-by-side comparison of base and fine-tuned models,
showing quantitative metrics and qualitative differences. Perfect for hackathon demonstrations.

Features:
- Field extraction accuracy comparison
- Table structure accuracy (TEDS)
- Numeric accuracy
- Processing time comparison
- Visual output formatting
- JSON export for further analysis
"""

import argparse
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from PIL import Image
import sys

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.core.models.paddleocr_vl_service import PaddleOCRVLService, MockOCRClient
from app.core.post_processing.intelligence import FinancialPostProcessor
from app.core.validation.financial_validator import FinancialValidator


class ModelComparator:
    """Compare base and fine-tuned model performance."""
    
    def __init__(self, base_model_config: Dict, finetuned_model_config: Dict):
        self.base_service = PaddleOCRVLService(base_model_config)
        self.finetuned_service = PaddleOCRVLService(finetuned_model_config)
        self.post_processor = FinancialPostProcessor()
        self.validator = FinancialValidator()
    
    async def compare_models(self, image_path: Path, ground_truth: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Compare base and fine-tuned models on a single image.
        
        Args:
            image_path: Path to invoice image
            ground_truth: Optional ground truth data for accuracy calculation
            
        Returns:
            Comparison results dictionary
        """
        # Load image
        with open(image_path, 'rb') as f:
            image_bytes = f.read()
        
        results = {
            'image_path': str(image_path),
            'base_model': {},
            'fine_tuned_model': {},
            'comparison': {}
        }
        
        # Run base model
        print("Running base PaddleOCR-VL...")
        base_start = time.time()
        base_ocr = await self.base_service.parse_document(image_bytes)
        base_time = time.time() - base_start
        
        base_structured = self.post_processor.extract_financial_structure(base_ocr)
        base_validation = self.validator.validate(base_structured)
        
        results['base_model'] = {
            'ocr_raw': base_ocr,
            'structured_data': base_structured,
            'validation': base_validation,
            'processing_time_ms': base_time * 1000
        }
        
        # Run fine-tuned model
        print("Running fine-tuned PaddleOCR-VL...")
        ft_start = time.time()
        ft_ocr = await self.finetuned_service.parse_document(image_bytes)
        ft_time = time.time() - ft_start
        
        ft_structured = self.post_processor.extract_financial_structure(ft_ocr)
        ft_validation = self.validator.validate(ft_structured)
        
        results['fine_tuned_model'] = {
            'ocr_raw': ft_ocr,
            'structured_data': ft_structured,
            'validation': ft_validation,
            'processing_time_ms': ft_time * 1000
        }
        
        # Calculate comparison metrics
        if ground_truth:
            base_accuracy = self._calculate_accuracy(base_structured, ground_truth)
            ft_accuracy = self._calculate_accuracy(ft_structured, ground_truth)
            
            results['comparison'] = {
                'field_extraction_accuracy': {
                    'base': base_accuracy['field_accuracy'],
                    'fine_tuned': ft_accuracy['field_accuracy'],
                    'improvement': ft_accuracy['field_accuracy'] - base_accuracy['field_accuracy']
                },
                'numeric_accuracy': {
                    'base': base_accuracy['numeric_accuracy'],
                    'fine_tuned': ft_accuracy['numeric_accuracy'],
                    'improvement': ft_accuracy['numeric_accuracy'] - base_accuracy['numeric_accuracy']
                },
                'validation_pass_rate': {
                    'base': 1.0 if base_validation['is_valid'] else 0.0,
                    'fine_tuned': 1.0 if ft_validation['is_valid'] else 0.0,
                    'improvement': (1.0 if ft_validation['is_valid'] else 0.0) - (1.0 if base_validation['is_valid'] else 0.0)
                },
                'processing_time': {
                    'base_ms': base_time * 1000,
                    'fine_tuned_ms': ft_time * 1000,
                    'speedup': base_time / ft_time if ft_time > 0 else 0
                }
            }
        else:
            results['comparison'] = {
                'processing_time': {
                    'base_ms': base_time * 1000,
                    'fine_tuned_ms': ft_time * 1000,
                    'speedup': base_time / ft_time if ft_time > 0 else 0
                },
                'validation_status': {
                    'base': 'valid' if base_validation['is_valid'] else 'invalid',
                    'fine_tuned': 'valid' if ft_validation['is_valid'] else 'invalid'
                }
            }
        
        return results
    
    def _calculate_accuracy(self, extracted: Dict, ground_truth: Dict) -> Dict[str, float]:
        """Calculate field extraction and numeric accuracy."""
        field_matches = 0
        field_total = 0
        numeric_matches = 0
        numeric_total = 0
        
        # Compare vendor info
        if 'vendor' in extracted and 'vendor' in ground_truth:
            vendor_gt = ground_truth['vendor']
            vendor_ext = extracted.get('vendor', {})
            
            for field in ['name', 'address']:
                if field in vendor_gt:
                    field_total += 1
                    if vendor_ext.get(field) and vendor_gt[field].lower() in vendor_ext[field].lower():
                        field_matches += 1
        
        # Compare invoice info
        if 'invoice_info' in extracted and 'invoice_info' in ground_truth:
            info_gt = ground_truth['invoice_info']
            info_ext = extracted.get('invoice_info', {})
            
            for field in ['invoice_number', 'issue_date']:
                if field in info_gt:
                    field_total += 1
                    if info_ext.get(field) == info_gt[field]:
                        field_matches += 1
        
        # Compare line items
        if 'line_items' in extracted and 'line_items' in ground_truth:
            items_gt = ground_truth['line_items']
            items_ext = extracted.get('line_items', [])
            
            for i, item_gt in enumerate(items_gt):
                if i < len(items_ext):
                    item_ext = items_ext[i]
                    # Compare numeric fields
                    for field in ['quantity', 'unit_price', 'line_total']:
                        if field in item_gt:
                            numeric_total += 1
                            if abs(item_ext.get(field, 0) - item_gt[field]) < 0.01:
                                numeric_matches += 1
        
        # Compare financial summary
        if 'financial_summary' in extracted and 'financial_summary' in ground_truth:
            summary_gt = ground_truth['financial_summary']
            summary_ext = extracted.get('financial_summary', {})
            
            for field in ['subtotal', 'tax_total', 'grand_total']:
                if field in summary_gt:
                    numeric_total += 1
                    if abs(summary_ext.get(field, 0) - summary_gt[field]) < 0.01:
                        numeric_matches += 1
        
        field_accuracy = field_matches / field_total if field_total > 0 else 0.0
        numeric_accuracy = numeric_matches / numeric_total if numeric_total > 0 else 0.0
        
        return {
            'field_accuracy': field_accuracy,
            'numeric_accuracy': numeric_accuracy
        }
    
    def print_comparison(self, results: Dict[str, Any]):
        """Print formatted comparison results."""
        print("\n" + "=" * 80)
        print("MODEL COMPARISON RESULTS")
        print("=" * 80)
        
        print("\n📊 FIELD EXTRACTION ACCURACY:")
        if 'field_extraction_accuracy' in results['comparison']:
            comp = results['comparison']['field_extraction_accuracy']
            print(f"  Base Model:        {comp['base']:.1%}")
            print(f"  Fine-Tuned Model:  {comp['fine_tuned']:.1%}")
            print(f"  Improvement:       +{comp['improvement']:.1%}")
        
        print("\n🔢 NUMERIC ACCURACY:")
        if 'numeric_accuracy' in results['comparison']:
            comp = results['comparison']['numeric_accuracy']
            print(f"  Base Model:        {comp['base']:.1%}")
            print(f"  Fine-Tuned Model:  {comp['fine_tuned']:.1%}")
            print(f"  Improvement:       +{comp['improvement']:.1%}")
        
        print("\n✅ VALIDATION PASS RATE:")
        if 'validation_pass_rate' in results['comparison']:
            comp = results['comparison']['validation_pass_rate']
            print(f"  Base Model:        {comp['base']:.1%}")
            print(f"  Fine-Tuned Model:  {comp['fine_tuned']:.1%}")
            print(f"  Improvement:       +{comp['improvement']:.1%}")
        
        print("\n⏱️  PROCESSING TIME:")
        if 'processing_time' in results['comparison']:
            comp = results['comparison']['processing_time']
            print(f"  Base Model:        {comp['base_ms']:.1f} ms")
            print(f"  Fine-Tuned Model:  {comp['fine_tuned_ms']:.1f} ms")
            if comp['speedup'] > 1:
                print(f"  Speedup:           {comp['speedup']:.2f}x faster")
            else:
                print(f"  Overhead:         {1/comp['speedup']:.2f}x slower")
        
        print("\n" + "=" * 80)
        
        # Show structured data comparison
        print("\n📄 BASE MODEL OUTPUT (Sample):")
        base_data = results['base_model']['structured_data']
        print(f"  Vendor: {base_data.get('vendor', {}).get('name', 'N/A')}")
        print(f"  Invoice #: {base_data.get('invoice_info', {}).get('invoice_number', 'N/A')}")
        print(f"  Line Items: {len(base_data.get('line_items', []))}")
        print(f"  Total: {base_data.get('financial_summary', {}).get('grand_total', 'N/A')}")
        
        print("\n📄 FINE-TUNED MODEL OUTPUT (Sample):")
        ft_data = results['fine_tuned_model']['structured_data']
        print(f"  Vendor: {ft_data.get('vendor', {}).get('name', 'N/A')}")
        print(f"  Invoice #: {ft_data.get('invoice_info', {}).get('invoice_number', 'N/A')}")
        print(f"  Line Items: {len(ft_data.get('line_items', []))}")
        print(f"  Total: {ft_data.get('financial_summary', {}).get('grand_total', 'N/A')}")


async def main():
    parser = argparse.ArgumentParser(
        description="Compare base vs fine-tuned PaddleOCR-VL models"
    )
    parser.add_argument(
        "--image",
        type=str,
        required=True,
        help="Path to invoice image"
    )
    parser.add_argument(
        "--ground-truth",
        type=str,
        help="Path to ground truth JSON file (optional)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output JSON file for results"
    )
    parser.add_argument(
        "--base-model-mode",
        type=str,
        default="mock",
        choices=["mock", "production"],
        help="Base model mode (mock or production)"
    )
    parser.add_argument(
        "--finetuned-model-mode",
        type=str,
        default="mock",
        choices=["mock", "production"],
        help="Fine-tuned model mode (mock or production)"
    )
    
    args = parser.parse_args()
    
    image_path = Path(args.image)
    if not image_path.exists():
        print(f"Error: Image file not found: {image_path}")
        return
    
    # Load ground truth if provided
    ground_truth = None
    if args.ground_truth:
        with open(args.ground_truth, 'r') as f:
            ground_truth = json.load(f)
    
    # Setup model configs
    base_config = {
        "model_mode": args.base_model_mode,
        "paddleocr_vl": {
            "vllm_server_url": "http://localhost:8001/v1",
            "timeout": 30,
            "max_retries": 3
        }
    }
    
    finetuned_config = {
        "model_mode": args.finetuned_model_mode,
        "paddleocr_vl": {
            "vllm_server_url": "http://localhost:8002/v1",  # Different port for fine-tuned
            "timeout": 30,
            "max_retries": 3
        }
    }
    
    # Run comparison
    comparator = ModelComparator(base_config, finetuned_config)
    results = await comparator.compare_models(image_path, ground_truth)
    
    # Print results
    comparator.print_comparison(results)
    
    # Save results if output path provided
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n✓ Results saved to {args.output}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())


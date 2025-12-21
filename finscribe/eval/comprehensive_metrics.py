"""
Comprehensive Evaluation Metrics for Financial Document Extraction

This module provides detailed evaluation metrics including:
- Field extraction accuracy
- Table structure accuracy (TEDS)
- Numeric accuracy
- Validation pass rate
- Processing time metrics
- Confidence score analysis
"""

from typing import Dict, Any, List, Optional
from decimal import Decimal
import json
import logging

logger = logging.getLogger(__name__)


class ComprehensiveEvaluator:
    """
    Comprehensive evaluator for financial document extraction models.
    """
    
    def __init__(self, tolerance: float = 0.01):
        self.tolerance = Decimal(str(tolerance))
    
    def evaluate(
        self,
        extracted: Dict[str, Any],
        ground_truth: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Comprehensive evaluation comparing extracted data to ground truth.
        
        Args:
            extracted: Extracted structured data
            ground_truth: Ground truth structured data
            
        Returns:
            Dictionary with all evaluation metrics
        """
        metrics = {
            'field_extraction': self._evaluate_field_extraction(extracted, ground_truth),
            'numeric_accuracy': self._evaluate_numeric_accuracy(extracted, ground_truth),
            'table_structure': self._evaluate_table_structure(extracted, ground_truth),
            'validation': self._evaluate_validation(extracted),
            'overall_score': 0.0
        }
        
        # Calculate overall score (weighted average)
        weights = {
            'field_extraction': 0.3,
            'numeric_accuracy': 0.3,
            'table_structure': 0.2,
            'validation': 0.2
        }
        
        overall = (
            metrics['field_extraction']['accuracy'] * weights['field_extraction'] +
            metrics['numeric_accuracy']['accuracy'] * weights['numeric_accuracy'] +
            metrics['table_structure']['teds_score'] * weights['table_structure'] +
            (1.0 if metrics['validation']['is_valid'] else 0.0) * weights['validation']
        )
        
        metrics['overall_score'] = overall
        
        return metrics
    
    def _evaluate_field_extraction(
        self,
        extracted: Dict[str, Any],
        ground_truth: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate field extraction accuracy."""
        matches = 0
        total = 0
        field_details = {}
        
        # Vendor fields
        vendor_gt = ground_truth.get('vendor', {})
        vendor_ext = extracted.get('vendor', {})
        
        for field in ['name', 'address']:
            if field in vendor_gt:
                total += 1
                gt_value = str(vendor_gt[field]).lower().strip()
                ext_value = str(vendor_ext.get(field, '')).lower().strip()
                
                # Fuzzy match (contains check)
                is_match = gt_value in ext_value or ext_value in gt_value
                if is_match:
                    matches += 1
                
                field_details[f'vendor_{field}'] = {
                    'match': is_match,
                    'ground_truth': vendor_gt[field],
                    'extracted': vendor_ext.get(field)
                }
        
        # Invoice info fields
        info_gt = ground_truth.get('invoice_info', {})
        info_ext = extracted.get('invoice_info', {})
        
        for field in ['invoice_number', 'issue_date', 'due_date']:
            if field in info_gt:
                total += 1
                gt_value = str(info_gt[field]).strip()
                ext_value = str(info_ext.get(field, '')).strip()
                
                is_match = gt_value == ext_value
                if is_match:
                    matches += 1
                
                field_details[f'invoice_{field}'] = {
                    'match': is_match,
                    'ground_truth': info_gt[field],
                    'extracted': info_ext.get(field)
                }
        
        accuracy = matches / total if total > 0 else 0.0
        
        return {
            'accuracy': accuracy,
            'matches': matches,
            'total': total,
            'field_details': field_details
        }
    
    def _evaluate_numeric_accuracy(
        self,
        extracted: Dict[str, Any],
        ground_truth: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate numeric field accuracy."""
        matches = 0
        total = 0
        numeric_details = {}
        
        # Line items
        items_gt = ground_truth.get('line_items', [])
        items_ext = extracted.get('line_items', [])
        
        for i, item_gt in enumerate(items_gt):
            if i < len(items_ext):
                item_ext = items_ext[i]
                
                for field in ['quantity', 'unit_price', 'line_total']:
                    if field in item_gt:
                        total += 1
                        gt_value = Decimal(str(item_gt[field]))
                        ext_value = Decimal(str(item_ext.get(field, 0)))
                        
                        diff = abs(gt_value - ext_value)
                        is_match = diff <= self.tolerance
                        
                        if is_match:
                            matches += 1
                        
                        numeric_details[f'line_item_{i}_{field}'] = {
                            'match': is_match,
                            'ground_truth': float(gt_value),
                            'extracted': float(ext_value),
                            'difference': float(diff)
                        }
        
        # Financial summary
        summary_gt = ground_truth.get('financial_summary', {})
        summary_ext = extracted.get('financial_summary', {})
        
        for field in ['subtotal', 'tax_total', 'discount_total', 'grand_total']:
            if field in summary_gt:
                total += 1
                gt_value = Decimal(str(summary_gt[field]))
                ext_value = Decimal(str(summary_ext.get(field, 0)))
                
                diff = abs(gt_value - ext_value)
                is_match = diff <= self.tolerance
                
                if is_match:
                    matches += 1
                
                numeric_details[f'summary_{field}'] = {
                    'match': is_match,
                    'ground_truth': float(gt_value),
                    'extracted': float(ext_value),
                    'difference': float(diff)
                }
        
        accuracy = matches / total if total > 0 else 0.0
        
        return {
            'accuracy': accuracy,
            'matches': matches,
            'total': total,
            'numeric_details': numeric_details
        }
    
    def _evaluate_table_structure(
        self,
        extracted: Dict[str, Any],
        ground_truth: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate table structure accuracy using simplified TEDS metric.
        
        Note: Full TEDS implementation would require HTML table structure comparison.
        This is a simplified version that compares row/column counts and alignment.
        """
        items_gt = ground_truth.get('line_items', [])
        items_ext = extracted.get('line_items', [])
        
        # Compare row counts
        row_count_match = len(items_ext) == len(items_gt)
        
        # Compare column structure (check if all items have same fields)
        if items_gt and items_ext:
            gt_fields = set(items_gt[0].keys())
            ext_fields = set(items_ext[0].keys()) if items_ext else set()
            column_match = gt_fields == ext_fields
        else:
            column_match = True
        
        # Simplified TEDS score
        teds_score = 0.0
        if row_count_match:
            teds_score += 0.5
        if column_match:
            teds_score += 0.5
        
        return {
            'teds_score': teds_score,
            'row_count_match': row_count_match,
            'column_structure_match': column_match,
            'ground_truth_rows': len(items_gt),
            'extracted_rows': len(items_ext)
        }
    
    def _evaluate_validation(self, extracted: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate validation results."""
        validation = extracted.get('validation', {})
        
        return {
            'is_valid': validation.get('arithmetic_valid', False),
            'arithmetic_valid': validation.get('arithmetic_valid', False),
            'expected_total': validation.get('expected_total', 0),
            'extracted_total': validation.get('extracted_total', 0),
            'difference': validation.get('difference', 0)
        }
    
    def batch_evaluate(
        self,
        results: List[Tuple[Dict[str, Any], Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Evaluate multiple documents and return aggregate metrics.
        
        Args:
            results: List of (extracted, ground_truth) tuples
            
        Returns:
            Aggregate metrics dictionary
        """
        all_metrics = []
        
        for extracted, ground_truth in results:
            metrics = self.evaluate(extracted, ground_truth)
            all_metrics.append(metrics)
        
        # Aggregate metrics
        aggregate = {
            'total_documents': len(all_metrics),
            'average_field_accuracy': sum(m['field_extraction']['accuracy'] for m in all_metrics) / len(all_metrics) if all_metrics else 0.0,
            'average_numeric_accuracy': sum(m['numeric_accuracy']['accuracy'] for m in all_metrics) / len(all_metrics) if all_metrics else 0.0,
            'average_teds_score': sum(m['table_structure']['teds_score'] for m in all_metrics) / len(all_metrics) if all_metrics else 0.0,
            'validation_pass_rate': sum(1 for m in all_metrics if m['validation']['is_valid']) / len(all_metrics) if all_metrics else 0.0,
            'average_overall_score': sum(m['overall_score'] for m in all_metrics) / len(all_metrics) if all_metrics else 0.0
        }
        
        return {
            'aggregate': aggregate,
            'per_document': all_metrics
        }



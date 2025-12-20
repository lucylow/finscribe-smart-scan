"""
Advanced Evaluation Metrics for Model Training

This module provides comprehensive evaluation metrics for financial document
extraction tasks, including field-level accuracy, table structure metrics,
and numerical validation.
"""

import json
import re
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import numpy as np


class FieldAccuracyMetric:
    """
    Computes field-level extraction accuracy for financial documents.
    """
    
    def __init__(self, field_names: Optional[List[str]] = None):
        """
        Initialize field accuracy metric.
        
        Args:
            field_names: List of field names to track (None = track all)
        """
        self.field_names = field_names
        self.reset()
    
    def reset(self):
        """Reset metric state."""
        self.correct_fields = defaultdict(int)
        self.total_fields = defaultdict(int)
        self.field_errors = defaultdict(list)
    
    def compute(
        self,
        predictions: List[Dict[str, Any]],
        ground_truth: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Compute field-level accuracy.
        
        Args:
            predictions: List of predicted field dictionaries
            ground_truth: List of ground truth field dictionaries
            
        Returns:
            Dictionary with accuracy metrics
        """
        for pred, gt in zip(predictions, ground_truth):
            # Extract fields from both
            pred_fields = self._extract_fields(pred)
            gt_fields = self._extract_fields(gt)
            
            # Compare each field
            all_fields = set(list(pred_fields.keys()) + list(gt_fields.keys()))
            
            for field_name in all_fields:
                if self.field_names is None or field_name in self.field_names:
                    self.total_fields[field_name] += 1
                    
                    pred_value = pred_fields.get(field_name, "").strip().lower()
                    gt_value = gt_fields.get(field_name, "").strip().lower()
                    
                    if self._fields_match(pred_value, gt_value, field_name):
                        self.correct_fields[field_name] += 1
                    else:
                        self.field_errors[field_name].append({
                            'predicted': pred_fields.get(field_name, ""),
                            'ground_truth': gt_fields.get(field_name, "")
                        })
        
        # Compute accuracies
        accuracies = {}
        for field_name in self.total_fields:
            if self.total_fields[field_name] > 0:
                acc = self.correct_fields[field_name] / self.total_fields[field_name]
                accuracies[field_name] = acc
        
        # Overall accuracy
        total_correct = sum(self.correct_fields.values())
        total_count = sum(self.total_fields.values())
        overall_accuracy = total_correct / total_count if total_count > 0 else 0.0
        
        return {
            'overall_accuracy': overall_accuracy,
            'field_accuracies': accuracies,
            'total_fields': dict(self.total_fields),
            'correct_fields': dict(self.correct_fields)
        }
    
    def _extract_fields(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Extract fields from nested dictionary structure."""
        fields = {}
        
        def extract_recursive(obj, prefix=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_key = f"{prefix}.{key}" if prefix else key
                    if isinstance(value, (dict, list)):
                        extract_recursive(value, new_key)
                    else:
                        fields[new_key] = str(value) if value is not None else ""
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    extract_recursive(item, f"{prefix}[{i}]")
        
        extract_recursive(data)
        return fields
    
    def _fields_match(self, pred: str, gt: str, field_name: str) -> bool:
        """Check if predicted and ground truth fields match."""
        # Exact match
        if pred == gt:
            return True
        
        # For numeric fields, allow small differences
        if any(keyword in field_name.lower() for keyword in ['amount', 'price', 'total', 'quantity', 'rate']):
            try:
                pred_num = float(re.sub(r'[^0-9.-]', '', pred))
                gt_num = float(re.sub(r'[^0-9.-]', '', gt))
                # Allow 0.01 difference for floating point
                return abs(pred_num - gt_num) < 0.01
            except (ValueError, AttributeError):
                pass
        
        # For date fields, try different formats
        if any(keyword in field_name.lower() for keyword in ['date', 'time']):
            # Normalize dates (remove special chars, compare core)
            pred_normalized = re.sub(r'[^0-9]', '', pred)
            gt_normalized = re.sub(r'[^0-9]', '', gt)
            if pred_normalized == gt_normalized:
                return True
        
        return False


class TableStructureMetric:
    """
    Computes table structure accuracy using TEDS (Tree-Edit-Distance-Based Similarity).
    Simplified version for financial tables.
    """
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset metric state."""
        self.total_tables = 0
        self.correct_structures = 0
        self.teds_scores = []
    
    def compute(
        self,
        predictions: List[Dict[str, Any]],
        ground_truth: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Compute table structure accuracy.
        
        Args:
            predictions: List of predicted structures
            ground_truth: List of ground truth structures
            
        Returns:
            Dictionary with structure metrics
        """
        for pred, gt in zip(predictions, ground_truth):
            pred_table = self._extract_table(pred)
            gt_table = self._extract_table(gt)
            
            if pred_table is None or gt_table is None:
                continue
            
            self.total_tables += 1
            
            # Compute TEDS score (simplified)
            teds_score = self._compute_teds(pred_table, gt_table)
            self.teds_scores.append(teds_score)
            
            if teds_score > 0.9:  # Threshold for "correct" structure
                self.correct_structures += 1
        
        avg_teds = np.mean(self.teds_scores) if self.teds_scores else 0.0
        structure_accuracy = self.correct_structures / self.total_tables if self.total_tables > 0 else 0.0
        
        return {
            'average_teds': avg_teds,
            'structure_accuracy': structure_accuracy,
            'total_tables': self.total_tables
        }
    
    def _extract_table(self, data: Dict[str, Any]) -> Optional[List[List[str]]]:
        """Extract table structure from data."""
        # Look for common table keys
        for key in ['line_items', 'items', 'table', 'rows']:
            if key in data:
                table_data = data[key]
                if isinstance(table_data, list):
                    # Convert to list of lists
                    table = []
                    for row in table_data:
                        if isinstance(row, dict):
                            table.append(list(row.values()))
                        elif isinstance(row, list):
                            table.append(row)
                    return table
        return None
    
    def _compute_teds(self, pred_table: List[List[str]], gt_table: List[List[str]]) -> float:
        """
        Compute simplified TEDS score.
        
        This is a simplified version. For production, use the full TEDS implementation.
        """
        if len(pred_table) == 0 and len(gt_table) == 0:
            return 1.0
        if len(pred_table) == 0 or len(gt_table) == 0:
            return 0.0
        
        # Compare row counts
        row_similarity = 1.0 - abs(len(pred_table) - len(gt_table)) / max(len(pred_table), len(gt_table))
        
        # Compare column counts (assume first row has headers)
        if len(pred_table) > 0 and len(gt_table) > 0:
            col_similarity = 1.0 - abs(len(pred_table[0]) - len(gt_table[0])) / max(len(pred_table[0]), len(gt_table[0]))
        else:
            col_similarity = 1.0
        
        # Simple average as TEDS approximation
        return (row_similarity + col_similarity) / 2.0


class NumericalValidationMetric:
    """
    Validates numerical consistency in financial documents (e.g., subtotal + tax = total).
    """
    
    def __init__(self, tolerance: float = 0.01):
        """
        Initialize numerical validation metric.
        
        Args:
            tolerance: Tolerance for numerical comparisons
        """
        self.tolerance = tolerance
        self.reset()
    
    def reset(self):
        """Reset metric state."""
        self.total_validations = 0
        self.passed_validations = 0
        self.validation_errors = []
    
    def compute(
        self,
        predictions: List[Dict[str, Any]],
        ground_truth: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, float]:
        """
        Compute numerical validation metrics.
        
        Args:
            predictions: List of predicted structures
            ground_truth: Optional ground truth for comparison
            
        Returns:
            Dictionary with validation metrics
        """
        for pred in predictions:
            # Validate subtotal + tax - discount = total
            validation_result = self._validate_financial_consistency(pred)
            
            self.total_validations += 1
            if validation_result['is_valid']:
                self.passed_validations += 1
            else:
                self.validation_errors.append(validation_result)
        
        pass_rate = self.passed_validations / self.total_validations if self.total_validations > 0 else 0.0
        
        return {
            'validation_pass_rate': pass_rate,
            'total_validations': self.total_validations,
            'passed_validations': self.passed_validations
        }
    
    def _validate_financial_consistency(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate financial consistency (subtotal + tax - discount = total)."""
        try:
            # Extract values
            subtotal = self._extract_numeric(data, ['subtotal', 'sub_total'])
            tax = self._extract_numeric(data, ['tax', 'tax_amount', 'tax_total'])
            discount = self._extract_numeric(data, ['discount', 'discount_amount'])
            total = self._extract_numeric(data, ['total', 'grand_total', 'amount_due'])
            
            if all(v is not None for v in [subtotal, total]):
                # Calculate expected total
                expected_total = subtotal
                if tax is not None:
                    expected_total += tax
                if discount is not None:
                    expected_total -= discount
                
                # Check if matches
                difference = abs(expected_total - total)
                is_valid = difference <= self.tolerance
                
                return {
                    'is_valid': is_valid,
                    'expected_total': expected_total,
                    'actual_total': total,
                    'difference': difference
                }
        except Exception as e:
            return {
                'is_valid': False,
                'error': str(e)
            }
        
        return {'is_valid': False, 'error': 'Missing required fields'}
    
    def _extract_numeric(self, data: Dict[str, Any], keys: List[str]) -> Optional[float]:
        """Extract numeric value from data using various key names."""
        for key in keys:
            # Try direct key
            if key in data:
                value = data[key]
                if isinstance(value, (int, float)):
                    return float(value)
                elif isinstance(value, str):
                    # Extract number from string
                    numbers = re.findall(r'-?\d+\.?\d*', value)
                    if numbers:
                        return float(numbers[0])
            
            # Try nested keys
            for nested_key, nested_value in data.items():
                if isinstance(nested_value, dict):
                    result = self._extract_numeric(nested_value, keys)
                    if result is not None:
                        return result
        
        return None


class ComprehensiveEvaluator:
    """
    Comprehensive evaluator that combines all metrics.
    """
    
    def __init__(self):
        self.field_metric = FieldAccuracyMetric()
        self.table_metric = TableStructureMetric()
        self.numerical_metric = NumericalValidationMetric()
    
    def evaluate(
        self,
        predictions: List[Dict[str, Any]],
        ground_truth: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Run comprehensive evaluation.
        
        Args:
            predictions: List of predictions
            ground_truth: List of ground truth
            
        Returns:
            Dictionary with all metrics
        """
        # Reset all metrics
        self.field_metric.reset()
        self.table_metric.reset()
        self.numerical_metric.reset()
        
        # Compute all metrics
        field_results = self.field_metric.compute(predictions, ground_truth)
        table_results = self.table_metric.compute(predictions, ground_truth)
        numerical_results = self.numerical_metric.compute(predictions, ground_truth)
        
        # Combine results
        return {
            'field_accuracy': field_results,
            'table_structure': table_results,
            'numerical_validation': numerical_results,
            'overall_score': self._compute_overall_score(field_results, table_results, numerical_results)
        }
    
    def _compute_overall_score(
        self,
        field_results: Dict,
        table_results: Dict,
        numerical_results: Dict
    ) -> float:
        """Compute overall weighted score."""
        field_score = field_results.get('overall_accuracy', 0.0)
        table_score = table_results.get('average_teds', 0.0)
        numerical_score = numerical_results.get('validation_pass_rate', 0.0)
        
        # Weighted average (field accuracy is most important)
        return 0.5 * field_score + 0.3 * table_score + 0.2 * numerical_score


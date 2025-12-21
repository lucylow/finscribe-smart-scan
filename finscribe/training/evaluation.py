"""
Comprehensive evaluation metrics for PaddleOCR-VL fine-tuning
Implements field-level accuracy, TEDS, and numerical validation
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import defaultdict
import numpy as np


class ModelEvaluator:
    """
    Evaluates model performance on financial document extraction.
    Implements comprehensive metrics from PaddleOCR-VL methodology.
    """
    
    def __init__(self):
        self.field_weights = {
            "vendor_block": 1.5,
            "client_info": 1.5,
            "invoice_metadata": 1.5,
            "line_item_table": 2.5,
            "financial_summary": 2.0,
        }
    
    def evaluate_field_extraction(
        self,
        predicted: Dict[str, Any],
        ground_truth: Dict[str, Any],
    ) -> Dict[str, float]:
        """
        Evaluate field-level extraction accuracy.
        
        Args:
            predicted: Model prediction
            ground_truth: Ground truth data
            
        Returns:
            Dictionary with per-field accuracies
        """
        accuracies = {}
        
        # Vendor block
        if "vendor" in ground_truth:
            vendor_acc = self._compare_dict(
                predicted.get("vendor", {}),
                ground_truth.get("vendor", {}),
            )
            accuracies["vendor_block"] = vendor_acc
        
        # Client info
        if "client" in ground_truth:
            client_acc = self._compare_dict(
                predicted.get("client", {}),
                ground_truth.get("client", {}),
            )
            accuracies["client_info"] = client_acc
        
        # Invoice metadata
        metadata_fields = ["invoice_id", "issue_date", "due_date", "payment_terms"]
        metadata_correct = 0
        for field in metadata_fields:
            pred_val = str(predicted.get(field, "")).strip().lower()
            gt_val = str(ground_truth.get(field, "")).strip().lower()
            if pred_val == gt_val:
                metadata_correct += 1
        accuracies["invoice_metadata"] = metadata_correct / len(metadata_fields) if metadata_fields else 0.0
        
        # Financial summary
        financial_fields = ["subtotal", "tax_total", "discount_total", "grand_total", "currency"]
        financial_correct = 0
        for field in financial_fields:
            pred_val = predicted.get(field)
            gt_val = ground_truth.get(field)
            
            if isinstance(gt_val, (int, float)) and isinstance(pred_val, (int, float)):
                if abs(pred_val - gt_val) < 0.01:
                    financial_correct += 1
            elif str(pred_val).strip().lower() == str(gt_val).strip().lower():
                financial_correct += 1
        
        accuracies["financial_summary"] = financial_correct / len(financial_fields) if financial_fields else 0.0
        
        return accuracies
    
    def evaluate_table_structure(
        self,
        predicted_items: List[Dict[str, Any]],
        ground_truth_items: List[Dict[str, Any]],
    ) -> Dict[str, float]:
        """
        Evaluate table structure accuracy using TEDS-like metrics.
        
        Args:
            predicted_items: Predicted line items
            ground_truth_items: Ground truth line items
            
        Returns:
            Dictionary with table metrics
        """
        if not predicted_items and not ground_truth_items:
            return {"teds_score": 1.0, "row_accuracy": 1.0, "cell_accuracy": 1.0}
        
        if not predicted_items or not ground_truth_items:
            return {"teds_score": 0.0, "row_accuracy": 0.0, "cell_accuracy": 0.0}
        
        # Row count accuracy
        row_accuracy = 1.0 if len(predicted_items) == len(ground_truth_items) else 0.0
        
        # Cell-level accuracy
        cell_correct = 0
        cell_total = 0
        
        min_len = min(len(predicted_items), len(ground_truth_items))
        for i in range(min_len):
            pred_item = predicted_items[i]
            gt_item = ground_truth_items[i]
            
            # Check each field
            for field in ["description", "quantity", "unit_price", "line_total"]:
                cell_total += 1
                pred_val = pred_item.get(field)
                gt_val = gt_item.get(field)
                
                if isinstance(gt_val, (int, float)) and isinstance(pred_val, (int, float)):
                    if abs(pred_val - gt_val) < 0.01:
                        cell_correct += 1
                elif str(pred_val).strip().lower() == str(gt_val).strip().lower():
                    cell_correct += 1
        
        cell_accuracy = cell_correct / cell_total if cell_total > 0 else 0.0
        
        # Simplified TEDS score (combination of structure and content)
        teds_score = (row_accuracy * 0.3 + cell_accuracy * 0.7)
        
        return {
            "teds_score": teds_score,
            "row_accuracy": row_accuracy,
            "cell_accuracy": cell_accuracy,
        }
    
    def validate_numerical_consistency(
        self,
        predicted: Dict[str, Any],
        ground_truth: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validate numerical consistency (subtotal + tax - discount = grand_total).
        
        Args:
            predicted: Model prediction
            ground_truth: Ground truth data
            
        Returns:
            Validation results
        """
        results = {
            "is_valid": True,
            "errors": [],
        }
        
        # Check predicted consistency
        if all(k in predicted for k in ["subtotal", "tax_total", "grand_total"]):
            calculated_total = (
                predicted["subtotal"] + 
                predicted["tax_total"] - 
                predicted.get("discount_total", 0)
            )
            predicted_total = predicted["grand_total"]
            
            if abs(calculated_total - predicted_total) > 0.01:
                results["is_valid"] = False
                results["errors"].append({
                    "type": "calculation_error",
                    "calculated": calculated_total,
                    "predicted": predicted_total,
                    "difference": abs(calculated_total - predicted_total),
                })
        
        # Check against ground truth
        if all(k in ground_truth for k in ["subtotal", "tax_total", "grand_total"]):
            gt_calculated = (
                ground_truth["subtotal"] + 
                ground_truth["tax_total"] - 
                ground_truth.get("discount_total", 0)
            )
            gt_total = ground_truth["grand_total"]
            
            if abs(gt_calculated - gt_total) > 0.01:
                results["errors"].append({
                    "type": "ground_truth_inconsistency",
                    "message": "Ground truth has calculation error",
                })
        
        return results
    
    def _compare_dict(
        self,
        predicted: Dict[str, Any],
        ground_truth: Dict[str, Any],
    ) -> float:
        """Compare two dictionaries and return accuracy"""
        if not ground_truth:
            return 1.0 if not predicted else 0.0
        
        correct = 0
        total = len(ground_truth)
        
        for key, gt_value in ground_truth.items():
            pred_value = predicted.get(key, "")
            
            if isinstance(gt_value, (int, float)) and isinstance(pred_value, (int, float)):
                if abs(pred_value - gt_value) < 0.01:
                    correct += 1
            elif str(pred_value).strip().lower() == str(gt_value).strip().lower():
                correct += 1
        
        return correct / total if total > 0 else 0.0
    
    def evaluate_sample(
        self,
        predicted: Dict[str, Any],
        ground_truth: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Comprehensive evaluation of a single sample.
        
        Args:
            predicted: Model prediction
            ground_truth: Ground truth data
            
        Returns:
            Complete evaluation results
        """
        # Field extraction accuracy
        field_accuracies = self.evaluate_field_extraction(predicted, ground_truth)
        
        # Table structure accuracy
        table_metrics = self.evaluate_table_structure(
            predicted.get("items", []),
            ground_truth.get("items", []),
        )
        
        # Numerical validation
        numerical_validation = self.validate_numerical_consistency(predicted, ground_truth)
        
        # Overall F1 score (weighted average)
        weighted_acc = 0.0
        total_weight = 0.0
        
        for field, acc in field_accuracies.items():
            weight = self.field_weights.get(field, 1.0)
            weighted_acc += acc * weight
            total_weight += weight
        
        # Add table accuracy
        weighted_acc += table_metrics["teds_score"] * self.field_weights.get("line_item_table", 1.0)
        total_weight += self.field_weights.get("line_item_table", 1.0)
        
        f1_score = weighted_acc / total_weight if total_weight > 0 else 0.0
        
        return {
            "field_accuracies": field_accuracies,
            "table_metrics": table_metrics,
            "numerical_validation": numerical_validation,
            "f1_score": f1_score,
            "exact_match": self._is_exact_match(predicted, ground_truth),
        }
    
    def _is_exact_match(
        self,
        predicted: Dict[str, Any],
        ground_truth: Dict[str, Any],
    ) -> bool:
        """Check if prediction exactly matches ground truth"""
        # Simplified exact match check
        key_fields = ["invoice_id", "grand_total", "vendor.name"]
        
        for field in key_fields:
            if "." in field:
                obj, key = field.split(".")
                pred_val = predicted.get(obj, {}).get(key, "")
                gt_val = ground_truth.get(obj, {}).get(key, "")
            else:
                pred_val = predicted.get(field, "")
                gt_val = ground_truth.get(field, "")
            
            if isinstance(gt_val, (int, float)) and isinstance(pred_val, (int, float)):
                if abs(pred_val - gt_val) >= 0.01:
                    return False
            elif str(pred_val).strip().lower() != str(gt_val).strip().lower():
                return False
        
        return True
    
    def evaluate_dataset(
        self,
        predictions: List[Dict[str, Any]],
        ground_truths: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Evaluate entire dataset.
        
        Args:
            predictions: List of model predictions
            ground_truths: List of ground truth data
            
        Returns:
            Aggregated evaluation results
        """
        if len(predictions) != len(ground_truths):
            raise ValueError("Predictions and ground truths must have same length")
        
        all_results = []
        field_accuracies_agg = defaultdict(list)
        table_teds_scores = []
        numerical_valid_count = 0
        exact_match_count = 0
        
        for pred, gt in zip(predictions, ground_truths):
            result = self.evaluate_sample(pred, gt)
            all_results.append(result)
            
            # Aggregate field accuracies
            for field, acc in result["field_accuracies"].items():
                field_accuracies_agg[field].append(acc)
            
            # Aggregate table metrics
            table_teds_scores.append(result["table_metrics"]["teds_score"])
            
            # Count validations
            if result["numerical_validation"]["is_valid"]:
                numerical_valid_count += 1
            
            if result["exact_match"]:
                exact_match_count += 1
        
        # Calculate means
        field_accuracies_mean = {
            field: np.mean(accs) for field, accs in field_accuracies_agg.items()
        }
        
        return {
            "num_samples": len(predictions),
            "field_accuracies": {
                "mean": field_accuracies_mean,
                "std": {field: np.std(accs) for field, accs in field_accuracies_agg.items()},
            },
            "table_accuracy": {
                "mean_teds": np.mean(table_teds_scores),
                "std_teds": np.std(table_teds_scores),
            },
            "numerical_validation": {
                "valid_count": numerical_valid_count,
                "valid_rate": numerical_valid_count / len(predictions) if predictions else 0.0,
            },
            "overall": {
                "mean_f1": np.mean([r["f1_score"] for r in all_results]),
                "exact_match_rate": exact_match_count / len(predictions) if predictions else 0.0,
            },
        }


def evaluate_model(
    predictions_path: str,
    ground_truth_path: str,
    output_path: str = "evaluation_results.json",
) -> Dict[str, Any]:
    """
    Main function to evaluate model predictions.
    
    Args:
        predictions_path: Path to predictions JSONL file
        ground_truth_path: Path to ground truth JSONL file
        output_path: Output path for results
        
    Returns:
        Evaluation results dictionary
    """
    evaluator = ModelEvaluator()
    
    # Load predictions and ground truth
    predictions = []
    ground_truths = []
    
    with open(predictions_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                predictions.append(data.get("prediction", {}))
    
    with open(ground_truth_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                ground_truths.append(json.loads(line))
    
    # Evaluate
    results = evaluator.evaluate_dataset(predictions, ground_truths)
    
    # Save results
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"Evaluation results saved to {output_path}")
    print(f"\nSummary:")
    print(f"  Field Accuracies: {results['field_accuracies']['mean']}")
    print(f"  Table TEDS Score: {results['table_accuracy']['mean_teds']:.3f}")
    print(f"  Numerical Validation Rate: {results['numerical_validation']['valid_rate']:.3f}")
    print(f"  Overall F1 Score: {results['overall']['mean_f1']:.3f}")
    print(f"  Exact Match Rate: {results['overall']['exact_match_rate']:.3f}")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Evaluate model predictions")
    parser.add_argument("--predictions", type=str, required=True, help="Path to predictions JSONL")
    parser.add_argument("--ground-truth", type=str, required=True, help="Path to ground truth JSONL")
    parser.add_argument("--output", type=str, default="evaluation_results.json", help="Output path")
    
    args = parser.parse_args()
    
    evaluate_model(
        predictions_path=args.predictions,
        ground_truth_path=args.ground_truth,
        output_path=args.output,
    )



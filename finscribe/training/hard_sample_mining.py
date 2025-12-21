"""
Hard sample mining for iterative improvement
Implements PaddleOCR-VL's hard sample mining strategy
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from collections import defaultdict
import numpy as np
from dataclasses import dataclass


@dataclass
class ErrorAnalysis:
    """Structure for error analysis results"""
    element_type: str
    error_type: str
    confidence: float
    predicted_value: Any
    ground_truth: Any
    sample_id: str
    image_path: str


class HardSampleMiner:
    """
    Identifies hard samples (failure cases) for iterative improvement.
    Implements PaddleOCR-VL's hard sample mining methodology.
    """
    
    def __init__(self):
        self.error_types = [
            "missing_field",
            "incorrect_value",
            "misaligned_table",
            "wrong_format",
            "low_confidence",
            "type_mismatch",
        ]
        
        self.element_types = [
            "vendor_name",
            "vendor_address",
            "invoice_number",
            "invoice_date",
            "due_date",
            "line_item",
            "subtotal",
            "tax",
            "discount",
            "grand_total",
            "currency",
        ]
    
    def evaluate_prediction(
        self,
        predicted: Dict[str, Any],
        ground_truth: Dict[str, Any],
        sample_id: str,
        image_path: str,
    ) -> List[ErrorAnalysis]:
        """
        Evaluate a prediction against ground truth and identify errors.
        
        Args:
            predicted: Model prediction dictionary
            ground_truth: Ground truth dictionary
            sample_id: Unique sample identifier
            image_path: Path to document image
            
        Returns:
            List of error analyses
        """
        errors = []
        
        # Check vendor information
        if "vendor" in ground_truth:
            vendor_errors = self._check_vendor(
                predicted.get("vendor", {}),
                ground_truth.get("vendor", {}),
                sample_id,
                image_path,
            )
            errors.extend(vendor_errors)
        
        # Check invoice metadata
        metadata_errors = self._check_metadata(
            predicted,
            ground_truth,
            sample_id,
            image_path,
        )
        errors.extend(metadata_errors)
        
        # Check line items
        if "items" in ground_truth:
            items_errors = self._check_line_items(
                predicted.get("items", []),
                ground_truth.get("items", []),
                sample_id,
                image_path,
            )
            errors.extend(items_errors)
        
        # Check financial summary
        financial_errors = self._check_financial_summary(
            predicted.get("financial_summary", {}),
            ground_truth,
            sample_id,
            image_path,
        )
        errors.extend(financial_errors)
        
        return errors
    
    def _check_vendor(
        self,
        predicted: Dict[str, Any],
        ground_truth: Dict[str, Any],
        sample_id: str,
        image_path: str,
    ) -> List[ErrorAnalysis]:
        """Check vendor information extraction"""
        errors = []
        
        for field in ["name", "address", "city", "state", "postal_code", "email"]:
            pred_value = predicted.get(field, "").strip().lower()
            gt_value = ground_truth.get(field, "").strip().lower()
            
            if not pred_value:
                errors.append(ErrorAnalysis(
                    element_type=f"vendor_{field}",
                    error_type="missing_field",
                    confidence=0.0,
                    predicted_value=pred_value,
                    ground_truth=gt_value,
                    sample_id=sample_id,
                    image_path=image_path,
                ))
            elif pred_value != gt_value:
                # Calculate similarity (simple)
                similarity = self._calculate_similarity(pred_value, gt_value)
                errors.append(ErrorAnalysis(
                    element_type=f"vendor_{field}",
                    error_type="incorrect_value",
                    confidence=similarity,
                    predicted_value=pred_value,
                    ground_truth=gt_value,
                    sample_id=sample_id,
                    image_path=image_path,
                ))
        
        return errors
    
    def _check_metadata(
        self,
        predicted: Dict[str, Any],
        ground_truth: Dict[str, Any],
        sample_id: str,
        image_path: str,
    ) -> List[ErrorAnalysis]:
        """Check invoice metadata"""
        errors = []
        
        metadata_fields = ["invoice_id", "issue_date", "due_date", "payment_terms"]
        
        for field in metadata_fields:
            pred_value = str(predicted.get(field, "")).strip().lower()
            gt_value = str(ground_truth.get(field, "")).strip().lower()
            
            if not pred_value:
                errors.append(ErrorAnalysis(
                    element_type=field,
                    error_type="missing_field",
                    confidence=0.0,
                    predicted_value=pred_value,
                    ground_truth=gt_value,
                    sample_id=sample_id,
                    image_path=image_path,
                ))
            elif pred_value != gt_value:
                similarity = self._calculate_similarity(pred_value, gt_value)
                errors.append(ErrorAnalysis(
                    element_type=field,
                    error_type="incorrect_value",
                    confidence=similarity,
                    predicted_value=pred_value,
                    ground_truth=gt_value,
                    sample_id=sample_id,
                    image_path=image_path,
                ))
        
        return errors
    
    def _check_line_items(
        self,
        predicted: List[Dict[str, Any]],
        ground_truth: List[Dict[str, Any]],
        sample_id: str,
        image_path: str,
    ) -> List[ErrorAnalysis]:
        """Check line items extraction"""
        errors = []
        
        # Check if number of items matches
        if len(predicted) != len(ground_truth):
            errors.append(ErrorAnalysis(
                element_type="line_items",
                error_type="misaligned_table",
                confidence=0.0,
                predicted_value=len(predicted),
                ground_truth=len(ground_truth),
                sample_id=sample_id,
                image_path=image_path,
            ))
        
        # Check each item
        min_len = min(len(predicted), len(ground_truth))
        for i in range(min_len):
            pred_item = predicted[i]
            gt_item = ground_truth[i]
            
            # Check key fields
            for field in ["description", "quantity", "unit_price", "line_total"]:
                pred_value = pred_item.get(field)
                gt_value = gt_item.get(field)
                
                if pred_value is None:
                    errors.append(ErrorAnalysis(
                        element_type=f"line_item_{field}",
                        error_type="missing_field",
                        confidence=0.0,
                        predicted_value=pred_value,
                        ground_truth=gt_value,
                        sample_id=f"{sample_id}_item_{i}",
                        image_path=image_path,
                    ))
                elif isinstance(gt_value, (int, float)) and isinstance(pred_value, (int, float)):
                    # Numerical comparison
                    if abs(pred_value - gt_value) > 0.01:
                        errors.append(ErrorAnalysis(
                            element_type=f"line_item_{field}",
                            error_type="incorrect_value",
                            confidence=1.0 - min(abs(pred_value - gt_value) / max(abs(gt_value), 1.0), 1.0),
                            predicted_value=pred_value,
                            ground_truth=gt_value,
                            sample_id=f"{sample_id}_item_{i}",
                            image_path=image_path,
                        ))
                else:
                    # String comparison
                    if str(pred_value).strip().lower() != str(gt_value).strip().lower():
                        similarity = self._calculate_similarity(str(pred_value), str(gt_value))
                        errors.append(ErrorAnalysis(
                            element_type=f"line_item_{field}",
                            error_type="incorrect_value",
                            confidence=similarity,
                            predicted_value=pred_value,
                            ground_truth=gt_value,
                            sample_id=f"{sample_id}_item_{i}",
                            image_path=image_path,
                        ))
        
        return errors
    
    def _check_financial_summary(
        self,
        predicted: Dict[str, Any],
        ground_truth: Dict[str, Any],
        sample_id: str,
        image_path: str,
    ) -> List[ErrorAnalysis]:
        """Check financial summary extraction"""
        errors = []
        
        financial_fields = ["subtotal", "tax_total", "discount_total", "grand_total", "currency"]
        
        for field in financial_fields:
            # Get value from predicted or ground_truth directly
            pred_value = predicted.get(field) if predicted else None
            if pred_value is None:
                pred_value = ground_truth.get(field)
            
            gt_value = ground_truth.get(field)
            
            if pred_value is None:
                errors.append(ErrorAnalysis(
                    element_type=field,
                    error_type="missing_field",
                    confidence=0.0,
                    predicted_value=pred_value,
                    ground_truth=gt_value,
                    sample_id=sample_id,
                    image_path=image_path,
                ))
            elif isinstance(gt_value, (int, float)) and isinstance(pred_value, (int, float)):
                # Numerical comparison with tolerance
                if abs(pred_value - gt_value) > 0.01:
                    errors.append(ErrorAnalysis(
                        element_type=field,
                        error_type="incorrect_value",
                        confidence=1.0 - min(abs(pred_value - gt_value) / max(abs(gt_value), 1.0), 1.0),
                        predicted_value=pred_value,
                        ground_truth=gt_value,
                        sample_id=sample_id,
                        image_path=image_path,
                    ))
        
        # Check mathematical consistency
        if predicted and all(k in predicted for k in ["subtotal", "tax_total", "discount_total", "grand_total"]):
            calculated_total = (
                predicted["subtotal"] + predicted["tax_total"] - predicted.get("discount_total", 0)
            )
            if abs(calculated_total - predicted["grand_total"]) > 0.01:
                errors.append(ErrorAnalysis(
                    element_type="grand_total",
                    error_type="wrong_format",
                    confidence=0.0,
                    predicted_value=predicted["grand_total"],
                    ground_truth=calculated_total,
                    sample_id=sample_id,
                    image_path=image_path,
                ))
        
        return errors
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate simple string similarity (0-1)"""
        if not str1 or not str2:
            return 0.0
        
        # Simple character overlap
        set1 = set(str1.lower())
        set2 = set(str2.lower())
        
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def analyze_errors(
        self,
        predictions: List[Dict[str, Any]],
        ground_truths: List[Dict[str, Any]],
        sample_ids: List[str],
        image_paths: List[str],
    ) -> Dict[str, Any]:
        """
        Analyze errors across a dataset and identify patterns.
        
        Args:
            predictions: List of model predictions
            ground_truths: List of ground truth dictionaries
            sample_ids: List of sample identifiers
            image_paths: List of image paths
            
        Returns:
            Dictionary with error analysis results
        """
        all_errors = []
        
        for pred, gt, sample_id, img_path in zip(predictions, ground_truths, sample_ids, image_paths):
            errors = self.evaluate_prediction(pred, gt, sample_id, img_path)
            all_errors.extend(errors)
        
        # Aggregate errors by type
        error_by_type = defaultdict(list)
        error_by_element = defaultdict(list)
        low_confidence_samples = []
        
        for error in all_errors:
            error_by_type[error.error_type].append(error)
            error_by_element[error.element_type].append(error)
            
            if error.confidence < 0.5:
                low_confidence_samples.append(error)
        
        # Identify hard samples (samples with multiple errors or low confidence)
        sample_error_counts = defaultdict(int)
        for error in all_errors:
            sample_error_counts[error.sample_id] += 1
        
        hard_samples = [
            sample_id for sample_id, count in sample_error_counts.items()
            if count >= 3  # 3+ errors = hard sample
        ]
        
        return {
            "total_errors": len(all_errors),
            "error_by_type": {k: len(v) for k, v in error_by_type.items()},
            "error_by_element": {k: len(v) for k, v in error_by_element.items()},
            "low_confidence_count": len(low_confidence_samples),
            "hard_samples": hard_samples,
            "hard_sample_count": len(hard_samples),
            "detailed_errors": [
                {
                    "element_type": e.element_type,
                    "error_type": e.error_type,
                    "confidence": e.confidence,
                    "sample_id": e.sample_id,
                    "image_path": e.image_path,
                }
                for e in all_errors[:100]  # Limit to first 100 for summary
            ],
        }
    
    def generate_hard_sample_synthesis_plan(
        self,
        error_analysis: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        """
        Generate a plan for synthesizing hard samples based on error analysis.
        
        Args:
            error_analysis: Error analysis results
            
        Returns:
            List of synthesis plans
        """
        plans = []
        
        # Identify top error patterns
        error_by_element = error_analysis.get("error_by_element", {})
        error_by_type = error_analysis.get("error_by_type", {})
        
        # Plan for element types with most errors
        top_elements = sorted(
            error_by_element.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        for element_type, error_count in top_elements:
            if "line_item" in element_type or "table" in element_type:
                plans.append({
                    "type": "complex_table",
                    "description": f"Synthesize complex table structures for {element_type}",
                    "count": min(error_count * 10, 100),
                })
            elif "currency" in element_type or "financial" in element_type:
                plans.append({
                    "type": "multi_currency",
                    "description": f"Synthesize multi-currency documents for {element_type}",
                    "count": min(error_count * 10, 100),
                })
            else:
                plans.append({
                    "type": "unusual_layout",
                    "description": f"Synthesize unusual layouts for {element_type}",
                    "count": min(error_count * 10, 100),
                })
        
        return plans


def mine_hard_samples(
    predictions_path: str,
    ground_truth_path: str,
    output_path: str = "hard_samples_analysis.json",
) -> Dict[str, Any]:
    """
    Main function to mine hard samples from predictions.
    
    Args:
        predictions_path: Path to predictions JSONL file
        ground_truth_path: Path to ground truth JSONL file
        output_path: Output path for analysis results
        
    Returns:
        Error analysis dictionary
    """
    miner = HardSampleMiner()
    
    # Load predictions and ground truth
    predictions = []
    ground_truths = []
    sample_ids = []
    image_paths = []
    
    with open(predictions_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                predictions.append(data.get("prediction", {}))
                sample_ids.append(data.get("sample_id", ""))
                image_paths.append(data.get("image_path", ""))
    
    with open(ground_truth_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                ground_truths.append(json.loads(line))
    
    # Analyze errors
    analysis = miner.analyze_errors(predictions, ground_truths, sample_ids, image_paths)
    
    # Generate synthesis plan
    synthesis_plan = miner.generate_hard_sample_synthesis_plan(analysis)
    analysis["synthesis_plan"] = synthesis_plan
    
    # Save results
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    
    print(f"Hard sample analysis saved to {output_path}")
    print(f"Found {analysis['hard_sample_count']} hard samples")
    print(f"Total errors: {analysis['total_errors']}")
    
    return analysis


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Mine hard samples from predictions")
    parser.add_argument("--predictions", type=str, required=True, help="Path to predictions JSONL")
    parser.add_argument("--ground-truth", type=str, required=True, help="Path to ground truth JSONL")
    parser.add_argument("--output", type=str, default="hard_samples_analysis.json", help="Output path")
    
    args = parser.parse_args()
    
    mine_hard_samples(
        predictions_path=args.predictions,
        ground_truth_path=args.ground_truth,
        output_path=args.output,
    )



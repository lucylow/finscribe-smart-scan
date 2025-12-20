#!/usr/bin/env python3
"""
Evaluate fine-tuned ERNIE model on test data.

Compares fine-tuned model predictions against ground truth and calculates
metrics like JSON formatting accuracy, field extraction accuracy, and validation compliance.
"""

import argparse
import json
from pathlib import Path
from typing import Dict, Any, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import torch
    from transformers import AutoModelForVision2Seq, AutoProcessor
    from peft import PeftModel
    from PIL import Image
except ImportError as e:
    logger.error(f"Missing required dependencies: {e}")
    logger.error("Install with: pip install transformers peft torch pillow")
    raise


def load_finetuned_model(model_path: Path, base_model_name: str = "baidu/ERNIE-4.5-8B"):
    """Load fine-tuned ERNIE model with LoRA adapters."""
    logger.info(f"Loading base model: {base_model_name}")
    base_model = AutoModelForVision2Seq.from_pretrained(
        base_model_name,
        trust_remote_code=True,
        torch_dtype=torch.float16
    )
    
    logger.info(f"Loading LoRA adapters from: {model_path}")
    model = PeftModel.from_pretrained(base_model, str(model_path))
    model.eval()
    
    processor = AutoProcessor.from_pretrained(base_model_name, trust_remote_code=True)
    
    return model, processor


def evaluate_sample(
    model,
    processor,
    image_path: Path,
    instruction: str,
    ground_truth: Dict[str, Any]
) -> Dict[str, Any]:
    """Evaluate a single sample."""
    # Load image
    image = Image.open(image_path)
    
    # Format prompt
    prompt = f"<image>\n{instruction}"
    
    # Generate prediction
    inputs = processor(images=[image], text=prompt, return_tensors="pt")
    
    with torch.no_grad():
        outputs = model.generate(**inputs, max_length=2048)
    
    prediction_text = processor.decode(outputs[0], skip_special_tokens=True)
    
    # Parse prediction
    try:
        prediction_json = json.loads(prediction_text)
    except json.JSONDecodeError:
        # Try to extract JSON from markdown
        import re
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', prediction_text, re.DOTALL)
        if json_match:
            prediction_json = json.loads(json_match.group(1))
        else:
            prediction_json = {"error": "Could not parse JSON"}
    
    # Calculate metrics
    metrics = {
        "json_valid": isinstance(prediction_json, dict) and "error" not in prediction_json,
        "field_accuracy": calculate_field_accuracy(prediction_json, ground_truth),
        "validation_compliance": check_validation_compliance(prediction_json, ground_truth)
    }
    
    return {
        "prediction": prediction_json,
        "ground_truth": ground_truth,
        "metrics": metrics
    }


def calculate_field_accuracy(pred: Dict[str, Any], gt: Dict[str, Any]) -> float:
    """Calculate field-level accuracy."""
    pred_data = pred.get("structured_data", {})
    gt_data = gt.get("structured_data", {})
    
    if not pred_data or not gt_data:
        return 0.0
    
    # Compare key fields
    fields_to_check = [
        "vendor_block.name",
        "client_info.invoice_number",
        "financial_summary.grand_total"
    ]
    
    correct = 0
    total = 0
    
    for field_path in fields_to_check:
        parts = field_path.split(".")
        pred_value = pred_data
        gt_value = gt_data
        
        try:
            for part in parts:
                pred_value = pred_value.get(part, {})
                gt_value = gt_value.get(part, {})
            
            total += 1
            if str(pred_value).strip().lower() == str(gt_value).strip().lower():
                correct += 1
        except (AttributeError, KeyError):
            total += 1
    
    return correct / total if total > 0 else 0.0


def check_validation_compliance(pred: Dict[str, Any], gt: Dict[str, Any]) -> bool:
    """Check if prediction follows validation rules."""
    pred_validation = pred.get("validation_summary", {})
    gt_validation = gt.get("validation_summary", {})
    
    # Check if math_verified matches
    pred_math = pred_validation.get("math_verified", False)
    gt_math = gt_validation.get("math_verified", False)
    
    return pred_math == gt_math


def evaluate_dataset(
    model,
    processor,
    test_data_path: Path
) -> Dict[str, Any]:
    """Evaluate model on entire test dataset."""
    # Load test data
    test_samples = []
    with open(test_data_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                test_samples.append(json.loads(line))
    
    logger.info(f"Evaluating on {len(test_samples)} samples")
    
    results = []
    for i, sample in enumerate(test_samples):
        if i % 10 == 0:
            logger.info(f"Processing sample {i+1}/{len(test_samples)}")
        
        image_path = Path(sample["image"])
        instruction = sample["conversations"][0]["content"]
        ground_truth = json.loads(sample["conversations"][1]["content"])
        
        result = evaluate_sample(model, processor, image_path, instruction, ground_truth)
        results.append(result)
    
    # Aggregate metrics
    json_valid_rate = sum(1 for r in results if r["metrics"]["json_valid"]) / len(results)
    avg_field_accuracy = sum(r["metrics"]["field_accuracy"] for r in results) / len(results)
    validation_compliance_rate = sum(1 for r in results if r["metrics"]["validation_compliance"]) / len(results)
    
    return {
        "num_samples": len(results),
        "json_valid_rate": json_valid_rate,
        "avg_field_accuracy": avg_field_accuracy,
        "validation_compliance_rate": validation_compliance_rate,
        "detailed_results": results
    }


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate fine-tuned ERNIE model"
    )
    parser.add_argument(
        "--model",
        type=Path,
        required=True,
        help="Path to fine-tuned model directory"
    )
    parser.add_argument(
        "--base-model",
        type=str,
        default="baidu/ERNIE-4.5-8B",
        help="Base model name (default: baidu/ERNIE-4.5-8B)"
    )
    parser.add_argument(
        "--test-data",
        type=Path,
        required=True,
        help="Path to test data JSONL file"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("evaluation_results.json"),
        help="Output file for evaluation results"
    )
    
    args = parser.parse_args()
    
    # Load model
    model, processor = load_finetuned_model(args.model, args.base_model)
    
    # Evaluate
    logger.info("Starting evaluation...")
    results = evaluate_dataset(model, processor, args.test_data)
    
    # Save results
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("\n" + "="*50)
    print("Evaluation Results")
    print("="*50)
    print(f"Number of samples: {results['num_samples']}")
    print(f"JSON Valid Rate: {results['json_valid_rate']:.2%}")
    print(f"Average Field Accuracy: {results['avg_field_accuracy']:.2%}")
    print(f"Validation Compliance Rate: {results['validation_compliance_rate']:.2%}")
    print(f"\nDetailed results saved to: {args.output}")


if __name__ == "__main__":
    main()


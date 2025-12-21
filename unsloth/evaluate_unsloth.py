"""
Evaluation Script: Baseline vs Unsloth Fine-tuned Model

Compares extraction accuracy between:
1. Baseline model (pre-trained, no fine-tuning)
2. Unsloth fine-tuned model

Metrics:
- JSON structure accuracy
- Field extraction accuracy
- Arithmetic validation accuracy
"""
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple
import torch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import Unsloth
try:
    from unsloth import FastLanguageModel
    UNSLOTH_AVAILABLE = True
except ImportError:
    logger.error("Unsloth not available")
    UNSLOTH_AVAILABLE = False

try:
    from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False


class ModelEvaluator:
    """Evaluator for comparing baseline vs fine-tuned models."""
    
    def __init__(self, baseline_model_name: str, fine_tuned_model_dir: str):
        self.baseline_model_name = baseline_model_name
        self.fine_tuned_model_dir = fine_tuned_model_dir
        self.baseline_model = None
        self.baseline_tokenizer = None
        self.fine_tuned_model = None
        self.fine_tuned_tokenizer = None
        
    def load_baseline(self):
        """Load baseline (pre-trained) model."""
        logger.info(f"Loading baseline model: {self.baseline_model_name}")
        try:
            if UNSLOTH_AVAILABLE:
                self.fine_tuned_model, self.fine_tuned_tokenizer = FastLanguageModel.from_pretrained(
                    model_name=self.baseline_model_name,
                    max_seq_length=2048,
                    dtype=None,
                    load_in_4bit=True,
                )
                FastLanguageModel.for_inference(self.fine_tuned_model)
            else:
                self.baseline_tokenizer = AutoTokenizer.from_pretrained(self.baseline_model_name)
                self.baseline_model = AutoModelForCausalLM.from_pretrained(
                    self.baseline_model_name,
                    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                ).to("cuda" if torch.cuda.is_available() else "cpu")
                self.baseline_model.eval()
            logger.info("Baseline model loaded")
        except Exception as e:
            logger.error(f"Failed to load baseline model: {e}")
            raise
    
    def load_fine_tuned(self):
        """Load fine-tuned model."""
        logger.info(f"Loading fine-tuned model: {self.fine_tuned_model_dir}")
        try:
            if UNSLOTH_AVAILABLE:
                self.fine_tuned_model, self.fine_tuned_tokenizer = FastLanguageModel.from_pretrained(
                    model_name=self.fine_tuned_model_dir,
                    max_seq_length=2048,
                    dtype=None,
                    load_in_4bit=True,
                )
                FastLanguageModel.for_inference(self.fine_tuned_model)
            else:
                self.fine_tuned_tokenizer = AutoTokenizer.from_pretrained(self.fine_tuned_model_dir)
                self.fine_tuned_model = AutoModelForCausalLM.from_pretrained(
                    self.fine_tuned_model_dir,
                    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                ).to("cuda" if torch.cuda.is_available() else "cpu")
                self.fine_tuned_model.eval()
            logger.info("Fine-tuned model loaded")
        except Exception as e:
            logger.error(f"Failed to load fine-tuned model: {e}")
            raise
    
    def infer(self, ocr_text: str, use_fine_tuned: bool = False) -> Dict[str, Any]:
        """Run inference on OCR text."""
        if use_fine_tuned:
            model = self.fine_tuned_model
            tokenizer = self.fine_tuned_tokenizer
        else:
            model = self.baseline_model
            tokenizer = self.baseline_tokenizer
        
        if model is None or tokenizer is None:
            return {"_error": "Model not loaded"}
        
        prompt = f"OCR_TEXT:\n{ocr_text}\n\nExtract structured JSON with vendor, invoice_number, dates, " \
                 f"line_items (desc, qty, unit_price, line_total), and financial_summary. " \
                 f"Output only valid JSON without any explanation."
        
        try:
            inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)
            if torch.cuda.is_available():
                inputs = {k: v.to("cuda") for k, v in inputs.items()}
            
            gen_config = GenerationConfig(
                temperature=0.0,
                max_new_tokens=512,
                pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
            )
            
            with torch.no_grad():
                outputs = model.generate(**inputs, generation_config=gen_config)
            
            decoded = tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extract JSON
            json_start = decoded.find("{")
            if json_start != -1:
                json_text = decoded[json_start:]
                try:
                    return json.loads(json_text)
                except:
                    return {"_parse_error": True, "_raw": decoded}
            else:
                return {"_parse_error": True, "_raw": decoded}
        except Exception as e:
            return {"_error": str(e)}
    
    def evaluate_field(self, predicted: Dict[str, Any], ground_truth: Dict[str, Any], field_path: str) -> bool:
        """Check if a specific field matches."""
        def get_nested_value(d: Dict, path: str):
            keys = path.split(".")
            value = d
            for key in keys:
                if isinstance(value, dict):
                    value = value.get(key)
                else:
                    return None
            return value
        
        pred_value = get_nested_value(predicted, field_path)
        gt_value = get_nested_value(ground_truth, field_path)
        
        # Normalize for comparison
        if isinstance(pred_value, str):
            pred_value = pred_value.strip().lower()
        if isinstance(gt_value, str):
            gt_value = gt_value.strip().lower()
        
        return pred_value == gt_value
    
    def evaluate_sample(self, ocr_text: str, ground_truth: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate a single sample."""
        baseline_result = self.infer(ocr_text, use_fine_tuned=False)
        fine_tuned_result = self.infer(ocr_text, use_fine_tuned=True)
        
        # Key fields to evaluate
        key_fields = [
            "vendor.name",
            "invoice_number",
            "invoice_date",
            "financial_summary.grand_total",
        ]
        
        baseline_correct = sum(
            self.evaluate_field(baseline_result, ground_truth, field) 
            for field in key_fields
        )
        fine_tuned_correct = sum(
            self.evaluate_field(fine_tuned_result, ground_truth, field)
            for field in key_fields
        )
        
        return {
            "baseline": {
                "result": baseline_result,
                "correct_fields": baseline_correct,
                "total_fields": len(key_fields),
                "accuracy": baseline_correct / len(key_fields) if key_fields else 0.0,
            },
            "fine_tuned": {
                "result": fine_tuned_result,
                "correct_fields": fine_tuned_correct,
                "total_fields": len(key_fields),
                "accuracy": fine_tuned_correct / len(key_fields) if key_fields else 0.0,
            },
            "improvement": fine_tuned_correct - baseline_correct,
        }
    
    def evaluate_dataset(self, test_file: Path) -> Dict[str, Any]:
        """Evaluate on a test dataset."""
        # Load test data
        test_samples = []
        with open(test_file, "r") as f:
            for line in f:
                if line.strip():
                    test_samples.append(json.loads(line))
        
        logger.info(f"Evaluating on {len(test_samples)} samples...")
        
        results = []
        for i, sample in enumerate(test_samples):
            logger.info(f"Evaluating sample {i+1}/{len(test_samples)}...")
            
            ocr_text = sample.get("input", sample.get("prompt", "")).replace("OCR_TEXT:\n", "").strip()
            ground_truth = json.loads(sample.get("output", sample.get("completion", "{}")))
            
            result = self.evaluate_sample(ocr_text, ground_truth)
            result["sample_id"] = i
            results.append(result)
        
        # Aggregate metrics
        baseline_accuracies = [r["baseline"]["accuracy"] for r in results]
        fine_tuned_accuracies = [r["fine_tuned"]["accuracy"] for r in results]
        
        avg_baseline = sum(baseline_accuracies) / len(baseline_accuracies) if baseline_accuracies else 0.0
        avg_fine_tuned = sum(fine_tuned_accuracies) / len(fine_tuned_accuracies) if fine_tuned_accuracies else 0.0
        
        return {
            "num_samples": len(results),
            "baseline_avg_accuracy": avg_baseline,
            "fine_tuned_avg_accuracy": avg_fine_tuned,
            "improvement": avg_fine_tuned - avg_baseline,
            "improvement_percent": ((avg_fine_tuned - avg_baseline) / avg_baseline * 100) if avg_baseline > 0 else 0.0,
            "detailed_results": results,
        }


def main():
    parser = argparse.ArgumentParser(description="Evaluate baseline vs Unsloth fine-tuned model")
    parser.add_argument("--baseline_model", type=str, 
                       default="unsloth/llama-3.1-8b-unsloth-bnb-4bit",
                       help="Baseline pre-trained model name")
    parser.add_argument("--fine_tuned_model", type=str,
                       default="./models/unsloth-finscribe",
                       help="Fine-tuned model directory")
    parser.add_argument("--test_data", type=str,
                       default="./data/unsloth_val.jsonl",
                       help="Test dataset JSONL file")
    parser.add_argument("--output", type=str,
                       default="./evaluation/unsloth_evaluation.json",
                       help="Output evaluation results file")
    
    args = parser.parse_args()
    
    evaluator = ModelEvaluator(args.baseline_model, args.fine_tuned_model)
    
    # Load models
    logger.info("Loading models...")
    evaluator.load_baseline()
    evaluator.load_fine_tuned()
    
    # Evaluate
    logger.info("Running evaluation...")
    results = evaluator.evaluate_dataset(Path(args.test_data))
    
    # Save results
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("\n" + "=" * 80)
    print("EVALUATION RESULTS")
    print("=" * 80)
    print(f"Number of samples: {results['num_samples']}")
    print(f"Baseline average accuracy: {results['baseline_avg_accuracy']:.2%}")
    print(f"Fine-tuned average accuracy: {results['fine_tuned_avg_accuracy']:.2%}")
    print(f"Improvement: {results['improvement']:.2%} ({results['improvement_percent']:.1f}% relative)")
    print("=" * 80)
    print(f"\nDetailed results saved to: {output_path}")


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""
Example: Evaluate fine-tuned model on test dataset
"""

import json
from pathlib import Path
from PIL import Image
from transformers import AutoModelForCausalLM, AutoProcessor

from finscribe.eval.field_accuracy import field_accuracy
from finscribe.eval.validation import validate_document


def evaluate_sample(image_path: Path, gt_path: Path, model_path: Path):
    """
    Evaluate a single sample.
    
    Args:
        image_path: Path to invoice image
        gt_path: Path to ground truth JSON
        model_path: Path to fine-tuned model
    """
    # Load model
    model = AutoModelForCausalLM.from_pretrained(
        str(model_path),
        trust_remote_code=True,
        torch_dtype="bfloat16",
        device_map="auto",
    )
    processor = AutoProcessor.from_pretrained(
        str(model_path),
        trust_remote_code=True,
    )
    
    # Load image and ground truth
    image = Image.open(image_path).convert("RGB")
    with open(gt_path) as f:
        gt = json.load(f)
    
    # Run inference
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": "OCR:"},
            ],
        }
    ]
    
    inputs = processor(text=[messages], images=[image], return_tensors="pt")
    inputs = {k: v.to(model.device) for k, v in inputs.items()}
    
    outputs = model.generate(**inputs, max_new_tokens=512)
    response = processor.decode(outputs[0], skip_special_tokens=True)
    
    # Parse response
    try:
        pred = json.loads(response)
    except:
        pred = {"raw": response}
    
    # Evaluate
    accuracy = field_accuracy(pred, gt)
    validation = validate_document(pred)
    
    return {
        "accuracy": accuracy,
        "validation": validation,
        "prediction": pred,
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--ground-truth", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", help="Output JSON file")
    
    args = parser.parse_args()
    
    results = evaluate_sample(
        Path(args.image),
        Path(args.ground_truth),
        Path(args.model),
    )
    
    print(f"Field Accuracy: {results['accuracy']:.2%}")
    print(f"Validation: {'PASS' if results['validation']['valid'] else 'FAIL'}")
    if results['validation']['errors']:
        print("Errors:", results['validation']['errors'])
    
    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)


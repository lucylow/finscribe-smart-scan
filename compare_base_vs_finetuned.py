#!/usr/bin/env python3
"""
Demo comparison script for judging
Shows side-by-side comparison of base vs fine-tuned PaddleOCR-VL
"""

import argparse
import json
from pathlib import Path
from PIL import Image

from transformers import AutoModelForCausalLM, AutoProcessor


def run_base_paddleocr(image_path: Path) -> dict:
    """
    Runs base PaddleOCR-VL on an image.
    
    Args:
        image_path: Path to invoice image
        
    Returns:
        Dictionary with raw output
    """
    model = AutoModelForCausalLM.from_pretrained(
        "PaddlePaddle/PaddleOCR-VL",
        trust_remote_code=True,
        torch_dtype="bfloat16",
        device_map="auto",
    )
    processor = AutoProcessor.from_pretrained(
        "PaddlePaddle/PaddleOCR-VL",
        trust_remote_code=True,
    )
    
    image = Image.open(image_path).convert("RGB")
    
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
    
    return {
        "raw_text": response,
        "model": "base",
    }


def run_finetuned(image_path: Path, model_path: Path) -> dict:
    """
    Runs fine-tuned model on an image.
    
    Args:
        image_path: Path to invoice image
        model_path: Path to fine-tuned model
        
    Returns:
        Dictionary with structured output
    """
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
    
    image = Image.open(image_path).convert("RGB")
    
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
    
    # Try to parse as JSON
    try:
        structured_json = json.loads(response)
    except:
        structured_json = {"raw": response}
    
    # Validate
    from finscribe.eval.validation import validate_document
    
    validation = validate_document(structured_json)
    
    return {
        "structured_json": structured_json,
        "validation": validation,
        "model": "fine-tuned",
    }


def main():
    parser = argparse.ArgumentParser(
        description="Compare base vs fine-tuned PaddleOCR-VL"
    )
    parser.add_argument(
        "--image",
        type=str,
        required=True,
        help="Path to invoice image",
    )
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        help="Path to fine-tuned model",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output JSON file for results",
    )
    
    args = parser.parse_args()
    
    image_path = Path(args.image)
    model_path = Path(args.model)
    
    print("=" * 80)
    print("BASE PADDLEOCR-VL OUTPUT:")
    print("=" * 80)
    base_result = run_base_paddleocr(image_path)
    print(base_result["raw_text"])
    print()
    
    print("=" * 80)
    print("FINETUNED OUTPUT:")
    print("=" * 80)
    fine_result = run_finetuned(image_path, model_path)
    print(json.dumps(fine_result["structured_json"], indent=2))
    print()
    
    print("=" * 80)
    print("VALIDATION:")
    print("=" * 80)
    print(json.dumps(fine_result["validation"], indent=2))
    
    if args.output:
        results = {
            "base": base_result,
            "fine_tuned": fine_result,
        }
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()


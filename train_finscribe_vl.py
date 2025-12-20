#!/usr/bin/env python3
"""
End-to-end training script for FinScribe PaddleOCR-VL fine-tuning
"""

import argparse
import json
from pathlib import Path
import torch
from transformers import Trainer, TrainingArguments
from datasets import Dataset

from finscribe.training.model import load_model
from finscribe.training.collate import collate_fn
from finscribe.training.lora import apply_lora
from finscribe.data.build_dataset import build_dataset, build_dataset_from_manifest


def main():
    parser = argparse.ArgumentParser(
        description="Fine-tune PaddleOCR-VL for financial document intelligence"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        required=True,
        help="Directory containing crops/ and annotations/ subdirectories",
    )
    parser.add_argument(
        "--manifest",
        type=str,
        help="Path to training manifest JSON (alternative to --data-dir)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./finetuned_finscribe_vl",
        help="Output directory for fine-tuned model",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=4,
        help="Number of training epochs",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=4,
        help="Per-device batch size",
    )
    parser.add_argument(
        "--gradient-accumulation-steps",
        type=int,
        default=4,
        help="Gradient accumulation steps",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=2e-5,
        help="Learning rate",
    )
    parser.add_argument(
        "--use-lora",
        action="store_true",
        help="Use LoRA for memory-efficient training",
    )
    parser.add_argument(
        "--lora-r",
        type=int,
        default=16,
        help="LoRA rank (if --use-lora)",
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default="PaddlePaddle/PaddleOCR-VL",
        help="Base model name",
    )
    parser.add_argument(
        "--save-steps",
        type=int,
        default=500,
        help="Save checkpoint every N steps",
    )
    parser.add_argument(
        "--logging-steps",
        type=int,
        default=10,
        help="Log metrics every N steps",
    )
    
    args = parser.parse_args()
    
    # Load model and processor
    print("Loading model and processor...")
    model, processor = load_model(
        model_name=args.model_name,
        use_flash_attention=True,
    )
    
    # Apply LoRA if requested
    if args.use_lora:
        print("Applying LoRA...")
        model = apply_lora(model, r=args.lora_r)
        print(f"LoRA parameters: {model.num_parameters()}")
    
    # Build dataset
    print("Building dataset...")
    if args.manifest:
        dataset = build_dataset_from_manifest(Path(args.manifest))
    else:
        data_dir = Path(args.data_dir)
        crops_dir = data_dir / "crops"
        annotations_dir = data_dir / "annotations"
        
        if not crops_dir.exists() or not annotations_dir.exists():
            raise ValueError(
                f"Data directory must contain 'crops/' and 'annotations/' subdirectories"
            )
        
        dataset = build_dataset(crops_dir, annotations_dir)
    
    print(f"Dataset size: {len(dataset)} samples")
    
    # Convert to HuggingFace Dataset
    hf_dataset = Dataset.from_list(dataset)
    
    # Training arguments
    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        warmup_ratio=0.1,
        bf16=True,  # Use bfloat16 for mixed precision
        logging_steps=args.logging_steps,
        save_steps=args.save_steps,
        save_total_limit=2,  # Keep only last 2 checkpoints
        remove_unused_columns=False,
        dataloader_num_workers=4,
        report_to="none",  # Disable wandb/tensorboard by default
        load_best_model_at_end=False,
    )
    
    # Create data collator
    def data_collator(batch):
        return collate_fn(batch, processor)
    
    # Initialize trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=hf_dataset,
        data_collator=data_collator,
    )
    
    # Train
    print("Starting training...")
    trainer.train()
    
    # Save final model
    print(f"Saving model to {args.output_dir}...")
    trainer.save_model()
    processor.save_pretrained(args.output_dir)
    
    # Save training config
    config = {
        "model_name": args.model_name,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "gradient_accumulation_steps": args.gradient_accumulation_steps,
        "learning_rate": args.learning_rate,
        "use_lora": args.use_lora,
        "lora_r": args.lora_r if args.use_lora else None,
        "dataset_size": len(dataset),
    }
    
    with open(Path(args.output_dir) / "training_config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    print("Training complete!")


if __name__ == "__main__":
    main()


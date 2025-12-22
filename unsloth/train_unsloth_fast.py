"""
Unsloth Fine-tuning Script with FastLanguageModel

Train Unsloth models using FastLanguageModel for efficient fine-tuning with LoRA/QLoRA.
This script uses the actual Unsloth framework for 2x faster training and 70% less VRAM.

Usage:
    python unsloth/train_unsloth_fast.py \
        --model_name unsloth/llama-3.1-8b-unsloth-bnb-4bit \
        --train_data data/unsloth_train.jsonl \
        --val_data data/unsloth_val.jsonl \
        --output_dir models/unsloth-finscribe \
        --num_epochs 3 \
        --batch_size 4 \
        --learning_rate 2e-5
"""
import os
import sys
import logging
import argparse
from pathlib import Path
from datasets import load_dataset
import torch

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import Unsloth
try:
    from unsloth import FastLanguageModel
    from trl import SFTTrainer
    UNSLOTH_AVAILABLE = True
except ImportError:
    logger.error("Unsloth not available. Install with: pip install 'unsloth[cu118] @ git+https://github.com/unslothai/unsloth.git'")
    UNSLOTH_AVAILABLE = False
    sys.exit(1)


def format_dataset(example):
    """
    Format dataset for instruction tuning.
    
    Expected input format:
    {
        "input": "OCR_TEXT:\n...",
        "output": "{\"vendor\": {...}, ...}"
    }
    
    Or:
    {
        "prompt": "OCR_TEXT:\n...",
        "completion": "{\"vendor\": {...}, ...}"
    }
    """
    # Support both formats
    if "input" in example and "output" in example:
        prompt = example["input"]
        completion = example["output"]
    elif "prompt" in example and "completion" in example:
        prompt = example["prompt"]
        completion = example["completion"]
    else:
        raise ValueError(f"Dataset must have 'input'/'output' or 'prompt'/'completion' fields. Got: {example.keys()}")
    
    # Format as instruction-response pair
    # Unsloth expects: instruction + response
    text = f"{prompt}{completion}"
    
    return {"text": text}


def main():
    """Main training function."""
    parser = argparse.ArgumentParser(description="Fine-tune Unsloth model for invoice extraction")
    parser.add_argument("--model_name", type=str, 
                       default=os.getenv("UNSLOTH_MODEL_NAME", "unsloth/llama-3.1-8b-unsloth-bnb-4bit"),
                       help="Pre-trained model name from HuggingFace")
    parser.add_argument("--train_data", type=str,
                       default=os.getenv("TRAIN_JSONL", "./data/unsloth_train.jsonl"),
                       help="Path to training JSONL file")
    parser.add_argument("--val_data", type=str,
                       default=os.getenv("VAL_JSONL", "./data/unsloth_val.jsonl"),
                       help="Path to validation JSONL file (optional)")
    parser.add_argument("--output_dir", type=str,
                       default=os.getenv("OUTPUT_DIR", "./models/unsloth-finscribe"),
                       help="Output directory for fine-tuned model")
    parser.add_argument("--num_epochs", type=int, default=int(os.getenv("NUM_EPOCHS", "3")),
                       help="Number of training epochs")
    parser.add_argument("--batch_size", type=int, default=int(os.getenv("BATCH_SIZE", "4")),
                       help="Per-device batch size")
    parser.add_argument("--gradient_accumulation_steps", type=int, 
                       default=int(os.getenv("GRADIENT_ACCUMULATION_STEPS", "4")),
                       help="Gradient accumulation steps")
    parser.add_argument("--learning_rate", type=float, 
                       default=float(os.getenv("LEARNING_RATE", "2e-5")),
                       help="Learning rate")
    parser.add_argument("--max_seq_length", type=int, 
                       default=int(os.getenv("MAX_SEQ_LENGTH", "2048")),
                       help="Maximum sequence length")
    parser.add_argument("--lora_r", type=int, default=16,
                       help="LoRA rank")
    parser.add_argument("--lora_alpha", type=int, default=32,
                       help="LoRA alpha (typically 2x rank)")
    parser.add_argument("--load_in_4bit", action="store_true", default=True,
                       help="Use 4-bit quantization (QLoRA)")
    
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("UNSLOTH FINE-TUNING WITH FastLanguageModel")
    logger.info("=" * 80)
    logger.info(f"Model: {args.model_name}")
    logger.info(f"Train file: {args.train_data}")
    logger.info(f"Val file: {args.val_data}")
    logger.info(f"Output dir: {args.output_dir}")
    logger.info(f"Epochs: {args.num_epochs}")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info(f"Gradient accumulation: {args.gradient_accumulation_steps}")
    logger.info(f"Learning rate: {args.learning_rate}")
    logger.info(f"LoRA r={args.lora_r}, alpha={args.lora_alpha}")
    logger.info(f"4-bit quantization: {args.load_in_4bit}")
    logger.info(f"Device: {'cuda' if torch.cuda.is_available() else 'cpu'}")
    logger.info("=" * 80)
    
    # Validate files
    if not os.path.exists(args.train_data):
        raise FileNotFoundError(f"Training file not found: {args.train_data}")
    
    if args.val_data and not os.path.exists(args.val_data):
        logger.warning(f"Validation file not found: {args.val_data}, proceeding without validation")
        args.val_data = None
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Load model and tokenizer using Unsloth FastLanguageModel
    logger.info(f"Loading model {args.model_name} with Unsloth...")
    try:
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=args.model_name,
            max_seq_length=args.max_seq_length,
            dtype=None,  # Auto-detect
            load_in_4bit=args.load_in_4bit,
        )
        logger.info("Model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load model: {str(e)}", exc_info=True)
        raise
    
    # Set pad token if needed
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id
    
    # Apply LoRA
    logger.info(f"Applying LoRA (r={args.lora_r}, alpha={args.lora_alpha})...")
    model = FastLanguageModel.get_peft_model(
        model,
        r=args.lora_r,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                       "gate_proj", "up_proj", "down_proj"],
        lora_alpha=args.lora_alpha,
        lora_dropout=0.05,
        bias="none",
        use_gradient_checkpointing=True,  # Saves VRAM
        random_state=3407,
    )
    logger.info("LoRA applied successfully")
    
    # Load datasets
    logger.info(f"Loading training dataset from {args.train_data}...")
    try:
        train_dataset = load_dataset("json", data_files={"train": args.train_data}, split="train")
        logger.info(f"Loaded {len(train_dataset)} training examples")
        
        # Format dataset
        train_dataset = train_dataset.map(format_dataset, remove_columns=train_dataset.column_names)
    except Exception as e:
        logger.error(f"Failed to load training dataset: {str(e)}", exc_info=True)
        raise
    
    eval_dataset = None
    if args.val_data:
        logger.info(f"Loading validation dataset from {args.val_data}...")
        try:
            eval_dataset = load_dataset("json", data_files={"val": args.val_data}, split="train")
            logger.info(f"Loaded {len(eval_dataset)} validation examples")
            eval_dataset = eval_dataset.map(format_dataset, remove_columns=eval_dataset.column_names)
        except Exception as e:
            logger.warning(f"Failed to load validation dataset: {str(e)}, continuing without validation")
            eval_dataset = None
    
    # Configure training arguments
    from trl import SFTConfig
    
    training_args = SFTConfig(
        output_dir=args.output_dir,
        num_train_epochs=args.num_epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        logging_steps=10,
        save_steps=500,
        save_total_limit=3,
        eval_steps=500 if eval_dataset else None,
        evaluation_strategy="steps" if eval_dataset else "no",
        fp16=torch.cuda.is_available() and not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        warmup_steps=100,
        report_to="none",
        optim="adamw_torch",
        max_seq_length=args.max_seq_length,
    )
    
    # Create trainer
    logger.info("Creating SFTTrainer...")
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        dataset_text_field="text",
        max_seq_length=args.max_seq_length,
        args=training_args,
    )
    
    # Train
    logger.info("Starting training...")
    try:
        train_result = trainer.train()
        logger.info("Training completed successfully!")
        logger.info(f"Training loss: {train_result.training_loss}")
        
        # Save model
        logger.info(f"Saving model to {args.output_dir}...")
        model.save_pretrained(args.output_dir)
        tokenizer.save_pretrained(args.output_dir)
        
        logger.info("=" * 80)
        logger.info("TRAINING COMPLETE")
        logger.info(f"Model saved to: {args.output_dir}")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Training failed: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    main()


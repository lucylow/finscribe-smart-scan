"""
Unsloth Fine-tuning Script

Train Unsloth models using LoRA/QLoRA for structured JSON extraction from OCR text.
Supports instruction tuning format (prompt -> completion).
"""
import os
import sys
import logging
from pathlib import Path
from datasets import load_dataset
from transformers import AutoTokenizer, TrainingArguments
from trl import SFTTrainer, SFTConfig
import torch

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main training function."""
    # Configuration - can be overridden via environment variables
    MODEL_NAME = os.getenv("MODEL_NAME", "unsloth/Mistral-7B-Instruct-v0.2-bnb-4bit")
    TRAIN_JSONL = os.getenv("TRAIN_JSONL", "./data/unsloth_train.jsonl")
    VAL_JSONL = os.getenv("VAL_JSONL", "./data/unsloth_val.jsonl")
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./models/unsloth-finscribe")
    NUM_EPOCHS = int(os.getenv("NUM_EPOCHS", "3"))
    BATCH_SIZE = int(os.getenv("BATCH_SIZE", "1"))
    GRADIENT_ACCUMULATION_STEPS = int(os.getenv("GRADIENT_ACCUMULATION_STEPS", "8"))
    LEARNING_RATE = float(os.getenv("LEARNING_RATE", "2e-5"))
    USE_LORA = os.getenv("USE_LORA", "true").lower() == "true"
    USE_QLORA = os.getenv("USE_QLORA", "false").lower() == "true"
    MAX_SEQ_LENGTH = int(os.getenv("MAX_SEQ_LENGTH", "2048"))
    
    logger.info("=" * 80)
    logger.info("UNSLOTH FINE-TUNING SCRIPT")
    logger.info("=" * 80)
    logger.info(f"Model: {MODEL_NAME}")
    logger.info(f"Train file: {TRAIN_JSONL}")
    logger.info(f"Val file: {VAL_JSONL}")
    logger.info(f"Output dir: {OUTPUT_DIR}")
    logger.info(f"Epochs: {NUM_EPOCHS}")
    logger.info(f"Batch size: {BATCH_SIZE}")
    logger.info(f"Gradient accumulation: {GRADIENT_ACCUMULATION_STEPS}")
    logger.info(f"Learning rate: {LEARNING_RATE}")
    logger.info(f"LoRA: {USE_LORA}, QLoRA: {USE_QLORA}")
    logger.info(f"Device: {'cuda' if torch.cuda.is_available() else 'cpu'}")
    logger.info("=" * 80)
    
    # Validate files exist
    if not os.path.exists(TRAIN_JSONL):
        raise FileNotFoundError(f"Training file not found: {TRAIN_JSONL}")
    if VAL_JSONL and not os.path.exists(VAL_JSONL):
        logger.warning(f"Validation file not found: {VAL_JSONL}, proceeding without validation")
        VAL_JSONL = None
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Load tokenizer
    logger.info(f"Loading tokenizer from {MODEL_NAME}...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True, use_fast=True)
        
        # Set pad token if not set
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
            tokenizer.pad_token_id = tokenizer.eos_token_id
            
    except Exception as e:
        logger.error(f"Failed to load tokenizer: {str(e)}")
        raise
    
    # Load datasets
    logger.info(f"Loading training dataset from {TRAIN_JSONL}...")
    try:
        train_dataset = load_dataset("json", data_files={"train": TRAIN_JSONL}, split="train")
        logger.info(f"Loaded {len(train_dataset)} training examples")
    except Exception as e:
        logger.error(f"Failed to load training dataset: {str(e)}")
        raise
    
    eval_dataset = None
    if VAL_JSONL:
        logger.info(f"Loading validation dataset from {VAL_JSONL}...")
        try:
            eval_dataset = load_dataset("json", data_files={"val": VAL_JSONL}, split="train")
            logger.info(f"Loaded {len(eval_dataset)} validation examples")
        except Exception as e:
            logger.warning(f"Failed to load validation dataset: {str(e)}, continuing without validation")
            eval_dataset = None
    
    # Preprocess function to format data
    def format_prompt(example):
        """Format prompt and completion into instruction format."""
        prompt = example.get("prompt", "")
        completion = example.get("completion", "")
        
        # Combine prompt and completion for training
        # Format: <prompt><completion><eos>
        text = prompt + completion
        
        return {"text": text}
    
    # Apply formatting
    logger.info("Formatting training dataset...")
    train_dataset = train_dataset.map(format_prompt, remove_columns=train_dataset.column_names)
    
    if eval_dataset:
        logger.info("Formatting validation dataset...")
        eval_dataset = eval_dataset.map(format_prompt, remove_columns=eval_dataset.column_names)
    
    # Configure training
    logger.info("Configuring training arguments...")
    
    # Use SFTConfig from TRL (which Unsloth supports)
    training_args = SFTConfig(
        output_dir=OUTPUT_DIR,
        num_train_epochs=NUM_EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
        learning_rate=LEARNING_RATE,
        max_seq_length=MAX_SEQ_LENGTH,
        logging_steps=100,
        save_steps=500,
        save_total_limit=3,
        eval_steps=500 if eval_dataset else None,
        evaluation_strategy="steps" if eval_dataset else "no",
        fp16=torch.cuda.is_available(),
        bf16=False,  # Set to True if using bf16 (A100, H100)
        warmup_steps=100,
        report_to="none",  # Set to "tensorboard" if you want TensorBoard logs
        # LoRA configuration
        use_lora=USE_LORA,
        lora_r=16 if USE_LORA else None,
        lora_alpha=32 if USE_LORA else None,
        lora_dropout=0.05 if USE_LORA else None,
        # QLoRA configuration (requires bitsandbytes)
        load_in_4bit=USE_QLORA,
        load_in_8bit=False,
    )
    
    # Create trainer
    logger.info("Creating SFTTrainer...")
    trainer = SFTTrainer(
        model_name_or_path=MODEL_NAME,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        tokenizer=tokenizer,
        args=training_args,
        dataset_text_field="text",
        max_seq_length=MAX_SEQ_LENGTH,
        packing=False,  # Set to True if you want packing (more efficient but can be slower)
    )
    
    # Train
    logger.info("Starting training...")
    try:
        train_result = trainer.train()
        logger.info("Training completed successfully!")
        logger.info(f"Training loss: {train_result.training_loss}")
        
        # Save model
        logger.info(f"Saving model to {OUTPUT_DIR}...")
        trainer.save_model(OUTPUT_DIR)
        tokenizer.save_pretrained(OUTPUT_DIR)
        
        logger.info("=" * 80)
        logger.info("TRAINING COMPLETE")
        logger.info(f"Model saved to: {OUTPUT_DIR}")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Training failed: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    main()

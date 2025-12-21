#!/usr/bin/env python3
"""
scripts/hf_lora_train.py

Fallback training path using Hugging Face Transformers (PyTorch) + PEFT/LoRA.
This script assumes an image-to-text VLM available via HF that supports finetuning 
with the HuggingFace Trainer or accelerate.
We will:
 - Read data/training/train.jsonl and val.jsonl
 - Build a simple dataloader that loads images and tokens
 - Use LoRA via peft if model supports it
 - Save best checkpoint to outputs/hf_checkpoint
Note: This script is a reproducible template but might need adaptation to the specific VLM's API.
"""
import os
import json
import time
from pathlib import Path
import torch
from torch.utils.data import Dataset, DataLoader
from PIL import Image
import numpy as np

ROOT = Path(__file__).parent.parent
TRAIN_FILE = ROOT / "data" / "training" / "train.jsonl"
VAL_FILE = ROOT / "data" / "training" / "val.jsonl"
OUT = ROOT / "outputs"
OUT.mkdir(parents=True, exist_ok=True)

# Model selection: use env var or default
MODEL_NAME = os.getenv("HF_MODEL", "google/flan-t5-base")  # example fallback; swap for a VLM that supports images

print(f"Using model: {MODEL_NAME}")
print("NOTE: This is a template script. For image-to-text VLMs, you may need to use")
print("      models like 'microsoft/git-base' or 'Salesforce/blip2-opt-2.7b'")
print("      and adapt the dataset class to handle images properly.")

class InvoiceDataset(Dataset):
    """Dataset that loads training pairs from JSONL"""
    def __init__(self, jsonl_path, tokenizer, max_length=512, root=None):
        self.root = Path(root) if root else ROOT
        self.rows = []
        with open(jsonl_path, "r", encoding="utf8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    self.rows.append(json.loads(line))
                except Exception as e:
                    print(f"Warning: skipping invalid line in {jsonl_path}: {e}")
        self.tokenizer = tokenizer
        self.max_length = max_length
        print(f"Loaded {len(self.rows)} samples from {jsonl_path}")
    
    def __len__(self):
        return len(self.rows)
    
    def __getitem__(self, idx):
        r = self.rows[idx]
        # For text-only models, we use prompt + response
        # For image models, you would load and encode the image here
        text_prompt = r.get("prompt", "")
        labels = r.get("response", "")
        
        # Tokenize input
        tok = self.tokenizer(
            text_prompt,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors="pt"
        )
        
        # Tokenize labels
        lab = self.tokenizer(
            labels,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors="pt"
        )
        
        input_ids = tok.input_ids.squeeze()
        attention_mask = tok.attention_mask.squeeze()
        labels = lab.input_ids.squeeze()
        
        # Set padding tokens to -100 so they're ignored in loss
        labels[labels == self.tokenizer.pad_token_id] = -100
        
        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels
        }

def main():
    try:
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, Trainer, TrainingArguments
        from peft import LoraConfig, get_peft_model, prepare_model_for_int8_training
    except ImportError as e:
        print(f"Error: Required packages not installed. Please install:")
        print(f"  pip install transformers datasets accelerate peft")
        print(f"Error details: {e}")
        return
    
    # Check if we have enough data
    if not TRAIN_FILE.exists() or TRAIN_FILE.stat().st_size == 0:
        print(f"Error: Training file {TRAIN_FILE} does not exist or is empty.")
        print("Please run: python scripts/prepare_dataset.py && python scripts/format_to_training.py")
        return
    
    # Load tokenizer and model
    print(f"Loading tokenizer and model: {MODEL_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)
    
    # Create datasets
    train_ds = InvoiceDataset(TRAIN_FILE, tokenizer, max_length=512, root=ROOT)
    val_ds = InvoiceDataset(VAL_FILE, tokenizer, max_length=512, root=ROOT) if VAL_FILE.exists() else None
    
    # Apply LoRA adapters
    print("Applying LoRA configuration...")
    lora_r = int(os.getenv("LORA_R", "16"))
    lora_alpha = int(os.getenv("LORA_ALPHA", "32"))
    
    # Determine target modules based on model architecture
    if hasattr(model, "encoder") and hasattr(model.encoder, "layer"):
        # T5-style architecture
        target_modules = ["q", "v", "k", "o", "wi_0", "wi_1"]
    else:
        # Fallback: try common module names
        target_modules = None
    
    peft_config = LoraConfig(
        r=lora_r,
        lora_alpha=lora_alpha,
        target_modules=target_modules,
        lora_dropout=0.1,
        bias="none",
        task_type="SEQ_2_SEQ_LM"
    )
    
    try:
        model = get_peft_model(model, peft_config)
        model.print_trainable_parameters()
    except Exception as e:
        print(f"Warning: Could not apply LoRA: {e}")
        print("Continuing with full fine-tuning instead...")
    
    # Training arguments
    training_args = TrainingArguments(
        output_dir=str(OUT / "hf_checkpoint"),
        per_device_train_batch_size=int(os.getenv("BATCH_SIZE", "4")),
        per_device_eval_batch_size=4,
        num_train_epochs=int(os.getenv("EPOCHS", "3")),
        learning_rate=float(os.getenv("LR", "2e-5")),
        logging_dir=str(ROOT / "logs"),
        logging_steps=50,
        evaluation_strategy="epoch" if val_ds else "no",
        save_strategy="epoch",
        save_total_limit=3,
        fp16=torch.cuda.is_available(),
        gradient_accumulation_steps=1,
        warmup_steps=100,
        load_best_model_at_end=True if val_ds else False,
        metric_for_best_model="loss",
        report_to="none",  # Set to "wandb" if you want wandb logging
    )
    
    # Create trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
    )
    
    print("Starting training...")
    trainer.train()
    
    # Save final model
    final_output = OUT / "hf_checkpoint" / "final"
    trainer.save_model(str(final_output))
    tokenizer.save_pretrained(str(final_output))
    
    # Save training config
    config_info = {
        "model_name": MODEL_NAME,
        "lora_r": lora_r,
        "lora_alpha": lora_alpha,
        "batch_size": training_args.per_device_train_batch_size,
        "epochs": training_args.num_train_epochs,
        "learning_rate": training_args.learning_rate,
        "train_samples": len(train_ds),
        "val_samples": len(val_ds) if val_ds else 0,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(final_output / "training_config.json", "w") as f:
        json.dump(config_info, f, indent=2)
    
    print(f"Training finished. Saved checkpoint to {final_output}")
    print(f"Training config saved to {final_output / 'training_config.json'}")

if __name__ == "__main__":
    main()


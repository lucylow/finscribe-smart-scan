#!/usr/bin/env python3
"""
Phase 2: Fine-Tuning Script for PaddleOCR-VL

This script implements LoRA-based fine-tuning of PaddleOCR-VL for invoice understanding.
It uses the instruction-response pairs created by create_instruction_pairs.py.

Note: This is a framework that needs to be adapted based on the actual PaddleOCR-VL
training API and ERNIEKit implementation. The structure follows best practices for
vision-language model fine-tuning.
"""

import os
import sys
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoProcessor,
    AutoModelForVision2Seq,
    TrainingArguments,
    Trainer,
    TrainerCallback
)
from peft import LoraConfig, get_peft_model, TaskType
from PIL import Image
import numpy as np
from tqdm import tqdm

# Import custom modules
from weighted_loss import get_loss_function
from evaluation_metrics import evaluate_sample, evaluate_dataset


class InvoiceInstructionDataset(Dataset):
    """
    Dataset class for invoice instruction-response pairs.
    """
    
    def __init__(
        self,
        jsonl_path: str,
        processor,
        max_length: int = 512,
        image_size: tuple = (224, 224)
    ):
        """
        Initialize dataset.
        
        Args:
            jsonl_path: Path to JSONL file with instruction-response pairs
            processor: Vision-language processor (from transformers)
            max_length: Maximum sequence length for text
            image_size: Target image size (height, width)
        """
        self.processor = processor
        self.max_length = max_length
        self.image_size = image_size
        
        # Load all samples
        self.samples = []
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    self.samples.append(json.loads(line))
        
        print(f"Loaded {len(self.samples)} training samples")
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        sample = self.samples[idx]
        
        # Load and preprocess image
        image_path = sample['image']
        if not os.path.isabs(image_path):
            # Try relative to dataset location
            image_path = os.path.join(os.path.dirname(sample.get('_dataset_path', '')), image_path)
        
        try:
            image = Image.open(image_path).convert('RGB')
            image = image.resize(self.image_size)
        except Exception as e:
            print(f"Error loading image {image_path}: {e}")
            # Return a blank image as fallback
            image = Image.new('RGB', self.image_size, color='white')
        
        # Format conversation
        conversations = sample['conversations']
        prompt = conversations[0]['content']  # Human message
        response = conversations[1]['content']  # Assistant message
        
        # Combine prompt and response for training
        full_text = f"{prompt}\n{response}"
        
        # Process with processor
        # Note: This is a simplified version - adjust based on actual processor API
        encoding = self.processor(
            images=image,
            text=full_text,
            padding="max_length",
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt"
        )
        
        # Extract region information for loss weighting (if available)
        try:
            response_dict = json.loads(response)
            region = response_dict.get('region', 'unknown')
        except:
            region = 'unknown'
        
        encoding['region'] = region
        encoding['image_path'] = image_path
        
        # Convert to format expected by model
        for key, value in encoding.items():
            if isinstance(value, torch.Tensor) and value.dim() == 1:
                encoding[key] = value.squeeze(0)
        
        return encoding


class CustomTrainer(Trainer):
    """
    Custom Trainer that uses weighted loss function.
    """
    
    def __init__(self, loss_config: Optional[Dict] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.loss_config = loss_config or {}
        if self.loss_config.get('weighted', False):
            self.custom_loss_fn = get_loss_function({'loss': self.loss_config})
        else:
            self.custom_loss_fn = None
    
    def compute_loss(self, model, inputs, return_outputs=False):
        """
        Compute loss with optional weighting.
        """
        labels = inputs.pop("labels", None)
        outputs = model(**inputs)
        logits = outputs.logits
        
        if self.custom_loss_fn and labels is not None:
            # Use custom weighted loss
            region = inputs.get('region', None)
            if isinstance(region, list) and region:
                current_region = region[0]
            else:
                current_region = None
            
            loss = self.custom_loss_fn(
                logits,
                labels,
                current_region=current_region
            )
        else:
            # Use default loss
            loss = outputs.loss if hasattr(outputs, 'loss') else None
            if loss is None and labels is not None:
                loss_fct = torch.nn.CrossEntropyLoss()
                loss = loss_fct(logits.view(-1, logits.size(-1)), labels.view(-1))
        
        return (loss, outputs) if return_outputs else loss


class EvaluationCallback(TrainerCallback):
    """
    Callback for periodic evaluation during training.
    """
    
    def __init__(self, eval_dataset, config):
        self.eval_dataset = eval_dataset
        self.config = config
        self.best_score = 0.0
    
    def on_evaluate(self, args, state, control, **kwargs):
        """Called after evaluation."""
        # Log evaluation metrics
        if state.log_history:
            last_log = state.log_history[-1]
            eval_loss = last_log.get('eval_loss', float('inf'))
            print(f"\nEvaluation - Loss: {eval_loss:.4f}")


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def setup_lora(model, lora_config: Dict):
    """
    Setup LoRA for efficient fine-tuning.
    
    Args:
        model: Base model
        lora_config: LoRA configuration dictionary
    """
    if not lora_config.get('enabled', False):
        return model
    
    peft_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,  # Adjust based on model architecture
        r=lora_config.get('r', 16),
        lora_alpha=lora_config.get('lora_alpha', 32),
        target_modules=lora_config.get('target_modules', ['q_proj', 'v_proj']),
        lora_dropout=lora_config.get('dropout', 0.05),
        bias=lora_config.get('bias', 'none')
    )
    
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()
    
    return model


def create_data_augmentation(config: Dict):
    """
    Create data augmentation transforms based on config.
    
    Note: This is a placeholder - implement actual augmentation pipeline
    using torchvision.transforms or albumentations.
    """
    from torchvision import transforms
    
    aug_config = config.get('vision_processor', {}).get('train', {})
    transforms_list = []
    
    # Add augmentation transforms based on config
    # This is simplified - implement full augmentation pipeline
    
    return transforms.Compose(transforms_list)


def main():
    """Main training function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fine-tune PaddleOCR-VL for invoice understanding")
    parser.add_argument(
        "--config",
        type=str,
        default="finetune_config.yaml",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        help="Path to checkpoint to resume from"
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    print(f"Loaded configuration from {args.config}")
    
    # Setup device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    # Load model and processor
    model_name = config['model_name_or_path']
    print(f"Loading model: {model_name}")
    
    try:
        processor = AutoProcessor.from_pretrained(model_name)
        model = AutoModelForVision2Seq.from_pretrained(model_name)
    except Exception as e:
        print(f"Error loading model: {e}")
        print("Note: PaddleOCR-VL may use a custom model class. Adjust imports as needed.")
        sys.exit(1)
    
    # Apply LoRA
    if config.get('lora', {}).get('enabled', False):
        print("Setting up LoRA...")
        model = setup_lora(model, config['lora'])
    
    model.to(device)
    
    # Create datasets
    dataset_path = config['dataset_path']
    print(f"Loading dataset from {dataset_path}")
    
    # Split dataset (if not pre-split)
    train_dataset = InvoiceInstructionDataset(
        dataset_path,
        processor,
        max_length=512,
        image_size=tuple(config.get('vision_processor', {}).get('train', {}).get('size', [224, 224]))
    )
    
    # Create validation split
    train_size = int(0.9 * len(train_dataset))
    val_size = len(train_dataset) - train_size
    train_subset, val_subset = torch.utils.data.random_split(
        train_dataset,
        [train_size, val_size],
        generator=torch.Generator().manual_seed(42)
    )
    
    # Setup training arguments
    training_config = config['training']
    training_args = TrainingArguments(
        output_dir=config['output_dir'],
        run_name=config.get('run_name', 'paddleocr-vl-finetune'),
        num_train_epochs=training_config['num_train_epochs'],
        per_device_train_batch_size=training_config['per_device_train_batch_size'],
        per_device_eval_batch_size=training_config.get('per_device_eval_batch_size', training_config['per_device_train_batch_size']),
        gradient_accumulation_steps=training_config['gradient_accumulation_steps'],
        learning_rate=training_config['learning_rate'],
        warmup_steps=training_config.get('warmup_steps', 0),
        warmup_ratio=training_config.get('warmup_ratio', None),
        weight_decay=training_config.get('weight_decay', 0.01),
        max_grad_norm=training_config.get('max_grad_norm', 1.0),
        lr_scheduler_type=training_config.get('lr_scheduler_type', 'linear'),
        logging_steps=training_config.get('logging_steps', 10),
        save_steps=training_config.get('save_steps', 500),
        save_total_limit=training_config.get('save_total_limit', 3),
        eval_steps=training_config.get('eval_steps', 250),
        evaluation_strategy=training_config.get('evaluation_strategy', 'steps'),
        fp16=training_config.get('fp16', False),
        dataloader_num_workers=training_config.get('dataloader_num_workers', 4),
        dataloader_pin_memory=training_config.get('dataloader_pin_memory', True),
        remove_unused_columns=training_config.get('remove_unused_columns', False),
        report_to=training_config.get('report_to', ['tensorboard']),
        seed=training_config.get('seed', 42),
        load_best_model_at_end=True,
        metric_for_best_model='eval_loss',
        greater_is_better=False
    )
    
    # Create trainer
    trainer = CustomTrainer(
        model=model,
        args=training_args,
        train_dataset=train_subset,
        eval_dataset=val_subset,
        loss_config=config.get('loss', {}),
        callbacks=[EvaluationCallback(val_subset, config)]
    )
    
    # Train
    print("\nStarting training...")
    if args.resume:
        trainer.train(resume_from_checkpoint=args.resume)
    else:
        trainer.train()
    
    # Save final model
    final_model_path = os.path.join(config['output_dir'], 'final_model')
    trainer.save_model(final_model_path)
    processor.save_pretrained(final_model_path)
    
    print(f"\n✓ Training complete!")
    print(f"✓ Model saved to: {final_model_path}")


if __name__ == "__main__":
    main()


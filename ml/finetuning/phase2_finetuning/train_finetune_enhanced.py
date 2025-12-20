#!/usr/bin/env python3
"""
Enhanced Fine-Tuning Script for PaddleOCR-VL with Completion-Only Training

This script implements the critical technique of completion-only training where
the loss is masked for prompt tokens, ensuring the model only learns from the
assistant's response text. This prevents the model from "forgetting" how to follow
instructions.

Key Features:
- Completion-only training (mask prompt tokens with -100)
- LoRA for efficient fine-tuning
- Weighted loss for different semantic regions
- Flash Attention 2 support for speed
- Mixed precision training (bf16)
- Comprehensive evaluation metrics
"""

import os
import sys
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoProcessor,
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer,
    TrainerCallback,
    BitsAndBytesConfig
)
from peft import LoraConfig, get_peft_model, TaskType, prepare_model_for_kbit_training
from PIL import Image
import numpy as np
from tqdm import tqdm
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import advanced loss and augmentation
try:
    from advanced_loss import create_loss_function, CombinedLoss
    ADVANCED_LOSS_AVAILABLE = True
except ImportError:
    ADVANCED_LOSS_AVAILABLE = False
    logger.warning("Advanced loss functions not available. Using standard loss.")

try:
    from advanced_augmentation import DocumentAugmentation
    ADVANCED_AUG_AVAILABLE = True
except ImportError:
    ADVANCED_AUG_AVAILABLE = False
    logger.warning("Advanced augmentation not available. Using basic augmentation.")


class InvoiceInstructionDataset(Dataset):
    """
    Dataset class for invoice instruction-response pairs with proper chat formatting.
    """
    
    def __init__(
        self,
        jsonl_path: str,
        processor,
        max_length: int = 2048,
        image_size: tuple = (1024, 1024),
        augmentation: Optional[DocumentAugmentation] = None
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
        self.augmentation = augmentation  # Optional augmentation for training
        
        # Load all samples
        self.samples = []
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    self.samples.append(json.loads(line))
        
        logger.info(f"Loaded {len(self.samples)} training samples")
        if self.augmentation is not None:
            logger.info("Data augmentation enabled")
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        sample = self.samples[idx]
        
        # Load and preprocess image
        image_path = sample['image']
        if not os.path.isabs(image_path):
            # Try relative to dataset location
            base_dir = Path(sample.get('_dataset_path', os.path.dirname(sample.get('image', ''))))
            image_path = os.path.join(base_dir, image_path)
        
        try:
            image = Image.open(image_path).convert('RGB')
            # Resize maintaining aspect ratio
            image.thumbnail(self.image_size, Image.Resampling.LANCZOS)
            
            # Apply augmentation if enabled (only during training)
            if self.augmentation is not None:
                image = self.augmentation(image)
        except Exception as e:
            logger.warning(f"Error loading image {image_path}: {e}")
            # Return a blank image as fallback
            image = Image.new('RGB', self.image_size, color='white')
        
        # Format conversation in chat format
        conversations = sample['conversations']
        prompt = conversations[0]['content']  # Human message
        response = conversations[1]['content']  # Assistant message
        
        # Format as chat messages for the processor
        # PaddleOCR-VL typically uses this format
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt}
                ]
            },
            {
                "role": "assistant",
                "content": response
            }
        ]
        
        # Process with processor
        try:
            # Try to use the processor's chat template if available
            if hasattr(self.processor, 'apply_chat_template'):
                # Get the formatted text with special tokens
                text_input = self.processor.apply_chat_template(
                    messages, 
                    tokenize=False, 
                    add_generation_prompt=False
                )
            elif hasattr(self.processor, 'tokenizer') and hasattr(self.processor.tokenizer, 'apply_chat_template'):
                text_input = self.processor.tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=False
                )
            else:
                # Fallback: manual formatting
                # Format: <image>\n[Human]: prompt\n[Assistant]: response
                text_input = f"<image>\nHuman: {prompt}\nAssistant: {response}"
            
            # Process image and text together
            encoding = self.processor(
                images=image,
                text=text_input,
                padding="max_length",
                truncation=True,
                max_length=self.max_length,
                return_tensors="pt"
            )
            
            # Store the prompt text length for better masking (if tokenizer available)
            if hasattr(self.processor, 'tokenizer'):
                try:
                    # Tokenize just the prompt to find its length
                    prompt_text = f"<image>\nHuman: {prompt}\nAssistant: "
                    prompt_tokens = self.processor.tokenizer.encode(
                        prompt_text,
                        add_special_tokens=False,
                        return_tensors="pt"
                    )
                    encoding['prompt_length'] = prompt_tokens.size(1)
                except:
                    encoding['prompt_length'] = None
            else:
                encoding['prompt_length'] = None
        except Exception as e:
            logger.warning(f"Error processing sample {idx}: {e}")
            # Create minimal encoding
            encoding = {
                "input_ids": torch.zeros(self.max_length, dtype=torch.long),
                "attention_mask": torch.zeros(self.max_length, dtype=torch.long),
                "pixel_values": torch.zeros((3, *self.image_size), dtype=torch.float32)
            }
        
        # Extract region information for loss weighting (if available)
        try:
            response_dict = json.loads(response)
            region = response_dict.get('region', 'unknown')
        except:
            region = 'unknown'
        
        # Convert to format expected by model
        result = {}
        for key, value in encoding.items():
            if isinstance(value, torch.Tensor):
                if value.dim() == 1:
                    result[key] = value.squeeze(0)
                elif value.dim() == 0:
                    result[key] = value
                else:
                    result[key] = value.squeeze(0) if value.size(0) == 1 else value
            else:
                result[key] = value
        
        result['region'] = region
        result['image_path'] = image_path
        
        return result


class CompletionOnlyTrainer(Trainer):
    """
    Custom Trainer that implements completion-only training.
    
    This masks the prompt tokens (setting them to -100) so the model
    only learns from the assistant's response. This is critical for
    preventing the model from forgetting how to follow instructions.
    """
    
    def __init__(self, loss_config: Optional[Dict] = None, tokenizer=None, advanced_loss_fn=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.loss_config = loss_config or {}
        self.region_weights = self.loss_config.get('region_weights', {})
        self.tokenizer = tokenizer
        self.advanced_loss_fn = advanced_loss_fn  # Optional advanced loss function
        
        # Common special tokens for assistant response markers
        # These will be used to identify where the assistant response starts
        self.assistant_tokens = []
        if tokenizer:
            # Try to find assistant-related tokens
            for token_name in ['assistant', 'assistant:', 'ai:', 'AI:', '[|AI|]', '<|assistant|>']:
                if hasattr(tokenizer, 'convert_tokens_to_ids'):
                    try:
                        token_id = tokenizer.convert_tokens_to_ids(token_name)
                        if token_id != tokenizer.unk_token_id:
                            self.assistant_tokens.append(token_id)
                    except:
                        pass
    
    def _find_assistant_start(self, input_ids: torch.Tensor, prompt_lengths: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Find the position where assistant response starts for each sequence in the batch.
        
        Args:
            input_ids: Input token IDs of shape (batch_size, seq_len)
            prompt_lengths: Optional tensor of prompt lengths from dataset (batch_size,)
        
        Returns:
            Tensor of shape (batch_size,) with start positions
        """
        batch_size = input_ids.size(0)
        seq_len = input_ids.size(1)
        start_positions = torch.zeros(batch_size, dtype=torch.long, device=input_ids.device)
        
        # If we have explicit prompt lengths from the dataset, use those
        if prompt_lengths is not None:
            for i in range(batch_size):
                prompt_len = prompt_lengths[i].item() if isinstance(prompt_lengths[i], torch.Tensor) else prompt_lengths[i]
                if prompt_len and prompt_len > 0 and prompt_len < seq_len:
                    start_positions[i] = prompt_len
                else:
                    # Fallback to token-based search
                    start_positions[i] = self._find_assistant_token(input_ids[i], seq_len)
        else:
            # Try to find assistant tokens
            for i in range(batch_size):
                start_positions[i] = self._find_assistant_token(input_ids[i], seq_len)
        
        return start_positions
    
    def _find_assistant_token(self, seq: torch.Tensor, seq_len: int) -> int:
        """Find assistant token position in a single sequence."""
        # Try to find assistant-related tokens
        if self.assistant_tokens:
            for token_id in self.assistant_tokens:
                positions = (seq == token_id).nonzero(as_tuple=True)[0]
                if len(positions) > 0:
                    # Start after the assistant token
                    return (positions[0] + 1).item()
        
        # Try common patterns: "Assistant:", "AI:", etc.
        if self.tokenizer:
            try:
                # Try to find "Assistant" or "AI" tokens
                for pattern in ["Assistant", "AI", "assistant", "ai"]:
                    pattern_ids = self.tokenizer.encode(pattern, add_special_tokens=False)
                    if len(pattern_ids) > 0:
                        # Search for pattern in sequence
                        pattern_len = len(pattern_ids)
                        for i in range(seq_len - pattern_len + 1):
                            if torch.equal(seq[i:i+pattern_len], torch.tensor(pattern_ids, device=seq.device)):
                                return i + pattern_len
            except:
                pass
        
        # Fallback: estimate based on sequence structure
        # Assume prompt is roughly first 40-60% of sequence
        return int(seq_len * 0.5)
    
    def _mask_prompt_tokens(self, labels: torch.Tensor, input_ids: torch.Tensor, prompt_lengths: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Mask prompt tokens by setting them to -100 (ignored in loss calculation).
        
        Uses tokenizer special tokens to identify where the assistant response begins.
        """
        # Create a copy of labels
        masked_labels = labels.clone()
        
        # Find where assistant response starts for each sequence
        assistant_starts = self._find_assistant_start(input_ids)
        
        # Mask all tokens before assistant response
        batch_size = labels.size(0)
        for i in range(batch_size):
            start_pos = assistant_starts[i].item()
            masked_labels[i, :start_pos] = -100
        
        return masked_labels
    
    def compute_loss(self, model, inputs, return_outputs=False):
        """
        Compute loss with completion-only training and optional region weighting.
        """
        labels = inputs.pop("labels", None)
        
        # If labels are not provided, create them from input_ids
        if labels is None and "input_ids" in inputs:
            labels = inputs["input_ids"].clone()
        
        # Apply completion-only masking
        if labels is not None:
            # Extract prompt lengths if available
            prompt_lengths = inputs.pop("prompt_length", None)
            if prompt_lengths is not None and isinstance(prompt_lengths, torch.Tensor):
                # Handle batched prompt lengths
                if prompt_lengths.dim() == 0:
                    prompt_lengths = prompt_lengths.unsqueeze(0)
            labels = self._mask_prompt_tokens(labels, inputs.get("input_ids"), prompt_lengths)
            inputs["labels"] = labels
        
        outputs = model(**inputs)
        logits = outputs.logits
        
        if labels is not None:
            # Prepare logits and labels for loss computation
            shift_logits = logits[..., :-1, :].contiguous()
            shift_labels = labels[..., 1:].contiguous()
            
            # Use advanced loss function if available, otherwise use standard CE
            if self.advanced_loss_fn is not None:
                # Get region for weighting if available
                region = None
                if "region" in inputs:
                    region_val = inputs.get("region")
                    if isinstance(region_val, list) and region_val:
                        region = region_val[0]
                    elif isinstance(region_val, str):
                        region = region_val
                
                # Compute loss using advanced loss function
                loss = self.advanced_loss_fn(shift_logits, shift_labels, region=region)
            else:
                # Standard cross-entropy loss
                loss_fct = torch.nn.CrossEntropyLoss(ignore_index=-100)
                loss = loss_fct(shift_logits.view(-1, shift_logits.size(-1)), shift_labels.view(-1))
                
                # Apply region-based weighting if configured
                if self.region_weights and "region" in inputs:
                    region = inputs.get("region")
                    if isinstance(region, list) and region:
                        current_region = region[0]
                        weight = self.region_weights.get(current_region, 1.0)
                        loss = loss * weight
        else:
            loss = outputs.loss if hasattr(outputs, 'loss') else None
            if loss is None:
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
        if state.log_history:
            last_log = state.log_history[-1]
            eval_loss = last_log.get('eval_loss', float('inf'))
            logger.info(f"\nEvaluation - Loss: {eval_loss:.4f}")


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def setup_lora(model, lora_config: Dict, use_quantization: bool = False):
    """
    Setup LoRA for efficient fine-tuning.
    
    Args:
        model: Base model
        lora_config: LoRA configuration dictionary
        use_quantization: Whether to use 4-bit quantization
    """
    if not lora_config.get('enabled', False):
        return model
    
    # Prepare model for quantization if needed
    if use_quantization:
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16
        )
        model = prepare_model_for_kbit_training(model)
    
    peft_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=lora_config.get('r', 16),
        lora_alpha=lora_config.get('lora_alpha', 32),
        target_modules=lora_config.get('target_modules', ['q_proj', 'k_proj', 'v_proj', 'o_proj']),
        lora_dropout=lora_config.get('dropout', 0.05),
        bias=lora_config.get('bias', 'none')
    )
    
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()
    
    return model


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
    parser.add_argument(
        "--use-quantization",
        action="store_true",
        help="Use 4-bit quantization to reduce memory"
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    logger.info(f"Loaded configuration from {args.config}")
    
    # Setup device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device}")
    
    if not torch.cuda.is_available():
        logger.warning("CUDA not available. Training will be slow on CPU.")
    
    # Load model and processor
    model_name = config['model_name_or_path']
    logger.info(f"Loading model: {model_name}")
    
    try:
        processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)
        
        # Load model with appropriate dtype
        model_kwargs = {
            "trust_remote_code": True,
            "torch_dtype": torch.bfloat16 if torch.cuda.is_available() else torch.float32,
        }
        
        if args.use_quantization:
            model_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16
            )
        
        model = AutoModelForCausalLM.from_pretrained(model_name, **model_kwargs)
        
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        logger.error("Note: PaddleOCR-VL may use a custom model class. Adjust imports as needed.")
        sys.exit(1)
    
    # Enable gradient checkpointing for memory efficiency
    if config.get('training', {}).get('gradient_checkpointing', True):
        if hasattr(model, 'gradient_checkpointing_enable'):
            model.gradient_checkpointing_enable()
            logger.info("Gradient checkpointing enabled")
        elif hasattr(model, 'config') and hasattr(model.config, 'gradient_checkpointing'):
            model.config.gradient_checkpointing = True
            logger.info("Gradient checkpointing enabled (via config)")
    
    # Apply LoRA
    if config.get('lora', {}).get('enabled', False):
        logger.info("Setting up LoRA...")
        model = setup_lora(model, config['lora'], use_quantization=args.use_quantization)
    
    model.to(device)
    
    # Create datasets
    dataset_path = config['dataset_path']
    logger.info(f"Loading dataset from {dataset_path}")
    
    # Setup augmentation for training dataset
    augmentation = None
    if ADVANCED_AUG_AVAILABLE and config.get('augmentation', {}).get('enabled', True):
        aug_config = config.get('augmentation', {})
        augmentation = DocumentAugmentation(
            rotation_range=tuple(aug_config.get('rotation_range', [-5, 5])),
            brightness_range=tuple(aug_config.get('brightness_range', [0.8, 1.2])),
            contrast_range=tuple(aug_config.get('contrast_range', [0.8, 1.2])),
            noise_std=tuple(aug_config.get('noise_std', [0.01, 0.05])),
            blur_probability=aug_config.get('blur_probability', 0.1),
            enabled=aug_config.get('enabled', True)
        )
    
    train_dataset = InvoiceInstructionDataset(
        dataset_path,
        processor,
        max_length=config.get('max_length', 2048),
        image_size=tuple(config.get('vision_processor', {}).get('train', {}).get('size', [1024, 1024])),
        augmentation=augmentation
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
        lr_scheduler_type=training_config.get('lr_scheduler_type', 'cosine'),
        logging_steps=training_config.get('logging_steps', 10),
        save_steps=training_config.get('save_steps', 500),
        save_total_limit=training_config.get('save_total_limit', 3),
        eval_steps=training_config.get('eval_steps', 250),
        evaluation_strategy=training_config.get('evaluation_strategy', 'steps'),
        fp16=training_config.get('fp16', False),
        bf16=training_config.get('bf16', True) if torch.cuda.is_available() else False,
        dataloader_num_workers=training_config.get('dataloader_num_workers', 4),
        dataloader_pin_memory=training_config.get('dataloader_pin_memory', True),
        remove_unused_columns=training_config.get('remove_unused_columns', False),
        report_to=training_config.get('report_to', ['tensorboard']),
        seed=training_config.get('seed', 42),
        load_best_model_at_end=True,
        metric_for_best_model='eval_loss',
        greater_is_better=False,
        # Flash Attention 2 support
        attn_implementation=training_config.get('attn_implementation', 'flash_attention_2') if torch.cuda.is_available() else 'eager',
        # Gradient checkpointing (can also be set on model, but setting here too for compatibility)
        gradient_checkpointing=training_config.get('gradient_checkpointing', True),
    )
    
    # Create advanced loss function if configured
    advanced_loss_fn = None
    if ADVANCED_LOSS_AVAILABLE:
        loss_config = config.get('loss', {})
        if loss_config.get('use_focal', False) or loss_config.get('use_label_smoothing', False):
            try:
                advanced_loss_fn = create_loss_function(config)
                logger.info("Using advanced loss function")
                if loss_config.get('use_focal', False):
                    logger.info(f"  - Focal Loss: alpha={loss_config.get('focal_alpha', 1.0)}, gamma={loss_config.get('focal_gamma', 2.0)}")
                if loss_config.get('use_label_smoothing', False):
                    logger.info(f"  - Label Smoothing: {loss_config.get('label_smoothing', 0.1)}")
            except Exception as e:
                logger.warning(f"Failed to create advanced loss function: {e}. Using standard loss.")
    
    # Create trainer with completion-only training
    trainer = CompletionOnlyTrainer(
        model=model,
        args=training_args,
        train_dataset=train_subset,
        eval_dataset=val_subset,
        loss_config=config.get('loss', {}),
        tokenizer=processor.tokenizer if hasattr(processor, 'tokenizer') else None,
        advanced_loss_fn=advanced_loss_fn,
        callbacks=[EvaluationCallback(val_subset, config)]
    )
    
    # Train
    logger.info("\nStarting training...")
    if args.resume:
        trainer.train(resume_from_checkpoint=args.resume)
    else:
        trainer.train()
    
    # Save final model
    final_model_path = os.path.join(config['output_dir'], 'final_model')
    trainer.save_model(final_model_path)
    processor.save_pretrained(final_model_path)
    
    logger.info(f"\n✓ Training complete!")
    logger.info(f"✓ Model saved to: {final_model_path}")


if __name__ == "__main__":
    main()


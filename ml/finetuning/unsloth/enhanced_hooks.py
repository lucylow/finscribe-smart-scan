import torch
from typing import Dict, Any

def apply_finscribe_optimizations(model, tokenizer):
    """
    Apply domain-specific optimizations for financial document parsing.
    1. Special tokens for currency and dates.
    2. LoRA target modules optimization.
    """
    special_tokens = ["<|vendor|>", "<|amount|>", "<|date|>", "<|invoice_no|>"]
    tokenizer.add_tokens(special_tokens)
    model.resize_token_embeddings(len(tokenizer))
    
    print(f"Added {len(special_tokens)} special tokens for financial parsing.")
    return model, tokenizer

def get_lora_config():
    return {
        "r": 32,
        "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        "lora_alpha": 64,
        "lora_dropout": 0.05,
        "bias": "none",
    }

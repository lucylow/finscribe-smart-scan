"""
LoRA (Low-Rank Adaptation) support for memory-efficient fine-tuning
"""

from peft import LoraConfig, get_peft_model
from transformers import PreTrainedModel
from typing import Optional


def apply_lora(
    model: PreTrainedModel,
    r: int = 16,
    lora_alpha: int = 32,
    lora_dropout: float = 0.1,
    target_modules: Optional[list] = None,
    bias: str = "none",
) -> PreTrainedModel:
    """
    Applies LoRA to the model for memory-efficient fine-tuning.
    
    Args:
        model: Base model to apply LoRA to
        r: LoRA rank (lower = fewer parameters)
        lora_alpha: LoRA alpha scaling factor
        lora_dropout: LoRA dropout rate
        target_modules: List of module names to apply LoRA to
                       (default: attention projection layers)
        bias: Bias handling ("none", "all", "lora_only")
        
    Returns:
        Model wrapped with LoRA adapters
    """
    if target_modules is None:
        # Default to attention projection layers
        target_modules = ["q_proj", "k_proj", "v_proj", "o_proj"]
    
    config = LoraConfig(
        r=r,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        target_modules=target_modules,
        bias=bias,
        task_type="CAUSAL_LM",
    )
    
    model = get_peft_model(model, config)
    
    return model



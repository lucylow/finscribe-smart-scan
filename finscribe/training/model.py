"""
Model loading and optimization for PaddleOCR-VL fine-tuning
"""

import torch
from transformers import AutoModelForCausalLM, AutoProcessor
from typing import Tuple, Optional


def load_model(
    model_name: str = "PaddlePaddle/PaddleOCR-VL",
    use_flash_attention: bool = True,
    torch_dtype: Optional[torch.dtype] = None,
    device_map: str = "auto",
) -> Tuple[AutoModelForCausalLM, AutoProcessor]:
    """
    Loads PaddleOCR-VL model and processor with optimizations.
    
    Args:
        model_name: HuggingFace model identifier
        use_flash_attention: Whether to use Flash Attention 2 (2-4x speedup)
        torch_dtype: Data type for model weights (default: bfloat16)
        device_map: Device mapping strategy
        
    Returns:
        Tuple of (model, processor)
    """
    if torch_dtype is None:
        torch_dtype = torch.bfloat16
    
    # Load model with optimizations
    model_kwargs = {
        "trust_remote_code": True,
        "torch_dtype": torch_dtype,
        "device_map": device_map,
    }
    
    if use_flash_attention:
        try:
            model_kwargs["attn_implementation"] = "flash_attention_2"
        except Exception as e:
            print(f"Warning: Flash Attention 2 not available: {e}")
            print("Falling back to default attention")
    
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        **model_kwargs,
    )
    
    # Load processor
    processor = AutoProcessor.from_pretrained(
        model_name,
        trust_remote_code=True,
    )
    
    return model, processor


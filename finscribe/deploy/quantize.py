"""
INT8 Quantization for model deployment
"""

from pathlib import Path
from typing import Optional


def quantize_model(
    model_path: Path,
    output_path: Path,
    quantization_config: Optional[dict] = None,
) -> Path:
    """
    Quantizes a fine-tuned model to INT8 using ONNX Runtime.
    
    Args:
        model_path: Path to the fine-tuned model
        output_path: Path to save quantized model
        quantization_config: Optional quantization configuration
        
    Returns:
        Path to quantized model
    """
    try:
        from optimum.onnxruntime import ORTQuantizer
        from optimum.onnxruntime.configuration import AutoQuantizationConfig
    except ImportError:
        raise ImportError(
            "optimum[onnxruntime] is required for quantization. "
            "Install with: pip install optimum[onnxruntime]"
        )
    
    # Load quantizer
    quantizer = ORTQuantizer.from_pretrained(
        str(model_path),
        feature="text-generation",
    )
    
    # Use default quantization config if not provided
    if quantization_config is None:
        qconfig = AutoQuantizationConfig.avx512_vnni(
            is_static=False,
            per_channel=True,
        )
    else:
        qconfig = AutoQuantizationConfig.from_dict(quantization_config)
    
    # Quantize
    quantizer.quantize(
        save_dir=str(output_path),
        quantization_config=qconfig,
    )
    
    return output_path


def load_quantized_model(model_path: Path):
    """
    Loads a quantized model for inference.
    
    Args:
        model_path: Path to quantized model
        
    Returns:
        Loaded model
    """
    try:
        from transformers import AutoModelForCausalLM
        
        model = AutoModelForCausalLM.from_pretrained(
            str(model_path),
            device_map="auto",
        )
        return model
    except Exception as e:
        raise RuntimeError(f"Failed to load quantized model: {e}")


import os
from typing import Dict, Any

def load_config() -> Dict[str, Any]:
    """Load configuration from environment variables with sensible defaults."""
    
    model_mode = os.getenv("MODEL_MODE", "mock")  # mock | local | remote
    
    return {
        "model_mode": model_mode,
        "paddleocr_vl": {
            "vllm_server_url": os.getenv("PADDLEOCR_VLLM_URL", "http://localhost:8001/v1"),
            "model_name": "PaddlePaddle/PaddleOCR-VL",
            "timeout": int(os.getenv("PADDLEOCR_TIMEOUT", "30"))
        },
        "ernie_vl": {
            "vllm_server_url": os.getenv("ERNIE_VLLM_URL", "http://localhost:8002/v1"),
            "model_name": os.getenv("ERNIE_MODEL_NAME", "baidu/ERNIE-5"),  # Default to ERNIE 5
            "model_version": os.getenv("ERNIE_MODEL_VERSION", "auto"),  # auto, ernie-5, ernie-4.5-vl, ernie-4.5
            "timeout": int(os.getenv("ERNIE_TIMEOUT", "60")),
            "max_retries": int(os.getenv("ERNIE_MAX_RETRIES", "3")),
            "enable_thinking": os.getenv("ERNIE_ENABLE_THINKING", "true").lower() == "true",
            "huggingface_token": os.getenv("HUGGINGFACE_TOKEN", None),  # Optional HF token for private models
            "use_huggingface": os.getenv("USE_HUGGINGFACE", "false").lower() == "true"
        },
        "validation": {
            "check_arithmetic": True,
            "validate_dates": True,
            "min_confidence_threshold": float(os.getenv("MIN_CONFIDENCE", "0.7")),
            "arithmetic_tolerance": float(os.getenv("ARITHMETIC_TOLERANCE", "0.01"))
        },
        "storage": {
            "upload_dir": os.getenv("UPLOAD_DIR", "/tmp/finscribe_uploads"),
            "staging_dir": os.getenv("STAGING_DIR", "/tmp/finscribe_staging"),
            "max_upload_mb": int(os.getenv("MAX_UPLOAD_MB", "20"))
        },
        "active_learning": {
            "enabled": os.getenv("ACTIVE_LEARNING_ENABLED", "true").lower() == "true",
            "file_path": os.getenv("ACTIVE_LEARNING_FILE", "./active_learning.jsonl")
        }
    }

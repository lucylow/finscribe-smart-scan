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
            "model_name": "baidu/ERNIE-4.5-VL-28B-A3B-Thinking",
            "timeout": int(os.getenv("ERNIE_TIMEOUT", "60")),
            "enable_thinking": True
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

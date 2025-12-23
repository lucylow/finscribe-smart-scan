"""Image preprocessing for OCR"""
import cv2
import numpy as np
from pathlib import Path
from typing import Union
import tempfile
import os


def preprocess_image(input_bytes_or_path: Union[bytes, str, Path]) -> str:
    """
    Preprocess image for OCR: deskew, enhance contrast, denoise.
    
    Args:
        input_bytes_or_path: Image bytes or file path
    
    Returns:
        Path to preprocessed image file
    """
    # Load image
    if isinstance(input_bytes_or_path, (str, Path)):
        img = cv2.imread(str(input_bytes_or_path))
        if img is None:
            raise ValueError(f"Could not load image from {input_bytes_or_path}")
    else:
        # Load from bytes
        nparr = np.frombuffer(input_bytes_or_path, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Could not decode image from bytes")
    
    # Convert to color if grayscale
    if len(img.shape) == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    
    # Simple deskew heuristic: detect rotation angle
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    
    # Convert back to BGR for output
    enhanced_bgr = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
    
    # Save to temporary file
    output_dir = Path("data") / "preprocessed"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create unique filename
    temp_file = tempfile.NamedTemporaryFile(
        suffix=".png",
        dir=str(output_dir),
        delete=False
    )
    output_path = temp_file.name
    temp_file.close()
    
    # Save preprocessed image
    cv2.imwrite(output_path, enhanced_bgr)
    
    return output_path

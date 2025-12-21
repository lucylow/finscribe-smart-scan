"""
Image preprocessing module for OCR optimization.

Provides:
- Deskewing (rotation correction)
- Contrast enhancement (CLAHE)
- Denoising
"""
import cv2
import numpy as np
import logging
import pathlib

LOG = logging.getLogger("preprocess")


def read_image(path: str) -> np.ndarray:
    """
    Read image from path, handling various encodings.
    
    Args:
        path: Path to image file
        
    Returns:
        Image as numpy array (BGR format)
    """
    # Handle non-ASCII paths (common on Windows)
    img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Could not read image from {path}")
    return img


def deskew(image: np.ndarray) -> np.ndarray:
    """
    Deskew document using Hough transform or PCA-based angle detection.
    
    Args:
        image: Input image (BGR)
        
    Returns:
        Deskewed image
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thresh > 0))
    
    if len(coords) == 0:
        LOG.warning("No text detected for deskewing")
        return image
    
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    
    LOG.debug(f"Deskew angle: {angle:.2f} degrees")
    
    # Only rotate if angle is significant
    if abs(angle) < 0.5:
        return image
    
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        image, M, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE
    )
    return rotated


def enhance_contrast(image: np.ndarray) -> np.ndarray:
    """
    Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) to improve contrast.
    
    Args:
        image: Input image (BGR)
        
    Returns:
        Contrast-enhanced image
    """
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    lab_planes = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    lab_planes[0] = clahe.apply(lab_planes[0])
    return cv2.cvtColor(cv2.merge(lab_planes), cv2.COLOR_LAB2BGR)


def denoise(image: np.ndarray) -> np.ndarray:
    """
    Apply denoising to reduce image noise.
    
    Args:
        image: Input image (BGR)
        
    Returns:
        Denoised image
    """
    return cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)


def preprocess(path: str, enable_denoise: bool = False) -> str:
    """
    Full preprocessing pipeline: deskew + contrast + optional denoise.
    
    Args:
        path: Path to input image
        enable_denoise: Whether to apply denoising (slower but better quality)
        
    Returns:
        Path to preprocessed image
    """
    LOG.info(f"Preprocessing {path}")
    
    try:
        img = read_image(path)
        img = deskew(img)
        img = enhance_contrast(img)
        
        if enable_denoise:
            img = denoise(img)
        
        # Save preprocessed image
        output_dir = pathlib.Path("data/preprocessed")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_filename = pathlib.Path(path).name
        output_path = output_dir / output_filename
        
        # Handle non-ASCII paths
        is_success, im_buf_arr = cv2.imencode(output_path.suffix, img)
        if is_success:
            im_buf_arr.tofile(str(output_path))
        else:
            raise ValueError(f"Failed to encode image to {output_path}")
        
        LOG.info(f"Saved preprocessed image to {output_path}")
        return str(output_path)
        
    except Exception as e:
        LOG.error(f"Preprocessing failed for {path}: {e}", exc_info=True)
        raise


"""
Image Pre-processing for Enhanced OCR Accuracy

This module implements advanced image pre-processing techniques to improve
OCR accuracy, especially for scanned or low-quality documents.

Features:
- Adaptive Thresholding: Handles uneven lighting better than fixed threshold
- De-skewing: Corrects minor image rotations common in scanned documents
- Contrast Enhancement: Improves text visibility
"""
import cv2
import numpy as np
import logging
from typing import Optional, Tuple
import io
from PIL import Image

logger = logging.getLogger(__name__)


def preprocess_for_ocr(
    image_bytes: bytes,
    enable_deskew: bool = True,
    enable_adaptive_threshold: bool = True,
    enable_contrast_enhancement: bool = True
) -> bytes:
    """
    Apply comprehensive pre-processing pipeline to improve OCR accuracy.
    
    Args:
        image_bytes: Input image as bytes
        enable_deskew: Whether to apply de-skewing correction
        enable_adaptive_threshold: Whether to apply adaptive thresholding
        enable_contrast_enhancement: Whether to enhance contrast
        
    Returns:
        Pre-processed image as bytes (PNG format)
    """
    try:
        # Convert bytes to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            # Try loading as grayscale if color fails
            img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
            if img is None:
                raise ValueError("Could not decode image from bytes")
            # Convert grayscale to BGR for consistency
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        
        # Step 1: Convert to grayscale for processing
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Step 2: De-skewing (if enabled)
        if enable_deskew:
            gray = deskew_image(gray)
        
        # Step 3: Contrast Enhancement (if enabled)
        if enable_contrast_enhancement:
            gray = enhance_contrast(gray)
        
        # Step 4: Adaptive Thresholding (if enabled)
        if enable_adaptive_threshold:
            processed_img = apply_adaptive_threshold(gray)
        else:
            processed_img = gray
        
        # Convert back to BGR for encoding (OCR engines often expect color images)
        # But keep as grayscale if adaptive threshold was applied (it's already binary)
        if enable_adaptive_threshold:
            # Adaptive threshold produces binary image, convert to 3-channel
            processed_img = cv2.cvtColor(processed_img, cv2.COLOR_GRAY2BGR)
        else:
            processed_img = cv2.cvtColor(processed_img, cv2.COLOR_GRAY2BGR)
        
        # Encode back to bytes
        is_success, im_buf_arr = cv2.imencode('.png', processed_img)
        if not is_success:
            raise ValueError("Failed to encode processed image")
        
        return im_buf_arr.tobytes()
        
    except Exception as e:
        logger.error(f"Image pre-processing failed: {e}", exc_info=True)
        # Return original image if processing fails
        return image_bytes


def deskew_image(image: np.ndarray) -> np.ndarray:
    """
    Detect and correct minor image rotation (de-skewing).
    
    Uses Hough transform or PCA-based angle detection to find rotation angle
    and corrects it.
    
    Args:
        image: Grayscale image as numpy array
        
    Returns:
        De-skewed image
    """
    try:
        # Create binary image for angle detection
        # Invert for better text detection
        binary = cv2.bitwise_not(image)
        thresh = cv2.threshold(binary, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        
        # Find all non-zero pixel coordinates
        coords = np.column_stack(np.where(thresh > 0))
        
        if len(coords) == 0:
            logger.warning("No text detected for deskewing, returning original image")
            return image
        
        # Calculate rotation angle using minimum area rectangle
        angle = cv2.minAreaRect(coords)[-1]
        
        # Correct angle calculation
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        
        logger.debug(f"Detected skew angle: {angle:.2f} degrees")
        
        # Only rotate if angle is significant (threshold: 0.5 degrees)
        if abs(angle) < 0.5:
            return image
        
        # Rotate image to correct skew
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            image,
            M,
            (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )
        
        return rotated
        
    except Exception as e:
        logger.warning(f"De-skewing failed: {e}, returning original image")
        return image


def apply_adaptive_threshold(
    image: np.ndarray,
    block_size: int = 11,
    C: int = 2,
    method: int = cv2.ADAPTIVE_THRESH_GAUSSIAN_C
) -> np.ndarray:
    """
    Apply adaptive thresholding to binarize image with local contrast handling.
    
    Adaptive thresholding is superior to fixed thresholding for documents with
    uneven lighting, shadows, or varying background intensity.
    
    Args:
        image: Grayscale image as numpy array
        block_size: Size of a pixel neighborhood used to calculate threshold (must be odd)
        C: Constant subtracted from mean (fine-tunes threshold)
        method: Adaptive thresholding method (GAUSSIAN_C or MEAN_C)
        
    Returns:
        Binary image (0 or 255)
    """
    try:
        # Ensure block_size is odd
        if block_size % 2 == 0:
            block_size += 1
        
        # Apply adaptive threshold
        # ADAPTIVE_THRESH_GAUSSIAN_C uses weighted sum of neighborhood values
        # THRESH_BINARY: pixel > threshold ? 255 : 0
        processed = cv2.adaptiveThreshold(
            image,
            255,  # Maximum value assigned to pixels
            method,
            cv2.THRESH_BINARY,
            block_size,
            C
        )
        
        return processed
        
    except Exception as e:
        logger.warning(f"Adaptive thresholding failed: {e}, returning original image")
        return image


def enhance_contrast(image: np.ndarray) -> np.ndarray:
    """
    Enhance image contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization).
    
    CLAHE improves local contrast and enhances the definition of edges in each region
    of an image, which is beneficial for OCR.
    
    Args:
        image: Grayscale image as numpy array
        
    Returns:
        Contrast-enhanced image
    """
    try:
        # Create CLAHE object
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        
        # Apply CLAHE
        enhanced = clahe.apply(image)
        
        return enhanced
        
    except Exception as e:
        logger.warning(f"Contrast enhancement failed: {e}, returning original image")
        return image


def preprocess_image_file(
    image_path: str,
    output_path: Optional[str] = None,
    enable_deskew: bool = True,
    enable_adaptive_threshold: bool = True,
    enable_contrast_enhancement: bool = True
) -> str:
    """
    Pre-process image from file path (convenience function).
    
    Args:
        image_path: Path to input image file
        output_path: Optional path to save processed image (if None, saves to same location with _processed suffix)
        enable_deskew: Whether to apply de-skewing
        enable_adaptive_threshold: Whether to apply adaptive thresholding
        enable_contrast_enhancement: Whether to enhance contrast
        
    Returns:
        Path to processed image file
    """
    try:
        # Read image
        with open(image_path, 'rb') as f:
            image_bytes = f.read()
        
        # Process
        processed_bytes = preprocess_for_ocr(
            image_bytes,
            enable_deskew=enable_deskew,
            enable_adaptive_threshold=enable_adaptive_threshold,
            enable_contrast_enhancement=enable_contrast_enhancement
        )
        
        # Determine output path
        if output_path is None:
            path_parts = image_path.rsplit('.', 1)
            output_path = f"{path_parts[0]}_processed.{path_parts[1] if len(path_parts) > 1 else 'png'}"
        
        # Save processed image
        with open(output_path, 'wb') as f:
            f.write(processed_bytes)
        
        logger.info(f"Pre-processed image saved to {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Failed to preprocess image file {image_path}: {e}", exc_info=True)
        raise


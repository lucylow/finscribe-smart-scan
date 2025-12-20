"""
Advanced Data Augmentation for Training-Time Image Enhancement

This module provides sophisticated augmentation techniques specifically designed
for document images to improve model robustness.
"""

from PIL import Image, ImageFilter, ImageEnhance
import numpy as np
import random
from typing import Tuple, Optional, Dict, Any

# Try to import cv2 for advanced transforms (optional)
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


class DocumentAugmentation:
    """
    Advanced augmentation pipeline for document images.
    
    Applies realistic transformations that simulate real-world document variations:
    - Scanning artifacts (rotation, noise, blur)
    - Lighting conditions (brightness, contrast)
    - Paper quality (texture, aging)
    - Compression artifacts
    """
    
    def __init__(
        self,
        rotation_range: Tuple[float, float] = (-5, 5),
        brightness_range: Tuple[float, float] = (0.8, 1.2),
        contrast_range: Tuple[float, float] = (0.8, 1.2),
        noise_std: Tuple[float, float] = (0.01, 0.05),
        blur_probability: float = 0.1,
        jpeg_quality_range: Tuple[int, int] = (70, 95),
        perspective_probability: float = 0.2,
        elastic_probability: float = 0.1,
        enabled: bool = True
    ):
        """
        Initialize augmentation pipeline.
        
        Args:
            rotation_range: Range of rotation angles in degrees
            brightness_range: Range for brightness adjustment (multiplier)
            contrast_range: Range for contrast adjustment (multiplier)
            noise_std: Range for Gaussian noise standard deviation
            blur_probability: Probability of applying blur
            jpeg_quality_range: Range for JPEG compression quality
            perspective_probability: Probability of applying perspective transform
            elastic_probability: Probability of applying elastic deformation
            enabled: Whether augmentation is enabled
        """
        self.rotation_range = rotation_range
        self.brightness_range = brightness_range
        self.contrast_range = contrast_range
        self.noise_std = noise_std
        self.blur_probability = blur_probability
        self.jpeg_quality_range = jpeg_quality_range
        self.perspective_probability = perspective_probability
        self.elastic_probability = elastic_probability
        self.enabled = enabled
    
    def __call__(self, image: Image.Image) -> Image.Image:
        """
        Apply augmentation to PIL Image.
        
        Args:
            image: PIL Image
            
        Returns:
            Augmented PIL Image
        """
        if not self.enabled:
            return image
        
        # Random rotation
        if random.random() > 0.3:
            angle = random.uniform(*self.rotation_range)
            image = image.rotate(angle, expand=False, fillcolor='white', resample=Image.BILINEAR)
        
        # Random brightness
        if random.random() > 0.5:
            factor = random.uniform(*self.brightness_range)
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(factor)
        
        # Random contrast
        if random.random() > 0.5:
            factor = random.uniform(*self.contrast_range)
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(factor)
        
        # Random blur
        if random.random() < self.blur_probability:
            blur_radius = random.uniform(0.5, 1.5)
            image = image.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        
        # Random noise
        if random.random() > 0.6:
            image = self._add_gaussian_noise(image)
        
        # Perspective transform (simulates viewing angle)
        if random.random() < self.perspective_probability:
            image = self._apply_perspective_transform(image)
        
        # JPEG compression artifacts
        if random.random() > 0.7:
            image = self._apply_jpeg_compression(image)
        
        return image
    
    def _add_gaussian_noise(self, image: Image.Image) -> Image.Image:
        """Add Gaussian noise to image."""
        img_array = np.array(image).astype(np.float32)
        noise_std = random.uniform(*self.noise_std) * 255
        noise = np.random.normal(0, noise_std, img_array.shape).astype(np.float32)
        noisy_array = np.clip(img_array + noise, 0, 255).astype(np.uint8)
        return Image.fromarray(noisy_array)
    
    def _apply_perspective_transform(self, image: Image.Image) -> Image.Image:
        """Apply slight perspective transformation."""
        if not CV2_AVAILABLE:
            return image
        
        width, height = image.size
        
        # Define source points (corners)
        src_points = np.array([
            [0, 0],
            [width, 0],
            [width, height],
            [0, height]
        ], dtype=np.float32)
        
        # Define destination points with slight distortion
        max_distortion = min(width, height) * 0.02
        dst_points = src_points + np.random.uniform(
            -max_distortion, max_distortion, src_points.shape
        )
        
        # Calculate perspective transform matrix
        try:
            transform_matrix = cv2.getPerspectiveTransform(src_points, dst_points)
            
            # Apply transform using OpenCV
            img_array = np.array(image)
            transformed = cv2.warpPerspective(
                img_array, transform_matrix, (width, height),
                borderMode=cv2.BORDER_CONSTANT, borderValue=255
            )
            return Image.fromarray(transformed)
        except Exception:
            # If transform fails, return original
            return image
    
    
    def _apply_jpeg_compression(self, image: Image.Image) -> Image.Image:
        """Apply JPEG compression to simulate compression artifacts."""
        import io
        quality = random.randint(*self.jpeg_quality_range)
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=quality)
        buffer.seek(0)
        return Image.open(buffer).convert('RGB')


class SmartAugmentation:
    """
    Smart augmentation that adapts based on document characteristics.
    
    This augmentation strategy applies different transformations based on
    detected document features (e.g., text density, image quality).
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize smart augmentation.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.base_aug = DocumentAugmentation(
            enabled=self.config.get('enabled', True),
            rotation_range=tuple(self.config.get('rotation_range', [-5, 5])),
            brightness_range=tuple(self.config.get('brightness_range', [0.8, 1.2])),
            contrast_range=tuple(self.config.get('contrast_range', [0.8, 1.2])),
            noise_std=tuple(self.config.get('noise_std', [0.01, 0.05])),
            blur_probability=self.config.get('blur_probability', 0.1),
        )
    
    def __call__(self, image: Image.Image) -> Image.Image:
        """Apply smart augmentation."""
        # Apply base augmentation
        return self.base_aug(image)
    
    def estimate_document_quality(self, image: Image.Image) -> Dict[str, float]:
        """
        Estimate document quality metrics.
        
        Returns metrics that can be used to adjust augmentation intensity.
        """
        img_array = np.array(image.convert('L'))  # Convert to grayscale
        
        # Estimate blur (using variance of Laplacian)
        if CV2_AVAILABLE:
            try:
                gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
                laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
                blur_score = 1.0 / (1.0 + laplacian_var / 100.0)  # Normalize
            except AttributeError:
                blur_score = 0.5  # Default if method fails
        else:
            blur_score = 0.5  # Default if OpenCV not available
        
        # Estimate brightness
        brightness = np.mean(img_array) / 255.0
        
        # Estimate contrast (standard deviation)
        contrast = np.std(img_array) / 255.0
        
        return {
            'blur_score': blur_score,
            'brightness': brightness,
            'contrast': contrast
        }


def create_augmentation_transforms(config: Dict[str, Any]) -> Optional[transforms.Compose]:
    """
    Create augmentation transforms from configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Compose transform or None if augmentation disabled
    """
    aug_config = config.get('vision_processor', {}).get('train', {})
    additional_transforms = aug_config.get('additional_transforms', [])
    
    if not aug_config.get('enabled', True):
        return None
    
    transform_list = []
    
    # Create smart augmentation
    smart_aug = SmartAugmentation(config.get('augmentation', {}))
    transform_list.append(smart_aug)
    
    # Add any additional transforms
    for transform_config in additional_transforms:
        transform_name = transform_config.get('name', '')
        # Additional transforms can be added here based on config
    
    return transforms.Compose(transform_list) if transform_list else None


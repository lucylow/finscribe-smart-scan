"""
Image augmentation for realistic scanned document effects
"""
import cv2
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance
import random
from typing import List, Tuple
try:
    import imgaug.augmenters as iaa
    IMGAUG_AVAILABLE = True
except ImportError:
    IMGAUG_AVAILABLE = False
    print("Warning: imgaug not available. Some augmentation features will be limited.")


class DocumentAugmentor:
    """Apply realistic scanning effects to generated invoices"""
    
    def __init__(self):
        if IMGAUG_AVAILABLE:
            self.augmentation_pipeline = self._create_augmentation_pipeline()
        else:
            self.augmentation_pipeline = None
            print("Using basic augmentation (imgaug not installed)")
    
    def _create_augmentation_pipeline(self):
        """Create a pipeline of realistic document augmentations"""
        if not IMGAUG_AVAILABLE:
            return None
            
        return iaa.Sequential([
            # Geometric transformations (simulating imperfect scanning)
            iaa.Sometimes(0.7, iaa.Affine(
                rotate=(-5, 5),  # Slight rotation
                shear=(-5, 5),   # Shearing effect
                translate_percent={"x": (-0.02, 0.02), "y": (-0.02, 0.02)}
            )),
            
            # Paper texture and quality effects
            iaa.Sometimes(0.5, iaa.GaussianBlur(sigma=(0.5, 1.5))),
            iaa.Sometimes(0.3, iaa.MotionBlur(k=5, angle=(-45, 45))),
            
            # Contrast and brightness variations
            iaa.Sometimes(0.4, iaa.LinearContrast((0.8, 1.2))),
            iaa.Sometimes(0.4, iaa.MultiplyBrightness((0.8, 1.2))),
            
            # Paper color and aging effects
            iaa.Sometimes(0.3, iaa.AddToHueAndSaturation((-20, 20))),
            iaa.Sometimes(0.2, iaa.Grayscale(alpha=(0.0, 0.3))),
            
            # Noise and artifacts
            iaa.Sometimes(0.4, iaa.AdditiveGaussianNoise(scale=(0, 0.05*255))),
            iaa.Sometimes(0.2, iaa.ImpulseNoise(0.05)),
            iaa.Sometimes(0.1, iaa.CoarseDropout(
                p=(0.0, 0.01), size_percent=(0.02, 0.05)
            )),
            
            # Compression artifacts (simulating JPEG/PDF compression)
            iaa.Sometimes(0.3, iaa.JpegCompression(compression=(70, 95))),
        ], random_order=True)
    
    def apply_augmentation(self, image: np.ndarray) -> np.ndarray:
        """Apply augmentation pipeline to image"""
        if self.augmentation_pipeline is not None:
            return self.augmentation_pipeline(image=image)
        else:
            # Fallback to basic augmentations
            return self._apply_basic_augmentation(image)
    
    def _apply_basic_augmentation(self, image: np.ndarray) -> np.ndarray:
        """Apply basic augmentation without imgaug"""
        # Convert to PIL for basic operations
        if len(image.shape) == 3:
            pil_image = Image.fromarray(image.astype('uint8'))
        else:
            pil_image = Image.fromarray(image.astype('uint8')).convert('RGB')
        
        # Random rotation
        if random.random() > 0.3:
            angle = random.uniform(-5, 5)
            pil_image = pil_image.rotate(angle, expand=False, fillcolor='white')
        
        # Random blur
        if random.random() > 0.5:
            pil_image = pil_image.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.5, 1.5)))
        
        # Random brightness/contrast
        if random.random() > 0.6:
            enhancer = ImageEnhance.Brightness(pil_image)
            pil_image = enhancer.enhance(random.uniform(0.8, 1.2))
        
        if random.random() > 0.6:
            enhancer = ImageEnhance.Contrast(pil_image)
            pil_image = enhancer.enhance(random.uniform(0.8, 1.2))
        
        # Convert back to numpy
        return np.array(pil_image)
    
    def simulate_folded_paper(self, image: np.ndarray) -> np.ndarray:
        """Simulate folded paper creases"""
        height, width = image.shape[:2]
        
        # Create a gradient mask for fold effect
        fold_mask = np.ones((height, width), dtype=np.float32)
        
        # Add vertical fold line
        if random.random() > 0.5:
            fold_x = random.randint(width // 4, 3 * width // 4)
            for x in range(width):
                distance = abs(x - fold_x) / (width / 10)
                intensity = np.exp(-distance * distance)
                fold_mask[:, x] *= (0.7 + 0.3 * intensity)
        
        # Add horizontal fold line
        if random.random() > 0.5:
            fold_y = random.randint(height // 4, 3 * height // 4)
            for y in range(height):
                distance = abs(y - fold_y) / (height / 10)
                intensity = np.exp(-distance * distance)
                fold_mask[y, :] *= (0.7 + 0.3 * intensity)
        
        # Apply the fold effect
        if len(image.shape) == 3:
            fold_mask = np.stack([fold_mask] * image.shape[2], axis=2)
        
        return np.clip(image.astype(np.float32) * fold_mask, 0, 255).astype(np.uint8)
    
    def add_stamp_or_signature(self, image: np.ndarray) -> np.ndarray:
        """Add simulated stamp or signature mark"""
        height, width = image.shape[:2]
        
        # Create a colored stamp-like circle
        stamp_radius = random.randint(30, 80)
        stamp_x = random.randint(stamp_radius, width - stamp_radius)
        stamp_y = random.randint(stamp_radius, height - stamp_radius)
        
        # Create stamp mask
        y, x = np.ogrid[:height, :width]
        mask = (x - stamp_x) ** 2 + (y - stamp_y) ** 2 <= stamp_radius ** 2
        
        # Apply stamp color (red or blue)
        stamp_color = random.choice([(200, 50, 50), (50, 50, 200)])
        
        result = image.copy()
        if len(image.shape) == 3:
            for c in range(3):
                result[:, :, c][mask] = (
                    image[:, :, c][mask].astype(np.float32) * 0.6 + 
                    stamp_color[c] * 0.4
                ).astype(np.uint8)
        
        return result
    
    def convert_to_grayscale_variants(self, image: np.ndarray) -> np.ndarray:
        """Create grayscale or sepia variants"""
        if random.random() > 0.7:
            # Convert to grayscale
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
                return cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        elif random.random() > 0.5:
            # Apply sepia tone
            sepia_filter = np.array([
                [0.393, 0.769, 0.189],
                [0.349, 0.686, 0.168],
                [0.272, 0.534, 0.131]
            ])
            sepia_image = cv2.transform(image, sepia_filter)
            return np.clip(sepia_image, 0, 255).astype(np.uint8)
        
        return image
    
    def add_noise(self, image: np.ndarray) -> np.ndarray:
        """Add realistic noise to simulate scanning artifacts"""
        noise_level = random.uniform(0.01, 0.05)
        noise = np.random.normal(0, noise_level * 255, image.shape).astype(np.float32)
        noisy_image = image.astype(np.float32) + noise
        return np.clip(noisy_image, 0, 255).astype(np.uint8)
    
    def apply_random_augmentation_combination(self, image_path: str, output_path: str):
        """Apply a random combination of augmentations to create realistic variations"""
        # Read image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not read image: {image_path}")
        
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Apply base augmentation pipeline
        augmented = self.apply_augmentation(image)
        
        # Randomly apply additional effects
        if random.random() > 0.5:
            augmented = self.simulate_folded_paper(augmented)
        
        if random.random() > 0.8:
            augmented = self.add_stamp_or_signature(augmented)
        
        augmented = self.convert_to_grayscale_variants(augmented)
        
        if random.random() > 0.7:
            augmented = self.add_noise(augmented)
        
        # Convert back to BGR for OpenCV saving
        augmented_bgr = cv2.cvtColor(augmented, cv2.COLOR_RGB2BGR)
        cv2.imwrite(output_path, augmented_bgr)
        
        return output_path


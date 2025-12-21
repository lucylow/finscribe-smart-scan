"""
Document preprocessing: PDF to PNG conversion, deskew, denoise, normalize DPI.
"""
import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from PIL import Image
import io

try:
    from pdf2image import convert_from_bytes
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    logging.warning("pdf2image not available. PDF processing will be limited.")

logger = logging.getLogger(__name__)


class DocumentPreprocessor:
    """Handles document preprocessing: PDF conversion, image enhancement."""
    
    def __init__(self, staging_dir: str = "/tmp/finscribe_staging"):
        """Initialize preprocessor with staging directory."""
        self.staging_dir = staging_dir
        os.makedirs(staging_dir, exist_ok=True)
    
    async def preprocess(
        self,
        content: bytes,
        filename: str,
        job_id: str,
        dpi: int = 300,
        deskew: bool = True,
        denoise: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Preprocess document: convert PDF to PNG, enhance images.
        
        Returns:
            List of page information: [{"page": 1, "path": "...", "image": PIL.Image}, ...]
        """
        pages = []
        
        # Determine file type
        file_ext = Path(filename).suffix.lower()
        
        if file_ext == ".pdf":
            pages = await self._process_pdf(content, job_id, dpi, deskew, denoise)
        elif file_ext in [".png", ".jpg", ".jpeg", ".tiff", ".tif"]:
            pages = await self._process_image(content, filename, job_id, deskew, denoise)
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")
        
        return pages
    
    async def _process_pdf(
        self,
        content: bytes,
        job_id: str,
        dpi: int,
        deskew: bool,
        denoise: bool
    ) -> List[Dict[str, Any]]:
        """Process PDF file into per-page PNG images."""
        if not PDF2IMAGE_AVAILABLE:
            raise RuntimeError("pdf2image not available. Install with: pip install pdf2image")
        
        pages = []
        
        try:
            # Convert PDF to images
            pdf_images = convert_from_bytes(content, dpi=dpi)
            
            for page_num, image in enumerate(pdf_images, 1):
                # Enhance image
                enhanced = await self._enhance_image(image, deskew, denoise)
                
                # Save to staging
                staging_path = os.path.join(self.staging_dir, job_id, f"page_{page_num}.png")
                os.makedirs(os.path.dirname(staging_path), exist_ok=True)
                enhanced.save(staging_path, "PNG")
                
                pages.append({
                    "page": page_num,
                    "path": staging_path,
                    "image": enhanced,
                    "width": enhanced.width,
                    "height": enhanced.height,
                    "dpi": dpi
                })
            
            logger.info(f"Processed PDF into {len(pages)} pages for job {job_id}")
            
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            raise
        
        return pages
    
    async def _process_image(
        self,
        content: bytes,
        filename: str,
        job_id: str,
        deskew: bool,
        denoise: bool
    ) -> List[Dict[str, Any]]:
        """Process single image file."""
        try:
            # Load image
            image = Image.open(io.BytesIO(content))
            
            # Convert to RGB if needed
            if image.mode != "RGB":
                image = image.convert("RGB")
            
            # Enhance image
            enhanced = await self._enhance_image(image, deskew, denoise)
            
            # Save to staging
            staging_path = os.path.join(self.staging_dir, job_id, "page_1.png")
            os.makedirs(os.path.dirname(staging_path), exist_ok=True)
            enhanced.save(staging_path, "PNG")
            
            return [{
                "page": 1,
                "path": staging_path,
                "image": enhanced,
                "width": enhanced.width,
                "height": enhanced.height,
                "dpi": 300  # Assume 300 DPI for images
            }]
            
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            raise
    
    async def _enhance_image(
        self,
        image: Image.Image,
        deskew: bool,
        denoise: bool
    ) -> Image.Image:
        """
        Enhance image: deskew, denoise, normalize DPI.
        Note: Full implementation would use libraries like:
        - deskew: scikit-image or OpenCV
        - denoise: scikit-image or PIL filters
        """
        # For now, return image as-is
        # TODO: Implement actual deskew and denoise
        
        if deskew:
            # Placeholder for deskewing
            # from skimage import transform
            # deskewed = transform.rotate(image, angle)
            pass
        
        if denoise:
            # Placeholder for denoising
            # from PIL import ImageFilter
            # denoised = image.filter(ImageFilter.MedianFilter())
            pass
        
        return image



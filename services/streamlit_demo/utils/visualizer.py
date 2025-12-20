"""
Visualization utilities for OCR results.
Creates annotated images with bounding boxes and labels.
"""
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from typing import List, Dict, Optional
import os


class DocumentVisualizer:
    """Create visualizations for OCR results"""
    
    def __init__(self):
        """Initialize the visualizer with color scheme"""
        self.colors = {
            'vendor': (41, 128, 185),      # Blue
            'client': (39, 174, 96),       # Green
            'line_items': (142, 68, 173),  # Purple
            'tax': (230, 126, 34),         # Orange
            'totals': (231, 76, 60),       # Red
            'text': (52, 73, 94),          # Dark gray
            'header': (155, 89, 182),      # Light purple
            'table': (241, 196, 15)        # Yellow
        }
        
        # Try to load a font, fallback to default if not available
        try:
            self.font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
            self.font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
        except:
            try:
                self.font = ImageFont.truetype("arial.ttf", 12)
                self.font_large = ImageFont.truetype("arial.ttf", 14)
            except:
                self.font = ImageFont.load_default()
                self.font_large = ImageFont.load_default()
    
    def visualize_results(
        self, 
        image: np.ndarray, 
        regions: List[Dict],
        extracted_data: Optional[Dict] = None
    ) -> np.ndarray:
        """
        Create visualization with colored bounding boxes.
        
        Args:
            image: Original image (BGR format)
            regions: List of region dictionaries with type, bbox, and text
            extracted_data: Optional structured data for additional annotations
            
        Returns:
            Annotated image (BGR format)
        """
        # Convert to PIL for drawing
        pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_image, 'RGBA')
        
        # Draw each region
        for region in regions:
            region_type = region.get('type', 'text')
            bbox = region.get('bbox', [])
            
            if not bbox or len(bbox) < 4:
                continue
            
            # Get color for this region type
            color = self.colors.get(region_type.lower(), self.colors['text'])
            
            # Draw semi-transparent rectangle
            x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
            draw.rectangle(
                [x1, y1, x2, y2],
                outline=color + (255,),  # Add alpha
                fill=color + (30,),      # Semi-transparent fill
                width=3
            )
            
            # Add label
            text = region.get('text', region_type)
            if text:
                self._add_text_label(draw, bbox, region_type, text)
        
        # Add summary annotations if structured data is provided
        if extracted_data:
            self._add_summary_annotations(draw, pil_image.size, extracted_data)
        
        # Convert back to OpenCV format
        return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    
    def _add_text_label(
        self, 
        draw: ImageDraw.Draw, 
        bbox: List[int], 
        region_type: str, 
        text: str
    ):
        """Add a text label near the bounding box"""
        x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
        
        # Truncate text if too long
        display_text = text[:30] + '...' if len(text) > 30 else text
        label = f"{region_type.upper()}: {display_text}"
        
        # Calculate text position (above the box)
        text_y = max(0, y1 - 20)
        
        # Draw text background
        bbox_text = draw.textbbox((x1, text_y), label, font=self.font)
        draw.rectangle(
            bbox_text,
            fill=(255, 255, 255, 200),  # White background with transparency
            outline=(0, 0, 0, 255),
            width=1
        )
        
        # Draw text
        draw.text(
            (x1, text_y),
            label,
            fill=(0, 0, 0, 255),
            font=self.font
        )
    
    def _add_summary_annotations(
        self, 
        draw: ImageDraw.Draw, 
        image_size: tuple, 
        extracted_data: Dict
    ):
        """Add summary annotations at the bottom of the image"""
        width, height = image_size
        
        # Extract key information
        summary_items = []
        
        vendor = extracted_data.get('vendor', {}).get('name')
        if vendor:
            summary_items.append(f"Vendor: {vendor}")
        
        invoice_num = extracted_data.get('client', {}).get('invoice_number')
        if invoice_num:
            summary_items.append(f"Invoice #: {invoice_num}")
        
        total = extracted_data.get('financial_summary', {}).get('grand_total')
        if total:
            summary_items.append(f"Total: ${total:,.2f}")
        
        # Draw summary box
        if summary_items:
            box_height = len(summary_items) * 25 + 10
            box_y = height - box_height - 10
            
            # Draw background
            draw.rectangle(
                [(10, box_y), (width - 10, height - 10)],
                fill=(0, 0, 0, 180),
                outline=(255, 255, 255, 255),
                width=2
            )
            
            # Draw text items
            for idx, item in enumerate(summary_items):
                text_y = box_y + 5 + idx * 25
                draw.text(
                    (15, text_y),
                    item,
                    fill=(255, 255, 255, 255),
                    font=self.font_large
                )
    
    def create_comparison_overlay(
        self,
        original_image: np.ndarray,
        ft_results: Dict,
        vanilla_results: Dict
    ) -> np.ndarray:
        """
        Create a side-by-side comparison visualization.
        
        Args:
            original_image: Original document image
            ft_results: Fine-tuned model results
            vanilla_results: Vanilla model results
            
        Returns:
            Combined comparison image
        """
        h, w = original_image.shape[:2]
        
        # Create side-by-side layout
        comparison = np.zeros((h, w * 2, 3), dtype=np.uint8)
        
        # Left side: Fine-tuned results
        ft_viz = self.visualize_results(
            original_image,
            ft_results.get('metadata', {}).get('regions', []),
            ft_results.get('data', {})
        )
        comparison[:, :w] = ft_viz
        
        # Right side: Vanilla results
        vanilla_viz = self.visualize_results(
            original_image,
            vanilla_results.get('metadata', {}).get('regions', []),
            vanilla_results.get('data', {})
        )
        comparison[:, w:] = vanilla_viz
        
        # Add labels
        pil_comp = Image.fromarray(cv2.cvtColor(comparison, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_comp)
        
        # Fine-tuned label
        draw.text((10, 10), "Fine-Tuned Model", fill=(255, 255, 255, 255), font=self.font_large)
        
        # Vanilla label
        draw.text((w + 10, 10), "Vanilla PaddleOCR", fill=(255, 255, 255, 255), font=self.font_large)
        
        return cv2.cvtColor(np.array(pil_comp), cv2.COLOR_RGB2BGR)


def visualize_ocr_results(image: np.ndarray, results: Dict) -> np.ndarray:
    """
    Convenience function to visualize OCR results.
    
    Args:
        image: Original image
        results: Results dictionary from model
        
    Returns:
        Annotated image
    """
    visualizer = DocumentVisualizer()
    regions = results.get('metadata', {}).get('regions', [])
    extracted_data = results.get('data', {})
    return visualizer.visualize_results(image, regions, extracted_data)


def create_comparison_gif(
    original_image: np.ndarray,
    ft_results: Dict,
    vanilla_results: Dict,
    output_path: str
) -> str:
    """
    Create an animated GIF comparing both models.
    
    Args:
        original_image: Original document image
        ft_results: Fine-tuned model results
        vanilla_results: Vanilla model results
        output_path: Path to save the GIF
        
    Returns:
        Path to saved GIF
    """
    visualizer = DocumentVisualizer()
    
    # Create frames
    frames = []
    
    # Frame 1: Original
    frames.append(Image.fromarray(cv2.cvtColor(original_image, cv2.COLOR_BGR2RGB)))
    
    # Frame 2: Fine-tuned results
    ft_viz = visualizer.visualize_results(
        original_image,
        ft_results.get('metadata', {}).get('regions', []),
        ft_results.get('data', {})
    )
    frames.append(Image.fromarray(cv2.cvtColor(ft_viz, cv2.COLOR_BGR2RGB)))
    
    # Frame 3: Vanilla results
    vanilla_viz = visualizer.visualize_results(
        original_image,
        vanilla_results.get('metadata', {}).get('regions', []),
        vanilla_results.get('data', {})
    )
    frames.append(Image.fromarray(cv2.cvtColor(vanilla_viz, cv2.COLOR_BGR2RGB)))
    
    # Frame 4: Comparison overlay
    comparison = visualizer.create_comparison_overlay(original_image, ft_results, vanilla_results)
    frames.append(Image.fromarray(cv2.cvtColor(comparison, cv2.COLOR_BGR2RGB)))
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save as GIF
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=1500,  # 1.5 seconds per frame
        loop=0
    )
    
    return output_path

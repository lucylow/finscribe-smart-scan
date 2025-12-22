"""
Visualization utilities for OCR results.

Provides confidence heatmaps and bounding box overlays for debugging and demos.
"""

import io
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
import logging

logger = logging.getLogger(__name__)


def draw_ocr_overlay(
    image_bytes: bytes,
    regions: List[Dict[str, Any]],
    show_confidence: bool = True,
    show_text: bool = True,
    min_confidence: float = 0.0
) -> Image.Image:
    """
    Draw OCR bounding boxes and confidence heatmap overlay on image.
    
    Args:
        image_bytes: Original image bytes
        regions: List of OCR regions with 'bbox' and 'confidence' fields
        show_confidence: Whether to color-code by confidence
        show_text: Whether to draw text labels on boxes
        min_confidence: Minimum confidence to display (filter out low-confidence regions)
        
    Returns:
        PIL Image with overlays drawn
    """
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        draw = ImageDraw.Draw(img)
        
        # Try to load a font, fallback to default if not available
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
        except (OSError, IOError):
            try:
                font = ImageFont.truetype("arial.ttf", 12)
            except (OSError, IOError):
                font = ImageFont.load_default()
        
        for region in regions:
            confidence = region.get("confidence", 0.5)
            
            # Skip low-confidence regions
            if confidence < min_confidence:
                continue
            
            bbox = region.get("bbox", [])
            if len(bbox) < 4:
                continue
            
            x, y, w, h = bbox[0], bbox[1], bbox[2], bbox[3]
            
            # Color-code by confidence: green (high) -> yellow (medium) -> red (low)
            if show_confidence:
                # Map confidence 0-1 to color gradient
                # High confidence (0.9-1.0): Green
                # Medium confidence (0.7-0.9): Yellow
                # Low confidence (0.0-0.7): Red
                if confidence >= 0.9:
                    color = (0, 255, 0)  # Green
                elif confidence >= 0.7:
                    # Interpolate between yellow and green
                    ratio = (confidence - 0.7) / 0.2
                    color = (int(255 * (1 - ratio)), 255, 0)  # Yellow to Green
                else:
                    # Interpolate between red and yellow
                    ratio = confidence / 0.7
                    color = (255, int(255 * ratio), 0)  # Red to Yellow
            else:
                color = (0, 255, 0)  # Default green
            
            # Draw bounding box
            draw.rectangle([x, y, x + w, y + h], outline=color, width=2)
            
            # Draw text label if enabled
            if show_text:
                text = region.get("text", "")
                # Truncate long text
                if len(text) > 30:
                    text = text[:27] + "..."
                
                # Draw background for text (semi-transparent)
                text_bbox = draw.textbbox((x, y - 15), text, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                draw.rectangle(
                    [x, y - text_height - 2, x + text_width + 4, y],
                    fill=(0, 0, 0, 180),
                    outline=color
                )
                
                # Draw text
                draw.text((x + 2, y - text_height), text, fill=color, font=font)
                
                # Draw confidence score
                conf_text = f"{confidence:.2f}"
                conf_bbox = draw.textbbox((x + w - 40, y), conf_text, font=font)
                conf_width = conf_bbox[2] - conf_bbox[0]
                draw.rectangle(
                    [x + w - conf_width - 4, y, x + w, y + text_height + 2],
                    fill=(0, 0, 0, 180),
                    outline=color
                )
                draw.text((x + w - conf_width - 2, y), conf_text, fill=color, font=font)
        
        return img
        
    except Exception as e:
        logger.error(f"Failed to draw OCR overlay: {str(e)}")
        raise


def image_to_bytes(img: Image.Image, format: str = "PNG") -> bytes:
    """
    Convert PIL Image to bytes.
    
    Args:
        img: PIL Image object
        format: Image format (PNG, JPEG, etc.)
        
    Returns:
        Image bytes
    """
    buf = io.BytesIO()
    img.save(buf, format=format)
    bytes_data = buf.getvalue()
    buf.close()
    return bytes_data


def create_confidence_heatmap(
    image_bytes: bytes,
    regions: List[Dict[str, Any]],
    alpha: float = 0.5
) -> Image.Image:
    """
    Create a confidence heatmap overlay (more sophisticated than simple boxes).
    
    Args:
        image_bytes: Original image bytes
        regions: List of OCR regions
        alpha: Transparency of heatmap overlay (0.0 = transparent, 1.0 = opaque)
        
    Returns:
        PIL Image with confidence heatmap overlay
    """
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        
        # Create overlay image
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        for region in regions:
            confidence = region.get("confidence", 0.5)
            bbox = region.get("bbox", [])
            
            if len(bbox) < 4:
                continue
            
            x, y, w, h = bbox[0], bbox[1], bbox[2], bbox[3]
            
            # Color based on confidence
            # High confidence: Green (0, 255, 0)
            # Medium confidence: Yellow (255, 255, 0)
            # Low confidence: Red (255, 0, 0)
            if confidence >= 0.8:
                r, g, b = 0, 255, 0
            elif confidence >= 0.6:
                # Interpolate yellow
                ratio = (confidence - 0.6) / 0.2
                r, g, b = int(255 * (1 - ratio)), 255, 0
            else:
                # Interpolate red
                ratio = confidence / 0.6
                r, g, b = 255, int(255 * ratio), 0
            
            # Draw semi-transparent rectangle
            overlay_draw.rectangle(
                [x, y, x + w, y + h],
                fill=(r, g, b, int(255 * alpha))
            )
        
        # Composite overlay onto original image
        result = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        return result
        
    except Exception as e:
        logger.error(f"Failed to create confidence heatmap: {str(e)}")
        raise


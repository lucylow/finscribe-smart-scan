# backend/ocr/layout.py
"""
Layout detection wrapper for document structure analysis.
Supports PP-DocLayoutV2 and fallback heuristic methods.
"""
import os
import logging
import cv2
import numpy as np
from typing import List, Dict, Any, Optional

LOG = logging.getLogger(__name__)

# Environment variable to control layout backend
LAYOUT_BACKEND = os.getenv("LAYOUT_BACKEND", "heuristic")  # Options: pp_doclayout, heuristic


def detect_layout_heuristic(image_path: str) -> List[Dict[str, Any]]:
    """
    Heuristic layout detection using contour analysis.
    Falls back to this method when PP-DocLayoutV2 is not available.
    
    Args:
        image_path: Path to image file
    
    Returns:
        List of layout boxes with labels and scores
    """
    img = cv2.imread(image_path)
    if img is None:
        # Try with Chinese path support
        img = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
    
    if img is None:
        LOG.error(f"Failed to load image for layout detection: {image_path}")
        return []
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    
    # Detect horizontal lines (table separators, headers)
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    detected_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
    h_contours, _ = cv2.findContours(detected_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Detect vertical lines
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
    detected_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
    v_contours, _ = cv2.findContours(detected_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    boxes = []
    
    # Add horizontal regions (headers, separators)
    for i, contour in enumerate(h_contours[:10]):  # Limit to top 10
        x, y, w_box, h_box = cv2.boundingRect(contour)
        if w_box > w * 0.3:  # Only significant horizontal lines
            boxes.append({
                "bbox": [x, y, x + w_box, y + h_box],
                "label": "header" if y < h * 0.2 else "separator",
                "score": 0.7,
                "tokens": []
            })
    
    # Add vertical regions (columns)
    for i, contour in enumerate(v_contours[:10]):
        x, y, w_box, h_box = cv2.boundingRect(contour)
        if h_box > h * 0.3:  # Only significant vertical lines
            boxes.append({
                "bbox": [x, y, x + w_box, y + h_box],
                "label": "column",
                "score": 0.7,
                "tokens": []
            })
    
    # Add default regions if no boxes found
    if not boxes:
        LOG.warning("No layout boxes detected, using default regions")
        boxes = [
            {
                "bbox": [0, 0, w, int(h * 0.15)],
                "label": "header",
                "score": 0.5,
                "tokens": []
            },
            {
                "bbox": [0, int(h * 0.15), w, int(h * 0.85)],
                "label": "body",
                "score": 0.5,
                "tokens": []
            },
            {
                "bbox": [0, int(h * 0.85), w, h],
                "label": "footer",
                "score": 0.5,
                "tokens": []
            }
        ]
    
    LOG.debug(f"Heuristic layout detection found {len(boxes)} regions")
    return boxes


def detect_layout_pp_doclayout(image_path: str) -> List[Dict[str, Any]]:
    """
    Layout detection using PP-DocLayoutV2 (if available).
    
    Args:
        image_path: Path to image file
    
    Returns:
        List of layout boxes with labels and scores
    """
    try:
        # Attempt to import and use PP-DocLayoutV2
        # This is a placeholder - actual implementation would depend on
        # how PP-DocLayoutV2 is packaged/distributed
        from paddleocr import PPStructure
        
        table_engine = PPStructure(show_log=False)
        result = table_engine(image_path)
        
        boxes = []
        for item in result:
            if 'bbox' in item:
                boxes.append({
                    "bbox": item['bbox'],
                    "label": item.get('type', 'text'),
                    "score": item.get('res', {}).get('score', 0.9),
                    "tokens": item.get('res', {}).get('text', '')
                })
        
        LOG.debug(f"PP-DocLayoutV2 found {len(boxes)} regions")
        return boxes
    except ImportError:
        LOG.warning("PP-DocLayoutV2 not available, falling back to heuristic")
        return detect_layout_heuristic(image_path)
    except Exception as e:
        LOG.error(f"PP-DocLayoutV2 detection failed: {e}, falling back to heuristic", exc_info=True)
        return detect_layout_heuristic(image_path)


def detect_layout(image_path: str) -> List[Dict[str, Any]]:
    """
    Main layout detection interface.
    Routes to appropriate backend based on LAYOUT_BACKEND environment variable.
    
    Args:
        image_path: Path to image file
    
    Returns:
        List of layout boxes with labels, scores, and tokens
    """
    if not os.path.exists(image_path):
        # Try with Chinese path support check
        if not os.path.isfile(image_path):
            LOG.error(f"Layout detection: image file not found: {image_path}")
            return []
    
    start_time = os.times().elapsed if hasattr(os.times(), 'elapsed') else None
    
    try:
        if LAYOUT_BACKEND == "pp_doclayout":
            result = detect_layout_pp_doclayout(image_path)
        else:
            result = detect_layout_heuristic(image_path)
        
        if start_time:
            elapsed = (os.times().elapsed - start_time) * 1000 if hasattr(os.times(), 'elapsed') else 0
            LOG.debug(f"Layout detection completed in {elapsed:.2f}ms")
        
        return result
    except Exception as e:
        LOG.error(f"Layout detection failed: {e}", exc_info=True)
        return []


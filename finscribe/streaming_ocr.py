"""
Async streaming OCR capability.

Streams region-level OCR results as they finish, providing real-time updates.
"""

import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from celery import shared_task
from finscribe.ocr_client import get_ocr_client
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class StreamingOCRStorage:
    """Simple storage interface for streaming OCR results."""
    
    def __init__(self, base_path: str = "/tmp/finscribe_streaming"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def append_region(self, job_id: str, region: Dict[str, Any]) -> str:
        """
        Append a region result to the streaming output file.
        
        Args:
            job_id: Job identifier
            region: Region data dictionary
            
        Returns:
            Path to the results file
        """
        results_file = self.base_path / f"{job_id}_regions.jsonl"
        
        with open(results_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(region, ensure_ascii=False) + "\n")
        
        return str(results_file)
    
    def get_all_regions(self, job_id: str) -> List[Dict[str, Any]]:
        """Get all regions collected so far."""
        results_file = self.base_path / f"{job_id}_regions.jsonl"
        
        if not results_file.exists():
            return []
        
        regions = []
        with open(results_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    region = json.loads(line.strip())
                    regions.append(region)
                except json.JSONDecodeError:
                    continue
        
        return regions
    
    def clear_results(self, job_id: str):
        """Clear results for a job."""
        results_file = self.base_path / f"{job_id}_regions.jsonl"
        if results_file.exists():
            results_file.unlink()


# Global storage instance
_storage: Optional[StreamingOCRStorage] = None


def get_storage() -> StreamingOCRStorage:
    """Get or create storage instance."""
    global _storage
    if _storage is None:
        _storage = StreamingOCRStorage()
    return _storage


@shared_task(bind=True, name="finscribe.streaming_ocr.ocr_region_task")
def ocr_region_task(self, job_id: str, region: Dict[str, Any]):
    """
    Process a single OCR region and stream the result.
    
    Args:
        job_id: Job identifier
        region: Region dictionary with 'image_path' or 'image_bytes' and 'bbox'
        
    Returns:
        OCR artifact dictionary
    """
    try:
        ocr_client = get_ocr_client()
        
        # Get image data
        if "image_bytes" in region:
            image_bytes = region["image_bytes"]
        elif "image_path" in region:
            with open(region["image_path"], "rb") as f:
                image_bytes = f.read()
        else:
            raise ValueError("Region must have 'image_bytes' or 'image_path'")
        
        # Run OCR
        regions = ocr_client.analyze_image_bytes(image_bytes)
        
        # For region-level OCR, we expect a single region result
        if regions:
            ocr_result = regions[0]
        else:
            ocr_result = {
                "text": "",
                "bbox": region.get("bbox", [0, 0, 0, 0]),
                "confidence": 0.0
            }
        
        # Create artifact
        artifact = {
            "region_id": region.get("id", f"region_{job_id}"),
            "text": ocr_result.get("text", ""),
            "confidence": ocr_result.get("confidence", 0.0),
            "bbox": region.get("bbox", ocr_result.get("bbox", [0, 0, 0, 0])),
            "job_id": job_id,
        }
        
        # Stream result
        storage = get_storage()
        storage.append_region(job_id, artifact)
        
        logger.info(f"Processed OCR region {artifact['region_id']} for job {job_id}")
        
        return artifact
        
    except Exception as e:
        logger.error(f"Error processing OCR region for job {job_id}: {str(e)}")
        raise


async def stream_ocr_results(job_id: str) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Stream OCR results as they become available.
    
    Args:
        job_id: Job identifier
        
    Yields:
        Region dictionaries as they are processed
    """
    storage = get_storage()
    seen_region_ids = set()
    
    while True:
        # Get all regions collected so far
        regions = storage.get_all_regions(job_id)
        
        # Yield new regions
        for region in regions:
            region_id = region.get("region_id")
            if region_id and region_id not in seen_region_ids:
                seen_region_ids.add(region_id)
                yield region
        
        # Check if processing is complete (this would need to be tracked separately)
        # For now, we'll break after a timeout or when no new regions appear
        import asyncio
        await asyncio.sleep(0.5)  # Poll every 500ms
        
        # In a real implementation, you'd check job status
        # For now, break if we've seen all regions
        if len(regions) > 0 and len(seen_region_ids) >= len(regions):
            # Wait a bit more to see if new regions appear
            await asyncio.sleep(1.0)
            final_regions = storage.get_all_regions(job_id)
            if len(final_regions) == len(regions):
                break


def split_image_to_regions(
    image_bytes: bytes,
    grid_size: tuple = (3, 3)
) -> List[Dict[str, Any]]:
    """
    Split an image into regions for parallel OCR processing.
    
    Args:
        image_bytes: Original image bytes
        grid_size: Tuple of (rows, cols) for grid split
        
    Returns:
        List of region dictionaries with image slices and bboxes
    """
    from PIL import Image
    import io
    
    img = Image.open(io.BytesIO(image_bytes))
    width, height = img.size
    
    rows, cols = grid_size
    region_width = width // cols
    region_height = height // rows
    
    regions = []
    region_id = 0
    
    for row in range(rows):
        for col in range(cols):
            left = col * region_width
            top = row * region_height
            right = left + region_width if col < cols - 1 else width
            bottom = top + region_height if row < rows - 1 else height
            
            # Crop region
            region_img = img.crop((left, top, right, bottom))
            
            # Convert to bytes
            buf = io.BytesIO()
            region_img.save(buf, format="PNG")
            region_bytes = buf.getvalue()
            buf.close()
            
            regions.append({
                "id": f"region_{region_id}",
                "image_bytes": region_bytes,
                "bbox": [left, top, right - left, bottom - top],
                "grid_pos": (row, col)
            })
            
            region_id += 1
    
    return regions


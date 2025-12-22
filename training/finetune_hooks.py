"""
Hooks for PaddleOCR-VL fine-tuning (SFT / LoRA).

Produces JSONL suitable for Paddle training pipelines.
Exports training samples when OCR confidence is low or validation fails.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class FineTuningHooks:
    """Hooks for collecting fine-tuning training data."""
    
    def __init__(self, output_file: Optional[str] = None):
        """
        Initialize fine-tuning hooks.
        
        Args:
            output_file: Path to JSONL file for training samples (default: ./training_samples.jsonl)
        """
        self.output_file = output_file or os.getenv(
            "FINESCRIBE_TRAINING_SAMPLES",
            "./training_samples.jsonl"
        )
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.output_file) if os.path.dirname(self.output_file) else ".", exist_ok=True)
        logger.info(f"Fine-tuning hooks initialized: output={self.output_file}")
    
    def ocr_to_jsonl_sample(
        self,
        ocr_artifact: Dict[str, Any],
        structured_gt: Optional[Dict[str, Any]] = None,
        image_path: Optional[str] = None,
        confidence_threshold: float = 0.8
    ) -> Optional[Dict[str, Any]]:
        """
        Convert OCR artifact to training sample format.
        
        Args:
            ocr_artifact: OCR output with regions
            structured_gt: Ground truth structured data (if available)
            image_path: Path to source image
            confidence_threshold: Minimum confidence to include sample
            
        Returns:
            Training sample dictionary or None if below threshold
        """
        # Check if we have low confidence regions
        regions = ocr_artifact.get("regions", [])
        avg_confidence = (
            sum(r.get("confidence", 0) for r in regions) / len(regions)
            if regions else 0
        )
        
        # Only export if confidence is low (needs improvement) or if we have GT
        if avg_confidence >= confidence_threshold and not structured_gt:
            return None
        
        sample = {
            "image": image_path or ocr_artifact.get("source_key", "unknown"),
            "regions": regions,
            "timestamp": datetime.utcnow().isoformat(),
            "avg_confidence": avg_confidence,
        }
        
        if structured_gt:
            sample["target"] = structured_gt
        
        return sample
    
    def write_training_sample(self, sample: Dict[str, Any]) -> bool:
        """
        Write training sample to JSONL file.
        
        Args:
            sample: Training sample dictionary
            
        Returns:
            True if written successfully
        """
        try:
            with open(self.output_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(sample, ensure_ascii=False) + "\n")
            logger.debug(f"Wrote training sample to {self.output_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to write training sample: {str(e)}")
            return False
    
    def log_low_confidence_ocr(
        self,
        ocr_artifact: Dict[str, Any],
        image_path: Optional[str] = None,
        confidence_threshold: float = 0.7
    ):
        """
        Log OCR result when confidence is below threshold.
        
        Args:
            ocr_artifact: OCR output
            image_path: Path to source image
            confidence_threshold: Threshold below which to log
        """
        sample = self.ocr_to_jsonl_sample(
            ocr_artifact,
            structured_gt=None,
            image_path=image_path,
            confidence_threshold=confidence_threshold
        )
        
        if sample:
            self.write_training_sample(sample)
    
    def log_validation_failure(
        self,
        ocr_artifact: Dict[str, Any],
        structured_output: Dict[str, Any],
        validation_result: Dict[str, Any],
        image_path: Optional[str] = None
    ):
        """
        Log sample when validation fails (indicates extraction errors).
        
        Args:
            ocr_artifact: OCR output
            structured_output: Extracted structured data
            validation_result: Validation results
            image_path: Path to source image
        """
        if validation_result.get("is_valid", True):
            return  # Skip if validation passed
        
        sample = self.ocr_to_jsonl_sample(
            ocr_artifact,
            structured_gt=structured_output,  # Use extracted as "target" (can be corrected later)
            image_path=image_path,
            confidence_threshold=0.0  # Always log validation failures
        )
        
        if sample:
            sample["validation_errors"] = validation_result.get("issues", [])
            sample["needs_review"] = True
            self.write_training_sample(sample)
    
    def export_training_dataset(
        self,
        output_path: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Export collected training samples.
        
        Args:
            output_path: Optional path to export to (defaults to output_file)
            limit: Optional limit on number of samples
            
        Returns:
            List of training samples
        """
        output = output_path or self.output_file
        
        if not os.path.exists(self.output_file):
            logger.warning(f"Training samples file not found: {self.output_file}")
            return []
        
        samples = []
        try:
            with open(self.output_file, "r", encoding="utf-8") as f:
                for line in f:
                    if limit and len(samples) >= limit:
                        break
                    try:
                        sample = json.loads(line.strip())
                        samples.append(sample)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse line in {self.output_file}")
                        continue
            
            # Write to output path if different
            if output_path and output_path != self.output_file:
                with open(output_path, "w", encoding="utf-8") as f:
                    for sample in samples:
                        f.write(json.dumps(sample, ensure_ascii=False) + "\n")
                logger.info(f"Exported {len(samples)} samples to {output_path}")
            else:
                logger.info(f"Loaded {len(samples)} samples from {self.output_file}")
            
            return samples
            
        except Exception as e:
            logger.error(f"Failed to export training dataset: {str(e)}")
            raise


# Global instance
_finetune_hooks: Optional[FineTuningHooks] = None


def get_finetune_hooks() -> FineTuningHooks:
    """Get or create global fine-tuning hooks instance."""
    global _finetune_hooks
    if _finetune_hooks is None:
        _finetune_hooks = FineTuningHooks()
    return _finetune_hooks


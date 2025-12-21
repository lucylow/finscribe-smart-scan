"""
Curriculum Learning Utilities

This module provides utilities for implementing curriculum learning strategies,
where the model trains on easier examples first and gradually increases difficulty.
"""

import json
import random
from typing import List, Dict, Any, Callable, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DifficultyScorer:
    """
    Scores training samples by difficulty for curriculum learning.
    """
    
    def __init__(self):
        """Initialize difficulty scorer."""
        pass
    
    def score(self, sample: Dict[str, Any]) -> float:
        """
        Score a sample's difficulty (0 = easiest, 1 = hardest).
        
        Args:
            sample: Training sample dictionary
            
        Returns:
            Difficulty score between 0 and 1
        """
        score = 0.0
        factors = 0
        
        # Factor 1: Response length (longer = harder)
        if 'conversations' in sample and len(sample['conversations']) > 1:
            response = sample['conversations'][1].get('content', '')
            response_length = len(response)
            # Normalize: assume max 5000 chars, longer = harder
            length_score = min(response_length / 5000.0, 1.0)
            score += length_score * 0.3
            factors += 0.3
        
        # Factor 2: Number of fields (more fields = harder)
        try:
            response_dict = json.loads(response)
            if isinstance(response_dict, dict):
                num_fields = len(response_dict)
                # Normalize: assume max 50 fields
                field_score = min(num_fields / 50.0, 1.0)
                score += field_score * 0.3
                factors += 0.3
        except:
            pass
        
        # Factor 3: Contains tables (tables = harder)
        if 'table' in response.lower() or 'line_items' in response.lower():
            score += 0.4
            factors += 0.4
        
        # Normalize score
        if factors > 0:
            score = score / factors
        
        return min(max(score, 0.0), 1.0)


class CurriculumScheduler:
    """
    Schedules training curriculum based on difficulty.
    """
    
    def __init__(
        self,
        difficulty_scorer: Optional[DifficultyScorer] = None,
        initial_difficulty: float = 0.3,
        final_difficulty: float = 1.0,
        schedule_type: str = 'linear'
    ):
        """
        Initialize curriculum scheduler.
        
        Args:
            difficulty_scorer: Optional custom difficulty scorer
            initial_difficulty: Starting difficulty threshold (0-1)
            final_difficulty: Final difficulty threshold (0-1)
            schedule_type: 'linear', 'exponential', or 'cosine'
        """
        self.difficulty_scorer = difficulty_scorer or DifficultyScorer()
        self.initial_difficulty = initial_difficulty
        self.final_difficulty = final_difficulty
        self.schedule_type = schedule_type
    
    def get_difficulty_threshold(self, progress: float) -> float:
        """
        Get current difficulty threshold based on training progress.
        
        Args:
            progress: Training progress (0.0 to 1.0)
            
        Returns:
            Difficulty threshold (0-1)
        """
        if self.schedule_type == 'linear':
            threshold = self.initial_difficulty + (
                self.final_difficulty - self.initial_difficulty
            ) * progress
        elif self.schedule_type == 'exponential':
            threshold = self.initial_difficulty * (
                (self.final_difficulty / self.initial_difficulty) ** progress
            )
        elif self.schedule_type == 'cosine':
            import math
            threshold = self.initial_difficulty + (
                self.final_difficulty - self.initial_difficulty
            ) * (1 - math.cos(progress * math.pi / 2))
        else:
            # Default to linear
            threshold = self.initial_difficulty + (
                self.final_difficulty - self.initial_difficulty
            ) * progress
        
        return min(max(threshold, 0.0), 1.0)
    
    def filter_samples(
        self,
        samples: List[Dict[str, Any]],
        progress: float
    ) -> List[Dict[str, Any]]:
        """
        Filter samples based on current difficulty threshold.
        
        Args:
            samples: List of training samples
            progress: Training progress (0.0 to 1.0)
            
        Returns:
            Filtered list of samples
        """
        threshold = self.get_difficulty_threshold(progress)
        
        filtered = []
        for sample in samples:
            difficulty = self.difficulty_scorer.score(sample)
            if difficulty <= threshold:
                filtered.append(sample)
        
        logger.info(
            f"Curriculum: progress={progress:.2f}, threshold={threshold:.2f}, "
            f"filtered {len(filtered)}/{len(samples)} samples"
        )
        
        return filtered


def create_curriculum_dataset(
    jsonl_path: str,
    output_path: str,
    difficulty_scorer: Optional[DifficultyScorer] = None,
    sort_by_difficulty: bool = True
) -> List[Dict[str, Any]]:
    """
    Create a curriculum-ordered dataset by scoring and sorting samples.
    
    Args:
        jsonl_path: Path to input JSONL file
        output_path: Path to save curriculum-ordered JSONL file
        difficulty_scorer: Optional custom difficulty scorer
        sort_by_difficulty: Whether to sort by difficulty (easiest first)
        
    Returns:
        List of samples with difficulty scores
    """
    scorer = difficulty_scorer or DifficultyScorer()
    
    # Load and score samples
    samples_with_scores = []
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                sample = json.loads(line)
                difficulty = scorer.score(sample)
                sample['_difficulty'] = difficulty
                samples_with_scores.append(sample)
    
    # Sort by difficulty
    if sort_by_difficulty:
        samples_with_scores.sort(key=lambda x: x['_difficulty'])
    
    # Save curriculum-ordered dataset
    with open(output_path, 'w', encoding='utf-8') as f:
        for sample in samples_with_scores:
            # Remove difficulty score before saving (or keep it for reference)
            output_sample = {k: v for k, v in sample.items() if k != '_difficulty'}
            f.write(json.dumps(output_sample, ensure_ascii=False) + '\n')
    
    logger.info(
        f"Created curriculum dataset: {len(samples_with_scores)} samples, "
        f"difficulty range: {min(s['_difficulty'] for s in samples_with_scores):.2f} - "
        f"{max(s['_difficulty'] for s in samples_with_scores):.2f}"
    )
    
    return samples_with_scores


class CurriculumTrainerCallback:
    """
    Callback for implementing curriculum learning during training.
    """
    
    def __init__(
        self,
        scheduler: CurriculumScheduler,
        all_samples: List[Dict[str, Any]],
        update_frequency: int = 1  # Update every N epochs
    ):
        """
        Initialize curriculum trainer callback.
        
        Args:
            scheduler: Curriculum scheduler
            all_samples: All training samples
            update_frequency: How often to update curriculum (in epochs)
        """
        self.scheduler = scheduler
        self.all_samples = all_samples
        self.update_frequency = update_frequency
        self.current_epoch = 0
    
    def on_epoch_begin(self, epoch: int, num_epochs: int):
        """Called at the beginning of each epoch."""
        self.current_epoch = epoch
        
        if epoch % self.update_frequency == 0:
            progress = epoch / num_epochs
            filtered_samples = self.scheduler.filter_samples(self.all_samples, progress)
            
            logger.info(
                f"Curriculum update at epoch {epoch}: "
                f"using {len(filtered_samples)}/{len(self.all_samples)} samples"
            )
            
            return filtered_samples
        
        return None



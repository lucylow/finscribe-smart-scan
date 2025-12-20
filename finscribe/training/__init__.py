"""
Training module for PaddleOCR-VL fine-tuning
Implements PaddleOCR-VL's official training methodology
"""

from .data_synthesis import FinancialDocumentSynthesizer, create_synthetic_dataset
from .instruction_pairs import InstructionPairGenerator, create_instruction_pairs
from .hard_sample_mining import HardSampleMiner, mine_hard_samples
from .erniekit_train import ERNIEKitTrainer, train_with_erniekit
from .evaluation import ModelEvaluator, evaluate_model

__all__ = [
    "FinancialDocumentSynthesizer",
    "create_synthetic_dataset",
    "InstructionPairGenerator",
    "create_instruction_pairs",
    "HardSampleMiner",
    "mine_hard_samples",
    "ERNIEKitTrainer",
    "train_with_erniekit",
    "ModelEvaluator",
    "evaluate_model",
]

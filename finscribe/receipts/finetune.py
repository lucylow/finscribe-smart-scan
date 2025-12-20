"""
Fine-tuning script for PaddleOCR-VL on receipt data.
Prepares instruction-response pairs and trains the model using ERNIEKit.
"""

import json
import torch
from pathlib import Path
from typing import Dict, List, Any, Optional
from datasets import Dataset
import pandas as pd
from PIL import Image
import logging

logger = logging.getLogger(__name__)

class ReceiptFineTuner:
    """Fine-tune PaddleOCR-VL for receipt understanding"""
    
    def __init__(self, model_name: str = "PaddlePaddle/PaddleOCR-VL", config: Optional[Dict] = None):
        self.model_name = model_name
        self.config = config or {}
        self.processor = None
        self.model = None
        
    def load_model(self):
        """Load PaddleOCR-VL model and processor"""
        try:
            from transformers import AutoProcessor, AutoModelForVision2Seq
            
            logger.info(f"Loading model: {self.model_name}")
            
            self.processor = AutoProcessor.from_pretrained(self.model_name)
            self.model = AutoModelForVision2Seq.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
            )
            
            if torch.cuda.is_available():
                self.model.cuda()
            
            logger.info("Model loaded successfully!")
            return self.model, self.processor
        except ImportError:
            logger.error("transformers library not installed. Install with: pip install transformers")
            raise
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            raise
    
    def prepare_dataset(self, dataset_path: str) -> Dataset:
        """Prepare dataset for fine-tuning"""
        logger.info(f"Loading dataset from: {dataset_path}")
        
        # Load dataset manifest
        manifest_path = Path(dataset_path) / "dataset_manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Dataset manifest not found: {manifest_path}")
        
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        # Prepare training examples
        training_examples = []
        
        for item in manifest:
            image_path = item['image_path']
            label_path = item['label_path']
            
            # Verify files exist
            if not Path(image_path).exists():
                logger.warning(f"Image not found: {image_path}")
                continue
            
            if not Path(label_path).exists():
                logger.warning(f"Label not found: {label_path}")
                continue
            
            # Load label
            try:
                with open(label_path, 'r', encoding='utf-8') as f:
                    label = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load label {label_path}: {e}")
                continue
            
            # Create instruction-response pairs
            for pair in label.get('instruction_pairs', []):
                training_examples.append({
                    'image_path': image_path,
                    'instruction': pair['instruction'],
                    'response': pair['response']
                })
        
        logger.info(f"Prepared {len(training_examples)} training examples")
        
        if len(training_examples) == 0:
            raise ValueError("No training examples found in dataset")
        
        # Convert to HuggingFace Dataset
        dataset = Dataset.from_pandas(pd.DataFrame(training_examples))
        
        # Split dataset
        split_dataset = dataset.train_test_split(
            test_size=self.config.get('test_size', 0.2),
            seed=self.config.get('seed', 42)
        )
        
        return split_dataset
    
    def preprocess_function(self, examples):
        """Preprocess images and text for the model"""
        if not self.processor:
            raise ValueError("Processor not initialized. Call load_model() first.")
        
        # Load images
        images = []
        for path in examples['image_path']:
            try:
                img = Image.open(path).convert("RGB")
                images.append(img)
            except Exception as e:
                logger.warning(f"Failed to load image {path}: {e}")
                # Use a placeholder image
                images.append(Image.new('RGB', (384, 600), 'white'))
        
        # Process images and text
        model_inputs = self.processor(
            images=images,
            text=examples['instruction'],
            padding="max_length",
            max_length=512,
            truncation=True,
            return_tensors="pt"
        )
        
        # Prepare labels
        with self.processor.as_target_processor():
            labels = self.processor(
                text=examples['response'],
                padding="max_length",
                max_length=256,
                truncation=True,
                return_tensors="pt"
            )
        
        model_inputs["labels"] = labels["input_ids"]
        
        return model_inputs
    
    def fine_tune(
        self, 
        dataset: Dataset, 
        output_dir: str = "./fine_tuned_receipt_model",
        epochs: int = 5,
        batch_size: int = 4,
        learning_rate: float = 2e-4
    ):
        """Fine-tune the model on receipt data"""
        try:
            from transformers import TrainingArguments, Trainer
            
            if not self.model or not self.processor:
                raise ValueError("Model and processor must be loaded first. Call load_model() first.")
            
            # Preprocess dataset
            logger.info("Preprocessing dataset...")
            processed_dataset = dataset.map(
                self.preprocess_function,
                batched=True,
                remove_columns=dataset['train'].column_names
            )
            
            # Training arguments
            training_args = TrainingArguments(
                output_dir=output_dir,
                num_train_epochs=epochs,
                per_device_train_batch_size=batch_size,
                per_device_eval_batch_size=batch_size,
                warmup_steps=100,
                weight_decay=0.01,
                logging_dir=f'{output_dir}/logs',
                logging_steps=10,
                eval_strategy="epoch",
                save_strategy="epoch",
                load_best_model_at_end=True,
                metric_for_best_model="loss",
                greater_is_better=False,
                push_to_hub=False,
                report_to="none"
            )
            
            # Initialize trainer
            trainer = Trainer(
                model=self.model,
                args=training_args,
                train_dataset=processed_dataset['train'],
                eval_dataset=processed_dataset['test'],
                tokenizer=self.processor,
            )
            
            # Start training
            logger.info("Starting fine-tuning...")
            trainer.train()
            
            # Save model
            trainer.save_model(output_dir)
            self.processor.save_pretrained(output_dir)
            
            logger.info(f"Model saved to: {output_dir}")
            
            return trainer
        except ImportError:
            logger.error("transformers library not installed. Install with: pip install transformers")
            raise
        except Exception as e:
            logger.error(f"Fine-tuning failed: {str(e)}")
            raise

def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fine-tune PaddleOCR-VL for receipt processing")
    parser.add_argument("--dataset_path", type=str, required=True, help="Path to receipt dataset")
    parser.add_argument("--output_dir", type=str, default="./fine_tuned_receipt_model", help="Output directory for fine-tuned model")
    parser.add_argument("--model_name", type=str, default="PaddlePaddle/PaddleOCR-VL", help="Base model name")
    parser.add_argument("--epochs", type=int, default=5, help="Number of training epochs")
    parser.add_argument("--batch_size", type=int, default=4, help="Batch size")
    parser.add_argument("--learning_rate", type=float, default=2e-4, help="Learning rate")
    
    args = parser.parse_args()
    
    # Initialize fine-tuner
    fine_tuner = ReceiptFineTuner(
        model_name=args.model_name,
        config={
            'test_size': 0.2,
            'seed': 42
        }
    )
    
    # Load model
    try:
        model, processor = fine_tuner.load_model()
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        return
    
    # Prepare dataset
    try:
        dataset = fine_tuner.prepare_dataset(args.dataset_path)
    except Exception as e:
        logger.error(f"Failed to prepare dataset: {e}")
        return
    
    # Fine-tune model
    try:
        trainer = fine_tuner.fine_tune(
            dataset,
            output_dir=args.output_dir,
            epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate
        )
        logger.info("Fine-tuning complete!")
    except Exception as e:
        logger.error(f"Fine-tuning failed: {e}")
        return

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()


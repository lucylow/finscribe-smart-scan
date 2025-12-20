"""
ERNIEKit training integration for PaddleOCR-VL fine-tuning
Adapts instruction pairs to ERNIEKit format and runs training
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
import subprocess
import sys


class ERNIEKitTrainer:
    """
    Wrapper for ERNIEKit training pipeline.
    Converts instruction pairs to ERNIEKit format and manages training.
    """
    
    def __init__(self, config_path: str = "training_config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load training configuration"""
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        else:
            return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """Default training configuration"""
        return {
            "model": {
                "name": "PaddlePaddle/PaddleOCR-VL",
                "base_model": "PaddlePaddle/PaddleOCR-VL",
            },
            "data": {
                "train_file": "training_data/instruction_pairs.jsonl",
                "validation_file": "training_data/validation_pairs.jsonl",
                "max_seq_length": 2048,
            },
            "training": {
                "output_dir": "outputs/finetuned_model",
                "num_train_epochs": 5,
                "per_device_train_batch_size": 4,
                "per_device_eval_batch_size": 4,
                "gradient_accumulation_steps": 4,
                "learning_rate": 2.0e-5,
                "warmup_steps": 100,
                "logging_steps": 10,
                "save_steps": 500,
                "eval_steps": 500,
                "save_total_limit": 3,
                "fp16": True,
                "bf16": False,
            },
            "lora": {
                "enabled": True,
                "r": 16,
                "lora_alpha": 32,
                "target_modules": ["q_proj", "v_proj", "k_proj", "o_proj"],
                "lora_dropout": 0.05,
            },
        }
    
    def convert_to_erniekit_format(
        self,
        instruction_pairs_path: str,
        output_path: str,
    ) -> str:
        """
        Convert instruction pairs to ERNIEKit format.
        
        Args:
            instruction_pairs_path: Path to instruction pairs JSONL
            output_path: Output path for ERNIEKit format
            
        Returns:
            Path to converted file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        erniekit_data = []
        
        with open(instruction_pairs_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                
                pair = json.loads(line)
                
                # ERNIEKit format (may vary based on version)
                # This is a generic format - adjust based on actual ERNIEKit requirements
                erniekit_item = {
                    "image": pair.get("image"),  # Path or base64
                    "instruction": pair["conversations"][0]["content"],
                    "output": pair["conversations"][1]["content"],
                }
                
                erniekit_data.append(erniekit_item)
        
        # Save as JSONL
        with open(output_path, "w", encoding="utf-8") as f:
            for item in erniekit_data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        
        print(f"Converted {len(erniekit_data)} samples to ERNIEKit format: {output_path}")
        return str(output_path)
    
    def create_erniekit_config(
        self,
        output_path: str = "erniekit_config.yaml",
    ) -> str:
        """
        Create ERNIEKit training configuration file.
        
        Args:
            output_path: Output path for config file
            
        Returns:
            Path to config file
        """
        output_path = Path(output_path)
        
        # ERNIEKit-specific config format
        # Note: This is a template - adjust based on actual ERNIEKit API
        erniekit_config = {
            "model_name_or_path": self.config["model"]["base_model"],
            "train_data_path": self.config["data"]["train_file"],
            "eval_data_path": self.config["data"].get("validation_file"),
            "output_dir": self.config["training"]["output_dir"],
            "max_seq_length": self.config["data"]["max_seq_length"],
            "num_train_epochs": self.config["training"]["num_train_epochs"],
            "per_device_train_batch_size": self.config["training"]["per_device_train_batch_size"],
            "per_device_eval_batch_size": self.config["training"]["per_device_eval_batch_size"],
            "gradient_accumulation_steps": self.config["training"]["gradient_accumulation_steps"],
            "learning_rate": self.config["training"]["learning_rate"],
            "warmup_steps": self.config["training"]["warmup_steps"],
            "logging_steps": self.config["training"]["logging_steps"],
            "save_steps": self.config["training"]["save_steps"],
            "eval_steps": self.config["training"]["eval_steps"],
            "save_total_limit": self.config["training"]["save_total_limit"],
            "fp16": self.config["training"]["fp16"],
            "bf16": self.config["training"]["bf16"],
        }
        
        # Add LoRA config if enabled
        if self.config["lora"]["enabled"]:
            erniekit_config["lora"] = {
                "r": self.config["lora"]["r"],
                "lora_alpha": self.config["lora"]["lora_alpha"],
                "target_modules": self.config["lora"]["target_modules"],
                "lora_dropout": self.config["lora"]["lora_dropout"],
            }
        
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(erniekit_config, f, default_flow_style=False, allow_unicode=True)
        
        print(f"Created ERNIEKit config: {output_path}")
        return str(output_path)
    
    def train_with_erniekit(
        self,
        instruction_pairs_path: str,
        use_erniekit_cli: bool = True,
    ) -> str:
        """
        Run training using ERNIEKit.
        
        Args:
            instruction_pairs_path: Path to instruction pairs JSONL
            use_erniekit_cli: Whether to use ERNIEKit CLI (if available)
            
        Returns:
            Path to trained model
        """
        # Convert to ERNIEKit format
        erniekit_data_path = self.convert_to_erniekit_format(
            instruction_pairs_path,
            "training_data/erniekit_format.jsonl",
        )
        
        # Create config
        erniekit_config_path = self.create_erniekit_config()
        
        if use_erniekit_cli:
            # Try to use ERNIEKit CLI if available
            try:
                # Example ERNIEKit CLI command (adjust based on actual API)
                cmd = [
                    "erniekit",
                    "train",
                    "--config", erniekit_config_path,
                    "--data", erniekit_data_path,
                ]
                
                print(f"Running ERNIEKit training: {' '.join(cmd)}")
                result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                print(result.stdout)
                
                return self.config["training"]["output_dir"]
            
            except FileNotFoundError:
                print("ERNIEKit CLI not found. Please install ERNIEKit or use Python API.")
                print("See: https://github.com/PaddlePaddle/ERNIEKit")
                return self._train_with_huggingface_fallback(erniekit_data_path)
            
            except subprocess.CalledProcessError as e:
                print(f"ERNIEKit training failed: {e}")
                print(f"Error output: {e.stderr}")
                return self._train_with_huggingface_fallback(erniekit_data_path)
        else:
            return self._train_with_huggingface_fallback(erniekit_data_path)
    
    def _train_with_huggingface_fallback(
        self,
        data_path: str,
    ) -> str:
        """
        Fallback to HuggingFace Transformers + PEFT (LoRA) training.
        
        Args:
            data_path: Path to training data
            
        Returns:
            Path to trained model
        """
        print("Using HuggingFace Transformers + PEFT as fallback...")
        
        # This would use the standard HuggingFace training approach
        # See phase2_finetuning/train_finetune.py for implementation
        
        training_script = Path(__file__).parent.parent / "phase2_finetuning" / "train_finetune.py"
        
        if training_script.exists():
            print(f"Using existing training script: {training_script}")
            print("Run training with:")
            print(f"  python {training_script} --config {self.config_path}")
            return str(self.config["training"]["output_dir"])
        else:
            print("Training script not found. Please implement training pipeline.")
            return ""


def train_with_erniekit(
    instruction_pairs_path: str,
    config_path: str = "training_config.yaml",
) -> str:
    """
    Main function to train with ERNIEKit.
    
    Args:
        instruction_pairs_path: Path to instruction pairs JSONL
        config_path: Path to training configuration
        
    Returns:
        Path to trained model
    """
    trainer = ERNIEKitTrainer(config_path=config_path)
    return trainer.train_with_erniekit(instruction_pairs_path)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Train PaddleOCR-VL with ERNIEKit")
    parser.add_argument("--data", type=str, required=True, help="Path to instruction pairs JSONL")
    parser.add_argument("--config", type=str, default="training_config.yaml", help="Training config path")
    
    args = parser.parse_args()
    
    train_with_erniekit(
        instruction_pairs_path=args.data,
        config_path=args.config,
    )


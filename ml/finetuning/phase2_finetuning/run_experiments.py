#!/usr/bin/env python3
"""
Hyperparameter Experiment Runner for PaddleOCR-VL Fine-Tuning

This script helps automate running multiple hyperparameter experiments
systematically. It creates experiment configs from a baseline and runs them.

Usage:
    # Run all experiments defined in experiments.yaml
    python run_experiments.py --experiments experiments.yaml

    # Run a single experiment by name
    python run_experiments.py --experiments experiments.yaml --name lr_1e5

    # Dry run (just create configs, don't train)
    python run_experiments.py --experiments experiments.yaml --dry-run
"""

import argparse
import yaml
import json
import shutil
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import subprocess
import sys


def load_config(config_path: str) -> Dict[str, Any]:
    """Load YAML configuration file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def save_config(config: Dict[str, Any], output_path: str):
    """Save configuration to YAML file."""
    with open(output_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def create_experiment_config(
    baseline_config: Dict[str, Any],
    experiment_spec: Dict[str, Any],
    output_dir: Path
) -> Path:
    """
    Create an experiment configuration file from baseline + experiment spec.
    
    Args:
        baseline_config: The baseline configuration dictionary
        experiment_spec: Dictionary with hyperparameter overrides
        output_dir: Directory to save experiment config
        
    Returns:
        Path to created config file
    """
    # Deep copy baseline config
    import copy
    exp_config = copy.deepcopy(baseline_config)
    
    # Apply overrides from experiment spec
    overrides = experiment_spec.get('overrides', {})
    for key_path, value in overrides.items():
        # Handle nested keys like "training.learning_rate"
        keys = key_path.split('.')
        config_ref = exp_config
        for key in keys[:-1]:
            if key not in config_ref:
                config_ref[key] = {}
            config_ref = config_ref[key]
        config_ref[keys[-1]] = value
    
    # Update experiment metadata
    exp_config['experiment']['name'] = experiment_spec['name']
    exp_config['experiment']['description'] = experiment_spec.get('description', '')
    exp_config['experiment']['hyperparameters_under_test'] = experiment_spec.get('test_params', [])
    
    # Update run name and output dir
    exp_name = experiment_spec['name']
    exp_config['run_name'] = f"experiment-{exp_name}"
    exp_config['output_dir'] = f"./experiments/{exp_name}/checkpoints"
    
    # Save config
    output_dir.mkdir(parents=True, exist_ok=True)
    config_path = output_dir / f"{exp_name}.yaml"
    save_config(exp_config, str(config_path))
    
    return config_path


def run_experiment(
    config_path: Path,
    experiment_name: str,
    train_script: str = "train_finetune.py",
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Run a single training experiment.
    
    Args:
        config_path: Path to experiment config file
        experiment_name: Name of experiment
        train_script: Path to training script
        dry_run: If True, don't actually run training
        
    Returns:
        Dictionary with experiment results/metadata
    """
    print(f"\n{'='*60}")
    print(f"Experiment: {experiment_name}")
    print(f"{'='*60}")
    print(f"Config: {config_path}")
    
    if dry_run:
        print("DRY RUN - Not executing training")
        return {
            'name': experiment_name,
            'config_path': str(config_path),
            'status': 'dry_run',
            'start_time': datetime.now().isoformat()
        }
    
    # Run training
    cmd = [sys.executable, train_script, "--config", str(config_path)]
    print(f"Running: {' '.join(cmd)}")
    
    start_time = datetime.now()
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=False,  # Show output in real-time
            text=True
        )
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds() / 3600  # hours
        
        return {
            'name': experiment_name,
            'config_path': str(config_path),
            'status': 'completed',
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration_hours': round(duration, 2),
            'return_code': result.returncode
        }
    except subprocess.CalledProcessError as e:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds() / 3600
        
        return {
            'name': experiment_name,
            'config_path': str(config_path),
            'status': 'failed',
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration_hours': round(duration, 2),
            'error': str(e),
            'return_code': e.returncode
        }


def main():
    parser = argparse.ArgumentParser(
        description="Run hyperparameter experiments for PaddleOCR-VL fine-tuning"
    )
    parser.add_argument(
        "--baseline-config",
        type=str,
        default="finetune_config.yaml",
        help="Path to baseline configuration file"
    )
    parser.add_argument(
        "--experiments",
        type=str,
        required=True,
        help="Path to experiments specification YAML file"
    )
    parser.add_argument(
        "--name",
        type=str,
        help="Run only a specific experiment by name (optional)"
    )
    parser.add_argument(
        "--train-script",
        type=str,
        default="train_finetune.py",
        help="Path to training script"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Create configs but don't run training"
    )
    parser.add_argument(
        "--experiments-dir",
        type=str,
        default="./experiments",
        help="Directory to save experiment configs"
    )
    
    args = parser.parse_args()
    
    # Load baseline and experiments
    print(f"Loading baseline config: {args.baseline_config}")
    baseline_config = load_config(args.baseline_config)
    
    print(f"Loading experiments spec: {args.experiments}")
    experiments_spec = load_config(args.experiments)
    
    # Create experiments directory
    experiments_dir = Path(args.experiments_dir)
    experiments_dir.mkdir(parents=True, exist_ok=True)
    
    # Filter experiments if name specified
    experiment_list = experiments_spec.get('experiments', [])
    if args.name:
        experiment_list = [e for e in experiment_list if e['name'] == args.name]
        if not experiment_list:
            print(f"Error: Experiment '{args.name}' not found")
            sys.exit(1)
    
    print(f"\nFound {len(experiment_list)} experiment(s) to run")
    
    # Run each experiment
    results = []
    for exp_spec in experiment_list:
        # Create experiment config
        exp_name = exp_spec['name']
        exp_config_path = create_experiment_config(
            baseline_config,
            exp_spec,
            experiments_dir / exp_name
        )
        
        # Run experiment
        result = run_experiment(
            exp_config_path,
            exp_name,
            args.train_script,
            args.dry_run
        )
        results.append(result)
        
        # Small delay between experiments (if not dry run)
        if not args.dry_run and exp_spec != experiment_list[-1]:
            print("\nWaiting 10 seconds before next experiment...")
            import time
            time.sleep(10)
    
    # Save results summary
    results_file = experiments_dir / "results_summary.json"
    with open(results_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'baseline_config': args.baseline_config,
            'experiments_spec': args.experiments,
            'results': results
        }, f, indent=2)
    
    print(f"\n{'='*60}")
    print("Experiment Summary")
    print(f"{'='*60}")
    for result in results:
        status_emoji = "✅" if result['status'] == 'completed' else "❌" if result['status'] == 'failed' else "⏭️"
        print(f"{status_emoji} {result['name']}: {result['status']}")
        if result['status'] == 'completed' and 'duration_hours' in result:
            print(f"   Duration: {result['duration_hours']:.2f} hours")
        elif result['status'] == 'failed' and 'error' in result:
            print(f"   Error: {result['error']}")
    
    print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    main()


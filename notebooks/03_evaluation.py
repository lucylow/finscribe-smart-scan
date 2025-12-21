# Notebook runner script version of evaluation (compatible with papermill or jupyter)
# This script is a plain .py that can be converted to a notebook; instruct judges to run run_eval.sh for reproducibility.

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

def main():
    exp = "notebook_exp"
    
    print("Running evaluation via run_eval.sh...")
    print("=" * 60)
    
    # Run evaluation script
    result = subprocess.run(
        ["bash", str(ROOT / "run_eval.sh"), "", "", exp],
        cwd=ROOT,
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print("Errors:", result.stderr, file=sys.stderr)
    
    # Load and display results
    exp_dir = ROOT / "results" / exp
    baseline_file = exp_dir / "baseline_metrics.json"
    ft_file = exp_dir / "ft_metrics.json"
    
    if baseline_file.exists():
        print("\n" + "=" * 60)
        print("Baseline Metrics:")
        print("=" * 60)
        with open(baseline_file) as f:
            baseline = json.load(f)
        print(json.dumps(baseline, indent=2))
    
    if ft_file.exists():
        print("\n" + "=" * 60)
        print("Finetuned Metrics:")
        print("=" * 60)
        with open(ft_file) as f:
            ft = json.load(f)
        print(json.dumps(ft, indent=2))
    
    # Print comparison if available
    comparison_file = exp_dir / "comparison.json"
    if comparison_file.exists():
        print("\n" + "=" * 60)
        print("Comparison Summary:")
        print("=" * 60)
        with open(comparison_file) as f:
            comparison = json.load(f)
        
        print("\nKey Improvements:")
        for key, val in comparison.get("improvements", {}).items():
            if isinstance(val, dict) and "improvement_pct" in val:
                print(f"  {key}: {val['baseline']:.4f} -> {val['finetuned']:.4f} ({val['improvement_pct']:+.2f}%)")

if __name__ == "__main__":
    main()


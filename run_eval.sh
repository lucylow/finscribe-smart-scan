#!/usr/bin/env bash
set -euo pipefail
# Usage: ./run_eval.sh [HF_MODEL_OR_URL] [CHECKPOINT_PATH] [EXP_NAME]
# Example: ./run_eval.sh "" "outputs/hf_checkpoint" my_exp
HF_MODEL=${1:-""}
CKPT=${2:-""}
EXP=${3:-"exp_$(date +%Y%m%d_%H%M%S)"}

echo "========================================"
echo "Running evaluation: exp=$EXP"
echo "  HF_MODEL: ${HF_MODEL:-baseline}"
echo "  CHECKPOINT: ${CKPT:-none}"
echo "========================================"

mkdir -p results/$EXP logs/$EXP

# 1) baseline inference (attempt to use HF_MODEL if provided as url; otherwise use dummy runner)
echo ""
echo "Step 1: Running baseline inference..."
python3 src/models/runner.py \
    --model "${HF_MODEL:-baseline}" \
    --data data/dataset/test.jsonl \
    --out results/$EXP/baseline_preds.jsonl 2>&1 | tee logs/$EXP/baseline_inference.log

# 2) if checkpoint provided, run finetuned inference
if [ -n "$CKPT" ] && [ -d "$CKPT" ]; then
    echo ""
    echo "Step 2: Running finetuned inference with checkpoint $CKPT..."
    python3 src/models/runner.py \
        --model "$CKPT" \
        --data data/dataset/test.jsonl \
        --out results/$EXP/ft_preds.jsonl 2>&1 | tee logs/$EXP/ft_inference.log
else
    echo ""
    echo "Step 2: Skipping finetuned inference (no checkpoint provided or checkpoint not found)"
fi

# 3) compute metrics
echo ""
echo "Step 3: Computing baseline metrics..."
python3 scripts/compute_metrics.py \
    --preds results/$EXP/baseline_preds.jsonl \
    --out results/$EXP/baseline_metrics.json 2>&1 | tee logs/$EXP/baseline_metrics.log

if [ -n "$CKPT" ] && [ -f "results/$EXP/ft_preds.jsonl" ]; then
    echo ""
    echo "Step 4: Computing finetuned metrics..."
    python3 scripts/compute_metrics.py \
        --preds results/$EXP/ft_preds.jsonl \
        --out results/$EXP/ft_metrics.json 2>&1 | tee logs/$EXP/ft_metrics.log
    
    # 4) Create comparison summary if both exist
    echo ""
    echo "Step 5: Creating comparison summary..."
    python3 <<PY
import json
from pathlib import Path

exp_dir = Path("results/$EXP")
baseline_file = exp_dir / "baseline_metrics.json"
ft_file = exp_dir / "ft_metrics.json"

if baseline_file.exists() and ft_file.exists():
    with open(baseline_file) as f:
        baseline = json.load(f)
    with open(ft_file) as f:
        ft = json.load(f)
    
    comparison = {
        "experiment": "$EXP",
        "baseline": baseline,
        "finetuned": ft,
        "improvements": {}
    }
    
    # Calculate improvements
    for key in baseline:
        if isinstance(baseline[key], dict) and isinstance(ft.get(key), dict):
            improvements = {}
            for subkey in baseline[key]:
                if subkey in ft[key]:
                    b_val = baseline[key][subkey]
                    f_val = ft[key][subkey]
                    if isinstance(b_val, (int, float)) and isinstance(f_val, (int, float)):
                        improvements[subkey] = {
                            "baseline": b_val,
                            "finetuned": f_val,
                            "improvement": f_val - b_val,
                            "improvement_pct": ((f_val - b_val) / b_val * 100) if b_val > 0 else 0
                        }
            if improvements:
                comparison["improvements"][key] = improvements
        elif isinstance(baseline[key], (int, float)) and isinstance(ft.get(key), (int, float)):
            comparison["improvements"][key] = {
                "baseline": baseline[key],
                "finetuned": ft[key],
                "improvement": ft[key] - baseline[key],
                "improvement_pct": ((ft[key] - baseline[key]) / baseline[key] * 100) if baseline[key] > 0 else 0
            }
    
    with open(exp_dir / "comparison.json", "w") as f:
        json.dump(comparison, f, indent=2)
    
    print("Comparison saved to results/$EXP/comparison.json")
    print("\nKey Improvements:")
    for key, val in comparison["improvements"].items():
        if isinstance(val, dict) and "improvement_pct" in val:
            print(f"  {key}: {val['baseline']:.4f} -> {val['finetuned']:.4f} ({val['improvement_pct']:+.2f}%)")
PY
fi

echo ""
echo "========================================"
echo "Evaluation finished!"
echo "Results saved to: results/$EXP"
echo "========================================"


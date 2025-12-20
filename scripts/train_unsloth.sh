#!/usr/bin/env bash
set -euo pipefail

# Simple train script for Unsloth (LoRA SFT)
# Usage: ./scripts/train_unsloth.sh [--model MODEL_NAME] [--train data/...jsonl]
MODEL_NAME="${1:-unsloth/unsloth-small}"
TRAIN_FILE="${2:-data/unsloth_train.jsonl}"
OUTPUT_DIR="${3:-models/unsloth-finscribe}"
EPOCHS="${4:-3}"
BATCH_SIZE="${5:-1}"

echo "Model: $MODEL_NAME"
echo "Train file: $TRAIN_FILE"
echo "Output dir: $OUTPUT_DIR"

python3 -m venv venv_unsloth || true
source venv_unsloth/bin/activate
pip install --upgrade pip
# install Unsloth and deps (pick matching cuda/pytorch for your environment)
pip install --upgrade "git+https://github.com/unslothai/unsloth.git"
pip install transformers datasets trl accelerate bitsandbytes sentencepiece huggingface_hub

# create tiny training script (uses TRL/SFTTrainer)
cat > /tmp/train_unsloth_run.py <<'PY'
import os, sys
from datasets import load_dataset
from transformers import AutoTokenizer
from trl import SFTTrainer, SFTConfig

MODEL = os.environ.get("MODEL_NAME", sys.argv[1] if len(sys.argv)>1 else "unsloth/unsloth-small")
TRAIN_FILE = os.environ.get("TRAIN_FILE", sys.argv[2] if len(sys.argv)>2 else "data/unsloth_train.jsonl")
OUTDIR = os.environ.get("OUTDIR", sys.argv[3] if len(sys.argv)>3 else "models/unsloth-finscribe")

tokenizer = AutoTokenizer.from_pretrained(MODEL, use_fast=True)
ds = load_dataset("json", data_files=TRAIN_FILE, split="train")

def map_fn(ex):
    return {"input_text": ex["prompt"], "target_text": ex["completion"]}

ds = ds.map(map_fn, remove_columns=ds.column_names)

cfg = SFTConfig(
    model_name_or_path=MODEL,
    output_dir=OUTDIR,
    per_device_train_batch_size=1,
    num_train_epochs=3,
    max_seq_length=1024,
    use_lora=True,
    lora_r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    fp16=True,
)
trainer = SFTTrainer(config=cfg, train_dataset=ds)
trainer.train()
trainer.save_model(OUTDIR)
print("Saved to", OUTDIR)
PY

export MODEL_NAME="$MODEL_NAME"
export TRAIN_FILE="$TRAIN_FILE"
export OUTDIR="$OUTPUT_DIR"
python /tmp/train_unsloth_run.py "$MODEL_NAME" "$TRAIN_FILE" "$OUTPUT_DIR"

echo "Training finished. Check $OUTPUT_DIR for outputs."

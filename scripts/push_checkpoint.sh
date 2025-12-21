#!/usr/bin/env bash
# Usage: ./scripts/push_checkpoint.sh <checkpoint_dir> <repo_name_on_hf>
CKPT=${1:-}
REPO=${2:-}
if [ -z "$CKPT" ] || [ -z "$REPO" ]; then
    echo "Usage: $0 <checkpoint_dir> <hf_repo>"
    echo "Example: $0 outputs/hf_checkpoint/final lucylow/finscribe-paddleocr-vl-ft"
    exit 1
fi
if [ -z "${HF_TOKEN:-}" ]; then
    echo "Set HF_TOKEN in environment to push to HF Hub"
    echo "  export HF_TOKEN=your_token_here"
    exit 1
fi

python3 <<PY
from huggingface_hub import HfApi, upload_folder
import os
import sys
from pathlib import Path

api = HfApi()
repo = "$REPO"
ckpt = Path("$CKPT")

if not ckpt.exists():
    print(f"Error: Checkpoint directory {ckpt} does not exist")
    sys.exit(1)

print(f"Creating repo {repo} (if it doesn't exist)...")
try:
    api.create_repo(token=os.environ["HF_TOKEN"], repo_id=repo, exist_ok=True)
except Exception as e:
    print(f"Note: {e}")

print(f"Uploading checkpoint from {ckpt} to {repo}...")
upload_folder(
    folder_path=str(ckpt),
    repo_id=repo,
    token=os.environ["HF_TOKEN"],
    commit_message="Upload fine-tuned checkpoint"
)
print(f"Uploaded checkpoint to https://huggingface.co/{repo}")
PY


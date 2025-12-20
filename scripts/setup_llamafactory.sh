#!/usr/bin/env bash
set -euo pipefail

# Quick setup script for LLaMA-Factory integration
# This script clones LLaMA-Factory, installs dependencies, and sets up the dataset registration

echo "Setting up LLaMA-Factory integration for FinScribe..."

# Check if LLaMA-Factory directory exists
if [ -d "LLaMA-Factory" ]; then
    echo "LLaMA-Factory directory already exists. Skipping clone."
    cd LLaMA-Factory
else
    echo "Cloning LLaMA-Factory..."
    git clone --depth 1 https://github.com/hiyouga/LLaMA-Factory.git
    cd LLaMA-Factory
fi

# Install LLaMA-Factory
echo "Installing LLaMA-Factory (this may take a while)..."
pip install -e ".[torch,metrics]"

# Verify installation
echo "Verifying installation..."
llamafactory-cli version || echo "Warning: llamafactory-cli not found in PATH. Try: python -m llamafactory.entrypoints"

# Copy dataset info to LLaMA-Factory data directory
echo "Setting up dataset registration..."
if [ -f "../data/dataset_info.json" ]; then
    # Merge with existing dataset_info.json if it exists
    if [ -f "data/dataset_info.json" ]; then
        echo "Merging dataset_info.json..."
        python3 <<PY
import json
import sys

with open("data/dataset_info.json", "r") as f:
    existing = json.load(f)

with open("../data/dataset_info.json", "r") as f:
    new_data = json.load(f)

existing.update(new_data)

with open("data/dataset_info.json", "w") as f:
    json.dump(existing, f, indent=2)

print("Merged dataset_info.json")
PY
    else
        cp ../data/dataset_info.json data/dataset_info.json
        echo "Copied dataset_info.json"
    fi
fi

# Copy dataset file
if [ -f "../data/finscribe_unsloth.jsonl" ]; then
    cp ../data/finscribe_unsloth.jsonl data/finscribe_unsloth.jsonl || true
    echo "Copied finscribe_unsloth.jsonl"
fi

# Copy training configs
echo "Setting up training configurations..."
mkdir -p examples/train_lora examples/merge_lora
if [ -f "../examples/train_lora/finscribe_lora_sft.yaml" ]; then
    cp ../examples/train_lora/finscribe_lora_sft.yaml examples/train_lora/
    echo "Copied training config"
fi
if [ -f "../examples/merge_lora/finscribe_merge.yaml" ]; then
    cp ../examples/merge_lora/finscribe_merge.yaml examples/merge_lora/
    echo "Copied merge config"
fi

cd ..

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit examples/train_lora/finscribe_lora_sft.yaml and set model_name_or_path"
echo "2. Run: cd LLaMA-Factory && llamafactory-cli train examples/train_lora/finscribe_lora_sft.yaml"
echo "3. After training, merge LoRA: llamafactory-cli export examples/merge_lora/finscribe_merge.yaml"
echo "4. Serve model: llamafactory-cli api examples/inference/llama_vllm.yaml"
echo "5. Use finscribe.llm_client to call the API from your pipeline"


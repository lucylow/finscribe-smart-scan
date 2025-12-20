#!/bin/bash
# Example script for semantic understanding training workflow

set -e  # Exit on error

echo "=========================================="
echo "Semantic Understanding Training Workflow"
echo "=========================================="
echo ""

# Configuration
SYNTHETIC_DIR="../synthetic_invoice_generator"
OUTPUT_DIR="./training_output"
MANIFEST_PATH="${SYNTHETIC_DIR}/output/training_manifest.json"
INSTRUCTION_PAIRS="${OUTPUT_DIR}/semantic_instruction_pairs.jsonl"
CONFIG_FILE="finetune_config.yaml"

# Step 1: Generate synthetic invoices (if not already done)
if [ ! -f "$MANIFEST_PATH" ]; then
    echo "Step 1: Generating synthetic invoices..."
    cd "$SYNTHETIC_DIR"
    python generate_dataset.py
    cd - > /dev/null
    echo "✓ Synthetic invoices generated"
else
    echo "✓ Synthetic invoices already exist"
fi

# Step 2: Create semantic instruction pairs
echo ""
echo "Step 2: Creating semantic instruction pairs..."
mkdir -p "$OUTPUT_DIR"

python create_semantic_instruction_pairs.py \
    --manifest "$MANIFEST_PATH" \
    --output "$INSTRUCTION_PAIRS"

if [ ! -f "$INSTRUCTION_PAIRS" ]; then
    echo "Error: Failed to create instruction pairs"
    exit 1
fi

echo "✓ Instruction pairs created: $(wc -l < "$INSTRUCTION_PAIRS") pairs"

# Step 3: Update config file with dataset path
echo ""
echo "Step 3: Updating configuration..."
# Note: You may need to manually update finetune_config.yaml with the dataset path
echo "  Dataset path in config should be: $INSTRUCTION_PAIRS"
echo "  Please verify finetune_config.yaml has: dataset_path: \"$INSTRUCTION_PAIRS\""

# Step 4: Train the model
echo ""
echo "Step 4: Starting training..."
echo "  This will take a while depending on your GPU and dataset size..."
echo ""

python train_finetune_enhanced.py \
    --config "$CONFIG_FILE"

echo ""
echo "=========================================="
echo "Training Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Evaluate the model on test data"
echo "2. Check training logs in the output directory"
echo "3. Adjust hyperparameters if needed"
echo ""
echo "For more details, see: SEMANTIC_TRAINING_GUIDE.md"


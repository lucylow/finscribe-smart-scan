"""
Colab-Friendly Unsloth Training Script

Copy the cells below into Google Colab for easy fine-tuning.
Make sure to: Runtime → Change runtime type → GPU
"""

# ============================================================================
# CELL 1: Install Dependencies
# ============================================================================
"""
!pip install -q "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
!pip install -q --upgrade "unsloth-zoo @ git+https://github.com/unslothai/unsloth_zoo.git"
!pip install -q transformers>=4.35.0 datasets>=2.14.0 accelerate>=0.24.0 trl>=0.7.0 sentencepiece huggingface_hub
"""

# ============================================================================
# CELL 2: Create Synthetic Dataset
# ============================================================================
"""
import json
import random

vendors = ["TechCorp Inc.", "Acme LLC", "Globex Corporation", "Innotech", "BlueSky Ltd"]
train_data = []
val_data = []

for i in range(10):
    vendor = random.choice(vendors)
    inv = f"INV-{1000+i}"
    date = f"2024-0{random.randint(1,9)}-{random.randint(10,28)}"
    
    items = []
    for j in range(random.randint(1, 3)):
        desc = random.choice(["Widget A", "Service Fee", "Consulting Hours", "License"])
        qty = random.randint(1, 5)
        unit_price = round(random.uniform(50, 500), 2)
        items.append({
            "desc": desc,
            "qty": qty,
            "unit_price": unit_price,
            "line_total": round(qty * unit_price, 2)
        })
    
    subtotal = sum(item["line_total"] for item in items)
    tax_rate = random.choice([0.0, 0.1, 0.2])
    tax_amount = round(subtotal * tax_rate, 2)
    grand_total = subtotal + tax_amount
    
    prompt = f"OCR_TEXT:\\nVendor: {vendor}\\nInvoice: {inv}\\nDate: {date}\\n"
    for item in items:
        prompt += f"{item['desc']} {item['qty']} x ${item['unit_price']:.2f} = ${item['line_total']:.2f}\\n"
    prompt += f"Subtotal: ${subtotal:.2f}\\n"
    if tax_rate > 0:
        prompt += f"Tax: ${tax_amount:.2f}\\n"
    prompt += f"Total: ${grand_total:.2f}\\n\\nExtract structured JSON."
    
    completion = json.dumps({
        "document_type": "invoice",
        "vendor": {"name": vendor},
        "client": {},
        "line_items": items,
        "financial_summary": {
            "subtotal": subtotal,
            "tax_rate": tax_rate,
            "tax_amount": tax_amount,
            "grand_total": grand_total
        }
    })
    
    train_data.append({"prompt": prompt, "completion": completion})

# Validation set
for i in range(2):
    vendor = random.choice(vendors)
    inv = f"T-{100+i}"
    prompt = f"OCR_TEXT:\\nVendor: {vendor}\\nInvoice: {inv}\\nDate: 2024-01-01\\nService 1 x 100.00\\nTotal: 100.00\\n\\nExtract structured JSON."
    completion = json.dumps({
        "document_type": "invoice",
        "vendor": {"name": vendor},
        "line_items": [{"desc": "Service", "qty": 1, "unit_price": 100.0, "line_total": 100.0}],
        "financial_summary": {"subtotal": 100.0, "tax_rate": 0.0, "tax_amount": 0.0, "grand_total": 100.0}
    })
    val_data.append({"prompt": prompt, "completion": completion})

# Save
with open("unsloth_colab_train.jsonl", "w") as f:
    for item in train_data:
        f.write(json.dumps(item) + "\\n")

with open("unsloth_colab_val.jsonl", "w") as f:
    for item in val_data:
        f.write(json.dumps(item) + "\\n")

print(f"Created {len(train_data)} training and {len(val_data)} validation examples")
"""

# ============================================================================
# CELL 3: Load Model with Unsloth
# ============================================================================
"""
from unsloth import FastLanguageModel
from datasets import load_dataset
from transformers import TrainingArguments
from trl import SFTTrainer

MODEL_NAME = "unsloth/Mistral-7B-Instruct-v0.2-bnb-4bit"

# Load model with Unsloth optimizations
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=MODEL_NAME,
    max_seq_length=2048,
    dtype=None,
    load_in_4bit=True,
)

# Enable LoRA
model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_alpha=16,
    lora_dropout=0.05,
    bias="none",
    use_gradient_checkpointing=True,
    random_state=3407,
)

print("Model loaded successfully!")
"""

# ============================================================================
# CELL 4: Prepare Dataset
# ============================================================================
"""
from datasets import load_dataset

train_dataset = load_dataset("json", data_files="unsloth_colab_train.jsonl", split="train")
val_dataset = load_dataset("json", data_files="unsloth_colab_val.jsonl", split="train")

def format_prompt(example):
    return {"text": example["prompt"] + example["completion"]}

train_dataset = train_dataset.map(format_prompt, remove_columns=train_dataset.column_names)
val_dataset = val_dataset.map(format_prompt, remove_columns=val_dataset.column_names)

print(f"Training: {len(train_dataset)}, Validation: {len(val_dataset)}")
"""

# ============================================================================
# CELL 5: Configure Training
# ============================================================================
"""
from transformers import TrainingArguments

training_args = TrainingArguments(
    output_dir="./unsloth_colab_output",
    per_device_train_batch_size=1,
    gradient_accumulation_steps=8,
    learning_rate=2e-5,
    num_train_epochs=1,
    logging_steps=10,
    save_steps=500,
    eval_steps=500,
    evaluation_strategy="steps",
    warmup_steps=100,
    fp16=True,
    report_to="none",
)
"""

# ============================================================================
# CELL 6: Train Model
# ============================================================================
"""
from trl import SFTTrainer

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
    args=training_args,
    dataset_text_field="text",
    max_seq_length=2048,
    packing=False,
)

print("Starting training...")
trainer.train()

model.save_pretrained("./unsloth_colab_output")
tokenizer.save_pretrained("./unsloth_colab_output")

print("Training complete! Model saved to ./unsloth_colab_output")
"""

# ============================================================================
# CELL 7: Test Inference
# ============================================================================
"""
from unsloth import FastLanguageModel
import json
import re

# Load saved model
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="./unsloth_colab_output",
    max_seq_length=2048,
    dtype=None,
    load_in_4bit=True,
)

FastLanguageModel.for_inference(model)

# Test prompt
prompt = "OCR_TEXT:\\nVendor: TestVendor\\nInvoice: INV-999\\nDate: 2024-01-15\\nWidget A 2 x $50.00 Total $100.00\\n\\nExtract structured JSON."

inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
outputs = model.generate(**inputs, max_new_tokens=256, temperature=0.0, do_sample=False)
decoded = tokenizer.decode(outputs[0], skip_special_tokens=True)

print("Generated output:")
print(decoded)

# Extract JSON
json_match = re.search(r'\\{.*\\}', decoded, re.DOTALL)
if json_match:
    try:
        parsed = json.loads(json_match.group())
        print("\\nParsed JSON:")
        print(json.dumps(parsed, indent=2))
    except:
        print("\\nFailed to parse JSON")
"""


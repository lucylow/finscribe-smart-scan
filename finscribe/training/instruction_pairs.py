"""
Convert financial document data to instruction-response pairs for PaddleOCR-VL fine-tuning
Implements instruction-based fine-tuning format
"""

import json
import base64
from pathlib import Path
from typing import Dict, Any, List, Optional
from PIL import Image
import io


class InstructionPairGenerator:
    """
    Converts financial document data to instruction-response pairs
    for PaddleOCR-VL fine-tuning.
    """
    
    def __init__(self):
        self.instruction_templates = {
            "full_extraction": [
                "Parse this invoice and extract all fields into JSON format.",
                "Extract all information from this invoice.",
                "Read this invoice and return structured JSON data.",
                "Parse this financial document and extract all fields.",
            ],
            "vendor_block": [
                "Extract the vendor information from this invoice.",
                "What is the vendor name, address, and contact information?",
                "Extract the vendor block from this document.",
            ],
            "client_info": [
                "Extract the client/bill-to information from this invoice.",
                "What is the client name and address?",
                "Extract the billing information.",
            ],
            "invoice_metadata": [
                "Extract the invoice number, date, and due date.",
                "What is the invoice ID and issue date?",
                "Extract invoice metadata (number, dates, terms).",
            ],
            "line_items": [
                "Extract the line item table from this invoice.",
                "List all line items with quantities, prices, and totals.",
                "Extract the itemized list from this invoice.",
            ],
            "financial_summary": [
                "Extract the financial summary (subtotal, tax, discount, total) from this invoice.",
                "What are the subtotal, tax amount, and grand total?",
                "Extract all financial totals from this invoice.",
            ],
            "specific_field": [
                "What is the invoice number?",
                "What is the total amount due?",
                "What is the vendor name?",
                "What is the due date?",
            ],
        }
    
    def invoice_to_json(self, invoice: Dict[str, Any]) -> str:
        """
        Convert invoice dictionary to structured JSON string.
        
        Args:
            invoice: Invoice data dictionary
            
        Returns:
            JSON string representation
        """
        # Create structured JSON output
        output = {
            "invoice_id": invoice.get("invoice_id"),
            "vendor": invoice.get("vendor", {}),
            "client": invoice.get("client", {}),
            "issue_date": invoice.get("issue_date"),
            "due_date": invoice.get("due_date"),
            "payment_terms": invoice.get("payment_terms"),
            "items": invoice.get("items", []),
            "financial_summary": {
                "subtotal": invoice.get("subtotal"),
                "tax_rate": invoice.get("tax_rate"),
                "tax_total": invoice.get("tax_total"),
                "discount_total": invoice.get("discount_total"),
                "grand_total": invoice.get("grand_total"),
                "currency": invoice.get("currency"),
            },
        }
        
        # Add optional fields if present
        if "notes" in invoice:
            output["notes"] = invoice["notes"]
        
        return json.dumps(output, ensure_ascii=False, indent=2)
    
    def extract_region(self, invoice: Dict[str, Any], region: str) -> str:
        """
        Extract a specific region from invoice.
        
        Args:
            invoice: Invoice data dictionary
            region: Region to extract ("vendor_block", "client_info", etc.)
            
        Returns:
            JSON string for the region
        """
        if region == "vendor_block":
            return json.dumps({
                "region": "vendor_block",
                "content": invoice.get("vendor", {})
            }, ensure_ascii=False)
        
        elif region == "client_info":
            return json.dumps({
                "region": "client_info",
                "content": invoice.get("client", {})
            }, ensure_ascii=False)
        
        elif region == "invoice_metadata":
            return json.dumps({
                "region": "invoice_metadata",
                "content": {
                    "invoice_id": invoice.get("invoice_id"),
                    "issue_date": invoice.get("issue_date"),
                    "due_date": invoice.get("due_date"),
                    "payment_terms": invoice.get("payment_terms"),
                }
            }, ensure_ascii=False)
        
        elif region == "line_items":
            return json.dumps({
                "region": "line_items",
                "content": {
                    "items": invoice.get("items", [])
                }
            }, ensure_ascii=False)
        
        elif region == "financial_summary":
            return json.dumps({
                "region": "financial_summary",
                "content": {
                    "subtotal": invoice.get("subtotal"),
                    "tax_rate": invoice.get("tax_rate"),
                    "tax_total": invoice.get("tax_total"),
                    "discount_total": invoice.get("discount_total"),
                    "grand_total": invoice.get("grand_total"),
                    "currency": invoice.get("currency"),
                }
            }, ensure_ascii=False)
        
        else:
            return json.dumps({"region": region, "content": {}}, ensure_ascii=False)
    
    def create_instruction_pair(
        self,
        image_path: str,
        invoice: Dict[str, Any],
        instruction_type: str = "full_extraction",
        use_image_embedding: bool = True,
    ) -> Dict[str, Any]:
        """
        Create a single instruction-response pair.
        
        Args:
            image_path: Path to document image
            invoice: Invoice data dictionary
            instruction_type: Type of instruction
            use_image_embedding: Whether to embed image as base64 (for JSONL format)
            
        Returns:
            Instruction-response pair dictionary
        """
        import random
        
        # Select random template for the instruction type
        templates = self.instruction_templates.get(instruction_type, [])
        if not templates:
            templates = ["Extract information from this document."]
        
        instruction = random.choice(templates)
        
        # Generate response based on instruction type
        if instruction_type == "full_extraction":
            response = self.invoice_to_json(invoice)
        elif instruction_type in ["vendor_block", "client_info", "invoice_metadata", 
                                  "line_items", "financial_summary"]:
            response = self.extract_region(invoice, instruction_type)
        elif instruction_type == "specific_field":
            # Extract specific field based on instruction
            if "invoice number" in instruction.lower():
                response = json.dumps({"field": "invoice_id", "value": invoice.get("invoice_id")})
            elif "total" in instruction.lower():
                response = json.dumps({"field": "grand_total", "value": invoice.get("grand_total")})
            elif "vendor name" in instruction.lower():
                response = json.dumps({"field": "vendor_name", "value": invoice.get("vendor", {}).get("name")})
            elif "due date" in instruction.lower():
                response = json.dumps({"field": "due_date", "value": invoice.get("due_date")})
            else:
                response = json.dumps({"field": "unknown", "value": ""})
        else:
            response = self.invoice_to_json(invoice)
        
        # Format for PaddleOCR-VL / ERNIEKit
        if use_image_embedding:
            # Embed image as base64
            with open(image_path, "rb") as img_file:
                image_data = base64.b64encode(img_file.read()).decode("utf-8")
            
            pair = {
                "image": image_data,
                "conversations": [
                    {
                        "role": "human",
                        "content": f"<image>\n{instruction}"
                    },
                    {
                        "role": "assistant",
                        "content": response
                    }
                ]
            }
        else:
            # Use image path (for ERNIEKit format)
            pair = {
                "image": image_path,
                "conversations": [
                    {
                        "role": "human",
                        "content": f"<image>\n{instruction}"
                    },
                    {
                        "role": "assistant",
                        "content": response
                    }
                ]
            }
        
        return pair
    
    def generate_pairs_from_dataset(
        self,
        dataset_path: str,
        images_dir: str,
        output_path: str,
        pairs_per_sample: int = 5,
        instruction_types: List[str] = None,
    ) -> str:
        """
        Generate instruction pairs from a dataset file.
        
        Args:
            dataset_path: Path to JSONL dataset file
            images_dir: Directory containing document images
            output_path: Output path for instruction pairs JSONL
            pairs_per_sample: Number of instruction pairs per document
            instruction_types: List of instruction types to use (None = all)
            
        Returns:
            Path to generated instruction pairs file
        """
        if instruction_types is None:
            instruction_types = [
                "full_extraction",
                "vendor_block",
                "client_info",
                "line_items",
                "financial_summary",
            ]
        
        images_dir = Path(images_dir)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        pairs = []
        
        with open(dataset_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f):
                if not line.strip():
                    continue
                
                try:
                    invoice = json.loads(line)
                    
                    # Find corresponding image
                    invoice_id = invoice.get("invoice_id", f"invoice_{line_num}")
                    # Try different image extensions
                    image_path = None
                    for ext in [".png", ".jpg", ".jpeg", ".pdf"]:
                        potential_path = images_dir / f"{invoice_id}{ext}"
                        if potential_path.exists():
                            image_path = potential_path
                            break
                    
                    if image_path is None:
                        print(f"Warning: No image found for {invoice_id}, skipping")
                        continue
                    
                    # Generate multiple instruction pairs per document
                    selected_types = instruction_types[:pairs_per_sample]
                    for inst_type in selected_types:
                        pair = self.create_instruction_pair(
                            str(image_path),
                            invoice,
                            instruction_type=inst_type,
                            use_image_embedding=False,  # Use path for ERNIEKit
                        )
                        pairs.append(pair)
                
                except json.JSONDecodeError as e:
                    print(f"Error parsing line {line_num}: {e}")
                    continue
        
        # Write pairs to JSONL file
        with open(output_path, "w", encoding="utf-8") as f:
            for pair in pairs:
                f.write(json.dumps(pair, ensure_ascii=False) + "\n")
        
        print(f"Generated {len(pairs)} instruction pairs to {output_path}")
        return str(output_path)


def create_instruction_pairs(
    dataset_path: str,
    images_dir: str,
    output_path: str = "training_data/instruction_pairs.jsonl",
    pairs_per_sample: int = 5,
):
    """
    Main function to create instruction pairs from dataset.
    
    Args:
        dataset_path: Path to JSONL dataset file
        images_dir: Directory containing document images
        output_path: Output path for instruction pairs
        pairs_per_sample: Number of instruction pairs per document
    """
    generator = InstructionPairGenerator()
    
    return generator.generate_pairs_from_dataset(
        dataset_path=dataset_path,
        images_dir=images_dir,
        output_path=output_path,
        pairs_per_sample=pairs_per_sample,
    )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate instruction pairs for fine-tuning")
    parser.add_argument("--dataset", type=str, required=True, help="Path to dataset JSONL file")
    parser.add_argument("--images-dir", type=str, required=True, help="Directory with document images")
    parser.add_argument("--output", type=str, default="instruction_pairs.jsonl", help="Output path")
    parser.add_argument("--pairs-per-sample", type=int, default=5, help="Pairs per document")
    
    args = parser.parse_args()
    
    create_instruction_pairs(
        dataset_path=args.dataset,
        images_dir=args.images_dir,
        output_path=args.output,
        pairs_per_sample=args.pairs_per_sample,
    )


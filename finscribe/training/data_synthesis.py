"""
Enhanced synthetic data generation for PaddleOCR-VL fine-tuning
Implements PaddleOCR-VL's data synthesis strategy for financial documents
"""

import random
import json
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from faker import Faker
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.colors import black, gray
import io

fake = Faker()


class FinancialDocumentSynthesizer:
    """
    Synthesizes diverse financial documents with perfect ground truth.
    Implements PaddleOCR-VL's data synthesis methodology.
    """
    
    def __init__(
        self,
        output_dir: str = "synthetic_data",
        num_samples: int = 10000,
        currencies: List[str] = None,
        languages: List[str] = None,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.num_samples = num_samples
        
        self.currencies = currencies or ["USD", "EUR", "GBP", "JPY", "CAD", "AUD"]
        self.languages = languages or ["en", "es", "fr", "de"]
        
        # Layout templates
        self.layouts = ["traditional", "modern", "minimal", "international", "handwritten_style"]
        
    def generate_invoice(
        self,
        layout: str = None,
        currency: str = None,
        language: str = "en",
        num_items: int = None,
        include_tax: bool = True,
        include_discount: bool = False,
        complexity: str = "medium",  # "simple", "medium", "complex"
    ) -> Dict[str, Any]:
        """
        Generate a synthetic invoice with perfect ground truth.
        
        Args:
            layout: Layout template name
            currency: Currency code
            language: Language code
            num_items: Number of line items
            include_tax: Whether to include tax
            include_discount: Whether to include discount
            complexity: Document complexity level
            
        Returns:
            Dictionary with invoice data and metadata
        """
        if layout is None:
            layout = random.choice(self.layouts)
        if currency is None:
            currency = random.choice(self.currencies)
        if num_items is None:
            if complexity == "simple":
                num_items = random.randint(1, 3)
            elif complexity == "medium":
                num_items = random.randint(3, 8)
            else:  # complex
                num_items = random.randint(8, 15)
        
        # Generate vendor info
        vendor = {
            "name": fake.company(),
            "address": fake.street_address(),
            "city": fake.city(),
            "state": fake.state_abbr() if language == "en" else fake.state(),
            "postal_code": fake.zipcode(),
            "country": fake.country(),
            "phone": fake.phone_number(),
            "email": fake.company_email(),
            "tax_id": fake.ein(),
            "website": fake.url(),
        }
        
        # Generate client info
        client = {
            "name": fake.company(),
            "address": fake.street_address(),
            "city": fake.city(),
            "state": fake.state_abbr() if language == "en" else fake.state(),
            "postal_code": fake.zipcode(),
            "country": fake.country(),
        }
        
        # Generate line items
        line_items = []
        subtotal = Decimal("0.00")
        
        for i in range(num_items):
            qty = random.randint(1, 10)
            price = Decimal(str(random.uniform(5.0, 500.0))).quantize(Decimal("0.01"))
            total = (qty * price).quantize(Decimal("0.01"))
            subtotal += total
            
            # Add variety to descriptions
            description_types = [
                fake.bs() + " Service",
                fake.catch_phrase() + " Package",
                fake.word() + " Subscription",
                fake.company() + " License",
            ]
            
            line_items.append({
                "item_number": i + 1,
                "description": random.choice(description_types),
                "quantity": qty,
                "unit_price": float(price),
                "line_total": float(total),
                "sku": f"SKU-{random.randint(1000, 9999)}",
            })
        
        # Calculate tax
        tax_rate = Decimal("0.10") if include_tax else Decimal("0.00")
        if complexity == "complex":
            # Multiple tax rates
            tax_rate = Decimal(str(random.uniform(0.08, 0.15)))
        tax = (subtotal * tax_rate).quantize(Decimal("0.01"))
        
        # Calculate discount
        discount = Decimal("0.00")
        if include_discount and random.random() > 0.5:
            discount_rate = Decimal(str(random.uniform(0.05, 0.20)))
            discount = (subtotal * discount_rate).quantize(Decimal("0.01"))
        
        # Calculate grand total
        grand_total = (subtotal + tax - discount).quantize(Decimal("0.01"))
        
        # Generate invoice metadata
        invoice_id = f"INV-{fake.year()}-{random.randint(1000, 9999)}"
        issue_date = fake.date_between(start_date="-1y", end_date="today").isoformat()
        due_date = fake.date_between(start_date="today", end_date="+60d").isoformat()
        
        # Payment terms
        payment_terms_options = [
            "Net 30", "Net 15", "Net 60", "Due on Receipt",
            "2/10 Net 30", "1/15 Net 30", "Net 45"
        ]
        
        return {
            "invoice_id": invoice_id,
            "vendor": vendor,
            "client": client,
            "issue_date": issue_date,
            "due_date": due_date,
            "items": line_items,
            "subtotal": float(subtotal),
            "tax_rate": float(tax_rate),
            "tax_total": float(tax),
            "discount_total": float(discount),
            "grand_total": float(grand_total),
            "currency": currency,
            "payment_terms": random.choice(payment_terms_options),
            "notes": fake.text(max_nb_chars=100) if complexity == "complex" else "",
            "metadata": {
                "layout": layout,
                "language": language,
                "complexity": complexity,
                "num_items": num_items,
            }
        }
    
    def generate_hard_sample(
        self,
        error_type: str,
        base_invoice: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Generate a hard sample targeting a specific error type.
        
        Args:
            error_type: Type of error to target:
                - "multi_currency": Multiple currencies in one document
                - "nested_table": Nested table structures
                - "handwritten": Handwritten annotations
                - "poor_quality": Low quality scan simulation
                - "unusual_layout": Non-standard layout
                - "complex_tax": Multiple tax rates
                - "missing_fields": Intentionally missing optional fields
            base_invoice: Base invoice to modify (optional)
            
        Returns:
            Modified invoice dictionary
        """
        if base_invoice is None:
            base_invoice = self.generate_invoice(complexity="medium")
        
        if error_type == "multi_currency":
            # Add line items with different currencies
            for item in base_invoice["items"][:2]:
                item["currency"] = random.choice(self.currencies)
                item["currency_symbol"] = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥"}.get(
                    item["currency"], "$"
                )
        
        elif error_type == "complex_tax":
            # Multiple tax rates per item
            base_invoice["tax_rate"] = None
            base_invoice["tax_breakdown"] = []
            for item in base_invoice["items"]:
                item_tax_rate = Decimal(str(random.uniform(0.05, 0.15)))
                item_tax = (Decimal(str(item["line_total"])) * item_tax_rate).quantize(Decimal("0.01"))
                base_invoice["tax_breakdown"].append({
                    "item": item["description"],
                    "rate": float(item_tax_rate),
                    "amount": float(item_tax),
                })
            base_invoice["tax_total"] = sum(t["amount"] for t in base_invoice["tax_breakdown"])
            base_invoice["grand_total"] = (
                base_invoice["subtotal"] + base_invoice["tax_total"] - base_invoice["discount_total"]
            )
        
        elif error_type == "unusual_layout":
            base_invoice["metadata"]["layout"] = "unusual"
            base_invoice["metadata"]["rotation"] = random.uniform(-3, 3)
            base_invoice["metadata"]["skew"] = random.uniform(-2, 2)
        
        elif error_type == "missing_fields":
            # Randomly remove optional fields
            optional_fields = ["notes", "payment_terms", "vendor.website", "client.country"]
            for field in random.sample(optional_fields, k=random.randint(1, 2)):
                if "." in field:
                    obj, key = field.split(".")
                    if obj in base_invoice and key in base_invoice[obj]:
                        del base_invoice[obj][key]
                elif field in base_invoice:
                    del base_invoice[field]
        
        base_invoice["metadata"]["hard_sample_type"] = error_type
        return base_invoice
    
    def generate_dataset(
        self,
        output_format: str = "jsonl",  # "jsonl" or "json"
        include_hard_samples: bool = True,
        hard_sample_ratio: float = 0.1,  # 10% hard samples
    ) -> str:
        """
        Generate a complete dataset of synthetic financial documents.
        
        Args:
            output_format: Output format ("jsonl" or "json")
            include_hard_samples: Whether to include hard samples
            hard_sample_ratio: Ratio of hard samples to total
            
        Returns:
            Path to generated dataset file
        """
        num_hard_samples = int(self.num_samples * hard_sample_ratio) if include_hard_samples else 0
        num_regular_samples = self.num_samples - num_hard_samples
        
        output_file = self.output_dir / f"financial_documents.{output_format}"
        
        error_types = [
            "multi_currency", "complex_tax", "unusual_layout",
            "missing_fields", "nested_table", "poor_quality"
        ]
        
        with open(output_file, "w", encoding="utf-8") as f:
            # Generate regular samples
            for i in range(num_regular_samples):
                complexity = random.choice(["simple", "medium", "complex"])
                invoice = self.generate_invoice(
                    currency=random.choice(self.currencies),
                    language=random.choice(self.languages),
                    complexity=complexity,
                )
                
                if output_format == "jsonl":
                    f.write(json.dumps(invoice, ensure_ascii=False) + "\n")
                else:
                    # For JSON format, we'll collect all and write at end
                    pass
            
            # Generate hard samples
            for i in range(num_hard_samples):
                base_invoice = self.generate_invoice(complexity="complex")
                error_type = random.choice(error_types)
                hard_invoice = self.generate_hard_sample(error_type, base_invoice)
                
                if output_format == "jsonl":
                    f.write(json.dumps(hard_invoice, ensure_ascii=False) + "\n")
        
        print(f"Generated {self.num_samples} samples to {output_file}")
        return str(output_file)


def create_synthetic_dataset(
    num_samples: int = 10000,
    output_dir: str = "synthetic_data",
    include_hard_samples: bool = True,
):
    """
    Main function to create synthetic dataset.
    
    Args:
        num_samples: Number of samples to generate
        output_dir: Output directory
        include_hard_samples: Whether to include hard samples
    """
    synthesizer = FinancialDocumentSynthesizer(
        output_dir=output_dir,
        num_samples=num_samples,
    )
    
    dataset_path = synthesizer.generate_dataset(
        include_hard_samples=include_hard_samples,
    )
    
    return dataset_path


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate synthetic financial documents")
    parser.add_argument("--num-samples", type=int, default=10000, help="Number of samples to generate")
    parser.add_argument("--output-dir", type=str, default="synthetic_data", help="Output directory")
    parser.add_argument("--no-hard-samples", action="store_true", help="Skip hard sample generation")
    
    args = parser.parse_args()
    
    create_synthetic_dataset(
        num_samples=args.num_samples,
        output_dir=args.output_dir,
        include_hard_samples=not args.no_hard_samples,
    )


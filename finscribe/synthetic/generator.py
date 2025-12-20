"""
Synthetic financial document generator
Creates perfectly labeled invoices with exact arithmetic
"""

import random
from decimal import Decimal
from typing import Dict, Any, List
from faker import Faker

fake = Faker()


def generate_invoice(
    num_items: int = None,
    currency: str = "USD",
    include_tax: bool = True,
    include_discount: bool = False,
) -> Dict[str, Any]:
    """
    Generates a synthetic invoice with perfect ground truth.
    
    Args:
        num_items: Number of line items (default: random 3-10)
        currency: Currency code (default: "USD")
        include_tax: Whether to include tax (default: True)
        include_discount: Whether to include discount (default: False)
        
    Returns:
        Dictionary with complete invoice data
    """
    if num_items is None:
        num_items = random.randint(3, 10)
    
    # Generate vendor info
    vendor = {
        "name": fake.company(),
        "address": fake.street_address(),
        "city": fake.city(),
        "state": fake.state_abbr(),
        "postal_code": fake.zipcode(),
        "country": "USA",
        "phone": fake.phone_number(),
        "email": fake.company_email(),
        "tax_id": fake.ein(),
    }
    
    # Generate client info
    client = {
        "name": fake.company(),
        "address": fake.street_address(),
        "city": fake.city(),
        "state": fake.state_abbr(),
        "postal_code": fake.zipcode(),
    }
    
    # Generate line items
    line_items = []
    subtotal = Decimal("0.00")
    
    for _ in range(num_items):
        qty = random.randint(1, 5)
        price = Decimal(str(random.uniform(5.0, 100.0))).quantize(Decimal("0.01"))
        total = (qty * price).quantize(Decimal("0.01"))
        subtotal += total
        
        line_items.append({
            "description": fake.bs() + " Service",
            "quantity": qty,
            "unit_price": float(price),
            "line_total": float(total),
        })
    
    # Calculate tax
    tax_rate = Decimal("0.10") if include_tax else Decimal("0.00")
    tax = (subtotal * tax_rate).quantize(Decimal("0.01"))
    
    # Calculate discount
    discount = Decimal("0.00")
    if include_discount and random.random() > 0.5:
        discount_rate = Decimal(str(random.uniform(0.05, 0.15)))
        discount = (subtotal * discount_rate).quantize(Decimal("0.01"))
    
    # Calculate grand total
    grand_total = (subtotal + tax - discount).quantize(Decimal("0.01"))
    
    # Generate invoice metadata
    invoice_id = f"INV-{fake.year()}-{random.randint(1000, 9999)}"
    issue_date = fake.date_between(start_date="-1y", end_date="today").isoformat()
    due_date = fake.date_between(start_date="today", end_date="+30d").isoformat()
    
    return {
        "invoice_id": invoice_id,
        "vendor": vendor,
        "client": client,
        "issue_date": issue_date,
        "due_date": due_date,
        "items": line_items,
        "subtotal": float(subtotal),
        "tax_total": float(tax),
        "discount_total": float(discount),
        "grand_total": float(grand_total),
        "currency": currency,
        "payment_terms": random.choice(["Net 30", "Net 15", "Due on Receipt", "Net 60"]),
    }


#!/usr/bin/env python3
"""
Generate 5 synthetic sample invoice PNGs for demo purposes.
Creates clean, professional-looking invoices with varied layouts.
"""
import os
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

# Ensure examples directory exists
examples_dir = Path("examples")
examples_dir.mkdir(exist_ok=True)

# Try to use a better font if available, otherwise use default
try:
    # Try to use a system font (adjust path for your OS)
    font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
    font_medium = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
    font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
except:
    font_large = ImageFont.load_default()
    font_medium = ImageFont.load_default()
    font_small = ImageFont.load_default()

def create_sample_invoice(num: int, layout_type: str = "standard"):
    """Create a sample invoice image."""
    # Create image (1200x800 pixels)
    img = Image.new("RGB", (1200, 800), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    
    # Colors
    black = (0, 0, 0)
    gray = (128, 128, 128)
    dark_gray = (64, 64, 64)
    blue = (0, 100, 200)
    
    y = 40
    
    # Header
    d.text((50, y), f"Sample Invoice #{num}", fill=black, font=font_large)
    y += 40
    
    # Vendor info (left side)
    d.text((50, y), "Vendor: DemoCo Ltd.", fill=black, font=font_medium)
    y += 25
    d.text((50, y), "123 Business Street", fill=dark_gray, font=font_small)
    y += 20
    d.text((50, y), "San Francisco, CA 94102", fill=dark_gray, font=font_small)
    y += 20
    d.text((50, y), "Tax ID: 12-3456789", fill=dark_gray, font=font_small)
    
    # Invoice info (right side)
    invoice_y = 80
    d.text((850, invoice_y), f"Invoice #: INV-2024-{num:03d}", fill=black, font=font_medium)
    invoice_y += 25
    d.text((850, invoice_y), "Date: 2024-01-15", fill=dark_gray, font=font_small)
    invoice_y += 20
    d.text((850, invoice_y), "Due: 2024-02-15", fill=dark_gray, font=font_small)
    invoice_y += 20
    d.text((850, invoice_y), "PO #: PO-2024-001", fill=dark_gray, font=font_small)
    
    # Bill to section
    y += 50
    d.text((50, y), "Bill To:", fill=black, font=font_medium)
    y += 25
    d.text((50, y), "Client Industries Inc.", fill=black, font=font_small)
    y += 20
    d.text((50, y), "456 Customer Avenue", fill=dark_gray, font=font_small)
    y += 20
    d.text((50, y), "New York, NY 10001", fill=dark_gray, font=font_small)
    
    # Line items table header
    y += 50
    d.line([(50, y), (1150, y)], fill=gray, width=2)
    y += 15
    d.text((50, y), "Description", fill=black, font=font_medium)
    d.text((450, y), "Qty", fill=black, font=font_medium)
    d.text((550, y), "Unit Price", fill=black, font=font_medium)
    d.text((750, y), "Total", fill=black, font=font_medium)
    y += 30
    d.line([(50, y), (1150, y)], fill=gray, width=1)
    
    # Line items (varies by invoice number)
    items = [
        (f"Widget A x{num}", num, 50.00, num * 50.00),
        (f"Service B - Package {num}", 1, 100.00 * num, 100.00 * num),
        (f"Support Plan {num} months", num, 25.00, num * 25.00),
    ]
    
    for desc, qty, price, total in items:
        y += 25
        d.text((50, y), desc, fill=black, font=font_small)
        d.text((450, y), str(qty), fill=dark_gray, font=font_small)
        d.text((550, y), f"${price:.2f}", fill=dark_gray, font=font_small)
        d.text((750, y), f"${total:.2f}", fill=black, font=font_small)
    
    # Totals section
    y += 40
    subtotal = sum(total for _, _, _, total in items)
    tax = subtotal * 0.10
    grand_total = subtotal + tax
    
    d.text((850, y), "Subtotal:", fill=dark_gray, font=font_medium)
    d.text((1000, y), f"${subtotal:.2f}", fill=black, font=font_medium)
    y += 30
    d.text((850, y), "Tax (10%):", fill=dark_gray, font=font_medium)
    d.text((1000, y), f"${tax:.2f}", fill=black, font=font_medium)
    y += 40
    d.line([(850, y), (1150, y)], fill=black, width=2)
    y += 20
    d.text((850, y), "Grand Total:", fill=black, font=font_large)
    d.text((1000, y), f"${grand_total:.2f}", fill=blue, font=font_large)
    
    # Footer
    y = 750
    d.text((50, y), "Thank you for your business!", fill=gray, font=font_small)
    d.text((850, y), "Payment terms: Net 30", fill=gray, font=font_small)
    
    return img

# Generate 5 sample invoices
print("Generating 5 sample invoices...")
for i in range(1, 6):
    invoice_img = create_sample_invoice(i)
    output_path = examples_dir / f"sample_invoice_{i}.png"
    invoice_img.save(output_path)
    print(f"Created: {output_path}")

print(f"\n✅ Generated 5 sample invoices in {examples_dir}/")
print("Files:")
for i in range(1, 6):
    print(f"  - sample_invoice_{i}.png")


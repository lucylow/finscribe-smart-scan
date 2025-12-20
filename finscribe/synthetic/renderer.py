"""
Invoice renderer - converts invoice data to images
"""

from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Any, Optional
from pathlib import Path


def render_invoice(
    data: Dict[str, Any],
    width: int = 2480,
    height: int = 3508,
    font_size: int = 40,
) -> Image.Image:
    """
    Renders an invoice as an image.
    
    Args:
        data: Invoice data dictionary
        width: Image width in pixels (default: A4 width at 300 DPI)
        height: Image height in pixels (default: A4 height at 300 DPI)
        font_size: Font size in pixels
        
    Returns:
        PIL Image of the invoice
    """
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    
    # Try to load a font, fallback to default
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size - 10)
    except:
        try:
            font = ImageFont.load_default()
            font_small = ImageFont.load_default()
        except:
            font = None
            font_small = None
    
    y = 100
    margin = 100
    
    # Header
    draw.text((margin, y), "INVOICE", font=font, fill="black")
    y += 60
    
    # Invoice number and date
    draw.text((margin, y), f"Invoice #: {data['invoice_id']}", font=font_small, fill="black")
    draw.text((width - margin - 300, y), f"Date: {data['issue_date']}", font=font_small, fill="black")
    y += 40
    
    # Vendor block
    vendor = data["vendor"]
    draw.text((margin, y), vendor["name"], font=font, fill="black")
    y += 40
    draw.text((margin, y), vendor["address"], font=font_small, fill="black")
    y += 30
    draw.text((margin, y), f"{vendor['city']}, {vendor['state']} {vendor['postal_code']}", font=font_small, fill="black")
    y += 50
    
    # Client block
    client = data["client"]
    draw.text((margin, y), f"Bill To: {client['name']}", font=font, fill="black")
    y += 40
    draw.text((margin, y), client["address"], font=font_small, fill="black")
    y += 30
    draw.text((margin, y), f"{client['city']}, {client['state']} {client['postal_code']}", font=font_small, fill="black")
    y += 60
    
    # Line items table header
    table_y = y
    draw.text((margin, y), "Description", font=font, fill="black")
    draw.text((width // 2 - 200, y), "Qty", font=font, fill="black")
    draw.text((width // 2, y), "Unit Price", font=font, fill="black")
    draw.text((width - margin - 200, y), "Total", font=font, fill="black")
    y += 50
    
    # Draw line
    draw.line([(margin, y), (width - margin, y)], fill="black", width=2)
    y += 20
    
    # Line items
    for item in data["items"]:
        draw.text((margin, y), item["description"], font=font_small, fill="black")
        draw.text((width // 2 - 200, y), str(item["quantity"]), font=font_small, fill="black")
        draw.text((width // 2, y), f"${item['unit_price']:.2f}", font=font_small, fill="black")
        draw.text((width - margin - 200, y), f"${item['line_total']:.2f}", font=font_small, fill="black")
        y += 40
    
    y += 20
    
    # Totals section
    totals_x = width - margin - 300
    draw.text((totals_x, y), f"Subtotal: ${data['subtotal']:.2f}", font=font_small, fill="black")
    y += 30
    
    if data.get("tax_total", 0) > 0:
        draw.text((totals_x, y), f"Tax: ${data['tax_total']:.2f}", font=font_small, fill="black")
        y += 30
    
    if data.get("discount_total", 0) > 0:
        draw.text((totals_x, y), f"Discount: ${data['discount_total']:.2f}", font=font_small, fill="black")
        y += 30
    
    draw.line([(totals_x, y), (width - margin, y)], fill="black", width=2)
    y += 20
    
    draw.text((totals_x, y), f"Total: ${data['grand_total']:.2f} {data['currency']}", font=font, fill="black")
    y += 40
    
    draw.text((margin, y), f"Payment Terms: {data['payment_terms']}", font=font_small, fill="black")
    
    return img


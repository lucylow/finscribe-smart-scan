#!/usr/bin/env python3
"""
generate_sample_invoice.py
Generates a realistic-looking invoice PNG/JPG for quick testing.
Produces examples/sample_invoice.jpg
"""
from PIL import Image, ImageDraw, ImageFont
import os

OUT_DIR = "examples"
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PATH = os.path.join(OUT_DIR, "sample_invoice.jpg")

W, H = 1240, 1754  # A4-like dimensions
bg = (248, 249, 250)
img = Image.new("RGB", (W, H), color=bg)
draw = ImageDraw.Draw(img)

# Try to pick a TTF font, fallback to default
def try_font(size):
    candidates = [
        "DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "arial.ttf"
    ]
    for c in candidates:
        try:
            return ImageFont.truetype(c, size=size)
        except Exception:
            continue
    return ImageFont.load_default()

title_font = try_font(40)
h1 = try_font(28)
mono = try_font(20)
small = try_font(16)

# Header
draw.rectangle([(40, 40), (W-40, 160)], fill=(255,255,255))
draw.text((60, 60), "TechCorp Inc.", font=title_font, fill=(10,10,30))
draw.text((60, 110), "123 Innovation Blvd, Suite 100\nCityville, CA 94000", font=small, fill=(70,70,90))

# Invoice meta
meta_x = W - 420
draw.text((meta_x, 60), "INVOICE", font=h1, fill=(0,30,60))
draw.text((meta_x, 100), "Invoice #: INV-2024-001", font=mono, fill=(30,30,40))
draw.text((meta_x, 130), "Date: 2024-01-15", font=mono, fill=(30,30,40))

# Bill to
draw.text((60, 200), "Bill To:", font=mono, fill=(10,10,20))
draw.text((60, 230), "ABC Holdings\n45 Business Rd\nMetro City, NY 10001", font=small, fill=(60,60,80))

# Table header
table_x = 60
y_table = 320
draw.rectangle([(table_x-8, y_table-8), (W-60, y_table+36)], fill=(245,246,247))
draw.text((table_x, y_table), "Description", font=mono, fill=(20,20,30))
draw.text((table_x+520, y_table), "Qty", font=mono, fill=(20,20,30))
draw.text((table_x+620, y_table), "Unit", font=mono, fill=(20,20,30))
draw.text((table_x+760, y_table), "Total", font=mono, fill=(20,20,30))
draw.line((table_x, y_table+40, W-60, y_table+40), fill=(220,220,225), width=1)

# Sample rows
rows = [
    ("Enterprise License", 5, 250.00),
    ("Support Package", 1, 292.76)
]
row_y = y_table + 56
for desc, qty, unit in rows:
    draw.text((table_x, row_y), desc, font=small, fill=(30,30,40))
    draw.text((table_x+520, row_y), str(qty), font=small, fill=(30,30,40))
    draw.text((table_x+620, row_y), f"{unit:.2f}", font=small, fill=(30,30,40))
    draw.text((table_x+760, row_y), f"{qty*unit:.2f}", font=small, fill=(30,30,40))
    row_y += 36

# Totals
y_tot = row_y + 24
draw.text((table_x+620, y_tot), "Subtotal", font=mono, fill=(10,10,20))
draw.text((table_x+760, y_tot), "1542.76", font=mono, fill=(10,10,20))
y_tot += 28
draw.text((table_x+620, y_tot), "Tax (10%)", font=mono, fill=(10,10,20))
draw.text((table_x+760, y_tot), "154.28", font=mono, fill=(10,10,20))
y_tot += 36
draw.text((table_x+620, y_tot), "Total", font=title_font, fill=(0,0,0))
draw.text((table_x+760, y_tot), "1697.04", font=title_font, fill=(0,0,0))

# Footer small print
draw.text((60, H-160), "Payment due within 30 days. Please remit to TechCorp Inc. bank details on file.", font=small, fill=(90,90,100))

# Subtle stamp
draw.ellipse((W-220, H-320, W-120, H-220), outline=(200,30,30), width=3)
draw.text((W-200, H-300), "PAID", font=try_font(24), fill=(200,30,30))

# Save
img.save(OUT_PATH, quality=92)
print(f"✓ Generated sample invoice: {OUT_PATH}")



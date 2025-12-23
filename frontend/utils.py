# frontend/utils.py
from PIL import Image, ImageDraw, ImageFont
import io, csv

def draw_bboxes_on_image(img: Image.Image, words: list):
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    for w in words or []:
        bbox = w.get("bbox")
        if not bbox or len(bbox) < 4:
            continue
        x1, y1, x2, y2 = bbox[0], bbox[1], bbox[2], bbox[3]
        draw.rectangle([x1,y1,x2,y2], outline="red", width=2)
        text = w.get("text","")
        if font:
            draw.text((x1, max(y1-12,0)), text, fill="white", font=font)
    return img

def editable_from_structured(struct: dict):
    # safe mapping; keep shape simple for UI
    vendor = struct.get("vendor", {})
    line_items = struct.get("line_items", [])
    items = []
    for li in line_items:
        items.append({
            "description": li.get("description",""),
            "quantity": int(li.get("quantity",1)),
            "unit_price": li.get("unit_price", ""),
            "line_total": li.get("line_total", "")
        })
    return {"vendor": {"name": vendor.get("name","")}, "invoice_date": struct.get("invoice_date",""), "line_items": items}

def json_to_csv(struct: dict):
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["description","quantity","unit_price","line_total"])
    for li in struct.get("line_items", []):
        writer.writerow([li.get("description",""), li.get("quantity",1), li.get("unit_price",""), li.get("line_total","")])
    return out.getvalue()

# frontend/utils.py
from PIL import Image, ImageDraw, ImageFont
import io, csv, json

def draw_bboxes_on_image(pil_img: Image.Image, words: list, box_color=(0,180,230)):
    img = pil_img.copy()
    draw = ImageDraw.Draw(img, "RGBA")
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    for w in words or []:
        bbox = w.get("bbox") or w.get("box") or []
        if len(bbox) >= 4:
            x1, y1, x2, y2 = bbox[0], bbox[1], bbox[2], bbox[3]
            draw.rectangle([x1,y1,x2,y2], outline=box_color+(255,), width=2)
            label = w.get("text","")
            if font:
                tw, th = draw.textsize(label, font=font)
                draw.rectangle([x1, max(0,y1-th-4), x1+tw+6, y1], fill=(0,0,0,180))
                draw.text((x1+3, max(0,y1-th-3)), label, fill=(255,255,255,255), font=font)
    return img

def struct_to_csv(struct):
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["description","quantity","unit_price","line_total"])
    for li in struct.get("line_items", []):
        writer.writerow([li.get("description",""), li.get("quantity",1), li.get("unit_price",""), li.get("line_total","")])
    return out.getvalue()

def pretty_json(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False)

# Backward compatibility aliases
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
    return struct_to_csv(struct)

def normalize_structured(struct: dict):
    """Normalize structured invoice for UI display"""
    return editable_from_structured(struct)

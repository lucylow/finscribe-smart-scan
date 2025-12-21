#!/usr/bin/env python3
"""
generate_synthetic_invoices.py
Generates synthetic invoices (images + ground-truth JSON + noisy OCR text)
and a dataset JSONL suitable for fine-tuning (prompt -> completion).

Produces two dataset variants:
 - clean ground truth dataset (ocr_text noisy -> correct JSON)
 - dataset with deliberate arithmetic errors injected at a configurable rate
"""

import os
import json
import random
import math
from datetime import datetime, timedelta
from faker import Faker
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import numpy as np
from tqdm import trange, tqdm
import argparse
from dateutil.relativedelta import relativedelta

# -------------------------
# Utilities and settings
# -------------------------
fake = Faker()
FALLBACK_FONT = None  # will use default PIL font if truetype not found

def try_load_font(preferred_list=("DejaVuSans.ttf","Arial.ttf","LiberationSans-Regular.ttf"), size=26):
    for name in preferred_list:
        try:
            return ImageFont.truetype(name, size=size)
        except Exception:
            continue
    return ImageFont.load_default()

# -------------------------
# Invoice data generator
# -------------------------
def random_vendor():
    return fake.company()

def random_invoice_number(i):
    return f"INV-{datetime.utcnow().year % 100:02d}-{10000 + i}"

def random_date(start_year=2023, end_year=2025):
    start = datetime(start_year,1,1)
    end = datetime(end_year,12,31)
    delta = end - start
    return (start + timedelta(days=random.randint(0, delta.days))).date().isoformat()

def generate_line_items(min_items=1, max_items=6, currency="$"):
    n = random.randint(min_items, max_items)
    items = []
    for _ in range(n):
        desc = random.choice([
            "Consulting", "Enterprise License", "Support Package", "Service Fee",
            "Cloud Hosting", "Hardware Kit", "Software Subscription", "Data Report",
            "Training", "Security Audit", "Integration Work"
        ])
        qty = random.randint(1,10)
        unit_price = round(random.choice([19.99,29.99,49.0,75.0,99.0,120.0,250.0,500.0,1500.0,2200.0]) * random.choice([1,1,1]), 2)
        line_total = round(qty * unit_price, 2)
        items.append({"desc": desc, "qty": qty, "unit_price": unit_price, "line_total": line_total})
    return items

def compute_financials(line_items, tax_rate=None):
    subtotal = round(sum(item["line_total"] for item in line_items), 2)
    if tax_rate is None:
        # choose tax rate sometimes 0, sometimes 10%, 20%
        tax_rate = random.choice([0.0, 0.0, 0.05, 0.1, 0.2])
    tax_amount = round(subtotal * tax_rate, 2)
    grand_total = round(subtotal + tax_amount, 2)
    return {"subtotal": subtotal, "tax_rate": tax_rate, "tax_amount": tax_amount, "grand_total": grand_total}

def make_invoice(i):
    vendor = random_vendor()
    inv_no = random_invoice_number(i)
    issue_date = random_date(2023, 2025)
    items = generate_line_items()
    fin = compute_financials(items)
    return {
        "invoice_id": inv_no,
        "vendor": {"name": vendor, "address": fake.address().replace("\n", ", ")},
        "client": {"name": fake.company(), "address": fake.address().replace("\n", ", ")},
        "issue_date": issue_date,
        "line_items": items,
        "financial_summary": fin,
    }

# -------------------------
# OCR text (noisy) generator
# -------------------------
# Character-level OCR error map for substitutions
OCR_SUBS = {
    "0": ["O", "D"],
    "1": ["I", "l"],
    "2": ["Z"],
    "5": ["S"],
    "6": ["G"],
    "8": ["B"],
    "O": ["0"],
    "I": ["1"],
    "l": ["1"],
    ".": [",", ""],
    ",": [".", ""],
    "$": ["S", ""],
    "rn": ["m"]
}

def apply_char_substitutions(s, p=0.02):
    # substitute characters with OCR-like mistakes with probability p
    out = []
    i = 0
    L = len(s)
    while i < L:
        # check digraph substitutions first (e.g., 'rn' -> 'm')
        substituted = False
        if i+1 < L:
            pair = s[i:i+2]
            if pair in OCR_SUBS and random.random() < p:
                out.append(random.choice(OCR_SUBS[pair]))
                i += 2
                substituted = True
        if substituted:
            continue
        ch = s[i]
        if ch in OCR_SUBS and random.random() < p:
            out.append(random.choice(OCR_SUBS[ch]))
        else:
            # random deletion or insertion
            r = random.random()
            if r < 0.005:
                # drop char
                pass
            elif r < 0.01:
                # duplicate char
                out.append(ch)
                out.append(ch)
            else:
                out.append(ch)
        i += 1
    return "".join(out)

def simulate_ocr_text(gt: dict, noise_level=0.04, shuffle_lines=False):
    """
    Build a realistic OCR-style text block from ground truth then apply noise.
    noise_level: base char-substitution probability
    """
    lines = []
    lines.append(f"Vendor: {gt['vendor']['name']}")
    lines.append(f"Invoice #: {gt['invoice_id']}")
    lines.append(f"Date: {gt['issue_date']}")
    lines.append("")  # blank line
    for item in gt["line_items"]:
        lines.append(f"{item['desc']}  Qty {item['qty']}  Unit {item['unit_price']:.2f}  Total {item['line_total']:.2f}")
    lines.append("")
    fs = gt["financial_summary"]
    lines.append(f"Subtotal {fs['subtotal']:.2f}")
    if fs['tax_rate'] > 0:
        lines.append(f"Tax {fs['tax_amount']:.2f}")
    lines.append(f"Total {fs['grand_total']:.2f}")

    if shuffle_lines and random.random() < 0.05:
        # occasionally scramble small blocks to emulate OCR ordering issues
        random.shuffle(lines)

    text = "\n".join(lines)
    # apply noisy substitutions at character-level
    noisy = apply_char_substitutions(text, p=noise_level)
    # also randomly merge tokens simulating missing spaces
    if random.random() < 0.08:
        noisy = noisy.replace("  ", " ")
    if random.random() < 0.05:
        noisy = noisy.replace("Unit", "Unit ")
    return noisy

# -------------------------
# Image renderer & augmentations
# -------------------------
def render_invoice_image(gt: dict, out_path, canvas_size=(1240,1754), font_path=None):
    """
    Render a simple invoice image (PIL) from ground truth dict.
    canvas_size default is roughly A4 at ~150 DPI (1240x1754).
    """
    W, H = canvas_size
    bg = (245,245,250)
    img = Image.new("RGB", (W,H), bg)
    draw = ImageDraw.Draw(img)

    # fonts
    h_font = try_load_font(size=34)
    sub_font = try_load_font(size=18)
    mono_font = try_load_font(size=16)

    # header vendor left
    x = 60
    y = 40
    draw.text((x,y), gt['vendor']['name'], font=h_font, fill=(10,10,20))
    draw.text((x, y+40), gt['vendor'].get('address',''), font=sub_font, fill=(60,60,80))

    # invoice meta right
    meta_x = W - 420
    draw.text((meta_x, y), f"Invoice #: {gt['invoice_id']}", font=sub_font, fill=(10,10,20))
    draw.text((meta_x, y+24), f"Date: {gt['issue_date']}", font=sub_font, fill=(10,10,20))

    # line items table header
    table_x = 60
    y_table = 160
    draw.text((table_x, y_table), "Description", font=sub_font, fill=(20,20,30))
    draw.text((table_x+520, y_table), "Qty", font=sub_font, fill=(20,20,30))
    draw.text((table_x+620, y_table), "Unit", font=sub_font, fill=(20,20,30))
    draw.text((table_x+760, y_table), "Total", font=sub_font, fill=(20,20,30))
    # draw a line
    draw.line((table_x, y_table+26, W-60, y_table+26), fill=(200,200,210), width=1)

    # rows
    row_y = y_table + 36
    for item in gt['line_items']:
        draw.text((table_x, row_y), item['desc'], font=mono_font, fill=(30,30,40))
        draw.text((table_x+520, row_y), str(item['qty']), font=mono_font, fill=(30,30,40))
        draw.text((table_x+620, row_y), f"{item['unit_price']:.2f}", font=mono_font, fill=(30,30,40))
        draw.text((table_x+760, row_y), f"{item['line_total']:.2f}", font=mono_font, fill=(30,30,40))
        row_y += 28

    # totals
    y_tot = row_y + 20
    fs = gt['financial_summary']
    draw.text((table_x+620, y_tot), "Subtotal", font=sub_font, fill=(10,10,20))
    draw.text((table_x+760, y_tot), f"{fs['subtotal']:.2f}", font=sub_font, fill=(10,10,20))
    y_tot += 26
    if fs['tax_amount'] > 0:
        draw.text((table_x+620, y_tot), f"Tax ({int(fs['tax_rate']*100)}%)", font=sub_font, fill=(10,10,20))
        draw.text((table_x+760, y_tot), f"{fs['tax_amount']:.2f}", font=sub_font, fill=(10,10,20))
        y_tot += 26
    draw.text((table_x+620, y_tot), "Total", font=h_font, fill=(0,0,0))
    draw.text((table_x+760, y_tot), f"{fs['grand_total']:.2f}", font=h_font, fill=(0,0,0))

    # subtle visual elements
    # add a light watermark or faint grid if desired
    # return image
    img.save(out_path, quality=95)
    return out_path

def augment_image(path_in, path_out,
                  rotate_max=3.0,  # degrees
                  jpeg_quality_range=(75, 95),
                  blur_radius_max=1.5,
                  noise_level=0.01,
                  add_stain_prob=0.08):
    img = Image.open(path_in).convert("RGB")
    W,H = img.size

    # small rotation
    angle = random.uniform(-rotate_max, rotate_max)
    img = img.rotate(angle, resample=Image.BICUBIC, expand=False, fillcolor=(245,245,250))

    # perspective-ish: small affine transform
    if random.random() < 0.2:
        coeffs = find_random_affine_coeffs(W,H, max_shift=8)
        img = img.transform((W,H), Image.AFFINE, coeffs, resample=Image.BICUBIC, fillcolor=(245,245,250))

    # gaussian blur
    if blur_radius_max > 0 and random.random() < 0.3:
        r = random.uniform(0.2, blur_radius_max)
        img = img.filter(ImageFilter.GaussianBlur(radius=r))

    # add gaussian noise
    if noise_level > 0 and random.random() < 0.6:
        arr = np.array(img).astype(np.float32) / 255.0
        noise = np.random.normal(0, noise_level, arr.shape)
        arr = np.clip(arr + noise, 0, 1)
        img = Image.fromarray((arr*255).astype(np.uint8))

    # optional stain (ellipse semi-transparent)
    if random.random() < add_stain_prob:
        stain = Image.new("RGBA", (W,H), (0,0,0,0))
        draw = ImageDraw.Draw(stain)
        rx = random.randint(int(W*0.1), int(W*0.4))
        ry = random.randint(int(H*0.02), int(H*0.12))
        x0 = random.randint(int(W*0.05), int(W*0.6))
        y0 = random.randint(int(H*0.15), int(H*0.7))
        color = (180, 150, 100, random.randint(20,60))
        draw.ellipse((x0,y0,x0+rx,y0+ry), fill=color)
        img = Image.alpha_composite(img.convert("RGBA"), stain).convert("RGB")

    # JPEG compression simulation by saving and reloading
    q = random.randint(*jpeg_quality_range)
    tmp = path_out + ".tmp.jpg"
    img.save(tmp, quality=q)
    img = Image.open(tmp).convert("RGB")
    os.remove(tmp)

    # final save
    img.save(path_out, quality=90)
    return path_out

def find_random_affine_coeffs(W,H, max_shift=10):
    # simple affine: scale + shear + translate small amount
    dx = random.uniform(-max_shift, max_shift)
    dy = random.uniform(-max_shift, max_shift)
    sx = random.uniform(0.98,1.02)
    sy = random.uniform(0.98,1.02)
    shx = random.uniform(-0.01,0.01)
    shy = random.uniform(-0.01,0.01)
    # Affine matrix coefficients (a,b,c,d,e,f) for PIL transform
    a = sx
    b = shx
    c = dx
    d = shy
    e = sy
    f = dy
    return (a,b,c,d,e,f)

# -------------------------
# Error injection for arithmetic faults
# -------------------------
def inject_arithmetic_error(gt: dict, max_delta_percent=0.15):
    """
    Modify financial_summary to introduce a realistic arithmetic error.
    Possible changes:
      - adjust a line_total randomly (less common)
      - change subtotal by adding/subtracting a small percent
      - or modify grand_total directly
    """
    fs = dict(gt["financial_summary"])
    choice = random.choice(["subtotal", "grand_total", "line"])
    if choice == "line" and len(gt["line_items"])>0 and random.random() < 0.4:
        idx = random.randrange(len(gt["line_items"]))
        orig = gt["line_items"][idx]["line_total"]
        factor = 1.0 + random.uniform(-max_delta_percent, max_delta_percent)
        new_line = round(orig * factor, 2)
        gt["line_items"][idx]["line_total"] = new_line
        # recompute subtotal but we will keep declared subtotal unchanged to create mismatch
        # do not change fs['subtotal']
    elif choice == "subtotal":
        delta = round(fs["subtotal"] * random.uniform(-max_delta_percent, max_delta_percent),2)
        gt["financial_summary"]["subtotal"] = round(fs["subtotal"] + delta,2)
        # keep grand_total unchanged to create mismatch
    else:
        # change grand_total
        delta = round(fs["grand_total"] * random.uniform(-max_delta_percent, max_delta_percent),2)
        gt["financial_summary"]["grand_total"] = round(fs["grand_total"] + delta,2)
    return gt

# -------------------------
# Main generation routine
# -------------------------
def generate_dataset(num_samples=1000, out_dir="data/synth", error_rate=0.1,
                     canvas_size=(1240,1754), noise_level=0.04, seed=1234):
    random.seed(seed)
    np.random.seed(seed)
    Faker.seed(seed)
    os.makedirs(out_dir, exist_ok=True)
    images_dir = os.path.join(out_dir, "images")
    gt_dir = os.path.join(out_dir, "gt")
    ocr_dir = os.path.join(out_dir, "ocr")
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(gt_dir, exist_ok=True)
    os.makedirs(ocr_dir, exist_ok=True)

    train_jsonl = os.path.join(out_dir, "unsloth_train.jsonl")
    train_error_jsonl = os.path.join(out_dir, "unsloth_train_with_errors.jsonl")
    # if existing, overwrite
    if os.path.exists(train_jsonl):
        os.remove(train_jsonl)
    if os.path.exists(train_error_jsonl):
        os.remove(train_error_jsonl)

    print(f"Generating {num_samples} invoices to {out_dir} (error_rate={error_rate})")
    for i in tqdm(range(1, num_samples+1)):
        gt = make_invoice(i)
        image_name = f"invoice_{i:06d}.jpg"
        image_path = os.path.join(images_dir, image_name)
        # render base image
        render_invoice_image(gt, image_path, canvas_size=canvas_size)
        # augment into final image
        augmented_path = os.path.join(images_dir, f"invoice_{i:06d}_aug.jpg")
        augment_image(image_path, augmented_path, noise_level=noise_level)
        # remove base if you like
        try:
            os.remove(image_path)
        except:
            pass
        # generate noisy OCR text
        noisy_text = simulate_ocr_text(gt, noise_level=noise_level)
        # sometimes more severe noise for a subset
        if random.random() < 0.05:
            noisy_text = simulate_ocr_text(gt, noise_level=min(0.12, noise_level*3), shuffle_lines=True)
        # write outputs
        with open(os.path.join(gt_dir, f"invoice_{i:06d}.json"), "w") as f:
            json.dump(gt, f, indent=2)
        with open(os.path.join(ocr_dir, f"invoice_{i:06d}.txt"), "w") as f:
            f.write(noisy_text)
        # write lines to training JSONL for unsloth: prompt is OCR text, completion is ground truth JSON (string)
        prompt = noisy_text + "\n\nExtract structured JSON."
        completion = json.dumps({
            "document_type": "invoice",
            "vendor": gt["vendor"],
            "client": gt["client"],
            "line_items": gt["line_items"],
            "financial_summary": gt["financial_summary"]
        })
        train_entry = {"prompt": prompt, "completion": completion}
        with open(train_jsonl, "a") as f:
            f.write(json.dumps(train_entry) + "\n")
        # make error version
        gt_error = json.loads(json.dumps(gt))  # deep copy
        if random.random() < error_rate:
            gt_error = inject_arithmetic_error(gt_error)
        entry_err = {"prompt": prompt, "completion": json.dumps({
            "document_type": "invoice",
            "vendor": gt_error["vendor"],
            "client": gt_error["client"],
            "line_items": gt_error["line_items"],
            "financial_summary": gt_error["financial_summary"]
        })}
        with open(train_error_jsonl, "a") as f:
            f.write(json.dumps(entry_err) + "\n")

    print("Done. Outputs:")
    print(" - images:", images_dir)
    print(" - ground truth JSONs:", gt_dir)
    print(" - OCR text:", ocr_dir)
    print(" - training jsonl:", train_jsonl)
    print(" - training (with errors) jsonl:", train_error_jsonl)

# -------------------------
# CLI
# -------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic invoices + OCR noise + error-injected dataset")
    parser.add_argument("--num", type=int, default=1000, help="Number of invoices to generate")
    parser.add_argument("--out", type=str, default="data/synth", help="Output directory")
    parser.add_argument("--error_rate", type=float, default=0.1, help="Fraction of samples with deliberate arithmetic errors")
    parser.add_argument("--seed", type=int, default=1234, help="Random seed")
    parser.add_argument("--width", type=int, default=1240, help="Canvas width in pixels")
    parser.add_argument("--height", type=int, default=1754, help="Canvas height in pixels")
    parser.add_argument("--noise", type=float, default=0.04, help="Base OCR noise level (char substitution prob)")
    args = parser.parse_args()

    generate_dataset(num_samples=args.num, out_dir=args.out, error_rate=args.error_rate,
                     canvas_size=(args.width, args.height), noise_level=args.noise, seed=args.seed)



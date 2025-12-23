"""
Streamlit demo for FinScribe Smart Scan
Features:
 - Upload invoice image / select demo sample
 - Call backend /process_invoice
 - Show OCR raw text and structured JSON
 - Display overlay with bounding boxes (PIL draw)
 - Inline edit for extracted fields
 - Accept & Send to Training (POST /active_learning)
 - ROI calculator
"""
import streamlit as st
import requests
import json
from io import BytesIO
from PIL import Image
from pathlib import Path
from frontend.utils import draw_bboxes_on_image, json_to_csv, normalize_structured, editable_from_structured
from frontend.components import show_roi_calculator, show_demo_controls, show_progress_status

# Configuration
BACKEND_URL = st.secrets.get("BACKEND_URL", "http://backend:8000")  # docker compose service name
# For local dev, allow override via env or sidebar
if "BACKEND_URL" not in st.secrets:
    BACKEND_URL = st.sidebar.text_input("Backend URL", value="http://localhost:8000", key="backend_url_override")

PROCESS_ENDPOINT = f"{BACKEND_URL}/process_invoice"
ACTIVE_LEARNING_ENDPOINT = f"{BACKEND_URL}/active_learning"

st.set_page_config(
    page_title="FinScribe Demo",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("FinScribe AI — Demo")
st.markdown("Upload an invoice or choose a demo sample. Edit fields, validate, and send corrections to training.")

# Sidebar: Demo mode and sample selector
with st.sidebar:
    demo_mode, sample_choice = show_demo_controls()
    st.markdown("---")
    show_roi_calculator()

# Main area: two columns
col_left, col_right = st.columns([1, 1])

# Upload / sample
uploaded_file = None
if sample_choice != "Upload your own":
    sample_path = Path("examples") / sample_choice
    if sample_path.exists():
        uploaded_file = sample_path.open("rb").read()
    else:
        st.sidebar.warning("Sample not found, upload your own file.")
else:
    uf = st.file_uploader("Upload invoice (jpg/png/pdf)", type=['jpg', 'jpeg', 'png', 'pdf'])
    if uf:
        uploaded_file = uf.read()

if not uploaded_file:
    st.info("Upload a file or select a demo sample to begin.")
    st.stop()

# Send to backend
show_progress_status("processing", "Sending to OCR backend...")
try:
    files = {"file": ("invoice.jpg", uploaded_file)}
    headers = {}
    if demo_mode:
        # propagate demo mode to backend via header (backend should inspect env)
        headers["X-DEMO-MODE"] = "1"
    
    with st.spinner("Processing invoice..."):
        resp = requests.post(PROCESS_ENDPOINT, files=files, headers=headers, timeout=60)
        resp.raise_for_status()
        o = resp.json()
    
    show_progress_status("done", "Processing complete!")
except requests.exceptions.RequestException as e:
    show_progress_status("error", f"Backend request failed: {e}")
    st.error(f"Processing failed: {e}")
    if hasattr(e, 'response') and e.response is not None:
        try:
            st.json(e.response.json())
        except:
            st.text(e.response.text)
    st.stop()
except Exception as e:
    show_progress_status("error", f"Unexpected error: {e}")
    st.error(f"Processing failed: {e}")
    st.stop()

# Extract content
structured = o.get("structured_invoice", {})
ocr_raw = o.get("ocr_raw", o.get("raw_text", ""))
ocr_words = o.get("ocr_words", o.get("words", []))  # fallback

# Normalize structured for UI
editable = editable_from_structured(structured)

# Image display with overlay
try:
    image = Image.open(BytesIO(uploaded_file)).convert("RGB")
    overlay_img = draw_bboxes_on_image(image.copy(), ocr_words)  # returns PIL.Image
except Exception as e:
    st.error(f"Failed to load image: {e}")
    st.stop()

col_left.header("Document + Overlay")
col_left.image(overlay_img, use_column_width=True)
if st.checkbox("Toggle raw image", key="rawimg"):
    col_left.image(image, caption="Original Image", use_column_width=True)

# OCR raw text (collapsible)
with col_left.expander("OCR Raw Text", expanded=False):
    st.code(ocr_raw[:10000] if ocr_raw else "No OCR text available")

# Structured JSON + inline editing
col_right.header("Structured Output (editable)")

# Show a simple JSON editor for debugging (monospace)
st_json = json.dumps(editable, indent=2, ensure_ascii=False)
edited_json = st.text_area(
    "Edit JSON directly (or use the UI below):",
    st_json,
    height=240,
    key="json_editor"
)

# Provide simple form-driven inline edits (vendor fields + line items)
vendor_name = st.text_input(
    "Vendor Name",
    value=editable.get("vendor", {}).get("name", ""),
    key="vendor_name"
)
invoice_date = st.text_input(
    "Invoice Date",
    value=editable.get("invoice_date", ""),
    key="invoice_date"
)

# Line items editor (allow add/remove)
st.write("Line items:")
line_items = editable.get("line_items", []) or []
new_line_items = []

for i, li in enumerate(line_items):
    with st.container():
        cols = st.columns([3, 1, 1, 1, 1])
        desc = cols[0].text_input(
            f"Item {i+1} description",
            value=li.get("description", ""),
            key=f"desc_{i}"
        )
        qty = cols[1].number_input(
            f"qty_{i}",
            min_value=1,
            value=int(li.get("quantity", 1)),
            key=f"qty_{i}"
        )
        unit = cols[2].text_input(
            f"unit_{i}",
            value=str(li.get("unit_price", "")),
            key=f"unit_{i}"
        )
        line_total = cols[3].text_input(
            f"line_total_{i}",
            value=str(li.get("line_total", "")),
            key=f"lt_{i}"
        )
        remove = cols[4].checkbox("Remove", key=f"remove_{i}")
        if not remove:
            new_line_items.append({
                "description": desc,
                "quantity": qty,
                "unit_price": unit,
                "line_total": line_total
            })

if st.button("Add line item", key="add_item"):
    new_line_items.append({
        "description": "New item",
        "quantity": 1,
        "unit_price": "0.00",
        "line_total": "0.00"
    })
    st.rerun()

# Update editable structure
editable["vendor"] = {"name": vendor_name}
editable["invoice_date"] = invoice_date
editable["line_items"] = new_line_items

# Show updated JSON preview and export actions
col_right.subheader("Preview / Export")
st.code(json.dumps(editable, indent=2, ensure_ascii=False))

# Download buttons
col_dl1, col_dl2 = st.columns(2)
with col_dl1:
    st.download_button(
        "Download JSON",
        data=json.dumps(editable, indent=2, ensure_ascii=False),
        file_name="invoice.json",
        mime="application/json",
        key="dl_json"
    )
with col_dl2:
    csv_bytes = json_to_csv(editable).encode("utf-8")
    st.download_button(
        "Download CSV",
        data=csv_bytes,
        file_name="invoice.csv",
        mime="text/csv",
        key="dl_csv"
    )

# Accept & send to training
st.markdown("---")
if st.button("Accept & Send to Training", key="accept_send", type="primary", use_container_width=True):
    try:
        with st.spinner("Sending to training queue..."):
            r = requests.post(ACTIVE_LEARNING_ENDPOINT, json=editable, timeout=15)
            r.raise_for_status()
        st.success("✅ Saved to active learning queue!")
        if r.json():
            result = r.json()
            st.info(f"Entry count: {result.get('entry_count', 'N/A')}")
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to save to training queue: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                st.json(e.response.json())
            except:
                st.text(e.response.text)
    except Exception as e:
        st.error(f"Unexpected error: {e}")

# Footer
st.markdown("---")
st.caption("FinScribe Smart Scan - Powered by PaddleOCR, ERNIE, and FastAPI")

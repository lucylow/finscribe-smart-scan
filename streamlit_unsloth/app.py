"""
FinScribe + Unsloth Active Learning UI

Streamlit application for testing OCR → Unsloth pipeline and collecting
human corrections for active learning.
"""
import streamlit as st
import requests
import json
import os
from datetime import datetime
from pathlib import Path

# Configuration (can be set via secrets.toml or environment)
OCR_URL = os.getenv("OCR_URL", st.secrets.get("OCR_URL", "http://localhost:8002/v1/ocr") if hasattr(st, 'secrets') else "http://localhost:8002/v1/ocr")
UNSLOTH_URL = os.getenv("UNSLOTH_URL", st.secrets.get("UNSLOTH_URL", "http://localhost:8001/v1/infer") if hasattr(st, 'secrets') else "http://localhost:8001/v1/infer")
ACTIVE_FILE = os.getenv("ACTIVE_LEARNING_FILE", "data/active_learning.jsonl")

# Create data directory if it doesn't exist
os.makedirs("data", exist_ok=True)

st.set_page_config(
    page_title="FinScribe: OCR → Unsloth UI",
    page_icon="📄",
    layout="wide"
)

st.title("📄 FinScribe — OCR → Unsloth Reasoning Demo")
st.markdown(
    """
    **Pipeline:** Upload document → Run OCR → Send to Unsloth for JSON extraction → Edit/Correct → Export for active learning
    """
)

# Initialize session state
if "ocr_text" not in st.session_state:
    st.session_state["ocr_text"] = ""
if "parsed_json" not in st.session_state:
    st.session_state["parsed_json"] = None
if "doc_id" not in st.session_state:
    st.session_state["doc_id"] = None

# Main layout: two columns
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1️⃣ Upload & OCR")
    
    uploaded = st.file_uploader(
        "Upload invoice image (PDF/JPG/PNG)",
        type=["png", "jpg", "jpeg", "pdf"],
        help="Upload a document image to process"
    )
    
    if uploaded:
        # Display image preview
        if uploaded.type.startswith("image/"):
            st.image(uploaded, caption="Uploaded document", use_column_width=True)
        else:
            st.info(f"📄 PDF file: {uploaded.name}")
        
        # OCR button
        if st.button("🔍 Run OCR", type="primary", use_container_width=True):
            with st.spinner("Running OCR..."):
                try:
                    # Reset uploaded file pointer
                    uploaded.seek(0)
                    files = {"file": (uploaded.name, uploaded.read(), uploaded.type)}
                    resp = requests.post(OCR_URL, files=files, timeout=60)
                    
                    if resp.status_code == 200:
                        result = resp.json()
                        ocr_text = result.get("text", "")
                        st.session_state["ocr_text"] = ocr_text
                        st.session_state["doc_id"] = f"doc-{datetime.utcnow().isoformat()}"
                        st.success("✅ OCR complete!")
                    else:
                        st.error(f"❌ OCR failed: {resp.status_code} - {resp.text}")
                except requests.exceptions.RequestException as e:
                    st.error(f"❌ OCR service error: {str(e)}")
                    st.info(f"💡 Make sure OCR service is running at {OCR_URL}")
    
    # OCR output display/editor
    st.subheader("2️⃣ OCR Output")
    ocr_text = st.text_area(
        "OCR-extracted text (editable)",
        value=st.session_state.get("ocr_text", ""),
        height=300,
        help="You can edit the OCR text before sending to Unsloth"
    )
    
    # Update session state
    if ocr_text != st.session_state.get("ocr_text"):
        st.session_state["ocr_text"] = ocr_text

with col2:
    st.subheader("3️⃣ Unsloth Inference")
    
    if st.button("🤖 Send to Unsloth", type="primary", use_container_width=True, disabled=not st.session_state.get("ocr_text")):
        if not st.session_state.get("ocr_text"):
            st.warning("⚠️ Please run OCR first")
        else:
            with st.spinner("Running Unsloth inference..."):
                try:
                    payload = {
                        "doc_id": st.session_state.get("doc_id"),
                        "ocr_text": st.session_state["ocr_text"]
                    }
                    resp = requests.post(UNSLOTH_URL, json=payload, timeout=120)
                    
                    if resp.status_code == 200:
                        result = resp.json()
                        parsed = result.get("parsed", {})
                        model_available = result.get("model_available", False)
                        
                        st.session_state["parsed_json"] = parsed
                        
                        if model_available:
                            st.success("✅ Unsloth returned output")
                        else:
                            st.warning("⚠️ Model not loaded - returned mock result")
                    else:
                        st.error(f"❌ Unsloth error: {resp.status_code} - {resp.text}")
                except requests.exceptions.RequestException as e:
                    st.error(f"❌ Unsloth service error: {str(e)}")
                    st.info(f"💡 Make sure Unsloth API is running at {UNSLOTH_URL}")
    
    # Display parsed JSON
    if st.session_state.get("parsed_json"):
        st.subheader("4️⃣ Parsed JSON (Editable)")
        parsed_str = json.dumps(st.session_state["parsed_json"], indent=2)
        edited_json = st.text_area(
            "Edit parsed JSON before saving",
            value=parsed_str,
            height=400,
            help="Correct any errors in the parsed JSON"
        )
        
        # Action buttons
        col_save, col_export = st.columns(2)
        
        with col_save:
            if st.button("💾 Save Correction", use_container_width=True):
                try:
                    # Validate JSON
                    corrected_obj = json.loads(edited_json)
                    
                    # Create training pair
                    training_pair = {
                        "prompt": st.session_state.get("ocr_text", ""),
                        "completion": corrected_obj
                    }
                    
                    # Append to active learning file
                    with open(ACTIVE_FILE, "a") as f:
                        f.write(json.dumps(training_pair) + "\n")
                    
                    st.success(f"✅ Saved to {ACTIVE_FILE}")
                    
                    # Show file stats
                    if os.path.exists(ACTIVE_FILE):
                        with open(ACTIVE_FILE, "r") as f:
                            lines = [l for l in f if l.strip()]
                        st.info(f"📊 Total corrections: {len(lines)}")
                        
                except json.JSONDecodeError as e:
                    st.error(f"❌ Invalid JSON: {str(e)}")
                except Exception as e:
                    st.error(f"❌ Failed to save: {str(e)}")
        
        with col_export:
            if os.path.exists(ACTIVE_FILE):
                with open(ACTIVE_FILE, "rb") as f:
                    st.download_button(
                        "📥 Download Dataset",
                        data=f.read(),
                        file_name="active_learning.jsonl",
                        mime="application/jsonl",
                        use_container_width=True
                    )
            else:
                st.info("No corrections saved yet")

# Sidebar with info and stats
with st.sidebar:
    st.header("ℹ️ Info")
    
    st.subheader("Services")
    st.write(f"**OCR:** `{OCR_URL}`")
    st.write(f"**Unsloth:** `{UNSLOTH_URL}`")
    
    # Test connections
    if st.button("🔌 Test Connections"):
        col_status1, col_status2 = st.columns(2)
        
        with col_status1:
            try:
                resp = requests.get(f"{OCR_URL.replace('/v1/ocr', '')}/health", timeout=5)
                if resp.status_code == 200:
                    st.success("✅ OCR")
                else:
                    st.error("❌ OCR")
            except:
                st.error("❌ OCR")
        
        with col_status2:
            try:
                resp = requests.get(f"{UNSLOTH_URL.replace('/v1/infer', '')}/health", timeout=5)
                if resp.status_code == 200:
                    st.success("✅ Unsloth")
                else:
                    st.error("❌ Unsloth")
            except:
                st.error("❌ Unsloth")
    
    st.divider()
    
    st.subheader("Active Learning Stats")
    if os.path.exists(ACTIVE_FILE):
        with open(ACTIVE_FILE, "r") as f:
            lines = [l for l in f if l.strip()]
        st.metric("Corrections", len(lines))
    else:
        st.info("No corrections yet")
    
    st.divider()
    
    st.subheader("📚 Usage")
    st.markdown("""
    1. Upload a document image
    2. Run OCR to extract text
    3. Send OCR text to Unsloth for JSON extraction
    4. Review and correct the parsed JSON
    5. Save corrections for training
    6. Export dataset for fine-tuning
    """)
    
    st.divider()
    
    st.markdown("""
    **Next Steps:**
    - Use saved corrections to retrain Unsloth
    - Run `./scripts/train_unsloth.sh` after collecting data
    """)

# Footer
st.divider()
st.caption("💡 Tip: Start by testing with the demo datasets in `data/` folder")



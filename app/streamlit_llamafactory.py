# app/streamlit_llamafactory.py
import streamlit as st
import requests, json, os
from datetime import datetime

# === CONFIG ===
OCR_URL = st.secrets.get("OCR_URL", "http://localhost:8002/v1/ocr")      # PaddleOCR service
LLAMA_API_URL = st.secrets.get("LLAMA_API_URL", "http://localhost:8000/v1/chat/completions")  # LLaMA-Factory API
ACTIVE_LEARN_FILE = st.secrets.get("ACTIVE_LEARN_FILE", "data/active_learning_queue.jsonl")

HEADERS = {"Content-Type": "application/json"}
# If your LLaMA-Factory API requires auth (e.g., 'Authorization: Bearer <token>'):
if st.secrets.get("LLAMA_API_KEY"):
    HEADERS["Authorization"] = f"Bearer {st.secrets['LLAMA_API_KEY']}"

os.makedirs(os.path.dirname(ACTIVE_LEARN_FILE) or ".", exist_ok=True)

st.set_page_config(page_title="FinScribe — LLaMA-Factory UI", layout="wide")
st.title("FinScribe — OCR → LLaMA-Factory (Validation & Correction)")

col1, col2 = st.columns([1,1])

with col1:
    st.header("1) Upload document & OCR")
    uploaded = st.file_uploader("Upload invoice image (PNG/JPG/PDF)", type=["png","jpg","jpeg","pdf"])
    if uploaded:
        st.image(uploaded, use_column_width=True)
        if st.button("Run OCR"):
            # send file to OCR microservice
            files = {"file": (uploaded.name, uploaded.getvalue())}
            with st.spinner("Calling OCR service..."):
                try:
                    resp = requests.post(OCR_URL, files=files, timeout=60)
                    resp.raise_for_status()
                    ocr_text = resp.json().get("text", "").strip()
                    # store in session
                    st.session_state["ocr_text"] = ocr_text
                    st.success("OCR completed")
                except Exception as e:
                    st.error(f"OCR failed: {e}")

    st.markdown("**OCR Output (editable)**")
    ocr_text = st.text_area("OCR text", value=st.session_state.get("ocr_text", ""), height=300)
    if st.button("Save OCR text"):
        st.session_state["ocr_text"] = ocr_text
        st.success("Saved")

with col2:
    st.header("2) LLaMA-Factory Validation / Correction")
    st.write("Send OCR result (or edited OCR) to the LLaMA-Factory API and receive corrected JSON. The app expects the LLaMA-Factory API to return JSON-only in the first choice's message content.")

    if st.button("Send to LLaMA-Factory"):
        if not st.session_state.get("ocr_text"):
            st.error("No OCR text available. Run OCR first.")
        else:
            payload = {
                "model": st.secrets.get("LLAMA_MODEL", "finscribe-llama"),
                # prompt using chat messages or simple prompt depending on your configured API
                "messages": [
                    {"role": "system", "content": "You are an invoice JSON validator. Return only JSON, no prose."},
                    {"role": "user", "content": f"Validate and correct the invoice. Input text:\n{st.session_state['ocr_text']}\n\nReturn a single JSON object with keys: document_type, vendor, client, line_items, financial_summary, validation"}
                ],
                "temperature": 0.0,
                "max_tokens": 800
            }
            with st.spinner("Calling LLaMA-Factory..."):
                try:
                    r = requests.post(LLAMA_API_URL, json=payload, headers=HEADERS, timeout=60)
                    r.raise_for_status()
                    data = r.json()
                    # adapt depending on /v1/chat/completions or /v1/completions
                    content = None
                    # try chat style
                    if "choices" in data and len(data["choices"])>0:
                        ch = data["choices"][0]
                        if isinstance(ch.get("message"), dict):
                            content = ch["message"]["content"]
                        else:
                            content = ch.get("text") or ch.get("message")
                    else:
                        content = data.get("output") or str(data)
                    if not content:
                        st.error("No content returned from LLaMA-Factory.")
                    else:
                        # try to extract JSON
                        import re
                        m = re.search(r"\{[\s\S]*\}", content)
                        if not m:
                            st.warning("No JSON found in response; raw model output is shown.")
                            corrected_json = {"_raw": content}
                        else:
                            corrected_json = json.loads(m.group(0))
                        st.session_state["corrected_json"] = corrected_json
                        st.success("LLaMA-Factory returned a result")
                except Exception as e:
                    st.error(f"LLaMA-Factory call failed: {e}")

    if "corrected_json" in st.session_state:
        st.subheader("Corrected JSON (editable)")
        formatted = json.dumps(st.session_state["corrected_json"], indent=2)
        edited = st.text_area("Edit corrected JSON before saving", value=formatted, height=300)
        cols = st.columns(3)
        if cols[0].button("Save accepted correction"):
            try:
                parsed = json.loads(edited)
                # append to active learning queue
                entry = {
                    "prompt": st.session_state.get("ocr_text", ""),
                    "completion": parsed,
                    "meta": {"saved_at": datetime.utcnow().isoformat()}
                }
                with open(ACTIVE_LEARN_FILE, "a") as f:
                    f.write(json.dumps(entry) + "\n")
                st.success(f"Saved to active learning queue: {ACTIVE_LEARN_FILE}")
            except Exception as e:
                st.error(f"Invalid JSON: {e}")
        if cols[1].button("Download corrected JSON"):
            st.download_button("Download", data=edited, file_name=f"corrected_{datetime.utcnow().isoformat()}.json", mime="application/json")
        if cols[2].button("Discard"):
            st.session_state.pop("corrected_json", None)
            st.success("Discarded current correction")

st.markdown("---")
st.markdown("**Active learning queue**:")
if os.path.exists(ACTIVE_LEARN_FILE):
    with open(ACTIVE_LEARN_FILE, "r") as f:
        lines = f.readlines()[-20:]
    st.code("".join(lines), language="json")
else:
    st.info("No accepted corrections yet.")


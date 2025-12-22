"""
FinScribe Smart Scan - Streamlit Frontend

A hackathon-grade frontend that demonstrates:
- Real OCR + AI reasoning
- Multi-agent verification (CAMEL)
- Structured invoice understanding (Unsloth/LLaMA)
- Active learning from corrections
"""
import streamlit as st
import requests
import json
from typing import Dict, Any, Optional

# Configuration
API_BASE = "http://localhost:8000"
PROCESS_ENDPOINT = f"{API_BASE}/api/v1/process_invoice"
ACTIVE_LEARNING_ENDPOINT = f"{API_BASE}/api/v1/active_learning"

# Page config
st.set_page_config(
    page_title="FinScribe Smart Scan",
    page_icon="📄",
    layout="wide"
)

# Title
st.title("📄 FinScribe Smart Scan")
st.markdown("**AI-Powered Invoice Processing with Multi-Agent Verification**")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    api_base = st.text_input("API Base URL", value=API_BASE)
    process_endpoint = f"{api_base}/api/v1/process_invoice"
    active_learning_endpoint = f"{api_base}/api/v1/active_learning"
    
    st.markdown("---")
    st.markdown("### 📊 Pipeline")
    st.markdown("""
    1. **OCR** → PaddleOCR-VL
    2. **Extraction** → Unsloth Fine-Tuned LLaMA
    3. **Validation** → CAMEL Multi-Agent System
    4. **Active Learning** → Corrections feed training
    """)

# Main content
uploaded_file = st.file_uploader(
    "Upload Invoice",
    type=["png", "jpg", "jpeg", "pdf"],
    help="Upload an invoice image or PDF to process"
)

if uploaded_file:
    # Process invoice
    with st.spinner("🔄 Running OCR + AI agents…"):
        try:
            files = {"file": (uploaded_file.name, uploaded_file.read(), uploaded_file.type)}
            response = requests.post(process_endpoint, files=files, timeout=120)
            response.raise_for_status()
            result = response.json()
            
            # Store in session state
            st.session_state["result"] = result
            st.session_state["invoice"] = result.get("structured_invoice", {})
            
        except requests.exceptions.RequestException as e:
            st.error(f"❌ API Error: {str(e)}")
            st.stop()
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            st.stop()
    
    # Display results in two columns
    col1, col2 = st.columns(2)
    
    # ========================================================================
    # LEFT COLUMN: OCR Preview + CAMEL Analysis
    # ========================================================================
    with col1:
        st.subheader("🔍 OCR Preview")
        ocr_preview = result.get("ocr_preview", "")
        if ocr_preview:
            st.code(ocr_preview[:3000], language="text")
            if len(ocr_preview) > 3000:
                st.caption(f"Showing first 3000 chars of {len(ocr_preview)} total")
        else:
            st.info("No OCR text available")
        
        st.markdown("---")
        
        # CAMEL Agent Verdict
        st.subheader("🤖 CAMEL Agent Verdict")
        camel_analysis = result.get("camel_analysis", {})
        confidence = camel_analysis.get("confidence", 0.0)
        
        # Confidence metric
        st.metric("Confidence", f"{confidence*100:.1f}%")
        
        # Notes
        notes = camel_analysis.get("notes", "No notes available")
        st.write("**Analysis:**")
        st.info(notes)
        
        # Issues
        issues = camel_analysis.get("issues", [])
        if issues:
            st.warning("⚠️ Issues detected")
            for issue in issues:
                st.write(f"- {issue}")
        else:
            st.success("✅ No issues detected")
        
        # Latency metrics
        st.markdown("---")
        st.subheader("⏱️ Performance")
        latency = result.get("latency_ms", {})
        col_l1, col_l2, col_l3 = st.columns(3)
        with col_l1:
            st.metric("OCR", f"{latency.get('ocr', 0)}ms")
        with col_l2:
            st.metric("LLM", f"{latency.get('llm', 0)}ms")
        with col_l3:
            st.metric("Agents", f"{latency.get('agents', 0)}ms")
    
    # ========================================================================
    # RIGHT COLUMN: Editable Structured Invoice
    # ========================================================================
    with col2:
        st.subheader("🧾 Structured Invoice")
        
        invoice = st.session_state.get("invoice", {})
        
        # Vendor section
        st.markdown("### Vendor")
        vendor = invoice.get("vendor", {})
        vendor_name = st.text_input(
            "Vendor Name",
            value=vendor.get("name", ""),
            key="vendor_name"
        )
        vendor_address = st.text_area(
            "Address",
            value=vendor.get("address", ""),
            key="vendor_address",
            height=60
        )
        
        # Invoice metadata
        st.markdown("### Invoice Details")
        col_i1, col_i2 = st.columns(2)
        with col_i1:
            invoice_number = st.text_input(
                "Invoice Number",
                value=invoice.get("invoice_number", ""),
                key="invoice_number"
            )
        with col_i2:
            invoice_date = st.text_input(
                "Invoice Date",
                value=invoice.get("invoice_date", ""),
                key="invoice_date"
            )
        
        # Line items
        st.markdown("### Line Items")
        line_items = invoice.get("line_items", [])
        
        if not line_items:
            st.info("No line items found")
        else:
            for i, item in enumerate(line_items):
                with st.expander(f"Line Item {i+1}", expanded=(i < 3)):
                    item["description"] = st.text_input(
                        "Description",
                        value=item.get("description", item.get("desc", "")),
                        key=f"desc_{i}"
                    )
                    
                    col_q1, col_q2, col_q3 = st.columns(3)
                    with col_q1:
                        item["quantity"] = st.number_input(
                            "Quantity",
                            value=float(item.get("quantity", 1.0)),
                            key=f"qty_{i}",
                            min_value=0.0,
                            step=0.1
                        )
                    with col_q2:
                        unit_price = item.get("unit_price", {})
                        if isinstance(unit_price, dict):
                            unit_price_val = unit_price.get("value", 0.0)
                        else:
                            unit_price_val = float(unit_price) if unit_price else 0.0
                        
                        item["unit_price"] = {
                            "value": st.number_input(
                                "Unit Price",
                                value=unit_price_val,
                                key=f"price_{i}",
                                min_value=0.0,
                                step=0.01,
                                format="%.2f"
                            ),
                            "currency": unit_price.get("currency", "USD") if isinstance(unit_price, dict) else "USD"
                        }
                    with col_q3:
                        line_total = item.get("line_total", 0.0)
                        st.metric(
                            "Line Total",
                            f"${line_total:.2f}" if isinstance(line_total, (int, float)) else line_total
                        )
        
        # Financial summary
        st.markdown("### Financial Summary")
        financial = invoice.get("financial_summary", {})
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            subtotal = st.number_input(
                "Subtotal",
                value=float(financial.get("subtotal", 0.0)),
                key="subtotal",
                min_value=0.0,
                step=0.01,
                format="%.2f"
            )
            tax_rate = st.number_input(
                "Tax Rate (%)",
                value=float(financial.get("tax_rate", 0.0)),
                key="tax_rate",
                min_value=0.0,
                step=0.1,
                format="%.2f"
            )
        with col_f2:
            tax_amount = st.number_input(
                "Tax Amount",
                value=float(financial.get("tax_amount", 0.0)),
                key="tax_amount",
                min_value=0.0,
                step=0.01,
                format="%.2f"
            )
            grand_total = st.number_input(
                "Grand Total",
                value=float(financial.get("grand_total", 0.0)),
                key="grand_total",
                min_value=0.0,
                step=0.01,
                format="%.2f"
            )
        
        # Update invoice in session state
        invoice["vendor"]["name"] = vendor_name
        invoice["vendor"]["address"] = vendor_address
        invoice["invoice_number"] = invoice_number
        invoice["invoice_date"] = invoice_date
        invoice["financial_summary"]["subtotal"] = subtotal
        invoice["financial_summary"]["tax_rate"] = tax_rate
        invoice["financial_summary"]["tax_amount"] = tax_amount
        invoice["financial_summary"]["grand_total"] = grand_total
        
        # Accept & Send to Training button
        st.markdown("---")
        if st.button("✅ Accept & Send to Training", type="primary", use_container_width=True):
            try:
                # Prepare active learning request
                al_request = {
                    "invoice": invoice,
                    "corrections": {
                        "vendor_name": vendor_name != vendor.get("name", ""),
                        "invoice_number": invoice_number != invoice.get("invoice_number", ""),
                        "line_items_edited": len(line_items) > 0
                    },
                    "metadata": {
                        "ocr_text": ocr_preview,
                        "invoice_id": result.get("invoice_id", ""),
                        "confidence": confidence
                    }
                }
                
                response = requests.post(active_learning_endpoint, json=al_request, timeout=30)
                response.raise_for_status()
                al_result = response.json()
                
                st.success(f"✅ Saved to training queue! ({al_result.get('entry_count', 0)} total entries)")
                
            except requests.exceptions.RequestException as e:
                st.error(f"❌ Failed to save: {str(e)}")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
        
        # Download JSON button
        if st.button("📥 Download JSON", use_container_width=True):
            json_str = json.dumps(invoice, indent=2)
            st.download_button(
                label="Download Invoice JSON",
                data=json_str,
                file_name=f"invoice_{result.get('invoice_id', 'unknown')}.json",
                mime="application/json"
            )

# Footer
st.markdown("---")
st.caption("FinScribe Smart Scan - Powered by Unsloth, CAMEL-AI, and LLaMA")


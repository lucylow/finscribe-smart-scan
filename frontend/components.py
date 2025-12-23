"""
Small UI component helpers for Streamlit.
"""
import streamlit as st
from typing import Dict, Any, Optional


def show_roi_calculator():
    """Display ROI calculator widget in sidebar."""
    st.header("ROI Calculator")
    invoices_per_month = st.number_input(
        "Invoices / month",
        min_value=0,
        value=1000,
        key="roi_invoices"
    )
    manual_cost = st.number_input(
        "Manual cost per invoice ($)",
        min_value=0.0,
        value=30.0,
        step=0.5,
        key="roi_manual"
    )
    estimated_processing_cost = st.number_input(
        "Processing cost per invoice ($)",
        min_value=0.0,
        value=0.10,
        step=0.01,
        key="roi_processing"
    )
    
    st.write("Estimated monthly savings:")
    monthly_savings = max(0, (manual_cost - estimated_processing_cost) * invoices_per_month)
    st.metric("Estimated Monthly Savings", f"${monthly_savings:,.2f}")
    
    if manual_cost > 0 and monthly_savings > 0:
        payback_months = (manual_cost * invoices_per_month) / monthly_savings
        st.write(f"Payback time (approx): {payback_months:.2f} months")
    elif monthly_savings == 0:
        st.write("N/A")
    
    return {
        "invoices_per_month": invoices_per_month,
        "manual_cost": manual_cost,
        "processing_cost": estimated_processing_cost,
        "monthly_savings": monthly_savings
    }


def show_demo_controls():
    """
    Show demo mode toggle and sample selector.
    
    Returns:
        (demo_mode: bool, sample_choice: str)
    """
    st.header("Demo Controls")
    demo_mode = st.checkbox(
        "Demo Mode (mock OCR)",
        value=True,
        help="Use mock OCR responses for guaranteed results",
        key="demo_mode"
    )
    
    from pathlib import Path
    sample_files = sorted([p.name for p in Path('examples').glob('sample*.jpg')]) if Path('examples').exists() else []
    if not sample_files:
        # Try PNG files as fallback
        sample_files = sorted([p.name for p in Path('examples').glob('sample*.png')]) if Path('examples').exists() else []
    
    sample_choice = st.selectbox(
        "Pick a sample invoice (demo mode)",
        options=["Upload your own"] + sample_files,
        index=0,
        key="sample_choice"
    )
    
    return demo_mode, sample_choice


def show_progress_status(status: str, message: str = ""):
    """
    Display progress status with appropriate UI element.
    
    Args:
        status: 'uploading', 'processing', 'done', 'error'
        message: Optional message to display
    """
    if status == "uploading":
        st.info(f"📤 Uploading... {message}")
    elif status == "processing":
        st.info(f"🔄 Processing... {message}")
    elif status == "done":
        st.success(f"✅ Done! {message}")
    elif status == "error":
        st.error(f"❌ Error: {message}")

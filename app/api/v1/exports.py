#!/usr/bin/env python3
"""
Export endpoints (JSON, CSV, QuickBooks) and ROI calculation
"""
import csv
import io
import json
import os
import logging
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Any, Dict, List
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(tags=["exports"])

# Configuration
DATA_DIR = os.getenv("DATA_DIR", "data")
ACTIVE_QUEUE = os.path.join(DATA_DIR, "active_learning.jsonl")


class ROICalculationRequest(BaseModel):
    invoices_per_month: int = 1000
    manual_cost_per_invoice: float = 30.0
    autom_cost_per_invoice: float = 0.15
    monthly_fixed_cost: float = 200.0


class ROICalculationResponse(BaseModel):
    invoices_per_month: int
    manual_cost_per_invoice: float
    autom_cost_per_invoice: float
    monthly_fixed_cost: float
    manual_total: float
    autom_total: float
    monthly_savings: float
    savings_pct: float
    annual_savings: float
    payback_months: float = 0.0  # If initial_cost provided


def _read_active_queue() -> List[Dict]:
    """Read active learning queue from JSONL file."""
    if not os.path.exists(ACTIVE_QUEUE):
        return []
    out = []
    try:
        with open(ACTIVE_QUEUE, "r", encoding="utf8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse line in {ACTIVE_QUEUE}")
                    continue
    except Exception as e:
        logger.error(f"Error reading active queue: {e}")
    return out


@router.get("/roi", response_model=ROICalculationResponse)
def calculate_roi(
    invoices_per_month: int = Query(1000, ge=0, description="Number of invoices processed per month"),
    manual_cost_per_invoice: float = Query(30.0, ge=0, description="Manual processing cost per invoice ($)"),
    autom_cost_per_invoice: float = Query(0.15, ge=0, description="Automated processing cost per invoice ($)"),
    monthly_fixed_cost: float = Query(200.0, ge=0, description="Monthly fixed infrastructure cost ($)"),
    initial_cost: float = Query(0.0, ge=0, description="One-time setup/development cost ($)"),
):
    """
    Calculate ROI for FinScribe automation.
    
    Returns:
    - Monthly savings
    - Annual savings
    - Payback time (if initial_cost provided)
    """
    manual = invoices_per_month * float(manual_cost_per_invoice)
    auto = invoices_per_month * float(autom_cost_per_invoice) + float(monthly_fixed_cost)
    saved = manual - auto
    saved_pct = (saved / manual) * 100 if manual > 0 else 0.0
    annual_savings = saved * 12
    
    payback_months = 0.0
    if initial_cost > 0 and saved > 0:
        payback_months = initial_cost / saved
    
    result = ROICalculationResponse(
        invoices_per_month=invoices_per_month,
        manual_cost_per_invoice=manual_cost_per_invoice,
        autom_cost_per_invoice=autom_cost_per_invoice,
        monthly_fixed_cost=monthly_fixed_cost,
        manual_total=round(manual, 2),
        autom_total=round(auto, 2),
        monthly_savings=round(saved, 2),
        savings_pct=round(saved_pct, 2),
        annual_savings=round(annual_savings, 2),
        payback_months=round(payback_months, 2) if payback_months > 0 else 0.0,
    )
    return result


@router.get("/exports/json")
def export_json():
    """
    Export active learning queue as newline-delimited JSON (NDJSON).
    """
    docs = _read_active_queue()
    return JSONResponse(
        content={
            "count": len(docs),
            "docs": docs,
            "format": "ndjson",
            "note": "Each doc in 'docs' array can be written as one JSON line per document"
        }
    )


@router.get("/exports/csv")
def export_csv():
    """
    Convert the active queue to CSV (flat-mapping common fields).
    Extracts: vendor name, invoice_number, issue_date, subtotal, tax_amount, grand_total, currency
    """
    docs = _read_active_queue()
    if not docs:
        raise HTTPException(status_code=404, detail="No queued documents found")
    
    # Define header
    header = [
        "doc_id",
        "vendor_name",
        "invoice_number",
        "issue_date",
        "subtotal",
        "tax_amount",
        "grand_total",
        "currency",
        "status"
    ]
    
    sio = io.StringIO()
    writer = csv.writer(sio)
    writer.writerow(header)
    
    for d in docs:
        # Try to get corrected data first, then extracted, then raw data
        ex = d.get("corrected") or d.get("extracted") or d.get("data") or {}
        
        # Extract vendor info
        vendor = ex.get("vendor", {})
        if isinstance(vendor, dict):
            vendor_name = vendor.get("name", "")
        else:
            vendor_name = str(vendor) if vendor else ""
        
        # Extract invoice number
        inv = ex.get("invoice_number", "")
        
        # Extract dates
        dates = ex.get("dates", {})
        if isinstance(dates, dict):
            issue_date = dates.get("issue_date", dates.get("invoice_date", ""))
        else:
            issue_date = str(dates) if dates else ""
        
        # Extract financial summary
        fs = ex.get("financial_summary", {})
        if not isinstance(fs, dict):
            fs = {}
        
        row = [
            d.get("doc_id", d.get("job_id", "")),
            vendor_name,
            inv,
            issue_date,
            fs.get("subtotal", ""),
            fs.get("tax_amount", fs.get("tax", "")),
            fs.get("grand_total", fs.get("total", "")),
            fs.get("currency", "USD"),
            d.get("status", "completed")
        ]
        writer.writerow(row)
    
    sio.seek(0)
    return StreamingResponse(
        iter([sio.read()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=finscribe_export.csv"}
    )


@router.get("/exports/quickbooks_csv")
def export_quickbooks():
    """
    Export a QuickBooks-compatible CSV.
    Simplified mapping for QuickBooks Online 'Sales Receipt' or 'Invoice' import style.
    """
    docs = _read_active_queue()
    if not docs:
        raise HTTPException(status_code=404, detail="No queued documents found")
    
    # QuickBooks CSV format (simplified)
    header = [
        "Customer",
        "Invoice Number",
        "Invoice Date",
        "Item",
        "Description",
        "Quantity",
        "Rate",
        "Amount",
        "Taxable"
    ]
    
    sio = io.StringIO()
    writer = csv.writer(sio)
    writer.writerow(header)
    
    for d in docs:
        ex = d.get("corrected") or d.get("extracted") or {}
        
        # Extract customer/vendor
        customer = ex.get("client", {})
        if isinstance(customer, dict):
            customer_name = customer.get("name", "Unknown")
        else:
            customer_name = str(customer) if customer else "Unknown"
        
        # Extract invoice metadata
        inv = ex.get("invoice_number", "")
        date = ex.get("dates", {})
        if isinstance(date, dict):
            invoice_date = date.get("issue_date", date.get("invoice_date", ""))
        else:
            invoice_date = str(date) if date else ""
        
        # Extract line items
        line_items = ex.get("line_items", [])
        if not line_items:
            # If no line items, create one from financial summary
            fs = ex.get("financial_summary", {})
            if isinstance(fs, dict):
                grand_total = fs.get("grand_total", fs.get("total", 0))
                line_items = [{
                    "description": "Service",
                    "quantity": 1,
                    "unit_price": grand_total,
                    "line_total": grand_total
                }]
        
        # Write one row per line item
        for it in line_items:
            if isinstance(it, dict):
                desc = it.get("description", it.get("desc", ""))
                qty = it.get("quantity", it.get("qty", 1))
                rate = it.get("unit_price", it.get("unit", it.get("price", 0)))
                amt = it.get("line_total", float(qty) * float(rate))
            else:
                desc = str(it)
                qty = 1
                rate = 0
                amt = 0
            
            writer.writerow([
                customer_name,
                inv,
                invoice_date,
                "ImportedItem",  # QuickBooks item name
                desc,
                qty,
                rate,
                amt,
                "TRUE"  # Taxable
            ])
    
    sio.seek(0)
    return StreamingResponse(
        iter([sio.read()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=finscribe_qb_export.csv"}
    )


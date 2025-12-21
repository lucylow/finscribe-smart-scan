#!/usr/bin/env python3
"""
scripts/compute_metrics.py

Compute evaluation metrics given:
 - gold annotations: data/dataset/test.jsonl
 - predictions: results/<exp>/predictions.jsonl

Outputs summary JSON to results/<exp>/metrics.json and prints a simple table.
"""
import json
import math
import sys
import argparse
from pathlib import Path
from collections import defaultdict
from typing import Dict, Any, List

ROOT = Path(__file__).parent.parent

def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Load JSONL file"""
    results = []
    with open(path, "r", encoding="utf8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                results.append(json.loads(line))
            except Exception as e:
                print(f"Warning: skipping invalid line in {path}: {e}")
    return results

def field_accuracy(gold: List[Dict], pred: List[Dict]) -> Dict[str, float]:
    """
    Compute simple exact-match accuracy for top-level fields:
      vendor.name, invoice_number, financial_summary.grand_total
    Returns: dict of accuracy per field
    """
    total = len(gold)
    if total == 0:
        return {}
    
    counts = defaultdict(int)
    
    for g, p in zip(gold, pred):
        gfields = g.get("fields", {})
        pfields = p.get("pred_fields") or p.get("pred") or {}
        
        # vendor name
        g_vendor_name = str(gfields.get("vendor", {}).get("name", "")).strip()
        p_vendor_name = str(pfields.get("vendor", {}).get("name", "")).strip()
        if g_vendor_name and p_vendor_name and g_vendor_name == p_vendor_name:
            counts["vendor.name"] += 1
        
        # invoice_number
        g_inv = str(gfields.get("invoice_number", "")).strip()
        p_inv = str(pfields.get("invoice_number", "")).strip()
        if g_inv and p_inv and g_inv == p_inv:
            counts["invoice_number"] += 1
        
        # numeric comparison with tolerance for grand_total
        g_total = gfields.get("financial_summary", {}).get("grand_total", None)
        p_total = None
        try:
            p_total_raw = pfields.get("financial_summary", {}).get("grand_total", None)
            if p_total_raw is not None:
                p_total = float(p_total_raw)
        except (ValueError, TypeError):
            p_total = None
        
        if g_total is not None and p_total is not None:
            if abs(float(g_total) - float(p_total)) <= 0.01:
                counts["grand_total_tol"] += 1
    
    return {k: counts[k] / total for k in ["vendor.name", "invoice_number", "grand_total_tol"]}

def numeric_accuracy(gold: List[Dict], pred: List[Dict], tolerance: float = 0.01) -> Dict[str, float]:
    """
    Compute numeric accuracy for all numeric fields in financial_summary and line_items.
    Returns dict with accuracy per field type.
    """
    total = len(gold)
    if total == 0:
        return {}
    
    field_counts = defaultdict(int)
    field_totals = defaultdict(int)
    
    for g, p in zip(gold, pred):
        gfields = g.get("fields", {})
        pfields = p.get("pred_fields") or p.get("pred") or {}
        
        # Financial summary fields
        gfs = gfields.get("financial_summary", {})
        pfs = pfields.get("financial_summary", {})
        
        for field in ["subtotal", "tax_amount", "grand_total"]:
            if field in gfs:
                field_totals[f"financial_summary.{field}"] += 1
                g_val = float(gfs[field])
                try:
                    p_val = float(pfs.get(field, 0))
                    if abs(g_val - p_val) <= tolerance:
                        field_counts[f"financial_summary.{field}"] += 1
                except (ValueError, TypeError):
                    pass
        
        # Line items
        g_items = gfields.get("line_items", [])
        p_items = pfields.get("line_items", [])
        
        # Compare line totals
        for i, g_item in enumerate(g_items):
            field_totals["line_items.line_total"] += 1
            g_total = float(g_item.get("line_total", 0))
            if i < len(p_items):
                try:
                    p_total = float(p_items[i].get("line_total", 0))
                    if abs(g_total - p_total) <= tolerance:
                        field_counts["line_items.line_total"] += 1
                except (ValueError, TypeError):
                    pass
    
    return {
        k: field_counts[k] / max(1, field_totals[k])
        for k in field_totals.keys()
    }

def validation_pass_rate(gold: List[Dict], pred: List[Dict]) -> float:
    """Compute validation pass rate: arithmetic checks (subtotal + tax == grand_total within tolerance)"""
    total = len(gold)
    if total == 0:
        return 0.0
    
    pass_count = 0
    
    for g, p in zip(gold, pred):
        pfs = (p.get("pred_fields") or p.get("pred") or {}).get("financial_summary", {})
        
        try:
            psubtotal = float(pfs.get("subtotal", 0))
            ptax = float(pfs.get("tax_amount", 0))
            pgrand = float(pfs.get("grand_total", 0))
            
            # Check: subtotal + tax_amount == grand_total (within tolerance)
            calculated_total = psubtotal + ptax
            if abs(calculated_total - pgrand) <= 0.01:
                pass_count += 1
        except (ValueError, TypeError):
            # If we can't parse, fail the validation
            pass
    
    return pass_count / total

def teds_like_score(gold: List[Dict], pred: List[Dict]) -> float:
    """
    Very simple TEDS-like heuristic:
    For each table, check header match and number of columns match
    """
    total = len(gold)
    if total == 0:
        return 0.0
    
    score_total = 0.0
    
    for g, p in zip(gold, pred):
        g_tables = g.get("tables", [])
        pfields = p.get("pred_fields") or p.get("pred") or {}
        p_tables = pfields.get("tables", []) if isinstance(pfields, dict) else []
        
        # If no tables in gold and none in pred => 1.0
        if not g_tables and not p_tables:
            score_total += 1.0
            continue
        
        if not g_tables or not p_tables:
            score_total += 0.0
            continue
        
        # Compare first table only for speed
        gt = g_tables[0] if g_tables else {}
        pt = p_tables[0] if p_tables else {}
        
        # Compare number of columns
        if isinstance(gt, dict) and isinstance(pt, dict):
            gc = len(gt.get("columns", []))
            pc = len(pt.get("columns", []))
            if gc > 0:
                score_total += max(0.0, 1 - abs(gc - pc) / max(1, gc))
            else:
                score_total += 1.0 if pc == 0 else 0.0
        else:
            # Fallback: compare line_items as a proxy for table structure
            g_items = g.get("fields", {}).get("line_items", [])
            p_items = pfields.get("line_items", []) if isinstance(pfields, dict) else []
            if len(g_items) > 0:
                score_total += max(0.0, 1 - abs(len(g_items) - len(p_items)) / max(1, len(g_items)))
            else:
                score_total += 1.0 if len(p_items) == 0 else 0.0
    
    return score_total / total

def overall_accuracy(gold: List[Dict], pred: List[Dict]) -> float:
    """Simple overall accuracy: average of field accuracies"""
    field_acc = field_accuracy(gold, pred)
    if not field_acc:
        return 0.0
    return sum(field_acc.values()) / len(field_acc)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute evaluation metrics")
    parser.add_argument("--gold", default="data/dataset/test.jsonl", type=Path, help="Gold annotations JSONL")
    parser.add_argument("--preds", required=True, type=Path, help="Predictions JSONL")
    parser.add_argument("--out", default=None, type=Path, help="Output metrics JSON file")
    args = parser.parse_args()
    
    # Load data
    gold = load_jsonl(ROOT / args.gold)
    preds = load_jsonl(args.preds)
    
    if len(gold) != len(preds):
        print(f"Warning: gold has {len(gold)} samples, preds has {len(preds)} samples")
        # Use minimum length
        min_len = min(len(gold), len(preds))
        gold = gold[:min_len]
        preds = preds[:min_len]
    
    # Compute metrics
    metrics = {
        "overall_accuracy": overall_accuracy(gold, preds),
        "field_accuracy": field_accuracy(gold, preds),
        "numeric_accuracy": numeric_accuracy(gold, preds),
        "validation_pass_rate": validation_pass_rate(gold, preds),
        "teds_like": teds_like_score(gold, preds),
        "num_samples": len(gold)
    }
    
    # Save to file if requested
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with open(args.out, "w", encoding="utf8") as f:
            json.dump(metrics, f, indent=2)
        print(f"Saved metrics to {args.out}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("Metrics Summary")
    print("=" * 60)
    print(f"Overall Accuracy: {metrics['overall_accuracy']:.4f}")
    print(f"\nField Accuracy:")
    for field, acc in metrics["field_accuracy"].items():
        print(f"  {field}: {acc:.4f}")
    print(f"\nNumeric Accuracy (tolerance ±0.01):")
    for field, acc in metrics["numeric_accuracy"].items():
        print(f"  {field}: {acc:.4f}")
    print(f"\nValidation Pass Rate: {metrics['validation_pass_rate']:.4f}")
    print(f"TEDS-like Score: {metrics['teds_like']:.4f}")
    print(f"Number of samples: {metrics['num_samples']}")
    print("=" * 60)


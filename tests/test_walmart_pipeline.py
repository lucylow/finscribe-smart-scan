# tests/test_walmart_pipeline.py
"""
Unit tests for Walmart receipt processing pipeline.
"""
import json
from pathlib import Path
from backend.pipeline.walmart_pipeline import run_walmart_pipeline
from backend.ocr import paddle_client

def test_walmart_pipeline_with_mock(monkeypatch, tmp_path):
    # ensure PADDLE_MODE mock to avoid external deps
    monkeypatch.setenv("PADDLE_MODE", "mock")
    repo_root = Path(__file__).resolve().parents[1]
    img = repo_root / "examples" / "Walmartreceipt.jpeg"
    # if image missing, the mock in paddle_client returns placeholder text so pipeline still runs
    out = run_walmart_pipeline(str(img if img.exists() else repo_root / "examples" / "sample_invoice_1.png"))
    assert "invoice_id" in out
    assert "structured_invoice" in out
    si = out["structured_invoice"]
    assert "vendor" in si
    assert "financial_summary" in si


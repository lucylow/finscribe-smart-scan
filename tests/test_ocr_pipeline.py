# tests/test_ocr_pipeline.py
import os, pytest
from backend.pipeline.ocr_pipeline import run_full_pipeline

def test_pipeline_mock_mode(monkeypatch):
    monkeypatch.setenv("PADDLE_MODE", "mock")
    # the function should run without raising
    res = run_full_pipeline("examples/sample1.jpg", use_ernie=False)
    assert "invoice_id" in res
    assert "structured_invoice" in res
    assert isinstance(res["latency_ms"]["total"], int)


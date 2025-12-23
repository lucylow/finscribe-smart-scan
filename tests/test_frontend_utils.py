"""
Unit tests for frontend utility functions.
"""
import pytest
from frontend.utils import editable_from_structured, json_to_csv, draw_bboxes_on_image, struct_to_csv, pretty_json
from PIL import Image


def test_editable_from_structured_empty():
    """Test with empty structured input."""
    out = editable_from_structured({})
    assert out["vendor"]["name"] == ""
    assert out["invoice_date"] == ""
    assert out["line_items"] == []


def test_editable_from_structured_with_data():
    """Test with actual structured data."""
    struct = {
        "vendor": {"name": "Test Vendor"},
        "invoice_date": "2024-01-15",
        "line_items": [
            {
                "description": "Item 1",
                "quantity": 2,
                "unit_price": "10.00",
                "line_total": "20.00"
            }
        ]
    }
    out = editable_from_structured(struct)
    assert out["vendor"]["name"] == "Test Vendor"
    assert out["invoice_date"] == "2024-01-15"
    assert len(out["line_items"]) == 1
    assert out["line_items"][0]["description"] == "Item 1"
    assert out["line_items"][0]["quantity"] == 2


def test_editable_from_structured_alternative_keys():
    """Test with alternative key names (desc, price, total)."""
    struct = {
        "vendor": {"name": "Vendor"},
        "line_items": [
            {
                "desc": "Alternative desc",
                "price": "5.50",
                "total": "11.00"
            }
        ]
    }
    out = editable_from_structured(struct)
    assert out["line_items"][0]["description"] == "Alternative desc"
    assert out["line_items"][0]["unit_price"] == "5.50"
    assert out["line_items"][0]["line_total"] == "11.00"


def test_json_to_csv_simple():
    """Test CSV export with simple data."""
    st = {
        "line_items": [
            {
                "description": "A",
                "quantity": 2,
                "unit_price": "1.00",
                "line_total": "2.00"
            }
        ]
    }
    csv = json_to_csv(st)
    assert "description" in csv
    assert "A" in csv
    assert "2.00" in csv
    assert "quantity" in csv


def test_json_to_csv_multiple_items():
    """Test CSV export with multiple line items."""
    st = {
        "line_items": [
            {"description": "Item 1", "quantity": 1, "unit_price": "10.00", "line_total": "10.00"},
            {"description": "Item 2", "quantity": 3, "unit_price": "5.00", "line_total": "15.00"}
        ]
    }
    csv = json_to_csv(st)
    lines = csv.strip().split("\n")
    assert len(lines) == 3  # header + 2 items
    assert "Item 1" in csv
    assert "Item 2" in csv


def test_json_to_csv_empty():
    """Test CSV export with no line items."""
    st = {"line_items": []}
    csv = json_to_csv(st)
    assert "description" in csv
    assert csv.count("\n") == 1  # only header


def test_draw_bboxes_no_error():
    """Test bbox drawing doesn't crash with valid input."""
    img = Image.new("RGB", (200, 200), color=(255, 255, 255))
    words = [
        {"text": "foo", "bbox": [10, 10, 80, 30], "conf": 0.9}
    ]
    out = draw_bboxes_on_image(img, words)
    assert out.size == img.size
    assert isinstance(out, Image.Image)


def test_draw_bboxes_empty_words():
    """Test bbox drawing with empty words list."""
    img = Image.new("RGB", (200, 200), color=(255, 255, 255))
    out = draw_bboxes_on_image(img, [])
    assert out.size == img.size


def test_draw_bboxes_invalid_bbox():
    """Test bbox drawing with invalid bbox (missing coordinates)."""
    img = Image.new("RGB", (200, 200), color=(255, 255, 255))
    words = [
        {"text": "foo", "bbox": [10, 10]},  # incomplete bbox
        {"text": "bar"}  # no bbox
    ]
    out = draw_bboxes_on_image(img, words)
    assert out.size == img.size


def test_draw_bboxes_out_of_bounds():
    """Test bbox drawing with coordinates outside image bounds."""
    img = Image.new("RGB", (200, 200), color=(255, 255, 255))
    words = [
        {"text": "foo", "bbox": [-10, -10, 300, 300], "conf": 0.9}
    ]
    out = draw_bboxes_on_image(img, words)
    assert out.size == img.size

def test_struct_to_csv_empty():
    csv = struct_to_csv({})
    assert "description" in csv

def test_pretty_json():
    s = pretty_json({"a":1})
    assert '"a": 1' in s

def test_draw_bboxes():
    img = Image.new("RGB", (200,200), color=(255,255,255))
    out = draw_bboxes_on_image(img, [{"text":"foo","bbox":[10,10,80,30],"conf":0.9}])
    assert out.size == (200,200)


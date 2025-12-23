# tests/test_api_flow.py
import requests, time, os
from pathlib import Path

BASE = os.getenv("TEST_BASE","http://localhost:8000")
def test_submit_and_poll():
    img = Path("examples/Walmartreceipt.jpeg")
    if not img.exists():
        # use placeholder sample file
        img = Path("examples/sample1.jpg")
    with open(img, "rb") as f:
        r = requests.post(f"{BASE}/api/submit", files={"file": ("test.jpg", f)})
    assert r.status_code == 200
    job = r.json()
    job_id = job["job_id"]
    # poll
    for _ in range(30):
        s = requests.get(f"{BASE}/api/status/{job_id}").json()
        if s.get("status") == "done":
            res = requests.get(f"{BASE}/api/result/{job_id}").json()
            assert "structured_invoice" in res
            return
        if s.get("status") == "error":
            assert False, f"job error: {s.get('error')}"
        time.sleep(1)
    assert False, "timeout waiting for job"


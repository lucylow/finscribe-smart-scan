# backend/ocr/paddle_client.py
import os, time, json, logging
from pathlib import Path

LOG = logging.getLogger("paddle_client")
PADDLE_MODE = os.getenv("PADDLE_MODE", "mock").lower()
PADDLE_SERVICE_URL = os.getenv("PADDLE_SERVICE_URL", "")

def _load_mock_for_image(image_path: str):
    p = Path("examples") / (Path(image_path).stem + "_ocr.json")
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            LOG.exception("Failed reading mock OCR JSON")
    # fallback sample
    default = Path("examples/sample_walmart_ocr.json")
    if default.exists():
        return json.loads(default.read_text())
    return {"raw_text":"WALMART\nSubtotal 4.98\nTax 0.30\nTotal 5.28", "words": [], "latency_ms":0, "model":"mock-paddle"}

def run_paddleocr(image_path: str) -> dict:
    start = time.time()
    mode = PADDLE_MODE
    LOG.info("run_paddleocr mode=%s image=%s", mode, image_path)
    if mode == "service" and PADDLE_SERVICE_URL:
        try:
            import requests
            with open(image_path, "rb") as f:
                r = requests.post(PADDLE_SERVICE_URL, files={"file": f}, timeout=30)
                r.raise_for_status()
                j = r.json()
                j["latency_ms"] = int((time.time()-start)*1000)
                j["model"] = j.get("model", "paddle-service")
                return j
        except Exception:
            LOG.exception("Paddle service failed, falling back to mock")
            return _load_mock_for_image(image_path)
    if mode == "local":
        try:
            from paddleocr import PaddleOCR
            ocr = PaddleOCR(use_angle_cls=True, lang="en")
            res = ocr.ocr(image_path, cls=True)
            raw_lines = []
            words = []
            for page in res:
                for line in page:
                    txt = line[1][0]
                    raw_lines.append(txt)
                    bbox = [int(x) for p in line[0] for x in p]
                    conf = float(line[1][1]) if line[1][1] else None
                    words.append({"text": txt, "bbox": bbox, "conf": conf})
            return {"raw_text": "\n".join(raw_lines), "words": words, "latency_ms": int((time.time()-start)*1000), "model":"local-paddle"}
        except Exception:
            LOG.exception("Local paddle failed, falling back to mock")
            return _load_mock_for_image(image_path)
    # default to mock
    return _load_mock_for_image(image_path)

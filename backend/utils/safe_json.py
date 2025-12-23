# backend/utils/safe_json.py
import json, re, logging
LOG = logging.getLogger("safe_json")

def safe_json_parse(s):
    if isinstance(s, dict):
        return s
    try:
        return json.loads(s)
    except Exception:
        try:
            m = re.search(r"(\{(?:.|\n)*\})", s, re.S)
            if m:
                return json.loads(m.group(1))
        except Exception as e:
            LOG.exception("safe_json_extract failed: %s", e)
    raise ValueError("Unable to parse JSON from string")


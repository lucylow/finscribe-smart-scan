# backend/logging_config.py
import logging
import sys

def configure_logging(level="INFO"):
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    logging.basicConfig(stream=sys.stdout, level=getattr(logging, level), format=fmt)
    # reduce noisy logs from external libs
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


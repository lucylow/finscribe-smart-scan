"""
staging.py

Simple staging utilities:
- stage_upload: detect file type and stage pages (PDF -> PNG per page, images pass-through)
- Storage abstraction (LocalStorage & MinIOStorage sample)
"""

import io
import os
import pathlib
import logging
from typing import List, Tuple, BinaryIO
from pdf2image import convert_from_bytes  # pip install pdf2image
from PIL import Image

logger = logging.getLogger(__name__)

# -------------------------
# Storage abstraction
# -------------------------
class StorageInterface:
    """Minimal storage interface used by staging / tasks."""

    def put_bytes(self, key: str, data: bytes) -> None:
        raise NotImplementedError

    def get_bytes(self, key: str) -> bytes:
        raise NotImplementedError

    def url_for(self, key: str, expires: int = 3600) -> str:
        raise NotImplementedError


class LocalStorage(StorageInterface):
    """Simple local filesystem storage (useful for dev)."""

    def __init__(self, base_path: str = "./storage"):
        self.base = pathlib.Path(base_path)
        self.base.mkdir(parents=True, exist_ok=True)
        logger.info("LocalStorage base: %s", str(self.base))

    def _path(self, key: str) -> pathlib.Path:
        # sanitize key - simple approach
        return self.base / key

    def put_bytes(self, key: str, data: bytes) -> None:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        logger.debug("LocalStorage.put_bytes -> %s", p)

    def get_bytes(self, key: str) -> bytes:
        p = self._path(key)
        return p.read_bytes()

    def url_for(self, key: str, expires: int = 3600) -> str:
        # local path; frontend can fetch via backend proxy if needed
        return str(self._path(key))


try:
    from minio import Minio  # type: ignore
    MINIO_AVAILABLE = True
except Exception:
    MINIO_AVAILABLE = False


class MinIOStorage(StorageInterface):
    """MinIO wrapper. Requires MINIO_* env vars and minio package installed."""

    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str = "finscribe"):
        if not MINIO_AVAILABLE:
            raise RuntimeError("Minio library not installed. pip install minio")
        self.client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=False)
        self.bucket = bucket
        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)

    def put_bytes(self, key: str, data: bytes) -> None:
        self.client.put_object(self.bucket, key, io.BytesIO(data), length=len(data))

    def get_bytes(self, key: str) -> bytes:
        resp = self.client.get_object(self.bucket, key)
        data = resp.read()
        resp.close()
        resp.release_conn()
        return data

    def url_for(self, key: str, expires: int = 3600) -> str:
        return self.client.presigned_get_object(self.bucket, key, expires=expires)


class Boto3StorageAdapter(StorageInterface):
    """Adapter for existing app.storage.storage_service.StorageService (boto3-based)."""

    def __init__(self, storage_service):
        """
        Args:
            storage_service: Instance of app.storage.storage_service.StorageService
        """
        self.storage = storage_service
        self.bucket = storage_service.bucket_name

    def put_bytes(self, key: str, data: bytes) -> None:
        """Put bytes using boto3 client."""
        self.storage.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data
        )

    def get_bytes(self, key: str) -> bytes:
        """Get bytes using boto3 client."""
        resp = self.storage.client.get_object(Bucket=self.bucket, Key=key)
        return resp['Body'].read()

    def url_for(self, key: str, expires: int = 3600) -> str:
        """Generate signed URL."""
        return self.storage.get_signed_url(key, expires_in=expires)


# -------------------------
# Staging functions
# -------------------------
def stage_upload(file_bytes: bytes, filename: str, job_id: str, storage: StorageInterface) -> List[str]:
    """
    Stage an uploaded file.

    - If PDF: convert each page to PNG at 300 DPI and store as `staging/{job_id}/page_{i}.png`
    - If image: store as `staging/{job_id}/page_0.png`
    - Returns list of storage keys for each staged page, in order.
    """
    filename_lower = filename.lower()
    staging_keys = []
    if filename_lower.endswith(".pdf"):
        logger.info("Staging PDF upload (%d bytes) for job %s", len(file_bytes), job_id)
        # convert pages
        pil_pages = convert_from_bytes(file_bytes, dpi=300)
        for i, pil in enumerate(pil_pages):
            buf = io.BytesIO()
            pil.save(buf, format="PNG")
            key = f"staging/{job_id}/page_{i}.png"
            storage.put_bytes(key, buf.getvalue())
            staging_keys.append(key)
            logger.debug("Staged page %s", key)
    else:
        # treat as single image
        logger.info("Staging image upload (%s) for job %s", filename, job_id)
        try:
            # normalize and re-save as PNG
            img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            key = f"staging/{job_id}/page_0.png"
            storage.put_bytes(key, buf.getvalue())
            staging_keys.append(key)
            logger.debug("Staged image %s", key)
        except Exception as e:
            logger.exception("Failed to process image upload: %s", e)
            raise

    return staging_keys


def read_bytes_from_storage(key: str, storage: StorageInterface) -> bytes:
    """Convenience wrapper to read bytes for tasks."""
    return storage.get_bytes(key)


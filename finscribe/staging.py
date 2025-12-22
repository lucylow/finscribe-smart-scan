# finscribe/staging.py
"""
Simple storage abstractions with Local fallback and MinIO (S3 compatible) option.

Provides:
 - StorageInterface (put_bytes/get_bytes/exists/list_prefix)
 - LocalStorage: filesystem-based storage rooted at base_path
 - MinIOStorage: S3-compatible using boto3 (optional, used if MINIO_ENDPOINT set)
 - get_storage(): factory that returns MinIOStorage if relevant env vars present else LocalStorage
 - helper read_bytes_from_storage(key, storage)
"""

from __future__ import annotations
import os
import io
import logging
from typing import Optional, Iterable, List
from pathlib import Path

logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("LOGLEVEL", "INFO"))

# Try optional boto3 import for MinIO support
try:
    import boto3
    from botocore.client import Config
    BOTO3_AVAILABLE = True
except Exception:
    BOTO3_AVAILABLE = False


class StorageInterface:
    """Minimal storage interface."""

    def put_bytes(self, key: str, data: bytes) -> None:
        raise NotImplementedError()

    def get_bytes(self, key: str) -> Optional[bytes]:
        raise NotImplementedError()

    def exists(self, key: str) -> bool:
        raise NotImplementedError()

    def list_prefix(self, prefix: str) -> Iterable[str]:
        raise NotImplementedError()


class LocalStorage(StorageInterface):
    """Local filesystem storage root-based implementation."""

    def __init__(self, base_path: str = "./storage"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info("LocalStorage rooted at %s", str(self.base_path))

    def _full_path(self, key: str) -> Path:
        # simple safety: don't allow escape above base_path
        safe_key = key.lstrip("/").replace("..", "")
        return self.base_path / safe_key

    def put_bytes(self, key: str, data: bytes) -> None:
        p = self._full_path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "wb") as f:
            f.write(data)
        logger.debug("LocalStorage.put_bytes %s (%d bytes)", str(p), len(data))

    def get_bytes(self, key: str) -> Optional[bytes]:
        p = self._full_path(key)
        if not p.exists():
            logger.debug("LocalStorage.get_bytes missing %s", str(p))
            return None
        with open(p, "rb") as f:
            return f.read()

    def exists(self, key: str) -> bool:
        return self._full_path(key).exists()

    def list_prefix(self, prefix: str) -> Iterable[str]:
        p = self._full_path(prefix)
        if not p.exists():
            return []
        if p.is_file():
            return [str(p)]
        out = []
        for child in p.rglob("*"):
            if child.is_file():
                out.append(str(child))
        return out


class MinIOStorage(StorageInterface):
    """
    MinIO (S3-compatible) implementation using boto3.

    Requires these env vars:
      MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_BUCKET
    """

    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str, secure: bool = False):
        if not BOTO3_AVAILABLE:
            raise RuntimeError("boto3 is required for MinIOStorage but is not installed.")
        self.endpoint = endpoint
        self.bucket = bucket
        self.secure = secure
        cfg = Config(signature_version="s3v4", s3={'addressing_style': 'path'})
        self.client = boto3.client(
            "s3",
            endpoint_url=f"http{'s' if secure else ''}://{endpoint}",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=cfg,
        )
        # ensure bucket exists
        try:
            self.client.head_bucket(Bucket=bucket)
        except Exception:
            logger.info("Creating bucket %s on %s", bucket, endpoint)
            self.client.create_bucket(Bucket=bucket)

    def put_bytes(self, key: str, data: bytes) -> None:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data)
        logger.debug("MinIOStorage.put_bytes %s (%d bytes) to bucket %s", key, len(data), self.bucket)

    def get_bytes(self, key: str) -> Optional[bytes]:
        try:
            resp = self.client.get_object(Bucket=self.bucket, Key=key)
            return resp["Body"].read()
        except Exception as e:
            logger.debug("MinIOStorage.get_bytes miss %s: %s", key, e)
            return None

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False

    def list_prefix(self, prefix: str) -> Iterable[str]:
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                yield obj["Key"]


def get_storage() -> StorageInterface:
    """
    Factory: If MINIO_ENDPOINT + MINIO_BUCKET present -> return MinIOStorage,
    otherwise LocalStorage rooted at STORAGE_BASE env var.
    """
    minio_endpoint = os.getenv("MINIO_ENDPOINT")
    bucket = os.getenv("MINIO_BUCKET")
    if minio_endpoint and bucket and BOTO3_AVAILABLE:
        access = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        secret = os.getenv("MINIO_SECRET_KEY", "minioadmin")
        secure = os.getenv("MINIO_SECURE", "false").lower() in ("1", "true", "yes")
        return MinIOStorage(minio_endpoint, access, secret, bucket, secure=secure)
    base = os.getenv("STORAGE_BASE", "./data/storage")
    return LocalStorage(base)


def read_bytes_from_storage(key: str, storage: StorageInterface) -> Optional[bytes]:
    """
    Safe helper to read bytes. Accepts key like 'staging/job/page_0.png' or
    an absolute path in LocalStorage.
    """
    return storage.get_bytes(key)

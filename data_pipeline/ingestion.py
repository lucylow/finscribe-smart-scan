"""
Source ingestion module for multi-source document ingestion.

Supports:
- Local file system
- S3/MinIO buckets
- Raw bytes (API uploads)
- Email attachments (future)
"""
import os
import logging
import pathlib
import uuid
from typing import Union

LOG = logging.getLogger("ingestion")

SUPPORTED_EXT = (".jpg", ".jpeg", ".png", ".pdf", ".tiff", ".tif")


def ingest_from_local(path: str) -> str:
    """
    Ingest file from local filesystem.
    
    Args:
        path: Path to source file
        
    Returns:
        Path to ingested file in data/raw directory
        
    Raises:
        FileNotFoundError: If source file doesn't exist
        ValueError: If file format is not supported
    """
    p = pathlib.Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Source file not found: {path}")
    if p.suffix.lower() not in SUPPORTED_EXT:
        raise ValueError(f"Unsupported format: {p.suffix}. Supported: {SUPPORTED_EXT}")

    storage_key = f"{uuid.uuid4().hex}{p.suffix.lower()}"
    dest = pathlib.Path("data/raw") / storage_key
    dest.parent.mkdir(parents=True, exist_ok=True)
    
    with open(p, "rb") as src, open(dest, "wb") as dst:
        dst.write(src.read())
    
    LOG.info(f"Ingested {path} → {dest}")
    return str(dest)


def ingest_from_minio(bucket: str, object_key: str) -> str:
    """
    Ingest file from MinIO/S3 bucket.
    
    Args:
        bucket: Bucket name
        object_key: Object key/path in bucket
        
    Returns:
        Path to downloaded file in data/raw directory
    """
    try:
        from minio import Minio
        from minio.error import S3Error
    except ImportError:
        # Fallback to boto3 if minio not available
        import boto3
        from botocore.exceptions import ClientError
        
        endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        access_key = os.getenv("MINIO_ACCESS_KEY", os.getenv("AWS_ACCESS_KEY_ID", "minioadmin"))
        secret_key = os.getenv("MINIO_SECRET_KEY", os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin"))
        use_ssl = os.getenv("MINIO_USE_SSL", "false").lower() == "true"
        
        # Parse endpoint
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            endpoint = endpoint.split("://", 1)[1]
        
        endpoint_url = f"{'https' if use_ssl else 'http'}://{endpoint}"
        
        s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        
        ext = os.path.splitext(object_key)[1] or ".bin"
        out_local = f"data/raw/{uuid.uuid4().hex}{ext}"
        pathlib.Path(out_local).parent.mkdir(parents=True, exist_ok=True)
        
        s3_client.download_file(bucket, object_key, out_local)
        LOG.info(f"Downloaded from MinIO {bucket}/{object_key} → {out_local}")
        return out_local
    
    # Use minio client if available
    endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    use_ssl = os.getenv("MINIO_USE_SSL", "false").lower() == "true"
    
    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        endpoint = endpoint.split("://", 1)[1]
    
    minio_client = Minio(
        endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=use_ssl
    )
    
    ext = os.path.splitext(object_key)[1] or ".bin"
    out_local = f"data/raw/{uuid.uuid4().hex}{ext}"
    pathlib.Path(out_local).parent.mkdir(parents=True, exist_ok=True)
    
    minio_client.fget_object(bucket, object_key, out_local)
    LOG.info(f"Downloaded from MinIO {bucket}/{object_key} → {out_local}")
    return out_local


def ingest_from_bytes(b: bytes, filename: str) -> str:
    """
    Ingest raw bytes (e.g., from API upload).
    
    Args:
        b: File bytes
        filename: Original filename (for extension detection)
        
    Returns:
        Path to saved file in data/raw directory
    """
    ext = pathlib.Path(filename).suffix or ".bin"
    if ext.lower() not in SUPPORTED_EXT:
        LOG.warning(f"Unsupported extension {ext}, saving as .bin")
        ext = ".bin"
    
    fname = f"{uuid.uuid4().hex}{ext}"
    out = pathlib.Path("data/raw") / fname
    out.parent.mkdir(parents=True, exist_ok=True)
    
    with open(out, "wb") as fh:
        fh.write(b)
    
    LOG.info(f"Ingested bytes ({len(b)} bytes) → {out}")
    return str(out)


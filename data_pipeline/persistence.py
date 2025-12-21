"""
Persistence module for storing structured data.

Supports:
- PostgreSQL for structured data (invoices, line items)
- MinIO/S3 for blob storage (raw images, JSON, logs)
"""
import os
import logging
import json
import psycopg2
from psycopg2.extras import execute_values, Json
from typing import Dict, Any, Optional

LOG = logging.getLogger("persistence")

DB_PARAMS = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5432"),
    "dbname": os.getenv("POSTGRES_DB", "finscribe"),
    "user": os.getenv("POSTGRES_USER", "finscribe"),
    "password": os.getenv("POSTGRES_PASSWORD", ""),
}


def connect():
    """
    Create PostgreSQL connection.
    
    Returns:
        psycopg2 connection object
    """
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        return conn
    except Exception as e:
        LOG.error(f"Failed to connect to PostgreSQL: {e}")
        raise


def ensure_tables():
    """
    Ensure database tables exist (create if not).
    This is a convenience function - in production, use Alembic migrations.
    """
    conn = connect()
    try:
        with conn.cursor() as cur:
            # Create invoices table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS invoices (
                    id SERIAL PRIMARY KEY,
                    invoice_number TEXT,
                    vendor JSONB,
                    financial_summary JSONB,
                    raw_ocr JSONB,
                    source_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create line_items table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS line_items (
                    id SERIAL PRIMARY KEY,
                    invoice_id INT REFERENCES invoices(id) ON DELETE CASCADE,
                    description TEXT,
                    qty NUMERIC,
                    unit_price NUMERIC,
                    line_total NUMERIC
                )
            """)
            
            conn.commit()
            LOG.info("Database tables ensured")
    except Exception as e:
        conn.rollback()
        LOG.error(f"Failed to ensure tables: {e}")
        raise
    finally:
        conn.close()


def save_invoice(
    parsed: Dict[str, Any],
    raw_ocr: Dict[str, Any],
    source_path: str
) -> int:
    """
    Save invoice and line items to PostgreSQL.
    
    Args:
        parsed: Parsed invoice data
        raw_ocr: Raw OCR output
        source_path: Path to source file
        
    Returns:
        Invoice ID
    """
    ensure_tables()
    
    conn = connect()
    try:
        with conn.cursor() as cur:
            # Insert invoice
            cur.execute("""
                INSERT INTO invoices (
                    invoice_number, vendor, financial_summary, raw_ocr, source_path
                )
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (
                parsed.get("invoice_number"),
                Json(parsed.get("vendor", {})),
                Json(parsed.get("financial_summary", {})),
                Json(raw_ocr),
                source_path
            ))
            
            inv_id = cur.fetchone()[0]
            
            # Insert line items
            items = parsed.get("line_items", [])
            if items:
                values = [
                    (
                        inv_id,
                        item.get("description", ""),
                        item.get("qty"),
                        item.get("unit_price"),
                        item.get("line_total")
                    )
                    for item in items
                ]
                
                execute_values(
                    cur,
                    """INSERT INTO line_items 
                       (invoice_id, description, qty, unit_price, line_total) 
                       VALUES %s""",
                    values
                )
            
            conn.commit()
            LOG.info(f"Persisted invoice {parsed.get('invoice_number')} as ID {inv_id}")
            return inv_id
            
    except Exception as e:
        conn.rollback()
        LOG.error(f"Failed to save invoice: {e}", exc_info=True)
        raise
    finally:
        conn.close()


def save_to_minio(
    data: Dict[str, Any],
    bucket: str,
    object_key: str
) -> str:
    """
    Save data to MinIO/S3 as JSON.
    
    Args:
        data: Data dictionary to save
        bucket: Bucket name
        object_key: Object key/path
        
    Returns:
        Object key
    """
    try:
        import boto3
        from botocore.exceptions import ClientError
    except ImportError:
        raise ImportError("boto3 required for MinIO storage")
    
    endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    access_key = os.getenv("MINIO_ACCESS_KEY", os.getenv("AWS_ACCESS_KEY_ID", "minioadmin"))
    secret_key = os.getenv("MINIO_SECRET_KEY", os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin"))
    use_ssl = os.getenv("MINIO_USE_SSL", "false").lower() == "true"
    
    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        endpoint = endpoint.split("://", 1)[1]
    
    endpoint_url = f"{'https' if use_ssl else 'http'}://{endpoint}"
    
    s3_client = boto3.client(
        's3',
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key
    )
    
    # Ensure bucket exists
    try:
        s3_client.head_bucket(Bucket=bucket)
    except ClientError:
        s3_client.create_bucket(Bucket=bucket)
        LOG.info(f"Created bucket: {bucket}")
    
    # Upload JSON
    import io
    json_bytes = json.dumps(data, indent=2).encode('utf-8')
    s3_client.put_object(
        Bucket=bucket,
        Key=object_key,
        Body=io.BytesIO(json_bytes),
        ContentType='application/json'
    )
    
    LOG.info(f"Saved to MinIO: {bucket}/{object_key}")
    return object_key


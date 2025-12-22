"""S3/MinIO storage implementation with retry logic."""
import os
import logging
from typing import Optional, Dict, Any, List
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from .base import StorageInterface

logger = logging.getLogger(__name__)


class S3Storage(StorageInterface):
    """S3/MinIO storage implementation with retries and error handling."""
    
    def __init__(self):
        """Initialize S3/MinIO storage with automatic fallback detection."""
        # MinIO/S3 configuration
        endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        access_key = os.getenv("MINIO_ACCESS_KEY", os.getenv("AWS_ACCESS_KEY_ID", "minioadmin"))
        secret_key = os.getenv("MINIO_SECRET_KEY", os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin"))
        use_ssl = os.getenv("MINIO_USE_SSL", "false").lower() == "true"
        region = os.getenv("AWS_REGION", "us-east-1")
        
        # Parse endpoint (remove protocol if present)
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            endpoint = endpoint.split("://", 1)[1]
        
        # Determine if using MinIO (local development)
        try:
            port = int(endpoint.split(":")[-1]) if ":" in endpoint else 9000
            is_minio = "localhost" in endpoint or "minio" in endpoint or port < 10000
        except (ValueError, IndexError):
            is_minio = True
        
        self.bucket_name = os.getenv("STORAGE_BUCKET", "finscribe")
        
        # Configure boto3 client with retries
        config = Config(
            signature_version='s3v4',
            s3={
                'addressing_style': 'path' if is_minio else 'auto'
            },
            retries={
                'max_attempts': 3,
                'mode': 'standard'
            }
        )
        
        self.client = boto3.client(
            's3',
            endpoint_url=f"{'https' if use_ssl else 'http'}://{endpoint}",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=config
        )
        
        # Ensure bucket exists
        self._ensure_bucket()
        
        logger.info(f"Initialized S3Storage: endpoint={endpoint}, bucket={self.bucket_name}")
    
    def _ensure_bucket(self):
        """Ensure the bucket exists, create if it doesn't."""
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
            logger.debug(f"Bucket {self.bucket_name} exists")
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                # Bucket doesn't exist, create it
                try:
                    self.client.create_bucket(Bucket=self.bucket_name)
                    logger.info(f"Created bucket {self.bucket_name}")
                except Exception as create_error:
                    logger.error(f"Failed to create bucket {self.bucket_name}: {create_error}")
                    raise
            else:
                logger.error(f"Error checking bucket {self.bucket_name}: {error_code}")
                raise
    
    def exists(self, key: str) -> bool:
        """Check if object exists in S3."""
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                return False
            logger.error(f"Error checking existence of {key}: {error_code}")
            return False
    
    def put_bytes(self, key: str, content: bytes, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store bytes in S3 with retries."""
        try:
            # Convert metadata dict to S3 metadata format
            s3_metadata = {}
            if metadata:
                for k, v in metadata.items():
                    # S3 metadata keys must be lowercase and without special chars
                    s3_key = k.lower().replace(' ', '-')
                    s3_metadata[s3_key] = str(v)[:1024]  # S3 metadata values limited to 2KB total
            
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=content,
                Metadata=s3_metadata if s3_metadata else None
            )
            logger.debug(f"Stored {len(content)} bytes to s3://{self.bucket_name}/{key}")
            return key
        except Exception as e:
            logger.error(f"Failed to store {key} to S3: {e}")
            raise
    
    def get_bytes(self, key: str) -> Optional[bytes]:
        """Retrieve bytes from S3."""
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=key)
            return response['Body'].read()
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'NoSuchKey':
                return None
            logger.error(f"Error retrieving {key} from S3: {error_code}")
            return None
    
    def delete(self, key: str) -> bool:
        """Delete object from S3."""
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.debug(f"Deleted s3://{self.bucket_name}/{key}")
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            logger.error(f"Error deleting {key} from S3: {error_code}")
            return False
    
    def list_prefix(self, prefix: str) -> List[str]:
        """List all keys with given prefix."""
        keys = []
        try:
            paginator = self.client.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        keys.append(obj['Key'])
        except Exception as e:
            logger.error(f"Error listing prefix {prefix} from S3: {e}")
        
        return sorted(keys)


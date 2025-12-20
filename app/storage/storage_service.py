"""Object storage service using boto3 for S3/MinIO compatibility."""
import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import uuid

logger = logging.getLogger(__name__)


class StorageService:
    """Service for managing object storage (S3/MinIO)."""
    
    def __init__(self):
        """Initialize storage service with S3/MinIO configuration."""
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
        is_minio = "localhost" in endpoint or "minio" in endpoint or int(endpoint.split(":")[-1]) < 10000
        
        self.bucket_name = os.getenv("STORAGE_BUCKET", "finscribe")
        self.signed_url_ttl = int(os.getenv("SIGNED_URL_TTL_SECONDS", "3600"))  # 1 hour default
        
        # Configure boto3 client
        config = Config(
            signature_version='s3v4',
            s3={
                'addressing_style': 'path' if is_minio else 'auto'
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
        
        logger.info(f"Storage service initialized: endpoint={endpoint}, bucket={self.bucket_name}")
    
    def _ensure_bucket(self):
        """Ensure the bucket exists, create if it doesn't."""
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
            logger.debug(f"Bucket {self.bucket_name} exists")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                # Bucket doesn't exist, create it
                try:
                    if "localhost" in self.client._endpoint.host or "minio" in self.client._endpoint.host:
                        # MinIO: create bucket
                        self.client.create_bucket(Bucket=self.bucket_name)
                    else:
                        # AWS S3: create bucket with location constraint
                        try:
                            self.client.create_bucket(Bucket=self.bucket_name)
                        except ClientError:
                            # Try with location constraint
                            self.client.create_bucket(
                                Bucket=self.bucket_name,
                                CreateBucketConfiguration={'LocationConstraint': self.client.meta.region_name}
                            )
                    logger.info(f"Created bucket {self.bucket_name}")
                except Exception as create_error:
                    logger.error(f"Failed to create bucket {self.bucket_name}: {str(create_error)}")
                    raise
            else:
                logger.error(f"Error checking bucket {self.bucket_name}: {error_code}")
                raise
    
    def upload_raw(self, file_content: bytes, filename: str, job_id: str) -> str:
        """
        Upload raw document to storage.
        Returns: object key (storage path)
        """
        key = f"raw/{job_id}/{filename}"
        try:
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_content,
                Metadata={
                    'job_id': job_id,
                    'filename': filename,
                    'uploaded_at': datetime.utcnow().isoformat(),
                    'type': 'raw_upload'
                }
            )
            logger.info(f"Uploaded raw file: {key}")
            return key
        except Exception as e:
            logger.error(f"Failed to upload raw file {key}: {str(e)}")
            raise
    
    def upload_processed_image(self, image_content: bytes, job_id: str, page_num: int, format: str = "png") -> str:
        """
        Upload processed image (per-page from PDF).
        Returns: object key
        """
        key = f"processed/{job_id}/page_{page_num}.{format}"
        try:
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=image_content,
                Metadata={
                    'job_id': job_id,
                    'page_num': str(page_num),
                    'format': format,
                    'uploaded_at': datetime.utcnow().isoformat(),
                    'type': 'processed_image'
                }
            )
            logger.debug(f"Uploaded processed image: {key}")
            return key
        except Exception as e:
            logger.error(f"Failed to upload processed image {key}: {str(e)}")
            raise
    
    def upload_ocr_result(self, ocr_data: Dict[str, Any], job_id: str) -> str:
        """
        Upload OCR result JSON.
        Returns: object key
        """
        import json
        key = f"ocr/{job_id}/result.json"
        try:
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=json.dumps(ocr_data, indent=2).encode('utf-8'),
                ContentType='application/json',
                Metadata={
                    'job_id': job_id,
                    'uploaded_at': datetime.utcnow().isoformat(),
                    'type': 'ocr_result'
                }
            )
            logger.debug(f"Uploaded OCR result: {key}")
            return key
        except Exception as e:
            logger.error(f"Failed to upload OCR result {key}: {str(e)}")
            raise
    
    def upload_result(self, result_data: Dict[str, Any], job_id: str, result_id: str) -> str:
        """
        Upload final result JSON.
        Returns: object key
        """
        import json
        key = f"results/{result_id}/result.json"
        try:
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=json.dumps(result_data, indent=2).encode('utf-8'),
                ContentType='application/json',
                Metadata={
                    'job_id': job_id,
                    'result_id': result_id,
                    'uploaded_at': datetime.utcnow().isoformat(),
                    'type': 'result'
                }
            )
            logger.info(f"Uploaded result: {key}")
            return key
        except Exception as e:
            logger.error(f"Failed to upload result {key}: {str(e)}")
            raise
    
    def get_signed_url(self, key: str, expires_in: Optional[int] = None) -> str:
        """
        Generate a signed URL for accessing an object.
        Returns: signed URL
        """
        expires_in = expires_in or self.signed_url_ttl
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expires_in
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate signed URL for {key}: {str(e)}")
            raise
    
    def delete_object(self, key: str):
        """Delete an object from storage."""
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.debug(f"Deleted object: {key}")
        except Exception as e:
            logger.error(f"Failed to delete object {key}: {str(e)}")
            raise
    
    def cleanup_staging(self, ttl_days: int = 7):
        """
        Clean up staging objects older than TTL days.
        This should be run periodically (e.g., via Celery periodic task).
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=ttl_days)
            deleted_count = 0
            
            # List objects in staging prefix
            paginator = self.client.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix='raw/'):
                if 'Contents' not in page:
                    continue
                
                for obj in page['Contents']:
                    if obj['LastModified'].replace(tzinfo=None) < cutoff_date:
                        self.delete_object(obj['Key'])
                        deleted_count += 1
            
            logger.info(f"Cleaned up {deleted_count} staging objects older than {ttl_days} days")
            return deleted_count
        except Exception as e:
            logger.error(f"Error during staging cleanup: {str(e)}")
            raise
    
    def archive_results(self, archive_prefix: str = "archive/", older_than_days: int = 90):
        """
        Archive results older than specified days to archive prefix.
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
            archived_count = 0
            
            paginator = self.client.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix='results/'):
                if 'Contents' not in page:
                    continue
                
                for obj in page['Contents']:
                    if obj['LastModified'].replace(tzinfo=None) < cutoff_date:
                        # Copy to archive
                        archive_key = archive_prefix + obj['Key']
                        self.client.copy_object(
                            Bucket=self.bucket_name,
                            CopySource={'Bucket': self.bucket_name, 'Key': obj['Key']},
                            Key=archive_key
                        )
                        # Delete original
                        self.delete_object(obj['Key'])
                        archived_count += 1
            
            logger.info(f"Archived {archived_count} results older than {older_than_days} days")
            return archived_count
        except Exception as e:
            logger.error(f"Error during archival: {str(e)}")
            raise


# Singleton instance
_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """Get or create storage service singleton."""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service


"""
ETL adapters for different data sources.
"""
import os
import asyncio
import aiofiles
from typing import Generator, Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
import logging

from .base import ETLAdapter, StagedFile

logger = logging.getLogger(__name__)


class MultipartAdapter(ETLAdapter):
    """Adapter for multipart file uploads."""
    
    def ingest(self, config: Dict[str, Any]) -> Generator[StagedFile, None, None]:
        """Ingest files from multipart upload."""
        files = config.get("files", [])
        user_id = config.get("user_id")
        tags = config.get("tags", [])
        metadata = config.get("metadata", {})
        
        for file_data in files:
            if isinstance(file_data, dict):
                content = file_data.get("content", b"")
                filename = file_data.get("filename", "unknown")
            else:
                # Assume it's a file-like object
                content = file_data.read() if hasattr(file_data, "read") else b""
                filename = getattr(file_data, "filename", "unknown")
            
            yield StagedFile(
                source_type="multipart",
                filename=filename,
                content=content,
                user_id=user_id,
                tags=tags,
                metadata=metadata
            )
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate multipart config."""
        return "files" in config and isinstance(config["files"], (list, tuple))


class S3Adapter(ETLAdapter):
    """Adapter for S3/MinIO bucket watch."""
    
    def ingest(self, config: Dict[str, Any]) -> Generator[StagedFile, None, None]:
        """Ingest files from S3/MinIO bucket."""
        try:
            import boto3
        except ImportError:
            logger.error("boto3 not installed. Install with: pip install boto3")
            return
        
        bucket_name = config.get("bucket_name")
        prefix = config.get("prefix", "")
        endpoint_url = config.get("endpoint_url")  # For MinIO
        access_key = config.get("access_key")
        secret_key = config.get("secret_key")
        
        s3_client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        
        # List objects in bucket
        paginator = s3_client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)
        
        for page in pages:
            for obj in page.get("Contents", []):
                key = obj["Key"]
                
                # Download object
                response = s3_client.get_object(Bucket=bucket_name, Key=key)
                content = response["Body"].read()
                
                yield StagedFile(
                    source_type="s3",
                    source_id=f"s3://{bucket_name}/{key}",
                    filename=Path(key).name,
                    content=content,
                    metadata={
                        "bucket": bucket_name,
                        "key": key,
                        "size": obj.get("Size", 0),
                        "last_modified": obj.get("LastModified").isoformat() if obj.get("LastModified") else None
                    }
                )
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate S3 config."""
        return all(k in config for k in ["bucket_name", "access_key", "secret_key"])


class IMAPAdapter(ETLAdapter):
    """Adapter for IMAP email attachment ingestion."""
    
    def ingest(self, config: Dict[str, Any]) -> Generator[StagedFile, None, None]:
        """Ingest email attachments from IMAP."""
        import imaplib
        import email
        from email.header import decode_header
        
        imap_server = config.get("imap_server")
        username = config.get("username")
        password = config.get("password")
        mailbox = config.get("mailbox", "INBOX")
        search_criteria = config.get("search_criteria", "ALL")
        
        try:
            mail = imaplib.IMAP4_SSL(imap_server)
            mail.login(username, password)
            mail.select(mailbox)
            
            # Search for emails
            status, messages = mail.search(None, search_criteria)
            email_ids = messages[0].split()
            
            for email_id in email_ids:
                status, msg_data = mail.fetch(email_id, "(RFC822)")
                email_body = msg_data[0][1]
                email_message = email.message_from_bytes(email_body)
                
                # Extract attachments
                for part in email_message.walk():
                    if part.get_content_disposition() == "attachment":
                        filename = part.get_filename()
                        if filename:
                            # Decode filename if needed
                            decoded_filename = decode_header(filename)[0][0]
                            if isinstance(decoded_filename, bytes):
                                decoded_filename = decoded_filename.decode()
                            
                            content = part.get_payload(decode=True)
                            
                            yield StagedFile(
                                source_type="imap",
                                source_id=f"imap://{mailbox}/{email_id.decode()}",
                                filename=decoded_filename,
                                content=content,
                                metadata={
                                    "subject": email_message["Subject"],
                                    "from": email_message["From"],
                                    "date": email_message["Date"]
                                }
                            )
            
            mail.close()
            mail.logout()
        except Exception as e:
            logger.error(f"IMAP ingestion error: {str(e)}")
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate IMAP config."""
        return all(k in config for k in ["imap_server", "username", "password"])


class LocalFolderAdapter(ETLAdapter):
    """Adapter for local folder watch (batch mode)."""
    
    def ingest(self, config: Dict[str, Any]) -> Generator[StagedFile, None, None]:
        """Ingest files from local folder."""
        folder_path = config.get("folder_path")
        pattern = config.get("pattern", "*")  # e.g., "*.pdf", "*.png"
        recursive = config.get("recursive", False)
        
        if not os.path.isdir(folder_path):
            logger.error(f"Folder not found: {folder_path}")
            return
        
        path = Path(folder_path)
        if recursive:
            files = path.rglob(pattern)
        else:
            files = path.glob(pattern)
        
        for file_path in files:
            if file_path.is_file():
                try:
                    with open(file_path, "rb") as f:
                        content = f.read()
                    
                    yield StagedFile(
                        source_type="local",
                        source_id=str(file_path),
                        filename=file_path.name,
                        content=content,
                        metadata={
                            "path": str(file_path),
                            "size": file_path.stat().st_size,
                            "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                        }
                    )
                except Exception as e:
                    logger.error(f"Error reading file {file_path}: {str(e)}")
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate local folder config."""
        return "folder_path" in config and os.path.isdir(config["folder_path"])


class ETLAdapterFactory:
    """Factory for creating ETL adapters."""
    
    _adapters = {
        "multipart": MultipartAdapter,
        "s3": S3Adapter,
        "imap": IMAPAdapter,
        "local": LocalFolderAdapter,
    }
    
    @classmethod
    def create(cls, adapter_type: str) -> Optional[ETLAdapter]:
        """Create adapter instance."""
        adapter_class = cls._adapters.get(adapter_type)
        if adapter_class:
            return adapter_class()
        return None
    
    @classmethod
    def register(cls, adapter_type: str, adapter_class: type):
        """Register a custom adapter."""
        cls._adapters[adapter_type] = adapter_class
    
    @classmethod
    def list_adapters(cls) -> List[str]:
        """List available adapter types."""
        return list(cls._adapters.keys())


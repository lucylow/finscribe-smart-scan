"""
Base ETL adapter interface for pluggable data sources.
"""
from abc import ABC, abstractmethod
from typing import Generator, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import hashlib


@dataclass
class StagedFile:
    """Represents a staged file ready for processing."""
    source_type: str  # multipart, s3, imap, local
    source_id: Optional[str] = None
    filename: str = ""
    content: bytes = b""
    checksum: str = ""
    ingest_time: datetime = None
    user_id: Optional[str] = None
    tags: Optional[list] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """Compute checksum if not provided."""
        if not self.checksum and self.content:
            self.checksum = hashlib.sha256(self.content).hexdigest()
        if self.ingest_time is None:
            self.ingest_time = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}


class ETLAdapter(ABC):
    """
    Base class for ETL adapters.
    Each adapter implements ingest() to yield StagedFile objects.
    """
    
    @abstractmethod
    def ingest(self, config: Dict[str, Any]) -> Generator[StagedFile, None, None]:
        """
        Ingest files from source and yield StagedFile objects.
        
        Args:
            config: Adapter-specific configuration
            
        Yields:
            StagedFile: Staged file ready for processing
        """
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate adapter configuration."""
        pass



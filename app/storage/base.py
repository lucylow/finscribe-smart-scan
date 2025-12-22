"""Storage abstraction interface with local filesystem fallback."""
import os
import json
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


class StorageInterface(ABC):
    """Abstract storage interface for file operations."""
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if object exists."""
        pass
    
    @abstractmethod
    def put_bytes(self, key: str, content: bytes, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store bytes at key. Returns key."""
        pass
    
    @abstractmethod
    def get_bytes(self, key: str) -> Optional[bytes]:
        """Retrieve bytes from key. Returns None if not found."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete object at key. Returns True if deleted."""
        pass
    
    @abstractmethod
    def list_prefix(self, prefix: str) -> List[str]:
        """List all keys with given prefix."""
        pass
    
    def put_json(self, key: str, data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store JSON data at key."""
        content = json.dumps(data, indent=2).encode('utf-8')
        return self.put_bytes(key, content, metadata)
    
    def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve JSON data from key."""
        content = self.get_bytes(key)
        if content is None:
            return None
        try:
            return json.loads(content.decode('utf-8'))
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from {key}: {e}")
            return None


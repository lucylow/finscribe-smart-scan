"""Local filesystem storage implementation."""
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from .base import StorageInterface

logger = logging.getLogger(__name__)


class LocalStorage(StorageInterface):
    """Local filesystem storage implementation."""
    
    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize local storage.
        
        Args:
            base_path: Base directory for storage. Defaults to ./storage
        """
        self.base_path = Path(base_path or os.getenv("STORAGE_PATH", "./storage"))
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized LocalStorage at {self.base_path.absolute()}")
    
    def _get_path(self, key: str) -> Path:
        """Convert key to filesystem path."""
        # Normalize key (remove leading /, handle ..)
        normalized_key = key.lstrip('/').replace('..', '')
        return self.base_path / normalized_key
    
    def exists(self, key: str) -> bool:
        """Check if file exists."""
        path = self._get_path(key)
        return path.exists() and path.is_file()
    
    def put_bytes(self, key: str, content: bytes, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store bytes to file."""
        path = self._get_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(path, 'wb') as f:
                f.write(content)
            
            # Store metadata as .meta file if provided
            if metadata:
                meta_path = path.with_suffix(path.suffix + '.meta')
                import json
                with open(meta_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
            
            logger.debug(f"Stored {len(content)} bytes to {key}")
            return key
        except Exception as e:
            logger.error(f"Failed to store {key}: {e}")
            raise
    
    def get_bytes(self, key: str) -> Optional[bytes]:
        """Retrieve bytes from file."""
        path = self._get_path(key)
        if not path.exists():
            return None
        
        try:
            with open(path, 'rb') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read {key}: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """Delete file."""
        path = self._get_path(key)
        if not path.exists():
            return False
        
        try:
            path.unlink()
            # Also delete metadata file if exists
            meta_path = path.with_suffix(path.suffix + '.meta')
            if meta_path.exists():
                meta_path.unlink()
            logger.debug(f"Deleted {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete {key}: {e}")
            return False
    
    def list_prefix(self, prefix: str) -> List[str]:
        """List all keys with given prefix."""
        prefix_path = self._get_path(prefix)
        if not prefix_path.exists():
            return []
        
        keys = []
        try:
            # If prefix is a directory, list all files recursively
            if prefix_path.is_dir():
                for file_path in prefix_path.rglob('*'):
                    if file_path.is_file() and not file_path.name.endswith('.meta'):
                        # Convert back to key format
                        relative = file_path.relative_to(self.base_path)
                        keys.append(str(relative).replace('\\', '/'))
            else:
                # If prefix is a file, return it if exists
                if prefix_path.is_file():
                    relative = prefix_path.relative_to(self.base_path)
                    keys.append(str(relative).replace('\\', '/'))
        except Exception as e:
            logger.error(f"Failed to list prefix {prefix}: {e}")
        
        return sorted(keys)


"""
Redis caching for OCR and LLM extraction results.

This module implements a two-layer caching system:
1. OCR Cache: Cache raw OCR output based on image hash
2. Extraction Cache: Cache final structured JSON based on OCR output hash
"""

import hashlib
import json
import logging
from typing import Optional, Dict, Any
import redis
import os

logger = logging.getLogger(__name__)


class CacheService:
    """
    Service for caching OCR and extraction results.
    
    Caching strategy:
    - OCR results cached by image file hash
    - Extraction results cached by OCR output hash + prompt version
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """Initialize cache service with Redis connection."""
        redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self.redis_client.ping()
            self.enabled = True
            logger.info("Redis cache enabled and connected")
        except Exception as e:
            logger.warning(f"Redis cache not available: {e}. Caching disabled.")
            self.redis_client = None
            self.enabled = False
    
    def _hash_image(self, file_content: bytes) -> str:
        """Generate hash for image file content."""
        return hashlib.sha256(file_content).hexdigest()
    
    def _hash_ocr_output(self, ocr_result: Dict[str, Any]) -> str:
        """Generate hash for OCR output."""
        # Create a stable representation of OCR output
        ocr_text = ocr_result.get("text", "")
        # Include key metadata for cache invalidation
        model_version = ocr_result.get("model_version", "")
        hash_input = f"{ocr_text}:{model_version}"
        return hashlib.sha256(hash_input.encode()).hexdigest()
    
    def get_ocr_cache_key(self, file_content: bytes) -> str:
        """Get cache key for OCR results."""
        image_hash = self._hash_image(file_content)
        return f"ocr:{image_hash}"
    
    def get_extraction_cache_key(self, ocr_result: Dict[str, Any], prompt_version: str = "v1") -> str:
        """Get cache key for extraction results."""
        ocr_hash = self._hash_ocr_output(ocr_result)
        return f"extraction:{ocr_hash}:{prompt_version}"
    
    async def get_ocr_result(self, file_content: bytes) -> Optional[Dict[str, Any]]:
        """
        Get cached OCR result.
        
        Args:
            file_content: Raw image file bytes
        
        Returns:
            Cached OCR result or None
        """
        if not self.enabled:
            return None
        
        try:
            cache_key = self.get_ocr_cache_key(file_content)
            cached = self.redis_client.get(cache_key)
            if cached:
                logger.debug(f"OCR cache hit for key: {cache_key}")
                return json.loads(cached)
            return None
        except Exception as e:
            logger.warning(f"Error reading OCR cache: {e}")
            return None
    
    async def set_ocr_result(
        self,
        file_content: bytes,
        ocr_result: Dict[str, Any],
        ttl: int = 86400  # 24 hours
    ) -> bool:
        """
        Cache OCR result.
        
        Args:
            file_content: Raw image file bytes
            ocr_result: OCR result dictionary
            ttl: Time to live in seconds
        
        Returns:
            True if caching succeeded
        """
        if not self.enabled:
            return False
        
        try:
            cache_key = self.get_ocr_cache_key(file_content)
            self.redis_client.setex(
                cache_key,
                ttl,
                json.dumps(ocr_result)
            )
            logger.debug(f"Cached OCR result with key: {cache_key}")
            return True
        except Exception as e:
            logger.warning(f"Error caching OCR result: {e}")
            return False
    
    async def get_extraction_result(
        self,
        ocr_result: Dict[str, Any],
        prompt_version: str = "v1"
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached extraction result.
        
        Args:
            ocr_result: OCR result dictionary
            prompt_version: Prompt template version
        
        Returns:
            Cached extraction result or None
        """
        if not self.enabled:
            return None
        
        try:
            cache_key = self.get_extraction_cache_key(ocr_result, prompt_version)
            cached = self.redis_client.get(cache_key)
            if cached:
                logger.debug(f"Extraction cache hit for key: {cache_key}")
                return json.loads(cached)
            return None
        except Exception as e:
            logger.warning(f"Error reading extraction cache: {e}")
            return None
    
    async def set_extraction_result(
        self,
        ocr_result: Dict[str, Any],
        extraction_result: Dict[str, Any],
        prompt_version: str = "v1",
        ttl: int = 86400  # 24 hours
    ) -> bool:
        """
        Cache extraction result.
        
        Args:
            ocr_result: OCR result dictionary
            extraction_result: Extraction result dictionary
            prompt_version: Prompt template version
            ttl: Time to live in seconds
        
        Returns:
            True if caching succeeded
        """
        if not self.enabled:
            return False
        
        try:
            cache_key = self.get_extraction_cache_key(ocr_result, prompt_version)
            self.redis_client.setex(
                cache_key,
                ttl,
                json.dumps(extraction_result)
            )
            logger.debug(f"Cached extraction result with key: {cache_key}")
            return True
        except Exception as e:
            logger.warning(f"Error caching extraction result: {e}")
            return False
    
    def clear_cache(self, pattern: str = "*") -> int:
        """
        Clear cache entries matching pattern.
        
        Args:
            pattern: Redis key pattern (default: all keys)
        
        Returns:
            Number of keys deleted
        """
        if not self.enabled:
            return 0
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Error clearing cache: {e}")
            return 0


# Global cache service instance
cache_service = CacheService()


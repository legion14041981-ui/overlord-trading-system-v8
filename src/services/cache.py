"""
Cache Service
Provides caching layer with Redis backend
"""
import logging
from typing import Optional, Any
import json
from datetime import timedelta

logger = logging.getLogger(__name__)


class CacheService:
    """Service for caching data with TTL support."""
    
    def __init__(self, redis_client=None):
        """Initialize cache service.
        
        Args:
            redis_client: Redis client instance (optional)
        """
        self.redis = redis_client
        self._local_cache = {}  # Fallback to in-memory cache
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache.
        
        Args:
            key: Cache key
        
        Returns:
            Cached value or None
        """
        try:
            if self.redis:
                value = await self.redis.get(key)
                if value:
                    return json.loads(value)
            else:
                return self._local_cache.get(key)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
        
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        
        Returns:
            True if successful
        """
        try:
            serialized = json.dumps(value)
            
            if self.redis:
                if ttl:
                    await self.redis.setex(key, ttl, serialized)
                else:
                    await self.redis.set(key, serialized)
            else:
                self._local_cache[key] = value
            
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache.
        
        Args:
            key: Cache key
        
        Returns:
            True if successful
        """
        try:
            if self.redis:
                await self.redis.delete(key)
            else:
                self._local_cache.pop(key, None)
            
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache.
        
        Args:
            key: Cache key
        
        Returns:
            True if key exists
        """
        if self.redis:
            return await self.redis.exists(key)
        else:
            return key in self._local_cache
    
    async def clear(self, pattern: Optional[str] = None) -> int:
        """Clear cache entries matching pattern.
        
        Args:
            pattern: Key pattern (e.g., "user:*")
        
        Returns:
            Number of keys deleted
        """
        count = 0
        
        try:
            if self.redis and pattern:
                keys = await self.redis.keys(pattern)
                if keys:
                    count = await self.redis.delete(*keys)
            elif not pattern:
                if self.redis:
                    await self.redis.flushdb()
                else:
                    count = len(self._local_cache)
                    self._local_cache.clear()
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
        
        return count


# Global cache service instance
_cache_service = None


def get_cache_service() -> CacheService:
    """Get or create global cache service instance."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service

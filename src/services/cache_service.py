"""Caching service for performance optimization."""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
import json
from decimal import Decimal

from src.core.structured_logger import get_logger

logger = get_logger(__name__)


class CacheService:
    """In-memory caching service with TTL support."""

    def __init__(self, default_ttl: int = 300):
        """Initialize cache service.
        
        Args:
            default_ttl: Default time-to-live in seconds
        """
        self.default_ttl = default_ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the cache service and cleanup task."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Cache service started")

    async def stop(self) -> None:
        """Stop the cache service."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Cache service stopped")

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        async with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            
            # Check if expired
            if datetime.utcnow() > entry["expires_at"]:
                del self._cache[key]
                return None
            
            entry["hits"] += 1
            return entry["value"]

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> None:
        """Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        async with self._lock:
            ttl = ttl if ttl is not None else self.default_ttl
            
            # Serialize Decimal values
            if isinstance(value, Decimal):
                value = str(value)
            
            self._cache[key] = {
                "value": value,
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(seconds=ttl),
                "hits": 0,
            }

    async def delete(self, key: str) -> bool:
        """Delete value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key was deleted
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear(self) -> None:
        """Clear all cached values."""
        async with self._lock:
            self._cache.clear()
            logger.info("Cache cleared")

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        async with self._lock:
            total_entries = len(self._cache)
            total_hits = sum(entry["hits"] for entry in self._cache.values())
            
            return {
                "total_entries": total_entries,
                "total_hits": total_hits,
                "avg_hits_per_entry": (
                    total_hits / total_entries if total_entries > 0 else 0
                ),
            }

    async def _cleanup_loop(self) -> None:
        """Background task to cleanup expired entries."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")

    async def _cleanup_expired(self) -> None:
        """Remove expired cache entries."""
        async with self._lock:
            now = datetime.utcnow()
            expired_keys = [
                key for key, entry in self._cache.items()
                if now > entry["expires_at"]
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

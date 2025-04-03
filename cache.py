from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import threading
import logging
from collections import OrderedDict

logger = logging.getLogger(__name__)

class CacheEntry:
    def __init__(self, value: Any, ttl: int):
        self.value = value
        self.timestamp = datetime.now()
        self.ttl = ttl
        self.last_accessed = datetime.now()

    def is_expired(self) -> bool:
        return datetime.now() - self.timestamp > timedelta(seconds=self.ttl)

class Cache:
    def __init__(self, ttl_seconds: int = 3600, max_size: int = 1000, prefix: str = ""):
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._default_ttl = ttl_seconds
        self._max_size = max_size
        self._prefix = prefix
        self._lock = threading.RLock()  # Using RLock for nested lock support
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }

    def _get_full_key(self, key: str) -> str:
        return f"{self._prefix}:{key}" if self._prefix else key

    def _evict_lru(self) -> None:
        """Evict the least recently used item from cache"""
        if self._cache:
            self._cache.popitem(last=False)  # Remove the first item (least recently used)
            self._stats["evictions"] += 1
            logger.debug("Cache eviction performed")

    def _cleanup_expired(self) -> None:
        """Remove all expired entries from the cache"""
        now = datetime.now()
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        for key in expired_keys:
            del self._cache[key]
            self._stats["evictions"] += 1

    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache"""
        with self._lock:
            full_key = self._get_full_key(key)
            entry = self._cache.get(full_key)

            if entry is None:
                self._stats["misses"] += 1
                return None

            if entry.is_expired():
                del self._cache[full_key]
                self._stats["evictions"] += 1
                self._stats["misses"] += 1
                return None

            # Update access time and move to end (most recently used)
            entry.last_accessed = datetime.now()
            self._cache.move_to_end(full_key)
            self._stats["hits"] += 1

            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value in the cache with optional TTL override"""
        with self._lock:
            self._cleanup_expired()  # Clean up expired entries first

            full_key = self._get_full_key(key)
            ttl_value = ttl if ttl is not None else self._default_ttl

            # If we're at max size, evict the LRU item
            if len(self._cache) >= self._max_size and full_key not in self._cache:
                self._evict_lru()

            self._cache[full_key] = CacheEntry(value, ttl_value)
            self._cache.move_to_end(full_key)  # Move to end (most recently used)
            logger.debug(f"Cache set: {full_key}")

    def clear(self) -> None:
        """Clear all items from the cache"""
        with self._lock:
            self._cache.clear()
            logger.debug("Cache cleared")

    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        with self._lock:
            return {
                **self._stats,
                "size": len(self._cache),
                "max_size": self._max_size
            }

    def get_keys(self) -> List[str]:
        """Get all non-expired keys in the cache"""
        with self._lock:
            self._cleanup_expired()
            return list(self._cache.keys())
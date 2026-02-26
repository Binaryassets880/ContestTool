"""TTL cache with stale-while-revalidate pattern."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Generic, Optional, TypeVar

from .config import config

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    """Cache entry with TTL tracking."""

    data: T
    fetched_at: datetime
    ttl_seconds: int

    @property
    def age_seconds(self) -> float:
        """Get age of cache entry in seconds."""
        return (datetime.now() - self.fetched_at).total_seconds()

    @property
    def is_fresh(self) -> bool:
        """Check if cache entry is within TTL."""
        return self.age_seconds < self.ttl_seconds

    @property
    def is_stale_but_usable(self) -> bool:
        """Check if stale but within grace period."""
        max_age = self.ttl_seconds + config.stale_grace_seconds
        return self.age_seconds < max_age


@dataclass
class FeedCache:
    """TTL cache with stale-while-revalidate pattern."""

    _entries: dict[str, CacheEntry] = field(default_factory=dict)
    _refresh_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def get_or_fetch(
        self,
        key: str,
        fetch_fn: Callable[[], Awaitable[T]],
        ttl: Optional[int] = None,
    ) -> T:
        """Get cached value or fetch if stale, serve stale on failure."""
        ttl = ttl or config.ttl_seconds
        entry = self._entries.get(key)

        # Fresh cache hit
        if entry and entry.is_fresh:
            logger.debug(f"Cache hit (fresh) for {key}, age={entry.age_seconds:.1f}s")
            return entry.data

        # Need to refresh - acquire lock to prevent thundering herd
        async with self._refresh_lock:
            # Double-check after acquiring lock
            entry = self._entries.get(key)
            if entry and entry.is_fresh:
                return entry.data

            # Try to fetch new data
            try:
                if entry:
                    logger.info(f"Cache stale for {key}, refreshing...")
                else:
                    logger.info(f"Cache miss for {key}, fetching...")

                data = await fetch_fn()
                self._entries[key] = CacheEntry(
                    data=data,
                    fetched_at=datetime.now(),
                    ttl_seconds=ttl,
                )
                return data

            except Exception as e:
                # Serve stale if available and within grace period
                if entry and entry.is_stale_but_usable:
                    logger.warning(
                        f"Fetch failed for {key}, serving stale data "
                        f"(age={entry.age_seconds:.1f}s): {e}"
                    )
                    return entry.data

                # No usable cached data
                logger.error(f"Fetch failed for {key} with no usable cache: {e}")
                raise

    def get_entry_info(self, key: str) -> Optional[dict]:
        """Get metadata about a cache entry."""
        entry = self._entries.get(key)
        if not entry:
            return None
        return {
            "age_seconds": entry.age_seconds,
            "is_fresh": entry.is_fresh,
            "is_stale_but_usable": entry.is_stale_but_usable,
            "fetched_at": entry.fetched_at.isoformat(),
        }

    def invalidate(self, key: Optional[str] = None):
        """Invalidate specific key or all cache."""
        if key is None:
            self._entries.clear()
            logger.info("Cache cleared")
        elif key in self._entries:
            del self._entries[key]
            logger.info(f"Cache invalidated for {key}")

    def keys(self) -> list[str]:
        """Get all cache keys."""
        return list(self._entries.keys())

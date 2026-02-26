"""Feed module - coordinates fetching, caching, and data store management."""

import logging
from typing import Optional

from .cache import FeedCache
from .client import FeedClient
from .config import config
from .exceptions import FeedUnavailableError
from .store import FeedDataStore

logger = logging.getLogger(__name__)

__all__ = [
    "FeedCoordinator",
    "get_feed",
    "FeedUnavailableError",
    "config",
]


class FeedCoordinator:
    """Coordinates feed fetching, caching, and data store management."""

    _instance: Optional["FeedCoordinator"] = None

    def __init__(self):
        self.client = FeedClient()
        self.cache = FeedCache()
        self.store = FeedDataStore()
        self._initialized = False
        self._manifest: Optional[dict] = None

    @classmethod
    def get_instance(cls) -> "FeedCoordinator":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = FeedCoordinator()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """Reset singleton instance (for testing)."""
        cls._instance = None

    async def initialize(self):
        """Initialize the feed coordinator - fetch manifest and load data."""
        if self._initialized:
            return

        logger.info("Initializing feed coordinator...")
        logger.info(f"Feed base URL: {config.base_url}")

        await self.refresh()
        self._initialized = True

        logger.info(
            f"Feed coordinator initialized: "
            f"{len(self.store.matches)} matches, "
            f"{len(self.store.scheduled_matches)} scheduled, "
            f"{len(self.store.scored_matches)} scored"
        )

    async def refresh(self):
        """Refresh data from remote feed."""
        # Fetch manifest
        self._manifest = await self.cache.get_or_fetch(
            "manifest", self.client.fetch_manifest
        )

        # Determine which partitions to load
        partitions_to_load = self._select_partitions(self._manifest)
        logger.info(f"Loading {len(partitions_to_load)} partitions...")

        # Clear store before reloading (to handle removed matches)
        self.store.clear()

        # Fetch needed partitions
        for partition in partitions_to_load:
            partition_key = f"partition:{partition['date']}"
            try:
                partition_data = await self.cache.get_or_fetch(
                    partition_key,
                    lambda p=partition: self.client.fetch_partition(p["url"]),
                )
                self.store.load_partition(partition_data)
            except Exception as e:
                logger.warning(f"Failed to load partition {partition['date']}: {e}")
                # Continue with other partitions

        # Fetch cumulative stats
        try:
            cumulative = await self.cache.get_or_fetch(
                "cumulative", self.client.fetch_cumulative
            )
            self.store.load_cumulative(cumulative)
        except Exception as e:
            logger.warning(f"Failed to load cumulative stats: {e}")
            # Continue without cumulative - will use defaults

        # Rebuild aggregates
        self.store.rebuild_aggregates()

        logger.info(f"Feed refresh complete. Loaded {len(self.store.matches)} matches.")

    def _select_partitions(self, manifest: dict) -> list[dict]:
        """Select which partitions to load based on config."""
        partitions = manifest.get("partitions", [])

        # Sort by date descending and take most recent N
        sorted_partitions = sorted(
            partitions, key=lambda p: p.get("date", ""), reverse=True
        )
        selected = sorted_partitions[: config.max_partitions]

        logger.info(
            f"Selected {len(selected)} of {len(partitions)} partitions "
            f"(max_partitions={config.max_partitions})"
        )
        return selected

    async def ensure_ready(self):
        """Ensure coordinator is initialized and data is fresh."""
        if not self._initialized:
            await self.initialize()

        # Check if manifest cache is stale and needs refresh
        manifest_info = self.cache.get_entry_info("manifest")
        if manifest_info and not manifest_info["is_fresh"]:
            logger.info("Manifest cache stale, refreshing in background...")
            # Refresh will happen via cache.get_or_fetch on next call

    def get_health_info(self) -> dict:
        """Get health/status information."""
        manifest_info = self.cache.get_entry_info("manifest")
        return {
            "initialized": self._initialized,
            "matches_loaded": len(self.store.matches),
            "scheduled_matches": len(self.store.scheduled_matches),
            "scored_matches": len(self.store.scored_matches),
            "champions_tracked": len(self.store.champion_winrates),
            "cumulative_players": len(self.store.cumulative_stats),
            "cache_keys": self.cache.keys(),
            "manifest_age_seconds": (
                manifest_info["age_seconds"] if manifest_info else None
            ),
            "manifest_fresh": manifest_info["is_fresh"] if manifest_info else False,
            "feed_base_url": config.base_url,
        }

    async def shutdown(self):
        """Clean shutdown."""
        logger.info("Shutting down feed coordinator...")
        await self.client.close()


async def get_feed() -> FeedCoordinator:
    """Get initialized feed coordinator."""
    feed = FeedCoordinator.get_instance()
    await feed.ensure_ready()
    return feed

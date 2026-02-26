"""Configuration for feed client."""

import os
from dataclasses import dataclass


@dataclass
class FeedConfig:
    """Feed configuration loaded from environment variables."""

    base_url: str
    ttl_seconds: int
    http_timeout_seconds: int
    stale_grace_seconds: int
    max_partitions: int

    @classmethod
    def from_env(cls) -> "FeedConfig":
        """Load configuration from environment variables."""
        return cls(
            base_url=os.getenv(
                "FEED_BASE_URL",
                "https://flowbot44.github.io/grand-arena-builder-skill/data"
            ),
            ttl_seconds=int(os.getenv("FEED_TTL_SECONDS", "600")),
            http_timeout_seconds=int(os.getenv("FEED_HTTP_TIMEOUT_SECONDS", "30")),
            stale_grace_seconds=int(os.getenv("FEED_STALE_GRACE_SECONDS", "300")),
            max_partitions=int(os.getenv("FEED_MAX_PARTITIONS", "14")),
        )


# Global config instance
config = FeedConfig.from_env()

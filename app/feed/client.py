"""HTTP client for fetching feed data."""

import gzip
import json
import logging
from typing import Any, Optional
import httpx

from .config import config
from .exceptions import FeedUnavailableError, FeedParseError

logger = logging.getLogger(__name__)


class FeedClient:
    """Async HTTP client for fetching remote feed data."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or config.base_url).rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(config.http_timeout_seconds),
                follow_redirects=True,
            )
        return self._client

    async def fetch_json(self, path: str) -> Any:
        """Fetch JSON from a path relative to base URL."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        logger.info(f"Fetching JSON from {url}")

        try:
            client = await self._get_client()
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException as e:
            logger.error(f"Timeout fetching {url}: {e}")
            raise FeedUnavailableError(f"Timeout fetching {path}")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching {url}: {e.response.status_code}")
            raise FeedUnavailableError(f"HTTP {e.response.status_code} fetching {path}")
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching {url}: {e}")
            raise FeedUnavailableError(f"Failed to fetch {path}: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for {url}: {e}")
            raise FeedParseError(f"Invalid JSON in {path}")

    async def fetch_gzip_json(self, path: str) -> Any:
        """Fetch and decompress GZIP JSON from a path."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        logger.info(f"Fetching GZIP JSON from {url}")

        try:
            client = await self._get_client()
            response = await client.get(url)
            response.raise_for_status()

            # Decompress GZIP
            decompressed = gzip.decompress(response.content)
            return json.loads(decompressed)
        except httpx.TimeoutException as e:
            logger.error(f"Timeout fetching {url}: {e}")
            raise FeedUnavailableError(f"Timeout fetching {path}")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching {url}: {e.response.status_code}")
            raise FeedUnavailableError(f"HTTP {e.response.status_code} fetching {path}")
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching {url}: {e}")
            raise FeedUnavailableError(f"Failed to fetch {path}: {e}")
        except gzip.BadGzipFile as e:
            logger.error(f"Invalid GZIP in {url}: {e}")
            raise FeedParseError(f"Invalid GZIP data in {path}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for {url}: {e}")
            raise FeedParseError(f"Invalid JSON in {path}")

    async def fetch_manifest(self) -> dict:
        """Fetch latest.json manifest."""
        return await self.fetch_json("latest.json")

    async def fetch_partition(self, partition_url: str) -> list[dict]:
        """Fetch and decompress a partition file."""
        # partition_url is relative like "partitions/raw_matches_2026-02-26.json.gz"
        return await self.fetch_gzip_json(partition_url)

    async def fetch_cumulative(self) -> list[dict]:
        """Fetch current_totals.json.gz cumulative stats."""
        return await self.fetch_gzip_json("cumulative/current_totals.json.gz")

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

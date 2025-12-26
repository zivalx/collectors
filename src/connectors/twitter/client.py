"""Low-level Twitter API v2 client."""

import httpx
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from connectors.twitter.models import TwitterClientConfig
from connectors.common.http import with_retry
from connectors.common.exceptions import (
    AuthenticationError,
    DataFetchError,
    RateLimitError,
)

logger = logging.getLogger(__name__)


class TwitterClient:
    """Low-level Twitter API v2 client using httpx.

    Enhanced from trender/app/services/twitter_collector.py lines 14-20.
    """

    BASE_URL = "https://api.twitter.com/2"

    def __init__(self, config: TwitterClientConfig):
        """Initialize Twitter client.

        Args:
            config: Twitter client configuration with bearer token
        """
        self.config = config
        self._client = httpx.AsyncClient(
            timeout=config.timeout,
            headers={"Authorization": f"Bearer {config.bearer_token}"},
        )

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup HTTP client."""
        await self._client.aclose()
        logger.info("Twitter client closed")

    @with_retry(max_attempts=3)
    async def search_recent(
        self,
        query: str,
        max_results: int = 10,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Search recent tweets using Twitter API v2.

        Enhanced from trender/app/services/twitter_collector.py lines 14-20.

        Args:
            query: Twitter search query
            max_results: Max tweets to return (10-100)
            start_time: Start time for search (UTC)
            end_time: End time for search (UTC)

        Returns:
            Raw API response JSON

        Raises:
            AuthenticationError: Invalid bearer token
            RateLimitError: Rate limit exceeded
            DataFetchError: Other API errors
        """
        url = f"{self.BASE_URL}/tweets/search/recent"
        params = {
            "query": query,
            "max_results": max_results,
            "tweet.fields": "created_at,author_id,public_metrics",
        }

        if start_time:
            params["start_time"] = start_time.isoformat().replace("+00:00", "Z")
        if end_time:
            params["end_time"] = end_time.isoformat().replace("+00:00", "Z")

        try:
            logger.info(f"Searching Twitter for: {query}")
            response = await self._client.get(url, params=params)

            # Handle specific error codes
            if response.status_code == 401:
                raise AuthenticationError("Invalid Twitter bearer token")
            elif response.status_code == 429:
                raise RateLimitError("Twitter API rate limit exceeded")

            response.raise_for_status()
            data = response.json()

            logger.info(
                f"Found {len(data.get('data', []))} tweets for query: {query}"
            )
            return data

        except httpx.HTTPStatusError as e:
            raise DataFetchError(f"Twitter API error: {e}")
        except httpx.RequestError as e:
            raise DataFetchError(f"Twitter request failed: {e}")

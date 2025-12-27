"""Low-level GNews API client."""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import logging
import httpx

from connectors.gnews.models import GNewsClientConfig
from connectors.common.exceptions import DataFetchError, AuthenticationError

logger = logging.getLogger(__name__)


class GNewsClient:
    """Low-level GNews API client.

    Wraps GNews API HTTP endpoints with async support.
    API Documentation: https://gnews.io/docs/v4
    """

    BASE_URL = "https://gnews.io/api/v4"

    def __init__(self, config: GNewsClientConfig):
        """Initialize GNews API client.

        Args:
            config: GNews client configuration
        """
        self.config = config
        self._client = None

    def _get_client(self) -> httpx.AsyncClient:
        """Lazy initialization of HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.config.timeout,
                headers={"User-Agent": "Connectors/1.0"},
            )
        return self._client

    async def close(self):
        """Close HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def search(
        self,
        q: str,
        lang: Optional[str] = None,
        country: Optional[str] = None,
        category: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        sortby: str = "publishedAt",
        max_results: int = 10,
    ) -> Dict[str, Any]:
        """Search for news articles.

        Args:
            q: Search query
            lang: Language code (e.g., 'en', 'es', 'fr')
            country: Country code (e.g., 'us', 'gb', 'ca')
            category: News category
            from_date: Start date
            to_date: End date
            sortby: Sort order (publishedAt or relevance)
            max_results: Maximum articles to return (max 100)

        Returns:
            Dict with 'totalArticles' and 'articles' keys

        Raises:
            AuthenticationError: If API key is invalid
            DataFetchError: If request fails
        """
        try:
            client = self._get_client()

            # Build query parameters
            params: Dict[str, Any] = {
                "apikey": self.config.api_key,
                "q": q,
                "max": min(max_results, 100),  # GNews max is 100
                "sortby": sortby,
            }

            if lang:
                params["lang"] = lang
            if country:
                params["country"] = country
            if category:
                params["topic"] = category  # GNews uses 'topic' parameter
            if from_date:
                params["from"] = from_date.strftime("%Y-%m-%dT%H:%M:%SZ")
            if to_date:
                params["to"] = to_date.strftime("%Y-%m-%dT%H:%M:%SZ")

            # Make request
            logger.debug(f"Requesting /search with params: {params}")
            response = await client.get(f"{self.BASE_URL}/search", params=params)

            # Handle errors
            if response.status_code == 401:
                raise AuthenticationError("Invalid GNews API key")
            elif response.status_code == 403:
                raise AuthenticationError("GNews API key access forbidden")
            elif response.status_code == 429:
                raise DataFetchError("Rate limit exceeded (100 requests/day on free tier)")
            elif response.status_code != 200:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("errors", [f"HTTP {response.status_code}"])
                raise DataFetchError(f"API error: {error_msg}")

            data = response.json()

            # Check for API-level errors
            if "errors" in data:
                raise DataFetchError(f"GNews API error: {data['errors']}")

            total_articles = data.get("totalArticles", 0)
            articles_count = len(data.get("articles", []))

            logger.info(
                f"Fetched {articles_count} articles for query '{q}' "
                f"(total available: {total_articles})"
            )

            return data

        except httpx.HTTPError as e:
            raise DataFetchError(f"HTTP error: {e}")
        except Exception as e:
            if isinstance(e, (AuthenticationError, DataFetchError)):
                raise
            raise DataFetchError(f"Error fetching articles: {e}")

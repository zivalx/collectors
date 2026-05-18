"""Low-level Polymarket Gamma API client for market discovery."""

import logging
from typing import Any, Dict, List, Optional

import httpx

from connectors.common.exceptions import DataFetchError
from connectors.common.http import with_retry
from connectors.polymarket.models import PolymarketClientConfig

logger = logging.getLogger(__name__)


class GammaClient:
    """Low-level client for Polymarket Gamma API.

    Handles market discovery, events, and search.
    API docs: https://docs.polymarket.com
    """

    def __init__(self, config: PolymarketClientConfig):
        self.config = config
        self._base_url = config.gamma_base_url
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.config.timeout,
                headers={"User-Agent": "Connectors/1.0"},
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "GammaClient":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    @with_retry(max_attempts=3, min_wait=2, max_wait=10)
    async def get_markets(
        self,
        active: Optional[bool] = None,
        closed: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
        order: Optional[str] = None,
        ascending: Optional[bool] = None,
        tag_id: Optional[str] = None,
        slug: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch markets with optional filters."""
        try:
            client = self._get_client()
            params: Dict[str, Any] = {"limit": limit, "offset": offset}
            if active is not None:
                params["active"] = str(active).lower()
            if closed is not None:
                params["closed"] = str(closed).lower()
            if order:
                params["order"] = order
            if ascending is not None:
                params["ascending"] = str(ascending).lower()
            if tag_id:
                params["tag_id"] = tag_id
            if slug:
                params["slug"] = slug

            logger.debug(f"GET /markets params={params}")
            response = await client.get(f"{self._base_url}/markets", params=params)

            if response.status_code != 200:
                raise DataFetchError(f"Gamma API /markets returned HTTP {response.status_code}")
            return response.json()
        except httpx.HTTPError as e:
            raise DataFetchError(f"HTTP error fetching markets: {e}")
        except DataFetchError:
            raise
        except Exception as e:
            raise DataFetchError(f"Error fetching markets: {e}")

    @with_retry(max_attempts=3, min_wait=2, max_wait=10)
    async def search(self, keyword: str) -> List[Dict[str, Any]]:
        """Search markets by keyword."""
        try:
            client = self._get_client()
            params = {"keyword": keyword}
            logger.debug(f"GET /search keyword={keyword}")
            response = await client.get(f"{self._base_url}/search", params=params)
            if response.status_code != 200:
                raise DataFetchError(f"Gamma API /search returned HTTP {response.status_code}")
            return response.json()
        except httpx.HTTPError as e:
            raise DataFetchError(f"HTTP error searching markets: {e}")
        except DataFetchError:
            raise
        except Exception as e:
            raise DataFetchError(f"Error searching markets: {e}")

    @with_retry(max_attempts=3, min_wait=2, max_wait=10)
    async def get_events(
        self,
        active: Optional[bool] = None,
        closed: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Fetch events with optional filters."""
        try:
            client = self._get_client()
            params: Dict[str, Any] = {"limit": limit, "offset": offset}
            if active is not None:
                params["active"] = str(active).lower()
            if closed is not None:
                params["closed"] = str(closed).lower()
            logger.debug(f"GET /events params={params}")
            response = await client.get(f"{self._base_url}/events", params=params)
            if response.status_code != 200:
                raise DataFetchError(f"Gamma API /events returned HTTP {response.status_code}")
            return response.json()
        except httpx.HTTPError as e:
            raise DataFetchError(f"HTTP error fetching events: {e}")
        except DataFetchError:
            raise
        except Exception as e:
            raise DataFetchError(f"Error fetching events: {e}")

    @with_retry(max_attempts=3, min_wait=2, max_wait=10)
    async def get_event(self, event_id: str) -> Dict[str, Any]:
        """Fetch a single event by ID."""
        try:
            client = self._get_client()
            logger.debug(f"GET /events/{event_id}")
            response = await client.get(f"{self._base_url}/events/{event_id}")
            if response.status_code != 200:
                raise DataFetchError(f"Gamma API /events/{event_id} returned HTTP {response.status_code}")
            return response.json()
        except httpx.HTTPError as e:
            raise DataFetchError(f"HTTP error fetching event {event_id}: {e}")
        except DataFetchError:
            raise
        except Exception as e:
            raise DataFetchError(f"Error fetching event {event_id}: {e}")

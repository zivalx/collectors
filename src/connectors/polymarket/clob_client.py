"""Low-level Polymarket CLOB API client for pricing and trade data."""

import logging
from typing import Any, Dict, Optional

import httpx

from connectors.common.exceptions import DataFetchError
from connectors.common.http import with_retry
from connectors.polymarket.models import PolymarketClientConfig

logger = logging.getLogger(__name__)


class CLOBClient:
    """Low-level client for Polymarket CLOB API.

    Handles prices, orderbooks, midpoints, and price history.
    All endpoints are read-only and public (no auth needed).
    """

    def __init__(self, config: PolymarketClientConfig):
        self.config = config
        self._base_url = config.clob_base_url
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

    async def __aenter__(self) -> "CLOBClient":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    @with_retry(max_attempts=3, min_wait=2, max_wait=10)
    async def get_price(self, token_id: str, side: str = "BUY") -> Dict[str, Any]:
        """Get current price for a token."""
        try:
            client = self._get_client()
            params = {"token_id": token_id, "side": side}
            logger.debug(f"GET /price token_id={token_id} side={side}")
            response = await client.get(f"{self._base_url}/price", params=params)
            if response.status_code != 200:
                raise DataFetchError(f"CLOB API /price returned HTTP {response.status_code}")
            return response.json()
        except httpx.HTTPError as e:
            raise DataFetchError(f"HTTP error fetching price: {e}")
        except DataFetchError:
            raise
        except Exception as e:
            raise DataFetchError(f"Error fetching price: {e}")

    @with_retry(max_attempts=3, min_wait=2, max_wait=10)
    async def get_book(self, token_id: str) -> Dict[str, Any]:
        """Get full orderbook for a token."""
        try:
            client = self._get_client()
            params = {"token_id": token_id}
            logger.debug(f"GET /book token_id={token_id}")
            response = await client.get(f"{self._base_url}/book", params=params)
            if response.status_code != 200:
                raise DataFetchError(f"CLOB API /book returned HTTP {response.status_code}")
            return response.json()
        except httpx.HTTPError as e:
            raise DataFetchError(f"HTTP error fetching orderbook: {e}")
        except DataFetchError:
            raise
        except Exception as e:
            raise DataFetchError(f"Error fetching orderbook: {e}")

    @with_retry(max_attempts=3, min_wait=2, max_wait=10)
    async def get_midpoint(self, token_id: str) -> Dict[str, Any]:
        """Get midpoint price for a token."""
        try:
            client = self._get_client()
            params = {"token_id": token_id}
            logger.debug(f"GET /midpoint token_id={token_id}")
            response = await client.get(f"{self._base_url}/midpoint", params=params)
            if response.status_code != 200:
                raise DataFetchError(f"CLOB API /midpoint returned HTTP {response.status_code}")
            return response.json()
        except httpx.HTTPError as e:
            raise DataFetchError(f"HTTP error fetching midpoint: {e}")
        except DataFetchError:
            raise
        except Exception as e:
            raise DataFetchError(f"Error fetching midpoint: {e}")

    @with_retry(max_attempts=3, min_wait=2, max_wait=10)
    async def get_price_history(
        self,
        token_id: str,
        interval: str = "1d",
        start_ts: Optional[int] = None,
        end_ts: Optional[int] = None,
        fidelity: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get historical price time-series."""
        try:
            client = self._get_client()
            params: Dict[str, Any] = {"market": token_id, "interval": interval}
            if start_ts is not None:
                params["startTs"] = start_ts
            if end_ts is not None:
                params["endTs"] = end_ts
            if fidelity is not None:
                params["fidelity"] = fidelity
            logger.debug(f"GET /prices-history params={params}")
            response = await client.get(f"{self._base_url}/prices-history", params=params)
            if response.status_code != 200:
                raise DataFetchError(f"CLOB API /prices-history returned HTTP {response.status_code}")
            return response.json()
        except httpx.HTTPError as e:
            raise DataFetchError(f"HTTP error fetching price history: {e}")
        except DataFetchError:
            raise
        except Exception as e:
            raise DataFetchError(f"Error fetching price history: {e}")

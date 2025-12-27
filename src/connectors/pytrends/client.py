"""Low-level Google Trends client using pytrends."""

import asyncio
from typing import Dict, List, Any
from datetime import datetime
import logging
import pandas as pd

from connectors.pytrends.models import PyTrendsClientConfig
from connectors.common.exceptions import DataFetchError

logger = logging.getLogger(__name__)


class PyTrendsClient:
    """Low-level Google Trends client using pytrends library.

    Wraps pytrends synchronous API with async support.
    """

    def __init__(self, config: PyTrendsClientConfig):
        """Initialize Google Trends client.

        Args:
            config: PyTrends client configuration
        """
        self.config = config
        self._pytrends = None

    def _get_pytrends(self):
        """Lazy initialization of pytrends object."""
        if self._pytrends is None:
            try:
                from pytrends.request import TrendReq
                self._pytrends = TrendReq(
                    timeout=self.config.timeout,
                    retries=self.config.retries,
                    backoff_factor=self.config.backoff_factor
                )
                logger.info("PyTrends client initialized")
            except ImportError:
                raise DataFetchError(
                    "pytrends library not installed. "
                    "Install with: pip install pytrends"
                )
        return self._pytrends

    async def get_interest_over_time(
        self,
        keywords: List[str],
        timeframe: str = "today 3-m",
        geo: str = "",
        category: int = 0
    ) -> pd.DataFrame:
        """Get interest over time for keywords.

        Args:
            keywords: List of keywords to track (max 5)
            timeframe: Time range
            geo: Geographic location code
            category: Category code

        Returns:
            DataFrame with interest over time data

        Raises:
            DataFetchError: If request fails
        """
        try:
            def _fetch():
                pytrends = self._get_pytrends()
                pytrends.build_payload(
                    keywords,
                    cat=category,
                    timeframe=timeframe,
                    geo=geo
                )
                return pytrends.interest_over_time()

            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, _fetch)

            logger.info(
                f"Fetched interest over time for {len(keywords)} keywords "
                f"({len(df)} data points)"
            )
            return df

        except Exception as e:
            raise DataFetchError(f"Error fetching interest over time: {e}")

    async def get_related_queries(
        self,
        keywords: List[str],
        timeframe: str = "today 3-m",
        geo: str = "",
        category: int = 0
    ) -> Dict[str, Any]:
        """Get related queries for keywords.

        Args:
            keywords: List of keywords
            timeframe: Time range
            geo: Geographic location code
            category: Category code

        Returns:
            Dictionary with related queries (top and rising)
        """
        try:
            def _fetch():
                pytrends = self._get_pytrends()
                pytrends.build_payload(
                    keywords,
                    cat=category,
                    timeframe=timeframe,
                    geo=geo
                )
                return pytrends.related_queries()

            loop = asyncio.get_event_loop()
            related = await loop.run_in_executor(None, _fetch)

            logger.info(f"Fetched related queries for {len(keywords)} keywords")
            return related

        except Exception as e:
            logger.error(f"Error fetching related queries: {e}")
            return {}

    async def get_interest_by_region(
        self,
        keywords: List[str],
        timeframe: str = "today 3-m",
        geo: str = "",
        category: int = 0
    ) -> pd.DataFrame:
        """Get interest by geographic region.

        Args:
            keywords: List of keywords
            timeframe: Time range
            geo: Geographic location code
            category: Category code

        Returns:
            DataFrame with regional interest data
        """
        try:
            def _fetch():
                pytrends = self._get_pytrends()
                pytrends.build_payload(
                    keywords,
                    cat=category,
                    timeframe=timeframe,
                    geo=geo
                )
                return pytrends.interest_by_region()

            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, _fetch)

            logger.info(f"Fetched regional interest for {len(keywords)} keywords")
            return df

        except Exception as e:
            logger.error(f"Error fetching interest by region: {e}")
            return pd.DataFrame()

    async def get_trending_searches(self, country: str = "united_states") -> List[str]:
        """Get current trending searches for a country.

        Args:
            country: Country name (lowercase with underscores)

        Returns:
            List of trending search terms
        """
        try:
            def _fetch():
                pytrends = self._get_pytrends()
                return pytrends.trending_searches(pn=country)

            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, _fetch)

            trending = df[0].tolist() if not df.empty else []
            logger.info(f"Fetched {len(trending)} trending searches for {country}")
            return trending

        except Exception as e:
            logger.error(f"Error fetching trending searches: {e}")
            return []

"""High-level Google Trends data collector."""

import asyncio
from typing import List
from datetime import datetime
import logging
import pandas as pd

from connectors.pytrends.client import PyTrendsClient
from connectors.pytrends.models import (
    PyTrendsClientConfig,
    PyTrendsCollectSpec,
    PyTrendsResult,
    TrendData,
    RelatedQuery,
)

logger = logging.getLogger(__name__)


class PyTrendsCollector:
    """High-level Google Trends data collector.

    Public API for collecting Google Trends data according to a specification.

    Error handling strategy:
    - Main data (interest_over_time) failure -> returns status='failed'
    - Optional data (related_queries, regional) failure -> logs warning, continues
    - This ensures pytrends instability won't break calling applications
    """

    def __init__(self, config: PyTrendsClientConfig):
        """Initialize Google Trends collector.

        Args:
            config: PyTrends client configuration
        """
        self.config = config

    async def fetch(self, spec: PyTrendsCollectSpec) -> PyTrendsResult:
        """Fetch Google Trends data according to specification.

        Args:
            spec: Collection specification (keywords, timeframe, etc.)

        Returns:
            PyTrendsResult object with trend data and status
            - status='success' if main data collected successfully
            - status='failed' if main data collection failed
            - Optional data failures are logged but don't affect status

        Example:
            ```python
            config = PyTrendsClientConfig(
                timeout=30,
                retries=3
            )
            spec = PyTrendsCollectSpec(
                keywords=["bitcoin", "ethereum"],
                timeframe="today 3-m",
                geo="US",
                include_related_queries=True
            )
            collector = PyTrendsCollector(config)
            result = await collector.fetch(spec)
            if result.status == "success":
                # Process data
                pass
            else:
                # Handle failure gracefully
                logger.warning(f"PyTrends failed: {result.error}")
            ```
        """
        result = PyTrendsResult(
            keywords=spec.keywords,
            timeframe=spec.timeframe,
            geo=spec.geo,
            collected_at=datetime.now(),
        )

        client = PyTrendsClient(self.config)

        # CRITICAL: Get interest over time (main data)
        # If this fails, the whole operation fails
        try:
            logger.info(
                f"Fetching interest over time for keywords: {', '.join(spec.keywords)}"
            )
            df_interest = await client.get_interest_over_time(
                keywords=spec.keywords,
                timeframe=spec.timeframe,
                geo=spec.geo,
                category=spec.category,
            )

            # Convert DataFrame to TrendData objects
            if not df_interest.empty:
                # Remove 'isPartial' column if it exists
                is_partial_col = df_interest.get("isPartial")
                if "isPartial" in df_interest.columns:
                    df_interest = df_interest.drop("isPartial", axis=1)

                # Process each row
                for date_idx, row in df_interest.iterrows():
                    for keyword in spec.keywords:
                        if keyword in row:
                            trend_data = TrendData(
                                keyword=keyword,
                                date=pd.to_datetime(date_idx),
                                interest=int(row[keyword]),
                                is_partial=(
                                    bool(is_partial_col.iloc[-1])
                                    if is_partial_col is not None
                                    and date_idx == df_interest.index[-1]
                                    else False
                                ),
                            )
                            result.interest_over_time.append(trend_data)

                logger.info(
                    f"Collected {len(result.interest_over_time)} trend data points"
                )
            else:
                logger.warning("No interest over time data returned (empty DataFrame)")

        except Exception as e:
            # CRITICAL FAILURE - can't proceed without main data
            logger.error(f"Failed to fetch interest over time: {e}")
            result.status = "failed"
            result.error = f"Failed to fetch interest over time: {e}"
            return result

        # OPTIONAL: Get related queries if requested
        # Failures here are logged but don't affect overall status
        if spec.include_related_queries:
            try:
                logger.info("Fetching related queries")
                related = await client.get_related_queries(
                    keywords=spec.keywords,
                    timeframe=spec.timeframe,
                    geo=spec.geo,
                    category=spec.category,
                )

                # Process related queries
                for keyword in spec.keywords:
                    if keyword in related:
                        keyword_data = related[keyword]

                        # Top queries
                        if "top" in keyword_data and isinstance(
                            keyword_data["top"], pd.DataFrame
                        ):
                            top_df = keyword_data["top"]
                            if not top_df.empty:
                                result.related_queries_top[keyword] = [
                                    RelatedQuery(
                                        query=str(row["query"]), value=int(row["value"])
                                    )
                                    for _, row in top_df.iterrows()
                                ]

                        # Rising queries
                        if "rising" in keyword_data and isinstance(
                            keyword_data["rising"], pd.DataFrame
                        ):
                            rising_df = keyword_data["rising"]
                            if not rising_df.empty:
                                result.related_queries_rising[keyword] = [
                                    RelatedQuery(
                                        query=str(row["query"]),
                                        value=(
                                            int(row["value"])
                                            if row["value"] != "Breakout"
                                            else None
                                        ),
                                    )
                                    for _, row in rising_df.iterrows()
                                ]

                logger.info(
                    f"Collected related queries for {len(result.related_queries_top)} keywords"
                )

            except Exception as e:
                # NON-CRITICAL - log and continue
                logger.warning(f"Failed to fetch related queries (skipped): {e}")

        # OPTIONAL: Get interest by region if requested
        # Failures here are logged but don't affect overall status
        if spec.include_interest_by_region:
            try:
                logger.info("Fetching interest by region")
                df_region = await client.get_interest_by_region(
                    keywords=spec.keywords,
                    timeframe=spec.timeframe,
                    geo=spec.geo,
                    category=spec.category,
                )

                # Convert to dict format
                if not df_region.empty:
                    for keyword in spec.keywords:
                        if keyword in df_region.columns:
                            region_data = df_region[keyword].to_dict()
                            result.interest_by_region[keyword] = {
                                str(k): int(v) for k, v in region_data.items() if v > 0
                            }

                logger.info(
                    f"Collected regional data for {len(result.interest_by_region)} keywords"
                )

            except Exception as e:
                # NON-CRITICAL - log and continue
                logger.warning(f"Failed to fetch interest by region (skipped): {e}")

        result.status = "success"
        logger.info(
            f"Successfully collected Google Trends data for {len(spec.keywords)} keywords"
        )

        return result

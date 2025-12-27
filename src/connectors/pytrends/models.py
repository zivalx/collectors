"""Pydantic models for Google Trends (pytrends) connector."""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from connectors.common.config import BaseClientConfig, BaseCollectSpec


class PyTrendsClientConfig(BaseClientConfig):
    """Google Trends client settings.

    No credentials required - pytrends is free and doesn't need API keys.
    """
    timeout: int = Field(default=30, description="Request timeout in seconds")
    retries: int = Field(default=3, description="Number of retries on failure")
    backoff_factor: float = Field(
        default=0.5,
        description="Backoff multiplier for retries"
    )


class PyTrendsCollectSpec(BaseCollectSpec):
    """Specification for Google Trends data collection.

    Describes WHAT trends to collect on each run.
    """
    keywords: List[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="Keywords to track (max 5 per request)"
    )
    timeframe: str = Field(
        default="today 3-m",
        description="Time range: 'now 1-H', 'now 4-H', 'now 1-d', 'today 1-m', 'today 3-m', 'today 12-m', 'today 5-y', 'all', or 'YYYY-MM-DD YYYY-MM-DD'"
    )
    geo: str = Field(
        default="",
        description="Geographic location (e.g., 'US', 'GB', '' for worldwide)"
    )
    category: int = Field(
        default=0,
        description="Category code (0 for all categories)"
    )
    include_related_queries: bool = Field(
        default=True,
        description="Include related queries and topics"
    )
    include_interest_by_region: bool = Field(
        default=False,
        description="Include interest breakdown by region"
    )


class TrendData(BaseModel):
    """Google Trends interest over time data point."""
    keyword: str = Field(..., description="Search keyword")
    date: datetime = Field(..., description="Date of measurement")
    interest: int = Field(..., description="Interest value (0-100)")
    is_partial: bool = Field(
        default=False,
        description="Whether data is partial (still collecting)"
    )


class RelatedQuery(BaseModel):
    """Related search query."""
    query: str = Field(..., description="Related query text")
    value: int = Field(..., description="Search interest value")


class PyTrendsResult(BaseModel):
    """Complete Google Trends collection result."""
    keywords: List[str] = Field(..., description="Searched keywords")
    timeframe: str = Field(..., description="Time range used")
    geo: str = Field(..., description="Geographic region")

    # Interest over time
    interest_over_time: List[TrendData] = Field(
        default_factory=list,
        description="Interest over time data points"
    )

    # Related queries (top and rising)
    related_queries_top: dict = Field(
        default_factory=dict,
        description="Top related queries by keyword"
    )
    related_queries_rising: dict = Field(
        default_factory=dict,
        description="Rising related queries by keyword"
    )

    # Interest by region
    interest_by_region: dict = Field(
        default_factory=dict,
        description="Interest breakdown by geographic region"
    )

    # Metadata
    collected_at: datetime = Field(
        default_factory=datetime.now,
        description="When data was collected"
    )
    status: str = Field(default="success", description="Collection status")
    error: Optional[str] = Field(default=None, description="Error message if failed")

    class Config:
        frozen = False

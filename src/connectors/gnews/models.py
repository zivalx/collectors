"""Pydantic models for GNews API connector."""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime
from connectors.common.config import BaseClientConfig, BaseCollectSpec


class GNewsClientConfig(BaseClientConfig):
    """GNews API credentials and client settings.

    Get your API key from: https://gnews.io/
    Free tier: 100 requests per day
    """

    api_key: str = Field(..., description="GNews API key")
    timeout: int = Field(default=30, description="Request timeout in seconds")


class GNewsCollectSpec(BaseCollectSpec):
    """Specification for GNews API data collection (runtime input).

    Describes WHAT to collect on each run.
    Passed as argument to collector.fetch().
    """

    query: str = Field(
        ..., min_length=1, description="Search query (keywords, phrases, boolean operators)"
    )
    language: Optional[str] = Field(
        default="en",
        description="Language code (en, es, fr, de, it, pt, ru, zh, ja, ko, etc.)",
    )
    country: Optional[str] = Field(
        default=None,
        description="Country code (us, gb, ca, au, de, fr, etc.)",
    )
    category: Optional[str] = Field(
        default=None,
        description="News category (general, world, nation, business, technology, entertainment, sports, science, health)",
    )
    from_date: Optional[datetime] = Field(
        default=None, description="Start date for articles (ISO 8601 format)"
    )
    to_date: Optional[datetime] = Field(
        default=None, description="End date for articles (ISO 8601 format)"
    )
    sort_by: str = Field(
        default="publishedAt",
        description="Sort order: publishedAt (newest first) or relevance",
    )
    max_results: int = Field(
        default=10, ge=1, le=100, description="Maximum articles to fetch (max 100)"
    )

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: Optional[str]) -> Optional[str]:
        """Validate language code."""
        if v is None:
            return v
        allowed = ["en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja", "ko", "ar", "hi"]
        if v not in allowed:
            raise ValueError(f"language must be one of {allowed}")
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        """Validate category."""
        if v is None:
            return v
        allowed = [
            "general",
            "world",
            "nation",
            "business",
            "technology",
            "entertainment",
            "sports",
            "science",
            "health",
        ]
        if v not in allowed:
            raise ValueError(f"category must be one of {allowed}")
        return v

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v: str) -> str:
        """Validate sort_by value."""
        allowed = ["publishedAt", "relevance"]
        if v not in allowed:
            raise ValueError(f"sort_by must be one of {allowed}")
        return v


class GNewsArticle(BaseModel):
    """GNews article data model.

    Represents a single news article from GNews API.
    """

    title: str = Field(..., description="Article title")
    description: str = Field(..., description="Article description/summary")
    content: str = Field(..., description="Article content (may be truncated)")
    url: str = Field(..., description="Article URL")
    image: Optional[str] = Field(default=None, description="Article image URL")
    published_at: datetime = Field(..., description="Publication timestamp")
    source_name: str = Field(..., description="News source name")
    source_url: str = Field(..., description="News source homepage URL")
    collected_at: datetime = Field(
        default_factory=datetime.now, description="When article was collected"
    )

    class Config:
        frozen = False


class GNewsResult(BaseModel):
    """GNews API collection result.

    Wraps list of articles with metadata and status.
    """

    articles: List[GNewsArticle] = Field(
        default_factory=list, description="List of news articles"
    )
    total_articles: int = Field(
        default=0, description="Total articles returned (not total available)"
    )
    query: str = Field(..., description="Search query used")
    language: Optional[str] = Field(default=None, description="Language filter")
    country: Optional[str] = Field(default=None, description="Country filter")
    category: Optional[str] = Field(default=None, description="Category filter")
    collected_at: datetime = Field(
        default_factory=datetime.now, description="Collection timestamp"
    )
    status: str = Field(default="success", description="Collection status")
    error: Optional[str] = Field(default=None, description="Error message if failed")

    class Config:
        frozen = False

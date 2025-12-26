"""Pydantic models for Twitter connector."""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from connectors.common.config import BaseClientConfig, BaseCollectSpec


class TwitterClientConfig(BaseClientConfig):
    """Twitter API v2 credentials and client settings.

    Requires a Twitter API v2 Bearer Token.
    """
    bearer_token: str = Field(..., description="Twitter API v2 Bearer Token")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    rate_limit: int = Field(
        default=15,
        description="Requests per 15-minute window (Twitter API v2 limit)"
    )


class TwitterCollectSpec(BaseCollectSpec):
    """Specification for Twitter data collection.

    Uses Twitter API v2 /tweets/search/recent endpoint.
    """
    query: str = Field(..., description="Twitter search query")
    max_results: int = Field(
        default=10,
        ge=10,
        le=100,
        description="Max tweets per request (10-100, API limit)"
    )
    start_time: Optional[datetime] = Field(
        default=None,
        description="Start time for search (UTC)"
    )
    end_time: Optional[datetime] = Field(
        default=None,
        description="End time for search (UTC)"
    )

    @field_validator('max_results')
    @classmethod
    def validate_max_results(cls, v: int) -> int:
        """Validate max_results is within Twitter API limits."""
        if not 10 <= v <= 100:
            raise ValueError('max_results must be between 10 and 100')
        return v


class Tweet(BaseModel):
    """Twitter tweet data model.

    Represents a single tweet with metadata and engagement metrics.
    """
    id: str = Field(..., description="Tweet ID")
    text: str = Field(..., description="Tweet text content")
    author_id: str = Field(..., description="Tweet author user ID")
    created_at: datetime = Field(..., description="Tweet creation timestamp (UTC)")

    # Optional engagement metrics (requires tweet.fields=public_metrics)
    like_count: Optional[int] = Field(
        default=None,
        description="Number of likes"
    )
    retweet_count: Optional[int] = Field(
        default=None,
        description="Number of retweets"
    )
    reply_count: Optional[int] = Field(
        default=None,
        description="Number of replies"
    )
    quote_count: Optional[int] = Field(
        default=None,
        description="Number of quote tweets"
    )

    class Config:
        frozen = False

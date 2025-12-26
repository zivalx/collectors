"""Base configuration classes for all connectors."""

from pydantic import BaseModel, Field
from typing import Optional


class BaseClientConfig(BaseModel):
    """Base configuration for all API clients.

    Contains credentials and HTTP settings only.
    Does NOT contain collection targets (subreddits, channels, etc.)
    """
    timeout: int = Field(default=30, description="Request timeout in seconds")
    rate_limit: Optional[int] = Field(
        default=None,
        description="Max requests per minute (None = no limit)"
    )

    class Config:
        frozen = True  # Immutable configs for thread safety


class BaseCollectSpec(BaseModel):
    """Base specification for data collection.

    Contains runtime collection parameters (what to collect).
    Passed to collector.fetch() method.
    """
    max_results: Optional[int] = Field(
        default=None,
        description="Maximum items to collect (None = no limit)"
    )

    class Config:
        frozen = False  # Mutable at runtime

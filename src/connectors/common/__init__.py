"""Common utilities and base classes for all connectors."""

from connectors.common.config import BaseClientConfig, BaseCollectSpec
from connectors.common.exceptions import (
    ConnectorError,
    AuthenticationError,
    RateLimitError,
    InvalidConfigError,
    DataFetchError,
)
from connectors.common.http import with_retry, RateLimiter

__all__ = [
    # Config
    'BaseClientConfig',
    'BaseCollectSpec',
    # Exceptions
    'ConnectorError',
    'AuthenticationError',
    'RateLimitError',
    'InvalidConfigError',
    'DataFetchError',
    # HTTP utilities
    'with_retry',
    'RateLimiter',
]

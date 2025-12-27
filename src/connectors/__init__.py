"""Connectors - Framework-agnostic data collectors for Reddit, Telegram, YouTube, Twitter, Google Trends, and GNews."""

__version__ = "0.1.0"

# Import common utilities so they're available at package level
from connectors.common import (
    BaseClientConfig,
    BaseCollectSpec,
    ConnectorError,
    AuthenticationError,
    RateLimitError,
    InvalidConfigError,
    DataFetchError,
)
from connectors.common.logging_config import setup_logging, disable_logging

__all__ = [
    '__version__',
    # Common exports
    'BaseClientConfig',
    'BaseCollectSpec',
    'ConnectorError',
    'AuthenticationError',
    'RateLimitError',
    'InvalidConfigError',
    'DataFetchError',
    # Logging
    'setup_logging',
    'disable_logging',
]

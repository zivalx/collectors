"""Logging configuration for connectors library.

Provides sensible defaults for library logging that calling applications can use.
"""

import logging
import sys
from typing import Optional


def setup_logging(
    level: str = "INFO",
    format_string: Optional[str] = None,
    include_timestamp: bool = True,
) -> None:
    """Configure logging for the connectors library.

    This is a convenience function for applications using this library.
    You can also configure logging yourself using standard Python logging.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Custom format string (uses default if None)
        include_timestamp: Whether to include timestamps in logs

    Example:
        ```python
        from connectors.common.logging_config import setup_logging

        # Simple setup
        setup_logging(level="DEBUG")

        # Custom format
        setup_logging(
            level="INFO",
            format_string="%(name)s - %(levelname)s - %(message)s"
        )
        ```
    """
    if format_string is None:
        if include_timestamp:
            format_string = (
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        else:
            format_string = "%(name)s - %(levelname)s - %(message)s"

    # Configure root logger for connectors namespace
    logger = logging.getLogger("connectors")
    logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Add console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper()))
    handler.setFormatter(logging.Formatter(format_string))
    logger.addHandler(handler)

    # Prevent propagation to root logger to avoid duplicate messages
    logger.propagate = False


def disable_logging() -> None:
    """Disable all logging from the connectors library.

    Useful for production environments where you only want errors.
    """
    logging.getLogger("connectors").setLevel(logging.CRITICAL + 1)


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module.

    Args:
        name: Module name (usually __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)

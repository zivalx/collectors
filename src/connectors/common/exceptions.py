"""Common exception classes for all connectors."""


class ConnectorError(Exception):
    """Base exception for all connector errors."""
    pass


class AuthenticationError(ConnectorError):
    """Authentication failed."""
    pass


class RateLimitError(ConnectorError):
    """Rate limit exceeded."""
    pass


class InvalidConfigError(ConnectorError):
    """Invalid configuration provided."""
    pass


class DataFetchError(ConnectorError):
    """Failed to fetch data from source."""
    pass

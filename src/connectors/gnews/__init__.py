"""GNews API data connector."""

from connectors.gnews.collector import GNewsCollector
from connectors.gnews.models import (
    GNewsClientConfig,
    GNewsCollectSpec,
    GNewsArticle,
    GNewsResult,
)

__all__ = [
    'GNewsCollector',
    'GNewsClientConfig',
    'GNewsCollectSpec',
    'GNewsArticle',
    'GNewsResult',
]

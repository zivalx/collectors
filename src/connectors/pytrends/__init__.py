"""Google Trends data connector."""

from connectors.pytrends.collector import PyTrendsCollector
from connectors.pytrends.models import (
    PyTrendsClientConfig,
    PyTrendsCollectSpec,
    PyTrendsResult,
    TrendData,
    RelatedQuery,
)

__all__ = [
    'PyTrendsCollector',
    'PyTrendsClientConfig',
    'PyTrendsCollectSpec',
    'PyTrendsResult',
    'TrendData',
    'RelatedQuery',
]

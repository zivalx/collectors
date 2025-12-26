"""Reddit data connector."""

from connectors.reddit.collector import RedditCollector
from connectors.reddit.models import (
    RedditClientConfig,
    RedditCollectSpec,
    RedditPost,
)

__all__ = [
    'RedditCollector',
    'RedditClientConfig',
    'RedditCollectSpec',
    'RedditPost',
]

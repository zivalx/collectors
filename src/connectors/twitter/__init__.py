"""Twitter data connector."""

from connectors.twitter.collector import TwitterCollector
from connectors.twitter.models import (
    TwitterClientConfig,
    TwitterCollectSpec,
    Tweet,
)

__all__ = [
    'TwitterCollector',
    'TwitterClientConfig',
    'TwitterCollectSpec',
    'Tweet',
]

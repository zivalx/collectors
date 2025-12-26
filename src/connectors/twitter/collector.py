"""High-level Twitter data collector."""

from typing import List
from datetime import datetime
import logging

from connectors.twitter.client import TwitterClient
from connectors.twitter.models import (
    TwitterClientConfig,
    TwitterCollectSpec,
    Tweet,
)

logger = logging.getLogger(__name__)


class TwitterCollector:
    """High-level Twitter data collector.

    Public API for collecting Twitter data according to a specification.
    """

    def __init__(self, config: TwitterClientConfig):
        """Initialize Twitter collector.

        Args:
            config: Twitter client configuration with bearer token
        """
        self.config = config

    async def fetch(self, spec: TwitterCollectSpec) -> List[Tweet]:
        """Fetch tweets according to specification.

        Enhanced from trender/app/services/twitter_collector.py lines 22-32.

        Args:
            spec: Collection specification (query, max results, time range)

        Returns:
            List of Tweet objects with typed fields

        Example:
            ```python
            config = TwitterClientConfig(
                bearer_token="..."
            )
            spec = TwitterCollectSpec(
                query="python OR programming",
                max_results=100
            )
            collector = TwitterCollector(config)
            tweets = await collector.fetch(spec)
            ```
        """
        tweets = []

        async with TwitterClient(self.config) as client:
            response = await client.search_recent(
                query=spec.query,
                max_results=spec.max_results,
                start_time=spec.start_time,
                end_time=spec.end_time,
            )

            # Process tweets from API response
            for tweet_data in response.get("data", []):
                metrics = tweet_data.get("public_metrics", {})

                # Parse timestamp
                created_at_str = tweet_data["created_at"]
                # Twitter returns ISO format with 'Z' suffix
                created_at = datetime.fromisoformat(
                    created_at_str.replace("Z", "+00:00")
                )

                tweet = Tweet(
                    id=tweet_data["id"],
                    text=tweet_data["text"],
                    author_id=tweet_data["author_id"],
                    created_at=created_at,
                    like_count=metrics.get("like_count"),
                    retweet_count=metrics.get("retweet_count"),
                    reply_count=metrics.get("reply_count"),
                    quote_count=metrics.get("quote_count"),
                )
                tweets.append(tweet)

        logger.info(f"Collected {len(tweets)} tweets for query: {spec.query}")
        return tweets

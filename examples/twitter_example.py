"""Twitter connector example.

Shows how to search for tweets using Twitter API v2.
"""

import asyncio
import os
from datetime import datetime, timedelta
from connectors.twitter import (
    TwitterCollector,
    TwitterClientConfig,
    TwitterCollectSpec,
)


async def main():
    # Configuration (bearer token from environment)
    config = TwitterClientConfig(
        bearer_token=os.environ.get("TWITTER_BEARER_TOKEN", "your_bearer_token"),
        rate_limit=15,  # Twitter API v2: 15 requests per 15-minute window
    )

    # Collection specification - search for Python-related tweets
    spec = TwitterCollectSpec(
        query="python programming -is:retweet",  # Exclude retweets
        max_results=50,  # 10-100 per request
        start_time=datetime.now() - timedelta(hours=24),  # Last 24 hours
    )

    # Collect data
    print(f"Searching Twitter for: {spec.query}")
    collector = TwitterCollector(config)
    tweets = await collector.fetch(spec)

    # Display results
    print(f"\n✓ Collected {len(tweets)} tweets\n")

    for tweet in tweets[:5]:  # Show first 5 tweets
        print(f"Tweet ID: {tweet.id}")
        print(f"  Author: {tweet.author_id}")
        print(f"  Text: {tweet.text[:100]}...")
        print(f"  Created: {tweet.created_at}")
        if tweet.like_count is not None:
            print(
                f"  Engagement: {tweet.like_count} likes, "
                f"{tweet.retweet_count} retweets, "
                f"{tweet.reply_count} replies"
            )
        print()


if __name__ == "__main__":
    asyncio.run(main())

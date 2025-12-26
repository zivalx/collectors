"""Tests for Twitter connector."""

import pytest
from datetime import datetime, timedelta
from connectors.twitter import (
    TwitterCollector,
    TwitterClientConfig,
    TwitterCollectSpec,
    Tweet,
)


class TestTwitterClientConfig:
    """Test Twitter client configuration."""

    def test_valid_config(self, twitter_bearer_token):
        """Test creating valid Twitter client config."""
        config = TwitterClientConfig(
            bearer_token=twitter_bearer_token,
        )
        assert config.bearer_token == twitter_bearer_token
        assert config.timeout == 30
        assert config.rate_limit == 15

    def test_custom_settings(self, twitter_bearer_token):
        """Test custom timeout and rate limit."""
        config = TwitterClientConfig(
            bearer_token=twitter_bearer_token,
            timeout=60,
            rate_limit=10,
        )
        assert config.timeout == 60
        assert config.rate_limit == 10


class TestTwitterCollectSpec:
    """Test Twitter collection specification."""

    def test_valid_spec(self):
        """Test creating valid collect spec."""
        spec = TwitterCollectSpec(
            query="python programming",
            max_results=50,
        )
        assert spec.query == "python programming"
        assert spec.max_results == 50

    def test_with_time_range(self):
        """Test spec with time range."""
        start = datetime.now() - timedelta(days=7)
        end = datetime.now() - timedelta(days=1)

        spec = TwitterCollectSpec(
            query="machine learning",
            max_results=100,
            start_time=start,
            end_time=end,
        )
        assert spec.start_time == start
        assert spec.end_time == end

    def test_max_results_validation(self):
        """Test that max_results is validated."""
        # Valid values
        spec = TwitterCollectSpec(query="test", max_results=10)
        assert spec.max_results == 10

        spec = TwitterCollectSpec(query="test", max_results=100)
        assert spec.max_results == 100

        # Invalid values
        with pytest.raises(ValueError):
            TwitterCollectSpec(query="test", max_results=5)  # Too low

        with pytest.raises(ValueError):
            TwitterCollectSpec(query="test", max_results=101)  # Too high

    def test_defaults(self):
        """Test default values."""
        spec = TwitterCollectSpec(query="test")
        assert spec.max_results == 10
        assert spec.start_time is None
        assert spec.end_time is None


@pytest.mark.asyncio
class TestTwitterCollector:
    """Test Twitter collector (integration tests with real API)."""

    async def test_fetch_tweets_basic(self, twitter_bearer_token):
        """Test fetching tweets with basic query."""
        config = TwitterClientConfig(
            bearer_token=twitter_bearer_token,
        )

        spec = TwitterCollectSpec(
            query="python",
            max_results=10,
        )

        collector = TwitterCollector(config)
        tweets = await collector.fetch(spec)

        assert len(tweets) > 0
        assert len(tweets) <= 10

        for tweet in tweets:
            assert isinstance(tweet, Tweet)
            assert tweet.id
            assert tweet.text
            assert tweet.author_id
            assert tweet.created_at
            assert isinstance(tweet.created_at, datetime)

    async def test_fetch_tweets_with_filters(self, twitter_bearer_token):
        """Test fetching tweets with query filters."""
        config = TwitterClientConfig(
            bearer_token=twitter_bearer_token,
        )

        # Search for tweets about Python, excluding retweets
        spec = TwitterCollectSpec(
            query="python programming -is:retweet",
            max_results=20,
        )

        collector = TwitterCollector(config)
        tweets = await collector.fetch(spec)

        assert len(tweets) > 0
        assert len(tweets) <= 20

        for tweet in tweets:
            assert tweet.text
            # Verify no retweet indicators
            assert not tweet.text.startswith("RT @")

    async def test_fetch_tweets_with_time_range(self, twitter_bearer_token):
        """Test fetching tweets within a time range."""
        config = TwitterClientConfig(
            bearer_token=twitter_bearer_token,
        )

        # Last 24 hours
        start_time = datetime.now() - timedelta(hours=24)

        spec = TwitterCollectSpec(
            query="technology",
            max_results=15,
            start_time=start_time,
        )

        collector = TwitterCollector(config)
        tweets = await collector.fetch(spec)

        assert len(tweets) > 0

        for tweet in tweets:
            # All tweets should be after start_time
            assert tweet.created_at >= start_time.replace(tzinfo=tweet.created_at.tzinfo)

    async def test_tweet_engagement_metrics(self, twitter_bearer_token):
        """Test that engagement metrics are present."""
        config = TwitterClientConfig(
            bearer_token=twitter_bearer_token,
        )

        spec = TwitterCollectSpec(
            query="python",
            max_results=10,
        )

        collector = TwitterCollector(config)
        tweets = await collector.fetch(spec)

        assert len(tweets) > 0

        for tweet in tweets:
            # Check that engagement metrics exist (can be None or int)
            assert isinstance(tweet.like_count, (int, type(None)))
            assert isinstance(tweet.retweet_count, (int, type(None)))
            assert isinstance(tweet.reply_count, (int, type(None)))
            assert isinstance(tweet.quote_count, (int, type(None)))

    async def test_fetch_different_max_results(self, twitter_bearer_token):
        """Test fetching different amounts of tweets."""
        config = TwitterClientConfig(
            bearer_token=twitter_bearer_token,
        )

        # Test minimum
        spec_min = TwitterCollectSpec(query="test", max_results=10)
        collector = TwitterCollector(config)
        tweets_min = await collector.fetch(spec_min)
        assert len(tweets_min) <= 10

        # Test maximum
        spec_max = TwitterCollectSpec(query="test", max_results=100)
        tweets_max = await collector.fetch(spec_max)
        assert len(tweets_max) <= 100

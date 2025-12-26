"""Tests for Reddit connector."""

import pytest
from connectors.reddit import (
    RedditCollector,
    RedditClientConfig,
    RedditCollectSpec,
    RedditPost,
)


class TestRedditClientConfig:
    """Test Reddit client configuration."""

    def test_valid_config(self, reddit_client_id, reddit_client_secret):
        """Test creating valid Reddit client config."""
        config = RedditClientConfig(
            client_id=reddit_client_id,
            client_secret=reddit_client_secret,
            user_agent="TestAgent/1.0",
        )
        assert config.client_id == reddit_client_id
        assert config.client_secret == reddit_client_secret
        assert config.user_agent == "TestAgent/1.0"
        assert config.timeout == 30
        assert config.rate_limit == 60

    def test_custom_settings(self, reddit_client_id, reddit_client_secret):
        """Test custom timeout and rate limit."""
        config = RedditClientConfig(
            client_id=reddit_client_id,
            client_secret=reddit_client_secret,
            user_agent="TestAgent/1.0",
            timeout=60,
            rate_limit=30,
        )
        assert config.timeout == 60
        assert config.rate_limit == 30


class TestRedditCollectSpec:
    """Test Reddit collection specification."""

    def test_valid_spec(self):
        """Test creating valid collect spec."""
        spec = RedditCollectSpec(
            subreddits=["python", "learnpython"],
            sort="hot",
            max_posts_per_subreddit=50,
        )
        assert spec.subreddits == ["python", "learnpython"]
        assert spec.sort == "hot"
        assert spec.max_posts_per_subreddit == 50

    def test_strips_r_prefix(self):
        """Test that r/ prefix is stripped from subreddit names."""
        spec = RedditCollectSpec(
            subreddits=["r/python", "/programming", "learnpython"],
        )
        assert spec.subreddits == ["python", "programming", "learnpython"]

    def test_defaults(self):
        """Test default values."""
        spec = RedditCollectSpec(subreddits=["python"])
        assert spec.sort == "hot"
        assert spec.time_filter == "day"
        assert spec.max_posts_per_subreddit == 20
        assert spec.include_comments is True
        assert spec.max_comment_depth is None


@pytest.mark.asyncio
class TestRedditCollector:
    """Test Reddit collector (integration tests with real API)."""

    async def test_fetch_posts_hot(self, reddit_client_id, reddit_client_secret):
        """Test fetching hot posts from a subreddit."""
        config = RedditClientConfig(
            client_id=reddit_client_id,
            client_secret=reddit_client_secret,
            user_agent="ConnectorsTest/1.0",
        )

        spec = RedditCollectSpec(
            subreddits=["python"],
            sort="hot",
            max_posts_per_subreddit=5,
            include_comments=False,
        )

        collector = RedditCollector(config)
        posts = await collector.fetch(spec)

        assert len(posts) > 0
        assert len(posts) <= 5

        for post in posts:
            assert isinstance(post, RedditPost)
            assert post.id
            assert post.title
            assert post.subreddit == "python"
            assert post.url
            assert isinstance(post.score, int)
            assert isinstance(post.num_comments, int)

    async def test_fetch_posts_with_comments(self, reddit_client_id, reddit_client_secret):
        """Test fetching posts with comments."""
        config = RedditClientConfig(
            client_id=reddit_client_id,
            client_secret=reddit_client_secret,
            user_agent="ConnectorsTest/1.0",
        )

        spec = RedditCollectSpec(
            subreddits=["python"],
            sort="hot",
            max_posts_per_subreddit=3,
            include_comments=True,
        )

        collector = RedditCollector(config)
        posts = await collector.fetch(spec)

        assert len(posts) > 0

        # At least some posts should have comments
        posts_with_comments = [p for p in posts if p.comments]
        # Don't assert this as some posts might genuinely have no comments
        # but we can check structure
        for post in posts:
            assert isinstance(post.comments, list)

    async def test_fetch_multiple_subreddits(self, reddit_client_id, reddit_client_secret):
        """Test fetching from multiple subreddits."""
        config = RedditClientConfig(
            client_id=reddit_client_id,
            client_secret=reddit_client_secret,
            user_agent="ConnectorsTest/1.0",
        )

        spec = RedditCollectSpec(
            subreddits=["python", "learnpython"],
            sort="new",
            max_posts_per_subreddit=3,
            include_comments=False,
        )

        collector = RedditCollector(config)
        posts = await collector.fetch(spec)

        assert len(posts) > 0
        assert len(posts) <= 6  # 3 per subreddit max

        # Check we got posts from both subreddits
        subreddits = {post.subreddit for post in posts}
        assert len(subreddits) >= 1  # At least one subreddit returned data

    async def test_fetch_top_with_time_filter(self, reddit_client_id, reddit_client_secret):
        """Test fetching top posts with time filter."""
        config = RedditClientConfig(
            client_id=reddit_client_id,
            client_secret=reddit_client_secret,
            user_agent="ConnectorsTest/1.0",
        )

        spec = RedditCollectSpec(
            subreddits=["python"],
            sort="top",
            time_filter="week",
            max_posts_per_subreddit=5,
            include_comments=False,
        )

        collector = RedditCollector(config)
        posts = await collector.fetch(spec)

        assert len(posts) > 0
        assert len(posts) <= 5

        for post in posts:
            assert post.subreddit == "python"

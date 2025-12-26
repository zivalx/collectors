"""Integration tests for all connectors.

This module tests all connectors together to ensure they work correctly
and can be used in a unified workflow.
"""

import pytest
from datetime import datetime, timedelta

from connectors.reddit import (
    RedditCollector,
    RedditClientConfig,
    RedditCollectSpec,
)
from connectors.youtube import (
    YouTubeCollector,
    YouTubeClientConfig,
    YouTubeCollectSpec,
)
from connectors.telegram import (
    TelegramCollector,
    TelegramClientConfig,
    TelegramCollectSpec,
)
from connectors.twitter import (
    TwitterCollector,
    TwitterClientConfig,
    TwitterCollectSpec,
)


@pytest.mark.asyncio
class TestAllConnectors:
    """Test all connectors in a single test suite."""

    async def test_all_connectors_independently(
        self,
        reddit_client_id,
        reddit_client_secret,
        telegram_api_id,
        telegram_api_hash,
        telegram_phone,
        twitter_bearer_token,
    ):
        """Test that all connectors can be initialized and used."""
        results = {}

        # Test Reddit
        try:
            reddit_config = RedditClientConfig(
                client_id=reddit_client_id,
                client_secret=reddit_client_secret,
                user_agent="IntegrationTest/1.0",
            )
            reddit_spec = RedditCollectSpec(
                subreddits=["python"],
                max_posts_per_subreddit=2,
                include_comments=False,
            )
            reddit_collector = RedditCollector(reddit_config)
            reddit_posts = await reddit_collector.fetch(reddit_spec)
            results["reddit"] = {"status": "success", "count": len(reddit_posts)}
            assert len(reddit_posts) > 0
        except Exception as e:
            results["reddit"] = {"status": "failed", "error": str(e)}

        # Test YouTube
        try:
            youtube_config = YouTubeClientConfig(
                use_transcript_api=True,
            )
            youtube_spec = YouTubeCollectSpec(
                urls=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
            )
            youtube_collector = YouTubeCollector(youtube_config)
            youtube_videos = await youtube_collector.fetch(youtube_spec)
            results["youtube"] = {"status": "success", "count": len(youtube_videos)}
            assert len(youtube_videos) > 0
        except Exception as e:
            results["youtube"] = {"status": "failed", "error": str(e)}

        # Test Telegram
        try:
            async def get_code():
                code = input("Enter Telegram code: ")
                return code

            async def get_password():
                return ""

            telegram_config = TelegramClientConfig(
                api_id=telegram_api_id,
                api_hash=telegram_api_hash,
                phone=telegram_phone,
                session_name="integration_test_session",
                auth_code_callback=get_code,
                auth_password_callback=get_password,
            )
            telegram_spec = TelegramCollectSpec(
                channels=["telegram"],
                max_messages_per_channel=2,
                include_replies=False,
            )
            telegram_collector = TelegramCollector(telegram_config)
            telegram_messages = await telegram_collector.fetch(telegram_spec)
            results["telegram"] = {"status": "success", "count": len(telegram_messages)}
            assert len(telegram_messages) > 0
        except Exception as e:
            results["telegram"] = {"status": "failed", "error": str(e)}

        # Test Twitter
        try:
            twitter_config = TwitterClientConfig(
                bearer_token=twitter_bearer_token,
            )
            twitter_spec = TwitterCollectSpec(
                query="python",
                max_results=10,
            )
            twitter_collector = TwitterCollector(twitter_config)
            twitter_tweets = await twitter_collector.fetch(twitter_spec)
            results["twitter"] = {"status": "success", "count": len(twitter_tweets)}
            assert len(twitter_tweets) > 0
        except Exception as e:
            results["twitter"] = {"status": "failed", "error": str(e)}

        # Print summary
        print("\n" + "=" * 60)
        print("INTEGRATION TEST SUMMARY")
        print("=" * 60)
        for connector, result in results.items():
            status = result.get("status", "unknown")
            if status == "success":
                count = result.get("count", 0)
                print(f"✓ {connector.upper()}: SUCCESS ({count} items collected)")
            else:
                error = result.get("error", "Unknown error")
                print(f"✗ {connector.upper()}: FAILED - {error}")
        print("=" * 60 + "\n")

        # At least some connectors should succeed
        successful = [k for k, v in results.items() if v.get("status") == "success"]
        assert len(successful) > 0, "At least one connector should succeed"

    async def test_all_connectors_sequential(self, skip_if_no_credentials):
        """Test running all connectors sequentially in a workflow."""
        import os

        collected_data = {
            "reddit": [],
            "youtube": [],
            "telegram": [],
            "twitter": [],
        }

        # 1. Collect Reddit posts
        reddit_config = RedditClientConfig(
            client_id=os.environ["REDDIT_CLIENT_ID"],
            client_secret=os.environ["REDDIT_CLIENT_SECRET"],
            user_agent="IntegrationTest/1.0",
        )
        reddit_spec = RedditCollectSpec(
            subreddits=["python"],
            max_posts_per_subreddit=3,
            include_comments=False,
        )
        reddit_collector = RedditCollector(reddit_config)
        collected_data["reddit"] = await reddit_collector.fetch(reddit_spec)

        # 2. Collect YouTube videos
        youtube_config = YouTubeClientConfig()
        youtube_spec = YouTubeCollectSpec(
            channels=["@TED"],
            max_videos_per_channel=2,
            days_back=30,
        )
        youtube_collector = YouTubeCollector(youtube_config)
        collected_data["youtube"] = await youtube_collector.fetch(youtube_spec)

        # 3. Collect Telegram messages
        async def get_code():
            code = input("Enter Telegram code: ")
            return code

        async def get_password():
            return os.environ.get("TELEGRAM_2FA_PASSWORD", "")

        telegram_config = TelegramClientConfig(
            api_id=os.environ["TELEGRAM_API_ID"],
            api_hash=os.environ["TELEGRAM_API_HASH"],
            phone=os.environ["TELEGRAM_PHONE"],
            session_name="integration_test_session",
            auth_code_callback=get_code,
            auth_password_callback=get_password,
        )
        telegram_spec = TelegramCollectSpec(
            channels=["telegram"],
            max_messages_per_channel=2,
            include_replies=False,
        )
        telegram_collector = TelegramCollector(telegram_config)
        collected_data["telegram"] = await telegram_collector.fetch(telegram_spec)

        # 4. Collect Twitter tweets
        twitter_config = TwitterClientConfig(
            bearer_token=os.environ["TWITTER_BEARER_TOKEN"],
        )
        twitter_spec = TwitterCollectSpec(
            query="python programming -is:retweet",
            max_results=10,
        )
        twitter_collector = TwitterCollector(twitter_config)
        collected_data["twitter"] = await twitter_collector.fetch(twitter_spec)

        # Verify all data was collected
        assert len(collected_data["reddit"]) > 0
        assert len(collected_data["youtube"]) > 0
        assert len(collected_data["telegram"]) > 0
        assert len(collected_data["twitter"]) > 0

        # Print summary
        total_items = sum(len(data) for data in collected_data.values())
        print(f"\n✓ Successfully collected {total_items} total items:")
        print(f"  - Reddit: {len(collected_data['reddit'])} posts")
        print(f"  - YouTube: {len(collected_data['youtube'])} videos")
        print(f"  - Telegram: {len(collected_data['telegram'])} messages")
        print(f"  - Twitter: {len(collected_data['twitter'])} tweets\n")

        return collected_data


@pytest.mark.asyncio
class TestConnectorCompatibility:
    """Test that all connectors follow the same patterns and are compatible."""

    async def test_all_configs_immutable(
        self,
        reddit_client_id,
        reddit_client_secret,
        telegram_api_id,
        telegram_api_hash,
        twitter_bearer_token,
    ):
        """Test that all client configs are immutable (frozen)."""
        # Reddit config should be frozen
        reddit_config = RedditClientConfig(
            client_id=reddit_client_id,
            client_secret=reddit_client_secret,
            user_agent="Test/1.0",
        )
        with pytest.raises(Exception):  # Pydantic ValidationError
            reddit_config.client_id = "different_id"

        # Twitter config should be frozen
        twitter_config = TwitterClientConfig(bearer_token=twitter_bearer_token)
        with pytest.raises(Exception):
            twitter_config.bearer_token = "different_token"

        # YouTube config should be frozen
        youtube_config = YouTubeClientConfig()
        with pytest.raises(Exception):
            youtube_config.whisper_model = "different_model"

    def test_all_specs_follow_pattern(self):
        """Test that all collect specs follow the same pattern."""
        # All specs should be instantiable with minimal params
        reddit_spec = RedditCollectSpec(subreddits=["python"])
        assert reddit_spec.subreddits == ["python"]

        youtube_spec = YouTubeCollectSpec(
            urls=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
        )
        assert youtube_spec.urls is not None

        telegram_spec = TelegramCollectSpec(channels=["telegram"])
        assert telegram_spec.channels == ["telegram"]

        twitter_spec = TwitterCollectSpec(query="test")
        assert twitter_spec.query == "test"

    async def test_all_collectors_have_fetch_method(
        self,
        reddit_client_id,
        reddit_client_secret,
        telegram_api_id,
        telegram_api_hash,
        telegram_phone,
        twitter_bearer_token,
    ):
        """Test that all collectors have a fetch() method with correct signature."""
        # Reddit
        reddit_config = RedditClientConfig(
            client_id=reddit_client_id,
            client_secret=reddit_client_secret,
            user_agent="Test/1.0",
        )
        reddit_collector = RedditCollector(reddit_config)
        assert hasattr(reddit_collector, "fetch")
        assert callable(reddit_collector.fetch)

        # YouTube
        youtube_config = YouTubeClientConfig()
        youtube_collector = YouTubeCollector(youtube_config)
        assert hasattr(youtube_collector, "fetch")
        assert callable(youtube_collector.fetch)

        # Telegram
        async def get_code():
            return "12345"

        telegram_config = TelegramClientConfig(
            api_id=telegram_api_id,
            api_hash=telegram_api_hash,
            phone=telegram_phone,
            auth_code_callback=get_code,
        )
        telegram_collector = TelegramCollector(telegram_config)
        assert hasattr(telegram_collector, "fetch")
        assert callable(telegram_collector.fetch)

        # Twitter
        twitter_config = TwitterClientConfig(bearer_token=twitter_bearer_token)
        twitter_collector = TwitterCollector(twitter_config)
        assert hasattr(twitter_collector, "fetch")
        assert callable(twitter_collector.fetch)

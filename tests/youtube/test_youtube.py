"""Tests for YouTube connector."""

import pytest
from connectors.youtube import (
    YouTubeCollector,
    YouTubeClientConfig,
    YouTubeCollectSpec,
    YouTubeVideo,
)


class TestYouTubeClientConfig:
    """Test YouTube client configuration."""

    def test_valid_config_defaults(self):
        """Test creating valid YouTube client config with defaults."""
        config = YouTubeClientConfig()
        assert config.whisper_model == "base"
        assert config.max_video_length == 3600
        assert config.audio_format == "m4a"
        assert config.use_transcript_api is True
        assert config.compute_type == "int8"
        assert config.timeout == 60

    def test_custom_config(self):
        """Test custom YouTube configuration."""
        config = YouTubeClientConfig(
            whisper_model="small",
            max_video_length=1800,
            audio_format="webm",
            use_transcript_api=False,
        )
        assert config.whisper_model == "small"
        assert config.max_video_length == 1800
        assert config.audio_format == "webm"
        assert config.use_transcript_api is False


class TestYouTubeCollectSpec:
    """Test YouTube collection specification."""

    def test_spec_with_urls(self):
        """Test spec with direct URLs."""
        spec = YouTubeCollectSpec(
            urls=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
        )
        assert spec.urls == ["https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
        assert spec.channels is None

    def test_spec_with_channels(self):
        """Test spec with channels."""
        spec = YouTubeCollectSpec(
            channels=["@Veritasium", "@VSauce"],
            max_videos_per_channel=10,
            days_back=14,
        )
        assert spec.channels == ["@Veritasium", "@VSauce"]
        assert spec.max_videos_per_channel == 10
        assert spec.days_back == 14

    def test_spec_requires_urls_or_channels(self):
        """Test that spec requires either urls or channels."""
        with pytest.raises(ValueError, match="Either urls or channels must be provided"):
            YouTubeCollectSpec()

    def test_spec_defaults(self):
        """Test default values for channel-based collection."""
        spec = YouTubeCollectSpec(channels=["@TestChannel"])
        assert spec.max_videos_per_channel == 5
        assert spec.days_back == 7


@pytest.mark.asyncio
class TestYouTubeCollector:
    """Test YouTube collector (integration tests)."""

    async def test_fetch_from_url_with_transcript_api(self):
        """Test fetching a single video using transcript API."""
        config = YouTubeClientConfig(
            use_transcript_api=True,
            whisper_model="base",
        )

        # Using a well-known video that should have captions
        spec = YouTubeCollectSpec(
            urls=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
        )

        collector = YouTubeCollector(config)
        videos = await collector.fetch(spec)

        assert len(videos) == 1
        video = videos[0]

        assert isinstance(video, YouTubeVideo)
        assert video.video_id == "dQw4w9WgXcQ"
        assert video.title
        assert video.channel
        assert video.duration > 0
        assert video.transcript
        # Should use transcript API if available
        assert video.transcript_source in ["youtube_api", "whisper"]
        assert video.status == "success"

    async def test_fetch_from_channels(self):
        """Test fetching videos from a channel."""
        config = YouTubeClientConfig(
            use_transcript_api=True,
            max_video_length=3600,
        )

        # Using a popular channel that regularly uploads
        spec = YouTubeCollectSpec(
            channels=["@TED"],
            max_videos_per_channel=2,
            days_back=30,
        )

        collector = YouTubeCollector(config)
        videos = await collector.fetch(spec)

        assert len(videos) > 0
        assert len(videos) <= 2

        for video in videos:
            assert isinstance(video, YouTubeVideo)
            assert video.title
            assert video.channel
            assert video.transcript
            assert video.video_id
            assert video.url

    async def test_fetch_multiple_urls(self):
        """Test fetching multiple videos from URLs."""
        config = YouTubeClientConfig(
            use_transcript_api=True,
        )

        spec = YouTubeCollectSpec(
            urls=[
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "https://www.youtube.com/watch?v=9bZkp7q19f0",  # PSY - Gangnam Style
            ],
        )

        collector = YouTubeCollector(config)
        videos = await collector.fetch(spec)

        assert len(videos) == 2

        for video in videos:
            assert video.status == "success"
            assert video.transcript
            assert video.duration > 0

    async def test_video_metadata_fields(self):
        """Test that all expected metadata fields are populated."""
        config = YouTubeClientConfig()

        spec = YouTubeCollectSpec(
            urls=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
        )

        collector = YouTubeCollector(config)
        videos = await collector.fetch(spec)

        assert len(videos) == 1
        video = videos[0]

        # Check all required fields are present
        assert video.video_id
        assert video.url
        assert video.title
        assert isinstance(video.description, str)
        assert video.duration > 0
        assert video.channel
        assert video.channel_id
        assert isinstance(video.view_count, int)
        assert isinstance(video.like_count, int)
        assert isinstance(video.tags, list)
        assert isinstance(video.categories, list)
        assert video.transcript
        assert video.transcript_source in ["youtube_api", "whisper"]
        assert video.processed_at
        assert video.status == "success"

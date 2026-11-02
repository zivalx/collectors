"""Tests for YouTube connector."""

import builtins
import sys

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from youtube_transcript_api._transcripts import FetchedTranscriptSnippet
from connectors.youtube import (
    YouTubeCollector,
    YouTubeClientConfig,
    YouTubeCollectSpec,
    YouTubeVideo,
)
from connectors.youtube.client import YouTubeClient
from connectors.youtube.models import published_at_from
from connectors.common.exceptions import DataFetchError


class TestPublishedAtFrom:
    """Epoch publish timestamp -> ISO-8601 UTC string."""

    def test_published_at_from_epoch(self):
        assert published_at_from(1786795200) == "2026-08-15T12:00:00Z"

    def test_published_at_from_float_epoch(self):
        assert published_at_from(1786795200.0) == "2026-08-15T12:00:00Z"

    def test_published_at_from_missing(self):
        assert published_at_from(None) is None

    @pytest.mark.parametrize("bad", [10**20, float("nan"), float("inf"), "soon", [1]])
    def test_published_at_from_unconvertible_returns_none(self, bad):
        assert published_at_from(bad) is None


class TestGetVideoMetadataTimestamp:
    """get_video_metadata picks the public-availability time for published_at."""

    @staticmethod
    async def _metadata_for(info):
        client = YouTubeClient(YouTubeClientConfig())
        ydl = MagicMock()
        ydl.__enter__.return_value.extract_info.return_value = info
        with patch("connectors.youtube.client.yt_dlp.YoutubeDL", return_value=ydl):
            return await client.get_video_metadata("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    @pytest.mark.asyncio
    async def test_prefers_release_timestamp_over_timestamp(self):
        # Premiere: uploaded earlier than it went public.
        meta = await self._metadata_for({"timestamp": 1786700000, "release_timestamp": 1786795200})
        assert meta["timestamp"] == 1786795200

    @pytest.mark.asyncio
    async def test_falls_back_to_timestamp(self):
        meta = await self._metadata_for({"timestamp": 1786795200})
        assert meta["timestamp"] == 1786795200


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


class FakeWhisperSegment:
    """Stand-in for faster_whisper's Segment (has .start / .text attrs)."""

    def __init__(self, text: str, start: float):
        self.text = text
        self.start = start


class TestGetTranscriptSegments:
    """Unit tests proving get_transcript retains per-segment timestamps.

    All external calls (YouTube Transcript API, Whisper) are mocked --
    no network access and no model downloads.
    """

    @pytest.mark.asyncio
    async def test_transcript_api_path_retains_segments_object_snippets(self):
        """youtube_transcript_api path: FetchedTranscriptSnippet objects."""
        config = YouTubeClientConfig(use_transcript_api=True)
        client = YouTubeClient(config)

        snippets = [
            FetchedTranscriptSnippet(text="Hello world", start=0.0, duration=2.5),
            FetchedTranscriptSnippet(text="second segment", start=5.5, duration=3.0),
        ]

        mock_transcript = MagicMock()
        mock_transcript.is_generated = False
        mock_transcript.language_code = "en"
        mock_transcript.fetch.return_value = snippets

        mock_transcript_list = MagicMock()
        mock_transcript_list.__iter__.return_value = iter([mock_transcript])

        mock_api_instance = MagicMock()
        mock_api_instance.list.return_value = mock_transcript_list

        with patch(
            "connectors.youtube.client.YouTubeTranscriptApi",
            return_value=mock_api_instance,
        ):
            text, source, segments = await client.get_transcript("abc123")

        assert source == "youtube_api"
        # Flat transcript string is unchanged: still the space-joined text
        assert text == "Hello world second segment"
        assert segments == [
            {"start": 0.0, "text": "Hello world"},
            {"start": 5.5, "text": "second segment"},
        ]

    @pytest.mark.asyncio
    async def test_transcript_api_path_retains_segments_dict_snippets(self):
        """youtube_transcript_api path: legacy dict-shaped snippets."""
        config = YouTubeClientConfig(use_transcript_api=True)
        client = YouTubeClient(config)

        snippets = [
            {"text": "Hello world", "start": 0.0, "duration": 2.5},
            {"text": "second segment", "start": 5.5, "duration": 3.0},
        ]

        mock_transcript = MagicMock()
        mock_transcript.is_generated = False
        mock_transcript.language_code = "en"
        mock_transcript.fetch.return_value = snippets

        mock_transcript_list = MagicMock()
        mock_transcript_list.__iter__.return_value = iter([mock_transcript])

        mock_api_instance = MagicMock()
        mock_api_instance.list.return_value = mock_transcript_list

        with patch(
            "connectors.youtube.client.YouTubeTranscriptApi",
            return_value=mock_api_instance,
        ):
            text, source, segments = await client.get_transcript("abc123")

        assert source == "youtube_api"
        assert text == "Hello world second segment"
        assert segments == [
            {"start": 0.0, "text": "Hello world"},
            {"start": 5.5, "text": "second segment"},
        ]

    @pytest.mark.asyncio
    async def test_whisper_path_retains_segments(self):
        """Whisper fallback path: segments carry .start / .text."""
        config = YouTubeClientConfig(use_transcript_api=False)
        client = YouTubeClient(config)

        fake_segments = [
            FakeWhisperSegment(" Hello world ", 0.0),
            FakeWhisperSegment(" second segment ", 5.5),
        ]
        fake_info = MagicMock(language="en", language_probability=0.98)

        # _whisper_model was "initialized" against the stub faster_whisper
        # module in conftest.py; replace its transcribe() with a mock.
        client._whisper_model = MagicMock()
        client._whisper_model.transcribe.return_value = (fake_segments, fake_info)

        with patch.object(
            client, "_download_audio", new=AsyncMock(return_value="/tmp/fake_audio.m4a")
        ):
            text, source, segments = await client.get_transcript("abc123")

        assert source == "whisper"
        # Flat transcript string is unchanged: still space-joined, stripped text
        assert text == "Hello world second segment"
        assert segments == [
            {"start": 0.0, "text": "Hello world"},
            {"start": 5.5, "text": "second segment"},
        ]

    @pytest.mark.asyncio
    async def test_whisper_path_used_when_api_disabled(self):
        """When use_transcript_api is False, Whisper is used directly (no API call)."""
        config = YouTubeClientConfig(use_transcript_api=False)
        client = YouTubeClient(config)

        client._whisper_model = MagicMock()
        client._whisper_model.transcribe.return_value = (
            [FakeWhisperSegment("only segment", 1.0)],
            MagicMock(language="en", language_probability=0.9),
        )

        with patch.object(
            client, "_download_audio", new=AsyncMock(return_value="/tmp/fake_audio.m4a")
        ):
            text, source, segments = await client.get_transcript("abc123")

        assert source == "whisper"
        assert segments == [{"start": 1.0, "text": "only segment"}]


class TestCollectorPopulatesTranscriptSegments:
    """Prove YouTubeCollector plumbs segments from client into YouTubeVideo."""

    @pytest.mark.asyncio
    async def test_process_video_sets_transcript_segments(self):
        config = YouTubeClientConfig(use_transcript_api=True)
        collector = YouTubeCollector(config)

        fake_metadata = {
            "title": "Test Video",
            "description": "",
            "duration": 120,
            "view_count": 0,
            "like_count": 0,
            "channel": "Chan",
            "channel_id": "c1",
            "upload_date": "20260101",
            "tags": [],
            "categories": [],
            "thumbnail": "",
        }
        fake_segments = [{"start": 0.0, "text": "hi"}, {"start": 2.0, "text": "there"}]

        collector.client.get_video_metadata = AsyncMock(return_value=fake_metadata)
        collector.client.get_transcript = AsyncMock(
            return_value=("hi there", "youtube_api", fake_segments)
        )

        spec = YouTubeCollectSpec(urls=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"])
        videos = await collector.fetch(spec)

        assert len(videos) == 1
        video = videos[0]
        assert video.status == "success"
        # Flat transcript string still produced, unchanged
        assert video.transcript == "hi there"
        assert video.transcript_source == "youtube_api"
        # New: per-segment timestamps retained for deep-linking
        assert video.transcript_segments == fake_segments

    @pytest.mark.asyncio
    async def test_process_video_sets_published_at_from_epoch(self):
        config = YouTubeClientConfig(use_transcript_api=True)
        collector = YouTubeCollector(config)

        fake_metadata = {
            "title": "Test Video",
            "description": "",
            "duration": 120,
            "view_count": 0,
            "like_count": 0,
            "channel": "Chan",
            "channel_id": "c1",
            "upload_date": "20260815",
            "timestamp": 1786795200,
            "tags": [],
            "categories": [],
            "thumbnail": "",
        }

        collector.client.get_video_metadata = AsyncMock(return_value=fake_metadata)
        collector.client.get_transcript = AsyncMock(
            return_value=("hi there", "youtube_api", [])
        )

        spec = YouTubeCollectSpec(urls=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"])
        videos = await collector.fetch(spec)

        assert len(videos) == 1
        video = videos[0]
        assert video.status == "success"
        assert video.published_at == "2026-08-15T12:00:00Z"
        # Existing date field unchanged
        assert video.upload_date == "20260815"


class TestFasterWhisperOptional:
    """faster-whisper is an OPTIONAL extra (pyproject.toml [youtube]/[all]).

    Importing the connector and constructing a client/collector must never
    require it -- only actually transcribing with Whisper does. These tests
    simulate faster-whisper being ABSENT (as it genuinely is in this venv;
    conftest.py only injects a fake module for the *other* tests) and prove
    nothing raises at import/construction time.
    """

    @staticmethod
    def _block_faster_whisper_import(monkeypatch):
        """Make `from faster_whisper import ...` raise ImportError everywhere,
        regardless of whether a fake module happens to be sitting in
        sys.modules (injected by conftest.py for the rest of the suite)."""
        monkeypatch.delitem(sys.modules, "faster_whisper", raising=False)
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "faster_whisper" or name.startswith("faster_whisper."):
                raise ImportError("No module named 'faster_whisper'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)

    def test_module_import_succeeds_without_faster_whisper(self, monkeypatch):
        """connectors.youtube (and .client) must import cleanly with no
        faster-whisper on the system -- the import must not be top-level."""
        self._block_faster_whisper_import(monkeypatch)

        import connectors.youtube  # noqa: F401
        import connectors.youtube.client  # noqa: F401

    def test_client_construction_succeeds_without_faster_whisper(self, monkeypatch):
        """Constructing YouTubeClient/YouTubeCollector must not raise when
        faster-whisper is missing; Whisper fallback is disabled instead."""
        self._block_faster_whisper_import(monkeypatch)

        config = YouTubeClientConfig(whisper_model="base")

        client = YouTubeClient(config)
        assert client._whisper_model is None

        collector = YouTubeCollector(config)
        assert collector.client._whisper_model is None

    @pytest.mark.asyncio
    async def test_whisper_fallback_raises_clean_error_when_unavailable(
        self, monkeypatch
    ):
        """A caption-less video with no Whisper model must fail with a clear
        DataFetchError, not an AttributeError on None.transcribe(...)."""
        self._block_faster_whisper_import(monkeypatch)

        config = YouTubeClientConfig(whisper_model="base", use_transcript_api=False)
        client = YouTubeClient(config)
        assert client._whisper_model is None

        with pytest.raises(DataFetchError, match="faster-whisper not installed"):
            await client.get_transcript("dQw4w9WgXcQ")

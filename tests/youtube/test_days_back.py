"""days_back handling for the YouTube connector (mocks only, no network)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from connectors.youtube import (
    YouTubeClientConfig,
    YouTubeCollectSpec,
    YouTubeCollector,
)
from connectors.youtube.client import YouTubeClient
from connectors.youtube.utils import video_published_at

NOW = datetime.now(timezone.utc)


def _ts(days_ago: float) -> int:
    return int((NOW - timedelta(days=days_ago)).timestamp())


def _vid(n: int) -> str:
    return f"https://www.youtube.com/watch?v={n:011d}"


def _metadata(**over):
    md = {
        "title": "t", "description": "", "duration": 60, "view_count": 0,
        "like_count": 0, "channel": "C", "channel_id": "c", "upload_date": "",
        "timestamp": None, "tags": [], "categories": [], "thumbnail": "",
    }
    md.update(over)
    return md


class TestVideoPublishedAt:
    def test_epoch_is_utc_aware(self):
        dt = video_published_at({"timestamp": 1_700_000_000})
        assert dt == datetime(2023, 11, 14, 22, 13, 20, tzinfo=timezone.utc)
        assert dt.utcoffset() == timedelta(0)

    def test_release_timestamp_preferred(self):
        dt = video_published_at({"release_timestamp": 1_700_000_000, "timestamp": 1_600_000_000})
        assert dt.year == 2023

    def test_upload_date_is_end_of_that_utc_day(self):
        dt = video_published_at({"upload_date": "20260101"})
        assert dt == datetime(2026, 1, 1, 23, 59, 59, tzinfo=timezone.utc)

    def test_bad_values_give_none(self):
        assert video_published_at({"timestamp": 10**20, "upload_date": "garbage"}) is None
        assert video_published_at({}) is None


class FakeYDL:
    """Stands in for yt_dlp.YoutubeDL; entries is a lazy generator like lazy_playlist."""

    pulled = 0
    entries_src: list = []
    opts: dict = {}

    def __init__(self, opts):
        FakeYDL.opts = opts

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def extract_info(self, url, download=False):
        def gen():
            for e in FakeYDL.entries_src:
                FakeYDL.pulled += 1
                yield e
        return {"entries": gen()}


@pytest.fixture
def client():
    return YouTubeClient(YouTubeClientConfig(whisper_model=""))


class TestGetChannelVideos:
    @pytest.fixture(autouse=True)
    def _reset(self):
        FakeYDL.pulled = 0

    async def test_stops_paging_at_first_dated_entry_older_than_cutoff(self, client):
        FakeYDL.entries_src = (
            [{"id": f"{i:011d}", "timestamp": _ts(1 + i)} for i in range(3)]
            + [{"id": f"{i:011d}", "timestamp": _ts(30)} for i in range(3, 50)]
        )
        with patch("connectors.youtube.client.yt_dlp.YoutubeDL", FakeYDL):
            urls = await client.get_channel_videos("@x", max_videos=20, days_back=7)
        assert urls == [_vid(0), _vid(1), _vid(2)]
        assert FakeYDL.pulled <= 4  # did not page through the whole channel

    async def test_max_videos_is_upper_bound(self, client):
        FakeYDL.entries_src = [{"id": f"{i:011d}", "timestamp": _ts(0.1)} for i in range(10)]
        with patch("connectors.youtube.client.yt_dlp.YoutubeDL", FakeYDL):
            urls = await client.get_channel_videos("@x", max_videos=4, days_back=7)
        assert len(urls) == 4
        assert FakeYDL.pulled <= 5

    async def test_undated_entries_are_kept_for_the_metadata_check(self, client):
        FakeYDL.entries_src = [{"id": f"{i:011d}"} for i in range(3)]
        with patch("connectors.youtube.client.yt_dlp.YoutubeDL", FakeYDL):
            urls = await client.get_channel_videos("@x", max_videos=5, days_back=7)
        assert len(urls) == 3

    async def test_lazy_playlist_enabled(self, client):
        FakeYDL.entries_src = []
        with patch("connectors.youtube.client.yt_dlp.YoutubeDL", FakeYDL):
            await client.get_channel_videos("@x", max_videos=5, days_back=7)
        assert FakeYDL.opts.get("lazy_playlist") is True
        assert FakeYDL.opts.get("extract_flat") is True


def _collector(meta_by_url, channel_urls):
    collector = YouTubeCollector(YouTubeClientConfig(whisper_model=""))
    collector.client.get_channel_videos = AsyncMock(return_value=channel_urls)
    collector.client.get_video_metadata = AsyncMock(side_effect=lambda u: meta_by_url[u])
    collector.client.get_transcript = AsyncMock(return_value=("text", "youtube_api", []))
    return collector


class TestCollectorCutoff:
    async def test_old_channel_video_skipped_before_transcript(self):
        urls = [_vid(1), _vid(2)]
        meta = {
            urls[0]: _metadata(timestamp=_ts(1)),
            urls[1]: _metadata(timestamp=_ts(20)),
        }
        c = _collector(meta, urls)
        videos = await c.fetch(YouTubeCollectSpec(channels=["@x"], days_back=7))
        assert [v.url for v in videos] == [urls[0]]
        assert c.client.get_transcript.await_count == 1
        assert c.last_run_stats["skipped_out_of_window"] == 1
        assert c.last_run_stats["skipped_undated"] == 0

    async def test_published_at_is_utc_iso(self):
        urls = [_vid(1)]
        c = _collector({urls[0]: _metadata(timestamp=1_700_000_000 + 10**9)}, urls)
        spec = YouTubeCollectSpec(channels=["@x"], days_back=100000)
        videos = await c.fetch(spec)
        assert videos[0].published_at.endswith("Z")
        assert datetime.fromisoformat(videos[0].published_at.replace("Z", "+00:00")).utcoffset() == timedelta(0)

    async def test_undated_skipped_and_counted_by_default(self):
        urls = [_vid(1), _vid(2)]
        meta = {urls[0]: _metadata(), urls[1]: _metadata(timestamp=_ts(1))}
        c = _collector(meta, urls)
        videos = await c.fetch(YouTubeCollectSpec(channels=["@x"], days_back=7))
        assert [v.url for v in videos] == [urls[1]]
        assert c.last_run_stats["skipped_undated"] == 1
        assert c.client.get_transcript.await_count == 1

    async def test_undated_kept_when_asked(self):
        urls = [_vid(1)]
        c = _collector({urls[0]: _metadata()}, urls)
        spec = YouTubeCollectSpec(channels=["@x"], days_back=7, include_undated=True)
        videos = await c.fetch(spec)
        assert len(videos) == 1 and videos[0].status == "success"
        assert videos[0].published_at is None

    async def test_direct_urls_are_not_date_filtered(self):
        u = _vid(9)
        c = _collector({u: _metadata(timestamp=_ts(400))}, [])
        videos = await c.fetch(YouTubeCollectSpec(urls=[u], days_back=7))
        assert len(videos) == 1 and videos[0].status == "success"

    async def test_upload_date_only_is_used_when_no_timestamp(self):
        urls = [_vid(1), _vid(2)]
        today = NOW.strftime("%Y%m%d")
        old = (NOW - timedelta(days=40)).strftime("%Y%m%d")
        meta = {urls[0]: _metadata(upload_date=today), urls[1]: _metadata(upload_date=old)}
        c = _collector(meta, urls)
        videos = await c.fetch(YouTubeCollectSpec(channels=["@x"], days_back=7))
        assert [v.url for v in videos] == [urls[0]]

    async def test_spec_defaults_backward_compatible(self):
        spec = YouTubeCollectSpec(channels=["@x"])
        assert spec.include_undated is False and spec.days_back == 7


class TestStreakIgnoresUndated:
    async def test_undated_videos_do_not_trigger_channel_stop(self):
        urls = [_vid(i) for i in range(6)]
        meta = {u: _metadata() for u in urls[:4]}  # 4 undated first
        meta[urls[4]] = _metadata(timestamp=_ts(1))
        meta[urls[5]] = _metadata(timestamp=_ts(1))
        c = _collector(meta, urls)
        videos = await c.fetch(YouTubeCollectSpec(channels=["@x"], days_back=7))
        assert [v.url for v in videos] == urls[4:]
        assert c.last_run_stats["skipped_undated"] == 4

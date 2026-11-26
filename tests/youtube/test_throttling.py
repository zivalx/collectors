"""Throttling, skip-list, circuit-breaker and cookies tests (all network mocked)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from connectors.youtube import YouTubeClientConfig, YouTubeCollectSpec, YouTubeCollector
from connectors.youtube.client import YouTubeClient

IDS = [f"vid{i:08d}"[:11] for i in range(12)]  # 11-char ids
URLS = [f"https://www.youtube.com/watch?v={i}" for i in IDS]
META = dict(
    title="t", description="", duration=10, upload_date="20260101", timestamp=1786795200,
    view_count=1, like_count=1, channel="c", channel_id="cid", tags=[], categories=[], thumbnail="",
)


def make_collector(**cfg):
    col = YouTubeCollector(YouTubeClientConfig(**cfg))
    col.client.get_video_metadata = AsyncMock(return_value=META)
    col.client.get_transcript = AsyncMock(return_value=("hello", "youtube_api", []))
    return col


def test_config_validation():
    c = YouTubeClientConfig()
    assert (c.max_concurrency, c.delay_seconds, c.cookies_file) == (4, 0.0, None)
    with pytest.raises(ValueError):
        YouTubeClientConfig(max_concurrency=0)
    with pytest.raises(ValueError):
        YouTubeClientConfig(delay_seconds=-1)


@pytest.mark.asyncio
async def test_concurrency_never_exceeds_limit():
    col = make_collector(max_concurrency=3)
    active = peak = 0

    async def meta(url):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.01)
        active -= 1
        return META

    col.client.get_video_metadata = meta
    videos = await col.fetch(YouTubeCollectSpec(urls=URLS))
    assert peak == 3
    assert [v.video_id for v in videos] == IDS  # order preserved
    assert all(v.status == "success" for v in videos)


@pytest.mark.asyncio
async def test_delay_applied_before_each_video_and_between_channels():
    col = make_collector(delay_seconds=2.0, max_concurrency=1)
    col.client.get_channel_videos = AsyncMock(side_effect=[URLS[:1], URLS[1:2]])
    sleeps = []

    async def fake_sleep(d):
        sleeps.append(d)

    with patch("connectors.youtube.collector.asyncio.sleep", fake_sleep):
        await col.fetch(YouTubeCollectSpec(channels=["@a", "@b"]))
    # 1 between channels + 2 before videos
    assert len(sleeps) == 3
    assert all(1.0 <= d <= 3.0 for d in sleeps)


@pytest.mark.asyncio
async def test_no_sleep_when_delay_zero():
    col = make_collector()
    with patch("connectors.youtube.collector.asyncio.sleep", AsyncMock()) as s:
        await col.fetch(YouTubeCollectSpec(urls=URLS[:2]))
    s.assert_not_called()


@pytest.mark.asyncio
async def test_channels_listed_sequentially():
    col = make_collector()
    active = peak = 0

    async def listing(*a):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.01)
        active -= 1
        return []

    col.client.get_channel_videos = listing
    await col.fetch(YouTubeCollectSpec(channels=["@a", "@b", "@c"]))
    assert peak == 1


@pytest.mark.asyncio
async def test_skip_video_ids_prevents_fetches():
    col = make_collector()
    col.client.get_channel_videos = AsyncMock(return_value=URLS[:4])
    videos = await col.fetch(
        YouTubeCollectSpec(channels=["@a"], skip_video_ids=[IDS[0], IDS[2]], days_back=3650)
    )
    assert [v.video_id for v in videos] == [IDS[1], IDS[3]]
    fetched = [c.args[0] for c in col.client.get_video_metadata.call_args_list]
    assert URLS[0] not in fetched and URLS[2] not in fetched
    assert col.client.get_transcript.call_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("msg", [
    "Sign in to confirm you're not a bot", "IpBlocked", "RequestBlocked",
    "Too Many Requests", "HTTP Error 429: x",
])
async def test_block_circuit_breaker_stops_after_five(msg):
    col = make_collector(max_concurrency=1)
    col.client.get_video_metadata = AsyncMock(side_effect=Exception(msg))
    videos = await col.fetch(YouTubeCollectSpec(urls=URLS))
    assert col.client.get_video_metadata.call_count == 5
    assert len(videos) == len(URLS)
    assert all(v.status == "failed" for v in videos)
    assert [v.error for v in videos[5:]] == ["skipped: YouTube block detected"] * 7
    assert [v.video_id for v in videos] == IDS


@pytest.mark.asyncio
async def test_success_resets_block_counter():
    col = make_collector(max_concurrency=1)
    blocked = Exception("IpBlocked")
    # 4 blocks, success, 4 blocks, success, 2 more -> never trips
    seq = [blocked] * 4 + [META] + [blocked] * 4 + [META, META, META]
    col.client.get_video_metadata = AsyncMock(side_effect=seq)
    videos = await col.fetch(YouTubeCollectSpec(urls=URLS[:12]))
    assert col.client.get_video_metadata.call_count == 12
    assert not any(v.error == "skipped: YouTube block detected" for v in videos)


@pytest.mark.asyncio
async def test_non_block_failures_do_not_trip_breaker():
    col = make_collector(max_concurrency=1)
    col.client.get_video_metadata = AsyncMock(side_effect=Exception("Video unavailable"))
    await col.fetch(YouTubeCollectSpec(urls=URLS))
    assert col.client.get_video_metadata.call_count == len(URLS)


@pytest.mark.asyncio
async def test_cookies_file_reaches_ytdlp_options():
    client = YouTubeClient(YouTubeClientConfig(cookies_file="/tmp/c.txt"))
    seen = []

    def fake_ydl(opts):
        seen.append(opts)
        ydl = MagicMock()
        ydl.__enter__.return_value.extract_info.return_value = {"entries": [], "id": "x"}
        return ydl

    with patch("connectors.youtube.client.yt_dlp.YoutubeDL", side_effect=fake_ydl):
        await client.get_video_metadata("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        await client.get_channel_videos("@a", 2, 7)
        with patch("connectors.youtube.client.tempfile", MagicMock()):
            try:
                await client._download_audio("dQw4w9WgXcQ", "/tmp")
            except Exception:
                pass
    assert len(seen) >= 2
    assert all(o.get("cookiefile") == "/tmp/c.txt" for o in seen)


def test_no_cookiefile_by_default():
    client = YouTubeClient(YouTubeClientConfig())
    opts = {}
    client._apply_cookies(opts)
    assert "cookiefile" not in opts


def test_cookies_file_reaches_transcript_api(tmp_path):
    cookies = tmp_path / "c.txt"
    cookies.write_text("# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\tTRUE\t2000000000\tSID\tabc\n")
    client = YouTubeClient(YouTubeClientConfig(cookies_file=str(cookies)))
    api = client._make_transcript_api()
    assert api._fetcher._http_client.cookies._cookies[".youtube.com"]["/"]["SID"].value == "abc"

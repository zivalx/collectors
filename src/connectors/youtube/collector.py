"""High-level YouTube data collector."""

import asyncio
import random
import re
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone
import logging

from connectors.youtube.client import YouTubeClient
from connectors.youtube.models import (
    YouTubeClientConfig,
    YouTubeCollectSpec,
    YouTubeVideo,
    published_at_from,
)
from connectors.youtube.utils import (
    extract_video_id,
    validate_youtube_url,
    is_block_error,
    video_published_at,
)

logger = logging.getLogger(__name__)

BLOCK_THRESHOLD = 5
BLOCK_SKIP_ERROR = "skipped: YouTube block detected"
# A channel listing is newest first; after this many consecutive videos that are
# dated and older than days_back, the rest of that channel is not fetched at all.
# Undated videos never count towards the streak.
CUTOFF_STREAK = 3
_is_block_error = is_block_error


class YouTubeCollector:
    """High-level YouTube data collector.

    Uses asyncio.gather() for parallel processing (from Daigest).
    Supports both direct URLs and channel-based collection.
    """

    def __init__(self, config: YouTubeClientConfig):
        """Initialize YouTube collector.

        Args:
            config: YouTube client configuration
        """
        self.config = config
        self.client = YouTubeClient(config)
        self._old_urls: set = set()
        # Counts from the most recent fetch(): channel-listed videos not processed
        # because they fell outside days_back or had no publish date.
        self.last_run_stats: Dict[str, int] = {
            "skipped_out_of_window": 0,
            "skipped_undated": 0,
        }

    async def fetch(self, spec: YouTubeCollectSpec) -> List[YouTubeVideo]:
        """Fetch YouTube videos according to specification.

        Supports both direct URLs and channel-based collection.
        Uses parallel processing for efficiency.

        Args:
            spec: Collection specification (urls or channels)

        Returns:
            List of YouTubeVideo objects

        Example:
            ```python
            # From channels
            config = YouTubeClientConfig(
                whisper_model="base",
                use_transcript_api=True
            )
            spec = YouTubeCollectSpec(
                channels=["@Veritasium", "@VSauce"],
                max_videos_per_channel=5,
                days_back=7
            )
            collector = YouTubeCollector(config)
            videos = await collector.fetch(spec)

            # From URLs
            spec = YouTubeCollectSpec(
                urls=["https://youtube.com/watch?v=..."]
            )
            videos = await collector.fetch(spec)
            ```
        """
        all_urls = []
        self.last_run_stats = {"skipped_out_of_window": 0, "skipped_undated": 0}
        # Channel-listed URLs are limited to the last days_back days; direct URLs are not.
        channel_of: Dict[str, str] = {}
        channel_urls = set()
        self._old_urls = set()
        cutoff = datetime.now(timezone.utc) - timedelta(days=spec.days_back)

        # Collect URLs from direct list
        if spec.urls:
            valid_urls = [url for url in spec.urls if validate_youtube_url(url)]
            invalid_urls = [url for url in spec.urls if not validate_youtube_url(url)]

            if invalid_urls:
                logger.warning(f"Invalid URLs (skipped): {invalid_urls}")

            all_urls.extend(valid_urls)

        # Collect URLs from channels (sequential, with a pause between channels)
        if spec.channels:
            logger.info(f"Fetching from {len(spec.channels)} channels...")

            for idx, channel in enumerate(spec.channels):
                if idx > 0:
                    await self._pause()
                try:
                    urls = await self.client.get_channel_videos(
                        channel,
                        spec.max_videos_per_channel,
                        spec.days_back,
                    )
                    all_urls.extend(urls)
                    for u in urls:
                        channel_urls.add(u)
                        channel_of.setdefault(u, channel)
                except Exception as e:
                    logger.error(f"Error fetching channel {channel}: {e}")

        if spec.skip_video_ids:
            skip = set(spec.skip_video_ids)
            before = len(all_urls)
            all_urls = [u for u in all_urls if extract_video_id(u) not in skip]
            logger.info(f"Skipped {before - len(all_urls)} already-collected videos")

        # A URL passed explicitly is never date-filtered, even if also listed
        channel_urls.difference_update(spec.urls or [])

        if not all_urls:
            logger.warning("No valid URLs to process")
            return []

        logger.info(
            f"Processing {len(all_urls)} videos "
            f"(max_concurrency={self.config.max_concurrency})..."
        )

        semaphore = asyncio.Semaphore(self.config.max_concurrency)
        state: Dict[str, Any] = {"consecutive_blocks": 0, "blocked": False}
        old_streak: Dict[str, int] = {}

        def past_cutoff(url: str) -> bool:
            channel = channel_of.get(url) if url in channel_urls else None
            return channel is not None and old_streak.get(channel, 0) >= CUTOFF_STREAK

        async def run_one(url: str) -> Optional[YouTubeVideo]:
            async with semaphore:
                if past_cutoff(url):
                    return None
                if state["blocked"]:
                    return self._failed_video(url, None, BLOCK_SKIP_ERROR)
                await self._pause()
                if past_cutoff(url):
                    return None
                if state["blocked"]:
                    return self._failed_video(url, None, BLOCK_SKIP_ERROR)
                result = await self._process_video(
                    url,
                    cutoff=cutoff if url in channel_urls else None,
                    include_undated=spec.include_undated,
                )
                if url in channel_urls:
                    channel = channel_of.get(url)
                    if url in self._old_urls:
                        old_streak[channel] = old_streak.get(channel, 0) + 1
                        if old_streak[channel] == CUTOFF_STREAK:
                            logger.info(
                                f"Channel {channel}: reached videos older than "
                                f"{spec.days_back} days; skipping the rest"
                            )
                    else:
                        old_streak[channel] = 0
                if result is None:
                    return None
                if result.status == 'failed' and _is_block_error(result.error):
                    state["consecutive_blocks"] += 1
                    if state["consecutive_blocks"] >= BLOCK_THRESHOLD:
                        if not state["blocked"]:
                            logger.error(
                                f"{BLOCK_THRESHOLD} consecutive block errors; "
                                "stopping remaining fetches"
                            )
                        state["blocked"] = True
                else:
                    state["consecutive_blocks"] = 0
                return result

        results = await asyncio.gather(
            *[run_one(u) for u in all_urls], return_exceptions=True
        )

        # Convert any unhandled exceptions to failed video objects
        videos = []
        for i, result in enumerate(results):
            if result is None:
                continue  # outside days_back / undated: counted in last_run_stats
            if isinstance(result, YouTubeVideo):
                videos.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Unhandled error for {all_urls[i]}: {result}")
                videos.append(self._failed_video(all_urls[i], None, str(result)))

        # Log success/failure stats
        successful_count = sum(1 for v in videos if v.status == 'success')
        failed_count = len(videos) - successful_count

        logger.info(
            f"Processed {len(videos)} videos: "
            f"{successful_count} successful, {failed_count} failed "
            f"(skipped: {self.last_run_stats['skipped_out_of_window']} older than "
            f"{spec.days_back} days, {self.last_run_stats['skipped_undated']} undated)"
        )

        return videos

    async def _pause(self) -> None:
        """Randomized pause (uniform in [0.5x, 1.5x] of delay_seconds)."""
        delay = self.config.delay_seconds
        if delay > 0:
            await asyncio.sleep(random.uniform(0.5 * delay, 1.5 * delay))

    @staticmethod
    def _failed_video(url: str, video_id: Optional[str], error: str) -> YouTubeVideo:
        return YouTubeVideo(
            video_id=video_id or extract_video_id(url) or 'unknown',
            url=url,
            title='',
            description='',
            duration=0,
            upload_date=None,
            view_count=0,
            like_count=0,
            channel='',
            channel_id='',
            tags=[],
            categories=[],
            thumbnail='',
            transcript='',
            transcript_source='',
            processed_at=datetime.now(),
            status='failed',
            error=error,
        )

    async def _process_video(
        self,
        url: str,
        cutoff: Optional[datetime] = None,
        include_undated: bool = False,
    ) -> Optional[YouTubeVideo]:
        """Process a single video.

        Args:
            url: YouTube video URL

        Returns:
            YouTubeVideo object (status may be 'failed'), or None when the video
            was skipped because of ``cutoff`` (older, or undated and not
            ``include_undated``); nothing is downloaded for skipped videos
        """
        video_id = None
        try:
            video_id = extract_video_id(url)
            if not video_id:
                raise ValueError(f"Could not extract video ID from {url}")

            # Get metadata
            metadata = await self.client.get_video_metadata(url)

            # Look-back window: decided on metadata alone, before captions/audio
            if cutoff is not None:
                published = video_published_at(metadata)
                if published is None:
                    if not include_undated:
                        self.last_run_stats["skipped_undated"] += 1
                        logger.info(f"Skipping {url}: no publish date")
                        return None
                elif published < cutoff:
                    self.last_run_stats["skipped_out_of_window"] += 1
                    self._old_urls.add(url)
                    logger.info(f"Skipping {url}: published {published:%Y-%m-%d}, before cutoff")
                    return None

            # Check duration limit
            if metadata['duration'] > self.config.max_video_length:
                raise ValueError(
                    f"Video too long: {metadata['duration']}s "
                    f"(max: {self.config.max_video_length}s)"
                )

            # Get transcript (YouTube API → Whisper fallback)
            transcript, source, segments = await self.client.get_transcript(video_id)

            # Build successful result
            return YouTubeVideo(
                video_id=video_id,
                url=url,
                title=metadata['title'],
                description=metadata['description'],
                duration=metadata['duration'],
                upload_date=metadata['upload_date'],
                published_at=published_at_from(metadata.get('timestamp')),
                view_count=metadata['view_count'],
                like_count=metadata['like_count'],
                channel=metadata['channel'],
                channel_id=metadata['channel_id'],
                tags=metadata['tags'],
                categories=metadata['categories'],
                thumbnail=metadata['thumbnail'],
                transcript=transcript,
                transcript_source=source,
                transcript_segments=segments,
                processed_at=datetime.now(),
                status='success',
            )

        except Exception as e:
            logger.error(f"Error processing {url}: {e}")

            # Return failed result with error info
            return YouTubeVideo(
                video_id=video_id or 'unknown',
                url=url,
                title='',
                description='',
                duration=0,
                upload_date=None,
                view_count=0,
                like_count=0,
                channel='',
                channel_id='',
                tags=[],
                categories=[],
                thumbnail='',
                transcript='',
                transcript_source='',
                processed_at=datetime.now(),
                status='failed',
                error=str(e),
            )

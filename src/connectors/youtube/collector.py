"""High-level YouTube data collector."""

import asyncio
from typing import List
from datetime import datetime
import logging

from connectors.youtube.client import YouTubeClient
from connectors.youtube.models import (
    YouTubeClientConfig,
    YouTubeCollectSpec,
    YouTubeVideo,
)
from connectors.youtube.utils import extract_video_id, validate_youtube_url

logger = logging.getLogger(__name__)


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

        # Collect URLs from direct list
        if spec.urls:
            valid_urls = [url for url in spec.urls if validate_youtube_url(url)]
            invalid_urls = [url for url in spec.urls if not validate_youtube_url(url)]

            if invalid_urls:
                logger.warning(f"Invalid URLs (skipped): {invalid_urls}")

            all_urls.extend(valid_urls)

        # Collect URLs from channels (parallel with gather)
        if spec.channels:
            logger.info(f"Fetching from {len(spec.channels)} channels...")

            channel_tasks = [
                self.client.get_channel_videos(
                    channel,
                    spec.max_videos_per_channel,
                    spec.days_back,
                )
                for channel in spec.channels
            ]

            channel_results = await asyncio.gather(
                *channel_tasks, return_exceptions=True
            )

            for channel, result in zip(spec.channels, channel_results):
                if isinstance(result, Exception):
                    logger.error(f"Error fetching channel {channel}: {result}")
                else:
                    all_urls.extend(result)

        if not all_urls:
            logger.warning("No valid URLs to process")
            return []

        logger.info(f"Processing {len(all_urls)} videos in parallel...")

        # Process all videos in parallel (Daigest pattern)
        video_tasks = [self._process_video(url) for url in all_urls]
        results = await asyncio.gather(*video_tasks, return_exceptions=True)

        # Convert any unhandled exceptions to failed video objects
        videos = []
        for i, result in enumerate(results):
            if isinstance(result, YouTubeVideo):
                videos.append(result)
            elif isinstance(result, Exception):
                # Unhandled exception - create failed video object
                logger.error(f"Unhandled error for {all_urls[i]}: {result}")
                videos.append(YouTubeVideo(
                    video_id='unknown',
                    url=all_urls[i],
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
                    error=str(result),
                ))

        # Log success/failure stats
        successful_count = sum(1 for v in videos if v.status == 'success')
        failed_count = len(videos) - successful_count

        logger.info(
            f"Processed {len(all_urls)} videos: "
            f"{successful_count} successful, {failed_count} failed"
        )

        return videos

    async def _process_video(self, url: str) -> YouTubeVideo:
        """Process a single video.

        Args:
            url: YouTube video URL

        Returns:
            YouTubeVideo object (status may be 'failed')
        """
        video_id = None
        try:
            video_id = extract_video_id(url)
            if not video_id:
                raise ValueError(f"Could not extract video ID from {url}")

            # Get metadata
            metadata = await self.client.get_video_metadata(url)

            # Check duration limit
            if metadata['duration'] > self.config.max_video_length:
                raise ValueError(
                    f"Video too long: {metadata['duration']}s "
                    f"(max: {self.config.max_video_length}s)"
                )

            # Get transcript (YouTube API → Whisper fallback)
            transcript, source = await self.client.get_transcript(video_id)

            # Build successful result
            return YouTubeVideo(
                video_id=video_id,
                url=url,
                title=metadata['title'],
                description=metadata['description'],
                duration=metadata['duration'],
                upload_date=metadata['upload_date'],
                view_count=metadata['view_count'],
                like_count=metadata['like_count'],
                channel=metadata['channel'],
                channel_id=metadata['channel_id'],
                tags=metadata['tags'],
                categories=metadata['categories'],
                thumbnail=metadata['thumbnail'],
                transcript=transcript,
                transcript_source=source,
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

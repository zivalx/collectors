"""YouTube data connector."""

from connectors.youtube.collector import YouTubeCollector
from connectors.youtube.models import (
    YouTubeClientConfig,
    YouTubeCollectSpec,
    YouTubeVideo,
)
from connectors.youtube.utils import (
    validate_youtube_url,
    extract_video_id,
    clean_filename,
)

__all__ = [
    'YouTubeCollector',
    'YouTubeClientConfig',
    'YouTubeCollectSpec',
    'YouTubeVideo',
    'validate_youtube_url',
    'extract_video_id',
    'clean_filename',
]

"""Pydantic models for YouTube connector."""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Literal, Optional
from datetime import datetime, timezone
from connectors.common.config import BaseClientConfig, BaseCollectSpec


def published_at_from(timestamp: "int | float | None") -> Optional[str]:
    """Convert an epoch timestamp to an ISO-8601 UTC string (YYYY-MM-DDTHH:MM:SSZ)."""
    if timestamp is None:
        return None
    try:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (OverflowError, OSError, ValueError, TypeError):
        # Out-of-range / non-numeric value: drop the publish time, keep the video.
        return None


class YouTubeClientConfig(BaseClientConfig):
    """YouTube processing configuration.

    Merged from Trender and Daigest configurations.
    """
    whisper_model: str = Field(
        default="base",
        description="Whisper model: tiny, base, small, medium, large"
    )
    whisper_backend: Literal["auto", "mlx", "faster-whisper"] = Field(
        default="auto",
        description="Whisper backend: auto (mlx on Apple Silicon if installed, else faster-whisper), mlx, or faster-whisper"
    )
    mlx_whisper_model: str = Field(
        default="mlx-community/whisper-large-v3-turbo",
        description="MLX Whisper model repo or path (used by the mlx backend)"
    )
    transcript_cache_dir: Optional[str] = Field(
        default=None,
        description=(
            "Directory where each transcript is saved as <video_id>.json the moment "
            "it is fetched, and reused on later runs instead of fetching again"
        ),
    )
    max_video_length: int = Field(
        default=3600,
        description="Maximum video length in seconds (1 hour default)"
    )
    audio_format: str = Field(
        default="m4a",
        description="Audio format for download (m4a, webm, mp3)"
    )
    use_transcript_api: bool = Field(
        default=True,
        description="Try YouTube Transcript API before Whisper fallback"
    )
    transcript_languages: Optional[List[str]] = Field(
        default=None,
        description="Preferred transcript languages in priority order (e.g., ['iw', 'he', 'en'] for Hebrew then English). If None, auto-detects available languages. Note: YouTube uses 'iw', Whisper uses 'he' for Hebrew."
    )
    compute_type: str = Field(
        default="int8",
        description="Whisper compute type: int8, float16, float32"
    )
    timeout: int = Field(default=60, description="Request timeout in seconds")
    max_concurrency: int = Field(
        default=4, ge=1,
        description="Maximum number of videos fetched concurrently"
    )
    delay_seconds: float = Field(
        default=0.0, ge=0,
        description="Randomized pause before each video fetch (uniform in [0.5x, 1.5x])"
    )
    cookies_file: Optional[str] = Field(
        default=None,
        description="Path to a Netscape cookies.txt used by yt-dlp and youtube-transcript-api"
    )


class YouTubeCollectSpec(BaseCollectSpec):
    """Specification for YouTube data collection.

    Supports both direct URLs and channel-based collection.
    """
    urls: Optional[List[str]] = Field(
        default=None,
        description="List of video URLs to process"
    )
    channels: Optional[List[str]] = Field(
        default=None,
        description="List of channel names (e.g., @username)"
    )
    max_videos_per_channel: int = Field(
        default=5,
        ge=1,
        description="Maximum videos per channel"
    )
    days_back: int = Field(
        default=7,
        ge=1,
        description="Only videos from last N days (channel-listed videos only; direct URLs are never date-filtered)"
    )
    include_undated: bool = Field(
        default=False,
        description="Keep channel-listed videos whose publish date cannot be determined (default: skip and count them)"
    )
    skip_video_ids: Optional[List[str]] = Field(
        default=None,
        description="Video ids to drop after listing; never fetched"
    )

    @model_validator(mode='after')
    def check_at_least_one_source(self):
        """Ensure either urls or channels is provided."""
        if not self.urls and not self.channels:
            raise ValueError('Either urls or channels must be provided')
        return self


class YouTubeVideo(BaseModel):
    """YouTube video data model with metadata and transcript.

    Merged from Trender and Daigest output structures.
    """
    # Video identification
    video_id: str = Field(..., description="YouTube video ID (11 chars)")
    url: str = Field(..., description="Full YouTube URL")

    # Metadata
    title: str = Field(..., description="Video title")
    description: str = Field(default="", description="Video description")
    duration: int = Field(..., description="Video duration in seconds")
    upload_date: Optional[str] = Field(
        default=None,
        description="Upload date in YYYYMMDD format"
    )
    published_at: Optional[str] = Field(
        default=None,
        description="Publish time, ISO-8601 UTC (YYYY-MM-DDTHH:MM:SSZ)"
    )

    # Stats
    view_count: int = Field(default=0, description="View count")
    like_count: int = Field(default=0, description="Like count")

    # Channel info
    channel: str = Field(..., description="Channel name")
    channel_id: str = Field(..., description="Channel ID")

    # Additional metadata
    tags: List[str] = Field(default_factory=list, description="Video tags")
    categories: List[str] = Field(default_factory=list, description="Video categories")
    thumbnail: str = Field(default="", description="Thumbnail URL")

    # Transcript data
    transcript: str = Field(..., description="Video transcript text")
    transcript_source: str = Field(
        ...,
        description="Source of transcript: 'youtube_api' or 'whisper'"
    )
    transcript_segments: Optional[List[dict]] = Field(
        default=None,
        description="Per-segment [{start: float (seconds), text: str}], if available"
    )
    language: Optional[str] = Field(
        default=None,
        description="Detected language code"
    )
    language_probability: Optional[float] = Field(
        default=None,
        description="Language detection confidence"
    )

    # Processing metadata
    processed_at: datetime = Field(
        ...,
        description="When video was processed"
    )
    status: str = Field(
        ...,
        description="Processing status: 'success' or 'failed'"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if status=failed"
    )

    class Config:
        frozen = False

"""Pydantic models for YouTube connector."""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional
from datetime import datetime
from connectors.common.config import BaseClientConfig, BaseCollectSpec


class YouTubeClientConfig(BaseClientConfig):
    """YouTube processing configuration.

    Merged from Trender and Daigest configurations.
    """
    whisper_model: str = Field(
        default="base",
        description="Whisper model: tiny, base, small, medium, large"
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
        description="Only videos from last N days"
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

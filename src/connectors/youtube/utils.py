"""YouTube utility functions."""

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

_BLOCK_MARKERS = (
    "sign in to confirm you",
    "ipblocked",
    "requestblocked",
    "too many requests",
)


def is_block_error(error: Optional[object]) -> bool:
    """True if an error message looks like a YouTube bot/IP block."""
    text = str(error or "").lower()
    return any(m in text for m in _BLOCK_MARKERS) or bool(re.search(r"\b429\b", text))


def validate_youtube_url(url: str) -> bool:
    """Validate if URL is a valid YouTube video URL.

    Extracted from trender/app/utils/youtube_utils.py lines 10-30.

    Args:
        url: URL to validate

    Returns:
        True if valid YouTube URL, False otherwise

    Example:
        >>> validate_youtube_url("https://youtube.com/watch?v=dQw4w9WgXcQ")
        True
        >>> validate_youtube_url("https://example.com")
        False
    """
    youtube_patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]{11})'
    ]

    for pattern in youtube_patterns:
        if re.match(pattern, url):
            return True
    return False


def extract_video_id(url: str) -> Optional[str]:
    """Extract video ID from YouTube URL.

    Extracted from trender/app/utils/youtube_utils.py lines 33-54.

    Args:
        url: YouTube URL

    Returns:
        11-character video ID if found, None otherwise

    Example:
        >>> extract_video_id("https://youtube.com/watch?v=dQw4w9WgXcQ")
        'dQw4w9WgXcQ'
    """
    youtube_patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]{11})'
    ]

    for pattern in youtube_patterns:
        match = re.match(pattern, url)
        if match:
            return match.group(1)
    return None


def clean_filename(filename: str) -> str:
    """Clean filename by removing invalid characters.

    Extracted from trender/app/utils/youtube_utils.py lines 100-119.

    Args:
        filename: Original filename

    Returns:
        Cleaned filename safe for filesystem use

    Example:
        >>> clean_filename("My Video: Part 1")
        'My Video_ Part 1'
    """
    # Remove invalid characters for filenames
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')

    # Limit length to avoid filesystem issues
    if len(filename) > 200:
        filename = filename[:200]

    return filename


def video_published_at(info: Dict[str, Any]) -> Optional[datetime]:
    """Best-known publish time of a yt-dlp info/metadata dict, as aware UTC.

    Prefers an epoch ``release_timestamp`` / ``timestamp``. When only the
    date-only ``upload_date`` (YYYYMMDD) exists, returns the END of that UTC day,
    so a cutoff check never drops a video that may still be inside the window.
    Returns None when no usable date is present.
    """
    for key in ('release_timestamp', 'timestamp'):
        ts = info.get(key)
        if ts:
            try:
                return datetime.fromtimestamp(float(ts), tz=timezone.utc)
            except (TypeError, ValueError, OverflowError, OSError):
                pass
    day = info.get('upload_date') or ''
    try:
        start = datetime.strptime(str(day), '%Y%m%d').replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return start + timedelta(days=1) - timedelta(seconds=1)

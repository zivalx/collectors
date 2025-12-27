"""Low-level YouTube client - MERGED from Trender + Daigest."""

import asyncio
import os
import tempfile
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from datetime import datetime, timedelta
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from faster_whisper import WhisperModel
import logging

from connectors.youtube.models import YouTubeClientConfig
from connectors.youtube.utils import extract_video_id, clean_filename
from connectors.common.exceptions import DataFetchError

logger = logging.getLogger(__name__)


class YouTubeClient:
    """Low-level YouTube client combining Trender + Daigest architectures.

    MERGED from:
    - daigest/backend/src/services/youtubeService.py
    - trender/app/services/youtube_processor.py
    """

    def __init__(self, config: YouTubeClientConfig):
        """Initialize YouTube client.

        Args:
            config: YouTube client configuration
        """
        self.config = config
        self._whisper_model: Optional[WhisperModel] = None

        # Initialize Whisper model lazily
        if config.whisper_model:
            try:
                self._whisper_model = WhisperModel(
                    config.whisper_model,
                    device="cpu",  # CPU for better compatibility
                    compute_type=config.compute_type,
                )
                logger.info(f"Whisper model initialized: {config.whisper_model}")
            except Exception as e:
                logger.error(f"Failed to initialize Whisper model: {e}")
                self._whisper_model = None

    async def get_channel_videos(
        self,
        channel_name: str,
        max_videos: int = 5,
        days_back: int = 7,
    ) -> List[str]:
        """Get recent video URLs from a channel.

        Extracted from daigest/youtubeService.py lines 115-245.

        Args:
            channel_name: Channel name (with or without @ prefix)
            max_videos: Maximum videos to return
            days_back: Only videos from last N days

        Returns:
            List of video URLs

        Raises:
            DataFetchError: If channel fetch fails
        """
        normalized_name = channel_name.lstrip('@')
        url = f"https://www.youtube.com/@{normalized_name}/videos"
        cutoff_date = datetime.now() - timedelta(days=days_back)

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'playlistend': max_videos * 2,  # Fetch more for date filtering
        }

        try:
            def extract_info():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=False)

            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, extract_info)

            # Extract video URLs
            video_urls = []
            for entry in info.get('entries', [])[:max_videos]:
                if entry and entry.get('id'):
                    video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                    video_urls.append(video_url)

            logger.info(
                f"Found {len(video_urls)} videos from channel @{normalized_name}"
            )
            return video_urls

        except Exception as e:
            raise DataFetchError(f"Error fetching channel {channel_name}: {e}")

    async def get_video_metadata(self, url: str) -> Dict[str, Any]:
        """Get video metadata using yt-dlp.

        Extracted from trender/youtube_processor.py lines 109-144.

        Args:
            url: YouTube video URL

        Returns:
            Dictionary with metadata fields

        Raises:
            DataFetchError: If metadata fetch fails
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }

        try:
            def extract_info():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=False)

            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, extract_info)

            return {
                'title': info.get('title', 'Unknown'),
                'description': info.get('description', ''),
                'duration': info.get('duration', 0),
                'view_count': info.get('view_count', 0),
                'like_count': info.get('like_count', 0),
                'channel': info.get('uploader', 'Unknown'),
                'channel_id': info.get('uploader_id', ''),
                'upload_date': info.get('upload_date', ''),
                'tags': info.get('tags', []) or [],
                'categories': info.get('categories', []) or [],
                'thumbnail': info.get('thumbnail', ''),
            }
        except Exception as e:
            raise DataFetchError(f"Error getting metadata for {url}: {e}")

    async def get_transcript(self, video_id: str) -> Tuple[str, str]:
        """Get transcript using YouTube Transcript API or Whisper.

        Supports multiple languages and auto-detection:
        - If transcript_languages is specified, tries those in order
        - If not specified or all fail, auto-detects and uses any available language
        - Falls back to Whisper if transcript API fails

        Args:
            video_id: YouTube video ID

        Returns:
            Tuple of (transcript_text, source) where source is 'youtube_api' or 'whisper'

        Raises:
            DataFetchError: If all transcription methods fail
        """
        # Try YouTube Transcript API first (if enabled)
        if self.config.use_transcript_api:
            try:
                def get_transcript():
                    ytt_api = YouTubeTranscriptApi()
                    transcript_list = ytt_api.list(video_id)

                    # Strategy 1: Try preferred languages if specified
                    if self.config.transcript_languages:
                        for lang_code in self.config.transcript_languages:
                            try:
                                # Try manual transcript first
                                transcript = transcript_list.find_transcript([lang_code])
                                logger.info(f"Found manual transcript in '{lang_code}' for {video_id}")
                                return transcript.fetch(), lang_code
                            except:
                                try:
                                    # Try auto-generated
                                    transcript = transcript_list.find_generated_transcript([lang_code])
                                    logger.info(f"Found auto-generated transcript in '{lang_code}' for {video_id}")
                                    return transcript.fetch(), lang_code
                                except:
                                    continue

                        # If preferred languages all failed, log and fall through to auto-detect
                        logger.warning(
                            f"None of the preferred languages {self.config.transcript_languages} "
                            f"available for {video_id}, trying auto-detection"
                        )

                    # Strategy 2: Auto-detect - use first available transcript
                    available_transcripts = list(transcript_list)
                    if available_transcripts:
                        # Prefer manual over auto-generated
                        manual = [t for t in available_transcripts if not t.is_generated]
                        transcript = manual[0] if manual else available_transcripts[0]
                        lang_code = transcript.language_code
                        logger.info(
                            f"Auto-detected transcript in '{lang_code}' "
                            f"({'manual' if not transcript.is_generated else 'auto-generated'}) "
                            f"for {video_id}"
                        )
                        return transcript.fetch(), lang_code

                    # No transcripts available at all
                    raise Exception("No transcripts available for this video")

                loop = asyncio.get_event_loop()
                transcript_data, lang_code = await loop.run_in_executor(None, get_transcript)
                full_text = ' '.join([t['text'] for t in transcript_data])

                logger.info(
                    f"Got transcript from YouTube API for {video_id} "
                    f"(language: {lang_code}, {len(full_text)} chars)"
                )
                return (full_text, 'youtube_api')

            except Exception as e:
                logger.warning(
                    f"YouTube Transcript API failed for {video_id}: {e}"
                )

        # Fall back to Whisper
        if self._whisper_model:
            return await self._transcribe_with_whisper(video_id)
        else:
            raise DataFetchError(
                f"No transcription method available for {video_id}"
            )

    async def _transcribe_with_whisper(self, video_id: str) -> Tuple[str, str]:
        """Download audio and transcribe with Whisper.

        Merged from both Trender and Daigest implementations.

        Args:
            video_id: YouTube video ID

        Returns:
            Tuple of (transcript_text, 'whisper')

        Raises:
            DataFetchError: If transcription fails
        """
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"

            # Use temp directory for audio (auto-cleanup)
            with tempfile.TemporaryDirectory() as temp_dir:
                # Download audio
                audio_file = await self._download_audio(url, video_id, temp_dir)
                if not audio_file:
                    raise DataFetchError("Failed to download audio")

                # Transcribe
                def transcribe():
                    segments, info = self._whisper_model.transcribe(
                        audio_file,
                        beam_size=5,
                        language=None,  # Auto-detect
                        condition_on_previous_text=False,
                    )
                    full_text = " ".join([seg.text.strip() for seg in segments])
                    return full_text, info.language, info.language_probability

                loop = asyncio.get_event_loop()
                text, lang, lang_prob = await loop.run_in_executor(None, transcribe)

                logger.info(
                    f"Transcribed {video_id} with Whisper "
                    f"({len(text)} chars, lang={lang})"
                )
                return (text, 'whisper')

        except Exception as e:
            raise DataFetchError(f"Whisper transcription failed: {e}")

    async def _download_audio(
        self, url: str, video_id: str, output_dir: str
    ) -> Optional[str]:
        """Download audio file using yt-dlp.

        Extracted from trender/youtube_processor.py lines 179-213.

        Args:
            url: YouTube video URL
            video_id: Video ID for filename
            output_dir: Output directory path

        Returns:
            Path to downloaded audio file, or None if failed
        """
        try:
            filename = clean_filename(f"{video_id}_audio")
            audio_path = os.path.join(output_dir, f"{filename}.%(ext)s")

            ydl_opts = {
                'format': f'bestaudio[ext={self.config.audio_format}]/bestaudio[ext=webm]/bestaudio',
                'outtmpl': audio_path,
                'quiet': True,
                'no_warnings': True,
            }

            def download():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, download)

            # Find downloaded file (extension may vary)
            base_path = os.path.splitext(audio_path)[0]
            for ext in ['m4a', 'webm', 'mp3', 'wav', 'opus']:
                potential_path = f"{base_path}.{ext}"
                if os.path.exists(potential_path):
                    logger.debug(f"Downloaded audio: {potential_path}")
                    return potential_path

            logger.error("Audio file not found after download")
            return None

        except Exception as e:
            logger.error(f"Error downloading audio for {video_id}: {e}")
            return None

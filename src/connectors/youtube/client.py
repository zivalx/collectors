"""Low-level YouTube client - MERGED from Trender + Daigest."""

import asyncio
import json
import os
import platform
import tempfile
from typing import TYPE_CHECKING, Optional, Dict, Any, List, Tuple
from pathlib import Path
from datetime import datetime, timedelta, timezone
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
import logging

if TYPE_CHECKING:
    # faster-whisper is an OPTIONAL extra (see pyproject.toml [youtube]/[all]).
    # Only import it for type-checking; the real import happens lazily inside
    # YouTubeClient.__init__ so importing this module never requires the
    # heavy ML stack (ctranslate2/onnxruntime) to be installed.
    from faster_whisper import WhisperModel

from connectors.youtube.models import YouTubeClientConfig
from connectors.youtube.utils import extract_video_id, clean_filename, is_block_error
from connectors.common.http import with_retry
from connectors.common.exceptions import DataFetchError

logger = logging.getLogger(__name__)

WHISPER_SAMPLE_RATE = 16000


def _decode_audio_ffmpeg(audio_file: str):
    """Decode an audio file to 16 kHz mono float32 for faster-whisper.

    faster-whisper's own decoder (PyAV) breaks on PyAV >= 15 ("open() got an
    unexpected keyword argument 'metadata_errors'"), so decode with the ffmpeg
    binary instead. Falls back to the file path when ffmpeg is not installed.
    """
    import shutil
    import subprocess

    import numpy as np

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return audio_file
    proc = subprocess.run(
        [ffmpeg, "-nostdin", "-loglevel", "error", "-i", audio_file,
         "-f", "f32le", "-ac", "1", "-ar", str(WHISPER_SAMPLE_RATE), "-"],
        capture_output=True,
        check=True,
    )
    return np.frombuffer(proc.stdout, dtype=np.float32)


def _resolve_whisper_backend(config: YouTubeClientConfig) -> Optional[str]:
    """Pick the Whisper backend: "mlx", "faster-whisper", or None (disabled).

    Whisper is disabled when ``config.whisper_model`` is empty (``--no-whisper``).
    "auto" picks mlx on Apple Silicon when mlx_whisper is importable. An
    explicit "mlx" that is not importable falls back to faster-whisper.
    """
    if not config.whisper_model:
        return None
    backend = config.whisper_backend
    if backend == "faster-whisper":
        return "faster-whisper"
    if backend == "auto" and not (
        platform.system() == "Darwin" and platform.machine() == "arm64"
    ):
        return "faster-whisper"
    try:
        import mlx_whisper  # noqa: F401
    except ImportError:
        if backend == "mlx":
            logger.warning(
                "mlx-whisper requested but not importable; "
                "falling back to faster-whisper"
            )
        return "faster-whisper"
    return "mlx"


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
        self._whisper_model: "Optional[WhisperModel]" = None
        self._captions_blocked = False
        self._captions_block_logged = False
        self._whisper_backend = _resolve_whisper_backend(config)

        # Initialize Whisper model lazily. faster-whisper is an OPTIONAL
        # extra, so its import happens here (not at module level) and any
        # failure just disables the Whisper fallback instead of breaking
        # the whole connector.
        if self._whisper_backend == "mlx":
            logger.info(f"Whisper backend: mlx ({config.mlx_whisper_model})")
        elif self._whisper_backend == "faster-whisper":
            try:
                from faster_whisper import WhisperModel

                self._whisper_model = WhisperModel(
                    config.whisper_model,
                    device="cpu",  # CPU for better compatibility
                    compute_type=config.compute_type,
                )
                logger.info(f"Whisper model initialized: {config.whisper_model}")
            except ImportError as e:
                logger.warning(
                    "faster-whisper not installed; Whisper fallback disabled, "
                    f"transcript-API only ({e})"
                )
                self._whisper_model = None
            except Exception as e:
                logger.error(f"Failed to initialize Whisper model: {e}")
                self._whisper_model = None

    @with_retry(max_attempts=3)
    def _apply_cookies(self, ydl_opts: Dict[str, Any]) -> None:
        """Add the configured cookies file to yt-dlp options."""
        if self.config.cookies_file:
            ydl_opts['cookiefile'] = self.config.cookies_file

    def _make_transcript_api(self) -> YouTubeTranscriptApi:
        """Build the transcript API, with cookies via a requests session if configured."""
        if not self.config.cookies_file:
            return YouTubeTranscriptApi()
        import requests
        from http.cookiejar import MozillaCookieJar

        jar = MozillaCookieJar(self.config.cookies_file)
        jar.load(ignore_discard=True, ignore_expires=True)
        session = requests.Session()
        session.cookies = jar
        return YouTubeTranscriptApi(http_client=session)

    async def get_channel_videos(
        self,
        channel_name: str,
        max_videos: int = 5,
        days_back: int = 7,
    ) -> List[str]:
        """Get recent video URLs from a channel.

        Retries on transient network errors (3 attempts with exponential backoff).

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
        self._apply_cookies(ydl_opts)

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

    @with_retry(max_attempts=3)
    async def get_video_metadata(self, url: str) -> Dict[str, Any]:
        """Get video metadata using yt-dlp.

        Retries on transient network errors (3 attempts with exponential backoff).

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
        self._apply_cookies(ydl_opts)

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
                # Premieres/scheduled streams: upload time can precede public availability.
                'timestamp': info.get('release_timestamp') or info.get('timestamp'),
                'tags': info.get('tags', []) or [],
                'categories': info.get('categories', []) or [],
                'thumbnail': info.get('thumbnail', ''),
            }
        except Exception as e:
            raise DataFetchError(f"Error getting metadata for {url}: {e}")

    def _cache_path(self, video_id: str) -> Optional[Path]:
        if not self.config.transcript_cache_dir:
            return None
        return Path(self.config.transcript_cache_dir).expanduser() / f"{video_id}.json"

    def _read_cached_transcript(self, video_id: str) -> Optional[Tuple[str, str, List[dict]]]:
        path = self._cache_path(video_id)
        if path is None or not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            text = data.get("transcript") or ""
            if not text.strip():
                return None
            return (text, data.get("source") or "cache", data.get("segments") or [])
        except (OSError, ValueError) as e:
            logger.warning(f"Ignoring unreadable cached transcript {path}: {e}")
            return None

    def _write_cached_transcript(
        self, video_id: str, text: str, source: str, segments: List[dict]
    ) -> None:
        path = self._cache_path(video_id)
        if path is None or not text.strip():
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps({
                "video_id": video_id,
                "source": source,
                "whisper_model": (
                    self.config.mlx_whisper_model if self._whisper_backend == "mlx"
                    else self.config.whisper_model
                ) if source == "whisper" else None,
                "saved_at": datetime.now(timezone.utc).isoformat(),
                "transcript": text,
                "segments": segments,
            }, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, path)
        except OSError as e:
            logger.warning(f"Could not save transcript for {video_id} to {path}: {e}")

    async def get_transcript(self, video_id: str) -> Tuple[str, str, List[dict]]:
        """Transcript for a video, using the on-disk cache when configured.

        A cached transcript (``transcript_cache_dir``) is returned without any
        network call; a freshly fetched one is saved there immediately, so long
        runs never lose finished work.
        """
        cached = self._read_cached_transcript(video_id)
        if cached is not None:
            logger.info(f"Using cached transcript for {video_id}")
            return cached
        text, source, segments = await self._fetch_transcript(video_id)
        self._write_cached_transcript(video_id, text, source, segments)
        return text, source, segments

    async def _fetch_transcript(self, video_id: str) -> Tuple[str, str, List[dict]]:
        """Get transcript using YouTube Transcript API or Whisper.

        Supports multiple languages and auto-detection:
        - If transcript_languages is specified, tries those in order
        - If not specified or all fail, auto-detects and uses any available language
        - Falls back to Whisper if transcript API fails

        Args:
            video_id: YouTube video ID

        Returns:
            Tuple of (transcript_text, source, segments) where source is
            'youtube_api' or 'whisper', and segments is a list of
            {"start": float, "text": str} dicts (may be empty if unavailable)

        Raises:
            DataFetchError: If all transcription methods fail
        """
        api_error: Optional[BaseException] = None
        if self._captions_blocked and not self._captions_block_logged:
            self._captions_block_logged = True
            logger.warning(
                "YouTube captions are blocked; skipping transcript API and "
                "using Whisper for remaining videos"
            )

        # Try YouTube Transcript API first (if enabled and not blocked)
        if self.config.use_transcript_api and not self._captions_blocked:
            try:
                def get_transcript():
                    ytt_api = self._make_transcript_api()
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
                # Handle both dict format and FetchedTranscriptSnippet object format
                full_text = ' '.join([
                    t['text'] if isinstance(t, dict) else t.text
                    for t in transcript_data
                ])
                segments = [
                    {
                        "start": float(t['start'] if isinstance(t, dict) else t.start),
                        "text": t['text'] if isinstance(t, dict) else t.text,
                    }
                    for t in transcript_data
                ]

                logger.info(
                    f"Got transcript from YouTube API for {video_id} "
                    f"(language: {lang_code}, {len(full_text)} chars)"
                )
                return (full_text, 'youtube_api', segments)

            except Exception as e:
                api_error = e
                logger.warning(
                    f"YouTube Transcript API failed for {video_id}: {e}"
                )
                if is_block_error(e):
                    self._captions_blocked = True

        # Fall back to Whisper
        if self._whisper_available():
            try:
                return await self._transcribe_with_whisper(video_id)
            except DataFetchError as whisper_error:
                if api_error is not None and is_block_error(api_error):
                    raise DataFetchError(
                        f"Transcript API failed: {api_error}; "
                        f"Whisper failed: {whisper_error}"
                    )
                raise
        msg = (
            f"No transcription method available for {video_id}: "
            "Whisper fallback unavailable (faster-whisper not installed "
            "or Whisper model not configured)"
        )
        if api_error is not None and is_block_error(api_error):
            msg = f"Transcript API failed: {api_error}; Whisper failed: {msg}"
        raise DataFetchError(msg)

    def _whisper_available(self) -> bool:
        return self._whisper_backend == "mlx" or self._whisper_model is not None

    async def _transcribe_with_whisper(self, video_id: str) -> Tuple[str, str, List[dict]]:
        """Download audio and transcribe with Whisper.

        Merged from both Trender and Daigest implementations.

        Args:
            video_id: YouTube video ID

        Returns:
            Tuple of (transcript_text, 'whisper', segments) where segments is
            a list of {"start": float, "text": str} dicts

        Raises:
            DataFetchError: If transcription fails
        """
        if not self._whisper_available():
            raise DataFetchError(
                "Whisper fallback unavailable: faster-whisper not installed"
            )

        try:
            url = f"https://www.youtube.com/watch?v={video_id}"

            # Use temp directory for audio (auto-cleanup)
            with tempfile.TemporaryDirectory() as temp_dir:
                # Download audio
                audio_file = await self._download_audio(url, video_id, temp_dir)
                if not audio_file:
                    raise DataFetchError("Failed to download audio")

                if self._whisper_backend == "mlx":
                    return await self._transcribe_mlx(audio_file, video_id)

                # Transcribe
                def transcribe():
                    segments, info = self._whisper_model.transcribe(
                        _decode_audio_ffmpeg(audio_file),
                        beam_size=5,
                        language=None,  # Auto-detect
                        condition_on_previous_text=False,
                    )
                    segments_list = list(segments)
                    full_text = " ".join([seg.text.strip() for seg in segments_list])
                    timed_segments = [
                        {"start": float(seg.start), "text": seg.text.strip()}
                        for seg in segments_list
                    ]
                    return full_text, info.language, info.language_probability, timed_segments

                loop = asyncio.get_event_loop()
                text, lang, lang_prob, timed_segments = await loop.run_in_executor(None, transcribe)

                logger.info(
                    f"Transcribed {video_id} with Whisper "
                    f"({len(text)} chars, lang={lang})"
                )
                return (text, 'whisper', timed_segments)

        except Exception as e:
            raise DataFetchError(f"Whisper transcription failed: {e}")

    def _whisper_language(self) -> Optional[str]:
        """The channel's first configured language as a Whisper code, else auto-detect."""
        langs = self.config.transcript_languages or []
        if not langs:
            return None
        code = langs[0].split("-")[0].lower()
        return {"iw": "he"}.get(code, code)

    async def _transcribe_mlx(
        self, audio_file: str, video_id: str
    ) -> Tuple[str, str, List[dict]]:
        """Transcribe an audio file with mlx-whisper (Apple GPU)."""
        import mlx_whisper

        result = await asyncio.to_thread(
            mlx_whisper.transcribe,
            audio_file,
            path_or_hf_repo=self.config.mlx_whisper_model,
            language=self._whisper_language(),
        )
        timed_segments = []
        for seg in result.get("segments", []):
            text = seg["text"].strip()
            if text:
                timed_segments.append({"start": float(seg["start"]), "text": text})
        full_text = " ".join(s["text"] for s in timed_segments)
        logger.info(
            f"Transcribed {video_id} with Whisper backend=mlx "
            f"({len(full_text)} chars, lang={result.get('language')})"
        )
        return (full_text, 'whisper', timed_segments)

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
            self._apply_cookies(ydl_opts)

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

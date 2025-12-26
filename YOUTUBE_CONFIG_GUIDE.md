# YouTube Configuration Guide

## Overview

YouTube connector **does NOT require API credentials**. It uses public APIs and Whisper AI for transcription.

## Configuration Options

### YouTubeClientConfig (How to Process Videos)

```python
YouTubeClientConfig(
    whisper_model="base",        # AI model for transcription
    use_transcript_api=True,     # Try YouTube captions first
    max_video_length=3600,       # Maximum video duration (seconds)
    audio_format="m4a",          # Audio download format
    compute_type="int8",         # Whisper computation type
    timeout=60,                  # Request timeout
)
```

#### whisper_model Options:
- **"tiny"** - Fastest, least accurate (good for testing)
- **"base"** - Fast, decent accuracy ⭐ **Recommended**
- **"small"** - Slower, better accuracy
- **"medium"** - Slow, high accuracy
- **"large"** - Very slow, best accuracy

#### use_transcript_api:
- **True** ⭐ **Recommended** - Try YouTube's built-in captions first (fast, free)
- **False** - Always use Whisper (slower, but works for all videos)

#### max_video_length:
- Maximum duration in seconds
- Default: **3600** (1 hour)
- Videos longer than this are skipped
- Examples:
  - 300 = 5 minutes
  - 1800 = 30 minutes
  - 3600 = 1 hour
  - 7200 = 2 hours

### YouTubeCollectSpec (What to Collect)

```python
YouTubeCollectSpec(
    channels=["@CoinBureau", "@DataDash"],  # Channel handles
    max_videos_per_channel=3,                # Videos to collect per channel
    days_back=7,                             # Only recent videos
)
```

Or collect specific videos:

```python
YouTubeCollectSpec(
    urls=[
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=9bZkp7q19f0",
    ]
)
```

#### max_videos_per_channel:
- How many recent videos to get from each channel
- Default: **5**
- Range: 1-100
- Example: `max_videos_per_channel=10` gets 10 most recent videos

#### days_back:
- Only collect videos uploaded in the last N days
- Default: **7** (last week)
- Examples:
  - 1 = today only
  - 7 = last week
  - 30 = last month
  - 365 = last year

## Current Configuration in Your Script

In [examples/my_crypto_collector.py](examples/my_crypto_collector.py:139-156):

```python
# YouTube configuration
config = YouTubeClientConfig(
    whisper_model="base",           # Fast + decent accuracy
    use_transcript_api=True,        # Use YouTube captions when available
    max_video_length=3600,          # Max 1 hour videos
)

# Collection specification
spec = YouTubeCollectSpec(
    channels=[
        "@CoinBureau",              # 5 popular crypto channels
        "@DataDash",
        "@AltcoinDaily",
        "@InvestAnswers",
        "@Benjamin_Cowen",
    ],
    max_videos_per_channel=3,       # 3 videos each = 15 total max
    days_back=7,                    # Only from last week
)
```

**This will collect:**
- Up to **3 videos** from each of 5 channels
- Only videos from the **last 7 days**
- Maximum **15 videos total** (5 channels × 3 videos)
- Videos up to **1 hour long**

## Customization Examples

### Get More Videos Per Channel
```python
spec = YouTubeCollectSpec(
    channels=["@CoinBureau", "@DataDash"],
    max_videos_per_channel=10,  # Changed from 3 to 10
    days_back=7,
)
# Result: Up to 20 videos (2 channels × 10 videos)
```

### Get Older Videos
```python
spec = YouTubeCollectSpec(
    channels=["@CoinBureau"],
    max_videos_per_channel=5,
    days_back=30,  # Changed from 7 to 30 days
)
# Result: 5 most recent videos from last month
```

### Allow Longer Videos
```python
config = YouTubeClientConfig(
    whisper_model="base",
    max_video_length=7200,  # Changed from 3600 to 7200 (2 hours)
)
# Result: Videos up to 2 hours are now allowed
```

### Use Better Transcription Model
```python
config = YouTubeClientConfig(
    whisper_model="small",  # Changed from "base" to "small"
    use_transcript_api=True,
)
# Result: Better accuracy, but slower (only for videos without captions)
```

### Add More Crypto Channels

Edit [examples/my_crypto_collector.py](examples/my_crypto_collector.py:147-153):

```python
spec = YouTubeCollectSpec(
    channels=[
        "@CoinBureau",           # Existing channels
        "@DataDash",
        "@AltcoinDaily",
        "@InvestAnswers",
        "@Benjamin_Cowen",

        # Add your favorite crypto channels:
        "@aantonop",             # Andreas Antonopoulos
        "@RealVision",           # Real Vision Crypto
        "@Finematics",           # DeFi education
        "@Bankless",             # Bankless
    ],
    max_videos_per_channel=3,
    days_back=7,
)
```

### Collect Specific Videos Only
```python
spec = YouTubeCollectSpec(
    urls=[
        "https://www.youtube.com/watch?v=abc123",
        "https://www.youtube.com/watch?v=def456",
        "https://www.youtube.com/watch?v=ghi789",
    ]
)
# Result: Only these 3 specific videos
```

## Performance Considerations

### Speed vs Quality

| Configuration | Speed | Accuracy | Use Case |
|--------------|-------|----------|----------|
| `use_transcript_api=True` + `whisper_model="tiny"` | ⚡⚡⚡ Very Fast | ⭐⭐ OK | Testing, quick scans |
| `use_transcript_api=True` + `whisper_model="base"` | ⚡⚡ Fast | ⭐⭐⭐ Good | **Recommended** |
| `use_transcript_api=True` + `whisper_model="small"` | ⚡ Moderate | ⭐⭐⭐⭐ Very Good | High accuracy needed |
| `use_transcript_api=False` + `whisper_model="base"` | 🐌 Slow | ⭐⭐⭐ Good | No captions available |
| `use_transcript_api=False` + `whisper_model="large"` | 🐌🐌 Very Slow | ⭐⭐⭐⭐⭐ Excellent | Maximum accuracy |

### Estimated Collection Times

**With `use_transcript_api=True` (most videos have captions):**
- 1 video: ~5-10 seconds
- 5 videos: ~30-60 seconds
- 15 videos: ~2-3 minutes

**With Whisper fallback (no captions available):**
- 1 video (5 min): ~30-60 seconds
- 1 video (30 min): ~3-5 minutes
- 1 video (1 hour): ~5-10 minutes

### Optimizing Collection

**For faster collection:**
```python
# Collect fewer, shorter videos
spec = YouTubeCollectSpec(
    channels=["@CoinBureau"],
    max_videos_per_channel=2,  # Just 2 videos
    days_back=3,                # Last 3 days only
)
config = YouTubeClientConfig(
    max_video_length=1800,      # Max 30 minutes
    whisper_model="tiny",       # Fastest model
)
```

**For comprehensive collection:**
```python
# Collect more, longer videos
spec = YouTubeCollectSpec(
    channels=["@CoinBureau", "@DataDash", "@AltcoinDaily"],
    max_videos_per_channel=10,  # 10 videos each
    days_back=14,               # Last 2 weeks
)
config = YouTubeClientConfig(
    max_video_length=7200,      # Max 2 hours
    whisper_model="small",      # Better accuracy
)
```

## What You Get

Each video returns a `YouTubeVideo` object with:

```python
video.title              # "Bitcoin To $100K? Market Analysis"
video.channel            # "Coin Bureau"
video.duration           # 1234 (seconds)
video.view_count         # 150000
video.like_count         # 5000
video.transcript         # Full video transcript text
video.transcript_source  # "youtube_api" or "whisper"
video.upload_date        # "20251224"
video.url                # "https://youtube.com/watch?v=..."
video.video_id           # "abc123xyz"
video.description        # Video description
video.tags               # ["bitcoin", "crypto", "trading"]
video.status             # "success" or "failed"
```

## Transcript Sources

- **youtube_api**: Fast, free, high quality (when available)
- **whisper**: Slower, uses AI transcription (fallback when no captions)

The connector automatically tries YouTube API first, then falls back to Whisper if needed.

## Tips

1. **Start small** - Test with 1-2 channels and `max_videos_per_channel=2`
2. **Use `use_transcript_api=True`** - Much faster when captions exist
3. **Filter by recency** - Use `days_back=7` to avoid old videos
4. **Limit video length** - Use `max_video_length=3600` to skip long videos
5. **Monitor first run** - First video takes longer (model loading)

## No API Key Needed! 🎉

Unlike Reddit, Telegram, and Twitter - YouTube connector works without any API credentials. Just specify channels and go!

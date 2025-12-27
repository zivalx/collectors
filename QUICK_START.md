# Quick Start Guide

## Installation

### From Git (Other Apps)
```bash
pip install git+https://github.com/YOUR_USERNAME/connectors.git
```

### Local Development
```bash
pip install -e /path/to/connectors
```

---

## Usage Pattern (All Connectors)

```python
from connectors import setup_logging

# 1. Optional: Enable logging
setup_logging(level="INFO")

# 2. Import connector
from connectors.reddit import RedditCollector, RedditClientConfig, RedditCollectSpec

# 3. Create config (credentials)
config = RedditClientConfig(
    client_id="your_id",
    client_secret="your_secret",
    user_agent="YourApp/1.0"
)

# 4. Create spec (what to collect)
spec = RedditCollectSpec(
    subreddits=["python"],
    max_posts_per_subreddit=10,
    skip_stickied=True
)

# 5. Collect data
collector = RedditCollector(config)
posts = await collector.fetch(spec)  # Returns List[RedditPost]

# 6. Use results
for post in posts:
    if post.status == 'success':  # Check status
        print(post.title, post.score)
```

---

## Reddit Connector

### Import
```python
from connectors.reddit import RedditCollector, RedditClientConfig, RedditCollectSpec
```

### Config (Credentials)
```python
RedditClientConfig(
    client_id: str,          # Reddit API client ID
    client_secret: str,      # Reddit API client secret
    user_agent: str,         # "YourApp/1.0"
    rate_limit: int = 60     # Requests per minute
)
```

### Spec (What to Collect)
```python
RedditCollectSpec(
    subreddits: List[str],              # ["python", "learnpython"]
    sort: str = "hot",                  # hot, new, top, rising
    time_filter: str = "day",           # hour, day, week, month, year, all
    max_posts_per_subreddit: int = 20,  # 1-100
    include_comments: bool = True,      # Collect comments
    skip_stickied: bool = False         # Skip pinned posts
)
```

### Returns
```python
List[RedditPost]  # Each post has:
    .id: str
    .title: str
    .text: str
    .author: str
    .created_at: datetime
    .num_comments: int
    .score: int
    .url: str
    .subreddit: str
    .stickied: bool           # Is pinned
    .comments: List[str]      # Comment texts
```

---

## YouTube Connector

### Import
```python
from connectors.youtube import YouTubeCollector, YouTubeClientConfig, YouTubeCollectSpec
```

### Config (Settings)
```python
YouTubeClientConfig(
    whisper_model: str = "base",               # tiny, base, small, medium, large
    use_transcript_api: bool = True,           # Try YouTube API first
    transcript_languages: List[str] = None,    # e.g., ["iw", "he", "en"] or None for auto-detect
    max_video_length: int = 3600,              # Max seconds
    audio_format: str = "m4a"                  # m4a, webm, mp3
)
```

### Spec (What to Collect)
```python
YouTubeCollectSpec(
    channels: List[str] = None,         # ["@Veritasium", "@VSauce"]
    urls: List[str] = None,             # ["https://youtube.com/watch?v=..."]
    max_videos_per_channel: int = 5,
    days_back: int = 7
)
```

### Returns
```python
List[YouTubeVideo]  # Each video has:
    .video_id: str
    .url: str
    .title: str
    .description: str
    .duration: int
    .upload_date: str
    .view_count: int
    .like_count: int
    .channel: str
    .channel_id: str
    .tags: List[str]
    .categories: List[str]
    .thumbnail: str
    .transcript: str           # Full transcript text
    .transcript_source: str    # "youtube_api" or "whisper"
    .processed_at: datetime
    .status: str               # "success" or "failed"
    .error: str                # Error message if failed
```

---

## Telegram Connector

### Import
```python
from connectors.telegram import TelegramCollector, TelegramClientConfig, TelegramCollectSpec
```

### Config (Credentials)
```python
TelegramClientConfig(
    api_id: int,              # Telegram API ID
    api_hash: str,            # Telegram API hash
    phone: str,               # "+1234567890"
    session_name: str = "session",
    code_callback: Callable = None,    # For 2FA code
    password_callback: Callable = None # For 2FA password
)
```

### Spec (What to Collect)
```python
TelegramCollectSpec(
    channels: List[str],              # ["channel_username", "https://t.me/..."]
    limit: int = 100,                 # Messages per channel
    include_replies: bool = False,    # Include reply threads
    offset_date: datetime = None      # Messages before this date
)
```

### Returns
```python
List[TelegramMessage]  # Each message has:
    .id: int
    .date: datetime
    .text: str
    .sender_id: int
    .channel: str
    .views: int
    .forwards: int
    .replies_count: int
    .media_type: str
    .reply_to_msg_id: int
```

---

## Twitter Connector

### Import
```python
from connectors.twitter import TwitterCollector, TwitterClientConfig, TwitterCollectSpec
```

### Config (Credentials)
```python
TwitterClientConfig(
    bearer_token: str  # Twitter API v2 Bearer Token
)
```

### Spec (What to Collect)
```python
TwitterCollectSpec(
    query: str,                    # "python OR javascript"
    max_results: int = 100,        # 10-100 per request
    start_time: datetime = None,
    end_time: datetime = None
)
```

### Returns
```python
List[TwitterTweet]  # Each tweet has:
    .id: str
    .text: str
    .author_id: str
    .created_at: datetime
    .public_metrics: dict  # retweet_count, reply_count, like_count, quote_count
    .lang: str
    .source: str
```

---

## Error Handling

**All collectors return items with status field:**

```python
videos = await collector.fetch(spec)

# Separate successes and failures
successful = [v for v in videos if v.status == 'success']
failed = [v for v in videos if v.status == 'failed']

# Handle failures
for item in failed:
    print(f"Failed: {item.url} - {item.error}")
```

---

## Complete Example

```python
import asyncio
from connectors import setup_logging
from connectors.reddit import RedditCollector, RedditClientConfig, RedditCollectSpec

async def collect_data():
    # Enable logging
    setup_logging(level="INFO")

    # Configure
    config = RedditClientConfig(
        client_id="YOUR_CLIENT_ID",
        client_secret="YOUR_CLIENT_SECRET",
        user_agent="MyApp/1.0"
    )

    spec = RedditCollectSpec(
        subreddits=["python"],
        max_posts_per_subreddit=10,
        skip_stickied=True
    )

    # Collect
    collector = RedditCollector(config)
    posts = await collector.fetch(spec)

    # Process
    for post in posts:
        print(f"{post.title} - {post.score} points")
        print(f"Comments: {len(post.comments)}")

if __name__ == "__main__":
    asyncio.run(collect_data())
```

---

## Key Points

✅ **All collectors are async** - use `await collector.fetch(spec)`
✅ **2-tier config** - Separate credentials (config) from runtime params (spec)
✅ **Type-safe** - All models use Pydantic with validation
✅ **Error handling** - Check `.status` field on returned items
✅ **Logging** - Use `setup_logging()` for visibility
✅ **No database** - Returns Pydantic models, you handle storage

---

## Need Help?

- Full API docs: [API_REFERENCE.md](API_REFERENCE.md)
- Logging guide: [LOGGING_AND_ERRORS.md](LOGGING_AND_ERRORS.md)
- Output formats: [OUTPUT_GUIDE.md](OUTPUT_GUIDE.md)

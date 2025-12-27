# Connectors

Framework-agnostic data collectors for Reddit, Telegram, YouTube, Twitter, Google Trends (PyTrends), and GNews.

**Use this library to collect social media data from your own applications.** Pass in channels, subreddits, and keywords dynamically - credentials stay separate from collection targets.

## Features

- **Async-first**: All collectors use asyncio for concurrent operations
- **Type-safe**: Pydantic models for configuration and data
- **Modular**: Install only the collectors you need
- **Retry/backoff**: Built-in resilience for network failures
- **Rate limiting**: Respect API limits automatically
- **Two-tier configuration**: Separate credentials from collection targets
- **Dynamic configuration**: Pass subreddits, channels, time ranges from your app
- **Programmatic API**: Perfect for integration with FastAPI, Flask, Celery, etc.

## For External Applications

See **[API_REFERENCE.md](API_REFERENCE.md)** for complete documentation on using this as a library.

**Quick example:**

```python
# Your app dynamically configures collection
from connectors.reddit import RedditCollector, RedditClientConfig, RedditCollectSpec

async def collect_for_user(user_subreddits: List[str]):
    config = RedditClientConfig(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        user_agent="MyApp/1.0"
    )

    spec = RedditCollectSpec(
        subreddits=user_subreddits,  # From your app/database
        max_posts_per_subreddit=50
    )

    collector = RedditCollector(config)
    return await collector.fetch(spec)  # Returns List[RedditPost]

# Use in your app
posts = await collect_for_user(["python", "programming"])
```

## Installation

```bash
# Install specific connectors
pip install connectors[reddit]
pip install connectors[youtube,twitter]

# Install all connectors
pip install connectors[all]

# Development install
git clone https://github.com/yourusername/connectors
cd connectors
pip install -e .[all,dev]
```

## Quick Start

### Reddit

```python
import asyncio
import os
from connectors.reddit import RedditCollector, RedditClientConfig, RedditCollectSpec

async def main():
    # Configuration (credentials - set once, reuse many times)
    config = RedditClientConfig(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        user_agent="MyApp/1.0"
    )

    # Collection specification (what to collect - varies per request)
    spec = RedditCollectSpec(
        subreddits=["python", "programming"],
        sort="hot",
        max_posts_per_subreddit=50,
        include_comments=True
    )

    # Fetch data
    collector = RedditCollector(config)
    posts = await collector.fetch(spec)

    # Use the data
    for post in posts:
        print(f"{post.title} by {post.author}")
        print(f"  Score: {post.score}, Comments: {post.num_comments}")

asyncio.run(main())
```

### YouTube

```python
import asyncio
import os
from connectors.youtube import YouTubeCollector, YouTubeClientConfig, YouTubeCollectSpec

async def main():
    # Configuration
    config = YouTubeClientConfig(
        whisper_model="base",
        use_transcript_api=True,  # Try YouTube API first, Whisper fallback
        transcript_languages=["iw", "he", "en"],  # Hebrew (iw/he) then English (None = auto-detect all)
        max_video_length=3600  # 1 hour max
    )

    # Collect from channels
    spec = YouTubeCollectSpec(
        channels=["@Veritasium", "@VSauce"],
        max_videos_per_channel=5,
        days_back=7
    )

    # Or from specific URLs
    # spec = YouTubeCollectSpec(
    #     urls=["https://youtube.com/watch?v=dQw4w9WgXcQ"]
    # )

    collector = YouTubeCollector(config)
    videos = await collector.fetch(spec)

    for video in videos:
        print(f"{video.title} ({video.duration}s)")
        print(f"  Transcript source: {video.transcript_source}")
        print(f"  Transcript: {video.transcript[:100]}...")

asyncio.run(main())
```

### Telegram

```python
import asyncio
import os
from connectors.telegram import TelegramCollector, TelegramClientConfig, TelegramCollectSpec

# Define auth callbacks for non-interactive authentication
async def get_code():
    return input("Enter 2FA code: ")

async def get_password():
    return input("Enter password: ")

async def main():
    # Configuration with auth callbacks
    config = TelegramClientConfig(
        api_id=os.environ["TELEGRAM_API_ID"],
        api_hash=os.environ["TELEGRAM_API_HASH"],
        phone="+1234567890",
        auth_code_callback=get_code,
        auth_password_callback=get_password
    )

    # Collection specification
    spec = TelegramCollectSpec(
        channels=["channel1", "channel2"],
        max_messages_per_channel=200,
        include_replies=True
    )

    collector = TelegramCollector(config)
    messages = await collector.fetch(spec)

    for msg in messages:
        print(f"[{msg.channel}] {msg.text}")
        if msg.replies:
            print(f"  {len(msg.replies)} replies")

asyncio.run(main())
```

### Twitter

```python
import asyncio
import os
from connectors.twitter import TwitterCollector, TwitterClientConfig, TwitterCollectSpec

async def main():
    # Configuration
    config = TwitterClientConfig(
        bearer_token=os.environ["TWITTER_BEARER_TOKEN"]
    )

    # Collection specification
    spec = TwitterCollectSpec(
        query="python OR programming",
        max_results=100
    )

    collector = TwitterCollector(config)
    tweets = await collector.fetch(spec)

    for tweet in tweets:
        print(f"@{tweet.author_id}: {tweet.text}")
        print(f"  Likes: {tweet.like_count}, Retweets: {tweet.retweet_count}")

asyncio.run(main())
```

### Google Trends (PyTrends)

```python
import asyncio
from connectors.pytrends import PyTrendsCollector, PyTrendsClientConfig, PyTrendsCollectSpec

async def main():
    # Configuration (no API key required)
    config = PyTrendsClientConfig(
        timeout=30,
        retries=3
    )

    # Collection specification
    spec = PyTrendsCollectSpec(
        keywords=["bitcoin", "ethereum"],
        timeframe="today 3-m",  # Last 3 months
        geo="US",  # United States (empty for worldwide)
        include_related_queries=True,
        include_interest_by_region=False
    )

    collector = PyTrendsCollector(config)
    result = await collector.fetch(spec)

    if result.status == "success":
        # Process trend data
        for trend in result.interest_over_time:
            print(f"{trend.date}: {trend.keyword} = {trend.interest}")

        # Show related queries
        for keyword, queries in result.related_queries_top.items():
            print(f"\nTop queries for '{keyword}':")
            for query in queries[:5]:
                print(f"  - {query.query} ({query.value})")
    else:
        print(f"Error: {result.error}")

asyncio.run(main())
```

### GNews API

```python
import asyncio
import os
from connectors.gnews import GNewsCollector, GNewsClientConfig, GNewsCollectSpec

async def main():
    # Configuration
    config = GNewsClientConfig(
        api_key=os.environ["GNEWS_API_KEY"],  # Get from https://gnews.io
        timeout=30
    )

    # Collection specification
    spec = GNewsCollectSpec(
        query="bitcoin OR cryptocurrency",  # Boolean operators supported
        language="en",  # en, es, fr, de, it, pt, ru, zh, ja, ko, ar, hi
        max_results=10,  # Max 100 per request
        sort_by="publishedAt"  # publishedAt or relevance
        # category="technology",  # Optional: technology, business, sports, etc.
        # country="us",  # Optional: us, gb, ca, au, de, fr, etc.
    )

    collector = GNewsCollector(config)
    result = await collector.fetch(spec)

    if result.status == "success":
        for article in result.articles:
            print(f"{article.title}")
            print(f"  Source: {article.source_name}")
            print(f"  Published: {article.published_at}")
            print(f"  URL: {article.url}")
    else:
        print(f"Error: {result.error}")
        # Note: GNews free tier allows 100 requests per day

asyncio.run(main())
```

## Configuration Pattern

All connectors follow a **two-tier configuration pattern**:

### 1. ClientConfig (Library-Owned)

Contains **only credentials and HTTP settings**. Set once, reused for multiple collections.

```python
RedditClientConfig(
    client_id="...",       # Credentials
    client_secret="...",
    user_agent="...",
    timeout=30,            # HTTP settings
    rate_limit=60          # Requests per minute
)
```

- ✅ **Contains**: Credentials, timeouts, rate limits
- ❌ **Does NOT contain**: Subreddits, channels, queries (those are runtime inputs)

### 2. CollectSpec (App-Owned, Runtime)

Describes **what to collect** on each request. Varies per collection.

```python
RedditCollectSpec(
    subreddits=["python", "programming"],  # WHAT to collect
    sort="hot",
    max_posts_per_subreddit=20,
    include_comments=True
)
```

- Passed to `collector.fetch(spec)`
- Serializable (can be loaded from YAML/JSON)
- Different apps can use different specs with the same config

### Why This Pattern?

- **Security**: Credentials stay separate from collection targets
- **Reusability**: One config, many specs
- **Serializability**: Specs can be stored in config files, credentials in environment variables

## Public API Contract

All collectors expose a consistent interface:

```python
# 1. Initialize with credentials
collector = SomeCollector(config)

# 2. Fetch with runtime specification
results = await collector.fetch(spec)

# 3. Get typed Pydantic models
for item in results:
    print(item.field)  # Fully typed!
```

## Architecture

Each connector consists of:

- **`models.py`**: Pydantic models for config and data
- **`client.py`**: Low-level API wrapper
- **`collector.py`**: High-level orchestration (public API)
- **`utils.py`**: Helper functions (YouTube only)

## Error Handling

All connectors raise typed exceptions:

```python
from connectors.common.exceptions import (
    AuthenticationError,     # Invalid credentials
    RateLimitError,          # API rate limit exceeded
    DataFetchError,          # Network/API error
    InvalidConfigError       # Invalid configuration
)

try:
    posts = await collector.fetch(spec)
except AuthenticationError:
    print("Invalid credentials!")
except RateLimitError:
    print("Rate limit exceeded, wait before retrying")
except DataFetchError as e:
    print(f"Fetch failed: {e}")
```

## Retry and Rate Limiting

Built-in retry logic with exponential backoff:

```python
from connectors.common.http import with_retry

@with_retry(max_attempts=5, min_wait=1, max_wait=10)
async def my_api_call():
    # Automatically retries on network errors
    ...
```

Rate limiting to respect API limits:

```python
from connectors.common.http import RateLimiter

limiter = RateLimiter(requests_per_minute=60)
async with limiter:
    # Makes API call
    ...
```

## YouTube: Transcript Sources

The YouTube connector tries multiple transcript methods:

1. **YouTube Transcript API** (fast, free, if available)
2. **Whisper transcription** (slower, uses CPU, always works)

The `transcript_source` field tells you which method was used:

```python
videos = await collector.fetch(spec)
for video in videos:
    if video.transcript_source == 'youtube_api':
        print("Used YouTube API (free captions)")
    elif video.transcript_source == 'whisper':
        print("Used Whisper (audio transcription)")
```

## Telegram: Non-Interactive Authentication

Telegram uses callbacks for 2FA instead of blocking `input()` calls:

```python
# For production: fetch codes from SMS gateway API
async def get_code():
    response = await sms_gateway.fetch_latest_code()
    return response.code

async def get_password():
    return os.environ["TELEGRAM_2FA_PASSWORD"]

config = TelegramClientConfig(
    api_id="...",
    api_hash="...",
    phone="+1234567890",
    auth_code_callback=get_code,        # Custom code retrieval
    auth_password_callback=get_password  # Custom password retrieval
)
```

This pattern allows:

- ✅ Automated authentication
- ✅ Testable code (mock callbacks)
- ✅ Integration with SMS gateways

## Development

```bash
# Clone repository
git clone https://github.com/yourusername/connectors
cd connectors

# Install with dev dependencies
pip install -e .[all,dev]

# Run tests
pytest

# Run with coverage
pytest --cov=src/connectors --cov-report=term-missing

# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

## Testing

Each connector has comprehensive tests:

```bash
# Run all tests
pytest

# Run specific connector tests
pytest tests/reddit/
pytest tests/youtube/

# Run with verbose output
pytest -v
```

## Dependencies

### Core (always installed)

- `pydantic>=2.4.0` - Data validation
- `tenacity>=8.0.0` - Retry logic
- `httpx>=0.24.0` - Async HTTP client

### Optional (per connector)

- **Reddit**: `asyncpraw>=7.7.0`
- **Telegram**: `telethon>=1.34.0`
- **YouTube**: `yt-dlp>=2024.12.0`, `youtube-transcript-api>=0.6.0`, `faster-whisper>=1.1.0`
- **Twitter**: No additional deps (uses httpx from core)
- **PyTrends**: `pytrends>=4.9.0`, `pandas>=2.0.0`
- **GNews**: No additional deps (uses httpx from core)

## What This Library Does NOT Do

This library focuses on **data collection only**. It does NOT:

- ❌ Persist data to databases
- ❌ Provide web APIs (FastAPI, Flask, etc.)
- ❌ Read environment variables (you pass credentials)
- ❌ Normalize data across platforms (raw platform data)

**Your application** handles:

- Database persistence
- API endpoints
- Environment variable loading
- Cross-platform normalization
- Post-processing (LLM, analytics, etc.)

## Migration from Existing Apps

### From Trender

**Before**:

```python
from config import config
from app.services.reddit_collector import RedditDataCollector

collector = RedditDataCollector(config)
posts = await collector.collect_data()
```

**After**:

```python
from connectors.reddit import RedditCollector, RedditClientConfig, RedditCollectSpec

config = RedditClientConfig(
    client_id=os.environ["REDDIT_CLIENT_ID"],
    client_secret=os.environ["REDDIT_CLIENT_SECRET"],
    user_agent="MyApp/1.0"
)
spec = RedditCollectSpec(subreddits=["python"], sort="hot")
collector = RedditCollector(config)
posts = await collector.fetch(spec)  # Note: fetch() not collect_data()
```

## License

MIT License - see [LICENSE](LICENSE) file.

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Ensure all tests pass (`pytest`)
5. Format code (`black src/ tests/`)
6. Submit a pull request

## Support

- **Issues**: https://github.com/yourusername/connectors/issues
- **Documentation**: https://connectors.readthedocs.io
- **Discussions**: https://github.com/yourusername/connectors/discussions

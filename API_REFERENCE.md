# API Reference - Using Connectors as a Library

This guide shows how to use the connectors library **programmatically** from your own applications.

## Installation

```bash
# Install from your application
pip install git+https://github.com/yourusername/connectors.git

# Or install specific connectors
pip install git+https://github.com/yourusername/connectors.git[reddit,youtube]

# Or local development
pip install -e /path/to/connectors[all]
```

## Quick Start - Library Usage

```python
import asyncio
from connectors.reddit import RedditCollector, RedditClientConfig, RedditCollectSpec

async def collect_reddit_data(subreddits, max_posts=10):
    """Collect Reddit data with dynamic configuration."""

    # Configuration (credentials)
    config = RedditClientConfig(
        client_id="your_client_id",
        client_secret="your_secret",
        user_agent="YourApp/1.0"
    )

    # Specification (what to collect - passed from your app)
    spec = RedditCollectSpec(
        subreddits=subreddits,  # Dynamic!
        max_posts_per_subreddit=max_posts,
        sort="hot"
    )

    # Collect and return
    collector = RedditCollector(config)
    posts = await collector.fetch(spec)

    return posts

# Use in your app
if __name__ == "__main__":
    # Get configuration from your app's config system
    my_subreddits = ["python", "programming"]  # From your DB/config

    posts = asyncio.run(collect_reddit_data(my_subreddits, max_posts=20))

    # Process results in your app
    for post in posts:
        print(f"{post.title} - {post.score} points")
```

---

## API Pattern

All connectors follow the same pattern:

### 1. Create Config (Credentials)
```python
config = ConnectorClientConfig(
    # API credentials
    # HTTP settings
)
```

### 2. Create Spec (What to Collect)
```python
spec = ConnectorCollectSpec(
    # Sources (subreddits, channels, etc.)
    # Limits (max_posts, max_videos, etc.)
    # Filters (time, sort, etc.)
)
```

### 3. Fetch Data
```python
collector = Connector(config)
results = await collector.fetch(spec)
```

### 4. Process Results
```python
for item in results:
    # item is a Pydantic model with typed fields
    print(item.field_name)
```

---

## Reddit API

### Configuration

```python
from connectors.reddit import RedditClientConfig

config = RedditClientConfig(
    client_id="your_reddit_client_id",      # Required
    client_secret="your_reddit_secret",     # Required
    user_agent="YourApp/1.0",               # Required
    timeout=30,                             # Optional (default: 30)
    rate_limit=60                           # Optional (default: 60 req/min)
)
```

### Collection Spec (Dynamic Parameters)

```python
from connectors.reddit import RedditCollectSpec

spec = RedditCollectSpec(
    subreddits=["bitcoin", "ethereum"],     # Required: List[str]
    sort="hot",                             # Optional: hot|new|top|rising
    time_filter="day",                      # Optional: hour|day|week|month|year|all
    max_posts_per_subreddit=50,             # Optional: 1-100 (default: 20)
    include_comments=True,                  # Optional: bool (default: True)
    max_comment_depth=None                  # Optional: int|None (default: None)
)
```

### Example: Dynamic Configuration from Database

```python
async def collect_from_user_settings(user_id: int):
    """Collect Reddit data based on user's saved settings."""

    # Get user settings from your database
    user_settings = await db.get_user_settings(user_id)

    config = RedditClientConfig(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        user_agent=f"MyApp/1.0 (user:{user_id})"
    )

    spec = RedditCollectSpec(
        subreddits=user_settings['subreddits'],  # From DB
        max_posts_per_subreddit=user_settings['max_posts'],
        sort=user_settings['sort_method'],
        time_filter=user_settings['time_filter']
    )

    collector = RedditCollector(config)
    return await collector.fetch(spec)
```

### Return Type

```python
List[RedditPost]  # List of Pydantic models

# RedditPost fields:
post.id              # str
post.title           # str
post.text            # str
post.author          # Optional[str]
post.created_at      # datetime
post.num_comments    # int
post.score           # int
post.url             # str
post.subreddit       # str
post.comments        # List[str]
```

---

## YouTube API

### Configuration

```python
from connectors.youtube import YouTubeClientConfig

config = YouTubeClientConfig(
    whisper_model="base",               # Optional: tiny|base|small|medium|large
    use_transcript_api=True,            # Optional: bool (default: True)
    max_video_length=3600,              # Optional: int (default: 3600)
    audio_format="m4a",                 # Optional: m4a|webm|mp3
    compute_type="int8",                # Optional: int8|float16|float32
    timeout=60                          # Optional: int (default: 60)
)
```

### Collection Spec

```python
from connectors.youtube import YouTubeCollectSpec

# Option 1: Collect from channels
spec = YouTubeCollectSpec(
    channels=["@CoinBureau", "@TED"],   # Required if no URLs
    max_videos_per_channel=5,           # Optional: int (default: 5)
    days_back=7                         # Optional: int (default: 7)
)

# Option 2: Collect specific videos
spec = YouTubeCollectSpec(
    urls=[                              # Required if no channels
        "https://youtube.com/watch?v=abc123",
        "https://youtube.com/watch?v=def456"
    ]
)
```

### Example: Collect from User's Favorite Channels

```python
async def collect_youtube_for_user(channels: List[str], days_back: int = 7):
    """Collect YouTube videos from user-specified channels."""

    config = YouTubeClientConfig(
        whisper_model="base",
        use_transcript_api=True
    )

    spec = YouTubeCollectSpec(
        channels=channels,              # Passed from your app
        max_videos_per_channel=10,
        days_back=days_back             # Configurable time range
    )

    collector = YouTubeCollector(config)
    return await collector.fetch(spec)

# Usage
user_channels = await db.get_user_youtube_channels(user_id)
videos = await collect_youtube_for_user(user_channels, days_back=14)
```

### Return Type

```python
List[YouTubeVideo]  # List of Pydantic models

# YouTubeVideo fields:
video.video_id                # str
video.url                     # str
video.title                   # str
video.description             # str
video.duration                # int (seconds)
video.view_count              # int
video.like_count              # int
video.channel                 # str
video.channel_id              # str
video.transcript              # str (full transcript)
video.transcript_source       # str: "youtube_api" | "whisper"
video.upload_date             # Optional[str] (YYYYMMDD)
video.tags                    # List[str]
video.status                  # str: "success" | "failed"
video.processed_at            # datetime
```

---

## Telegram API

### Configuration

```python
from connectors.telegram import TelegramClientConfig

# Define auth callbacks
async def get_code():
    # Your custom code retrieval logic
    return await your_sms_gateway.get_latest_code()

async def get_password():
    return os.environ.get("TELEGRAM_2FA_PASSWORD")

config = TelegramClientConfig(
    api_id="your_api_id",               # Required
    api_hash="your_api_hash",           # Required
    phone="+1234567890",                # Optional
    session_name="your_app_session",    # Optional (default: "connector_session")
    timeout=30,                         # Optional
    auth_code_callback=get_code,        # Optional: async callable
    auth_password_callback=get_password # Optional: async callable
)
```

### Collection Spec

```python
from connectors.telegram import TelegramCollectSpec

spec = TelegramCollectSpec(
    channels=["channel1", "channel2"],  # Required: List[str]
    max_messages_per_channel=200,       # Optional: int (default: 200)
    include_replies=True                # Optional: bool (default: True)
)
```

### Example: Monitor Channels

```python
async def monitor_telegram_channels(channel_list: List[str]):
    """Monitor Telegram channels for new messages."""

    config = TelegramClientConfig(
        api_id=os.environ["TELEGRAM_API_ID"],
        api_hash=os.environ["TELEGRAM_API_HASH"],
        phone=os.environ["TELEGRAM_PHONE"],
        session_name="monitoring_session",
        auth_code_callback=get_code_from_gateway,
        auth_password_callback=get_2fa_password
    )

    spec = TelegramCollectSpec(
        channels=channel_list,          # Dynamic from your app
        max_messages_per_channel=100,
        include_replies=True
    )

    collector = TelegramCollector(config)
    return await collector.fetch(spec)
```

### Return Type

```python
List[TelegramMessage]  # List of Pydantic models

# TelegramMessage fields:
message.message_id           # int
message.channel              # str
message.date                 # datetime
message.text                 # Optional[str]
message.author               # Optional[int]
message.replies              # List[TelegramReply]
```

---

## Twitter API

### Configuration

```python
from connectors.twitter import TwitterClientConfig

config = TwitterClientConfig(
    bearer_token="your_bearer_token",   # Required
    timeout=30,                         # Optional (default: 30)
    rate_limit=15                       # Optional (default: 15 req/15min)
)
```

### Collection Spec

```python
from connectors.twitter import TwitterCollectSpec
from datetime import datetime, timedelta

spec = TwitterCollectSpec(
    query="bitcoin OR ethereum",        # Required: str (Twitter query syntax)
    max_results=100,                    # Optional: 10-100 (default: 10)
    start_time=datetime.now() - timedelta(days=7),  # Optional
    end_time=datetime.now()             # Optional
)
```

### Example: Search with Time Range

```python
async def search_twitter(keywords: List[str], days_back: int = 7):
    """Search Twitter with dynamic keywords and time range."""

    config = TwitterClientConfig(
        bearer_token=os.environ["TWITTER_BEARER_TOKEN"]
    )

    # Build query from keywords
    query = " OR ".join(keywords) + " -is:retweet"

    spec = TwitterCollectSpec(
        query=query,
        max_results=100,
        start_time=datetime.now() - timedelta(days=days_back)
    )

    collector = TwitterCollector(config)
    return await collector.fetch(spec)

# Usage
keywords = await db.get_user_keywords(user_id)
tweets = await search_twitter(keywords, days_back=14)
```

### Return Type

```python
List[Tweet]  # List of Pydantic models

# Tweet fields:
tweet.id                     # str
tweet.text                   # str
tweet.author_id              # str
tweet.created_at             # datetime
tweet.like_count             # Optional[int]
tweet.retweet_count          # Optional[int]
tweet.reply_count            # Optional[int]
tweet.quote_count            # Optional[int]
```

---

## Complete Example: Multi-Source Collection

```python
"""Example: Collect from multiple sources based on app config."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any

from connectors.reddit import RedditCollector, RedditClientConfig, RedditCollectSpec
from connectors.youtube import YouTubeCollector, YouTubeClientConfig, YouTubeCollectSpec
from connectors.twitter import TwitterCollector, TwitterClientConfig, TwitterCollectSpec


async def collect_all_sources(app_config: Dict[str, Any]) -> Dict[str, List]:
    """
    Collect from all sources based on application configuration.

    Args:
        app_config: Dictionary with collection settings from your app

    Returns:
        Dictionary with collected data from each source
    """
    results = {}

    # Reddit
    if app_config.get('reddit_enabled'):
        reddit_config = RedditClientConfig(
            client_id=app_config['reddit_client_id'],
            client_secret=app_config['reddit_client_secret'],
            user_agent=app_config['reddit_user_agent']
        )

        reddit_spec = RedditCollectSpec(
            subreddits=app_config['reddit_subreddits'],
            max_posts_per_subreddit=app_config['reddit_max_posts'],
            sort=app_config.get('reddit_sort', 'hot')
        )

        reddit_collector = RedditCollector(reddit_config)
        results['reddit'] = await reddit_collector.fetch(reddit_spec)

    # YouTube
    if app_config.get('youtube_enabled'):
        youtube_config = YouTubeClientConfig(
            whisper_model=app_config.get('youtube_whisper_model', 'base'),
            use_transcript_api=True
        )

        youtube_spec = YouTubeCollectSpec(
            channels=app_config['youtube_channels'],
            max_videos_per_channel=app_config['youtube_max_videos'],
            days_back=app_config.get('youtube_days_back', 7)
        )

        youtube_collector = YouTubeCollector(youtube_config)
        results['youtube'] = await youtube_collector.fetch(youtube_spec)

    # Twitter
    if app_config.get('twitter_enabled'):
        twitter_config = TwitterClientConfig(
            bearer_token=app_config['twitter_bearer_token']
        )

        twitter_spec = TwitterCollectSpec(
            query=app_config['twitter_query'],
            max_results=app_config.get('twitter_max_results', 100),
            start_time=datetime.now() - timedelta(days=app_config.get('twitter_days_back', 7))
        )

        twitter_collector = TwitterCollector(twitter_config)
        results['twitter'] = await twitter_collector.fetch(twitter_spec)

    return results


# Usage in your application
if __name__ == "__main__":
    # Load config from your app's config system
    my_app_config = {
        'reddit_enabled': True,
        'reddit_client_id': 'xxx',
        'reddit_client_secret': 'yyy',
        'reddit_user_agent': 'MyApp/1.0',
        'reddit_subreddits': ['python', 'programming'],
        'reddit_max_posts': 20,
        'reddit_sort': 'hot',

        'youtube_enabled': True,
        'youtube_channels': ['@TED', '@Veritasium'],
        'youtube_max_videos': 5,
        'youtube_days_back': 7,

        'twitter_enabled': False,
    }

    # Collect data
    data = asyncio.run(collect_all_sources(my_app_config))

    # Process in your app
    for source, items in data.items():
        print(f"Collected {len(items)} items from {source}")
```

---

## Error Handling

```python
from connectors.common.exceptions import (
    AuthenticationError,
    RateLimitError,
    DataFetchError,
    InvalidConfigError
)

async def safe_collect():
    """Example with proper error handling."""
    try:
        collector = RedditCollector(config)
        posts = await collector.fetch(spec)
        return posts

    except AuthenticationError as e:
        # Invalid credentials
        logger.error(f"Auth failed: {e}")
        raise

    except RateLimitError as e:
        # Hit rate limit
        logger.warning(f"Rate limited: {e}")
        # Maybe retry later?
        await asyncio.sleep(60)

    except DataFetchError as e:
        # Network or API error
        logger.error(f"Fetch failed: {e}")
        return []

    except InvalidConfigError as e:
        # Bad configuration
        logger.error(f"Invalid config: {e}")
        raise
```

---

## Integration Patterns

### Pattern 1: Background Task

```python
# In your FastAPI/Flask app
from celery import Celery

app = Celery('myapp')

@app.task
async def collect_reddit_task(subreddits: List[str]):
    """Background task to collect Reddit data."""
    config = RedditClientConfig(...)
    spec = RedditCollectSpec(subreddits=subreddits)

    collector = RedditCollector(config)
    posts = await collector.fetch(spec)

    # Save to database
    await db.save_posts(posts)
```

### Pattern 2: Scheduled Collection

```python
# Using APScheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('interval', hours=6)
async def collect_data():
    """Collect data every 6 hours."""
    channels = await db.get_active_channels()
    data = await collect_youtube_for_user(channels)
    await db.store_data(data)

scheduler.start()
```

### Pattern 3: API Endpoint

```python
# FastAPI endpoint
from fastapi import FastAPI, BackgroundTasks

app = FastAPI()

@app.post("/collect/reddit")
async def trigger_reddit_collection(
    subreddits: List[str],
    background_tasks: BackgroundTasks
):
    """Trigger Reddit collection via API."""
    background_tasks.add_task(collect_and_save, subreddits)
    return {"status": "started", "subreddits": subreddits}

async def collect_and_save(subreddits: List[str]):
    config = RedditClientConfig(...)
    spec = RedditCollectSpec(subreddits=subreddits)
    collector = RedditCollector(config)
    posts = await collector.fetch(spec)
    await db.save(posts)
```

---

## Best Practices

1. **Separate Credentials from Spec**
   - Store credentials in environment variables or secret manager
   - Pass collection targets (subreddits, channels) dynamically from your app

2. **Reuse Config Objects**
   - Create config once, reuse for multiple collections
   - Only create new specs for different collection requests

3. **Handle Errors Gracefully**
   - Always wrap collector calls in try/except
   - Log errors for debugging
   - Return empty lists on failure rather than crashing

4. **Respect Rate Limits**
   - Use built-in rate limiting
   - Implement exponential backoff for retries
   - Monitor API usage

5. **Process Results Efficiently**
   - Results are Pydantic models - convert to dict if needed
   - Use `model_dump()` or `.dict()` for serialization
   - Filter/transform before storing

---

## Data Models

All return types are Pydantic models. Convert to dict:

```python
# Single item
post_dict = post.model_dump()  # or post.dict()

# List of items
posts_dicts = [p.model_dump() for p in posts]

# To JSON
import json
json_str = json.dumps(posts_dicts, default=str)
```

---

## Summary

**For external apps:**
1. Import connector classes
2. Create config with credentials (once)
3. Create spec with dynamic parameters (per request)
4. Call `await collector.fetch(spec)`
5. Process returned Pydantic models

**All connectors return:**
- List of typed Pydantic models
- Consistent error exceptions
- Async/await interface

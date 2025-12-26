# Library Usage Summary - For External Applications

## 🎯 Overview

This library is **ready for use by external applications**. Other apps can import and use these connectors to collect social media data with dynamic configuration.

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| **[API_REFERENCE.md](API_REFERENCE.md)** | Complete API docs for external apps |
| **[README.md](README.md)** | Quick start and examples |
| **[OUTPUT_GUIDE.md](OUTPUT_GUIDE.md)** | Data formats and output structure |
| **[YOUTUBE_CONFIG_GUIDE.md](YOUTUBE_CONFIG_GUIDE.md)** | YouTube-specific configuration |
| **[GIT_READY_CHECKLIST.md](GIT_READY_CHECKLIST.md)** | Pre-push security checklist |

---

## 🔌 How External Apps Use This Library

### 1. Install the Library

```bash
# From GitHub
pip install git+https://github.com/YOURUSERNAME/connectors.git[all]

# Or specific connectors
pip install git+https://github.com/YOURUSERNAME/connectors.git[reddit,youtube]
```

### 2. Import and Use

```python
from connectors.reddit import RedditCollector, RedditClientConfig, RedditCollectSpec
import os

async def collect_for_user(user_subreddits: list):
    """Function your app calls with dynamic configuration."""

    # Config (credentials - from environment)
    config = RedditClientConfig(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        user_agent="MyApp/1.0"
    )

    # Spec (what to collect - passed from your app)
    spec = RedditCollectSpec(
        subreddits=user_subreddits,  # Dynamic!
        max_posts_per_subreddit=50
    )

    # Fetch
    collector = RedditCollector(config)
    return await collector.fetch(spec)
```

### 3. Dynamic Configuration

Your app can pass configuration at runtime:

```python
# From database
user_config = await db.get_user_config(user_id)
posts = await collect_for_user(user_config['subreddits'])

# From API request
@app.post("/collect")
async def api_collect(subreddits: List[str]):
    posts = await collect_for_user(subreddits)
    return {"count": len(posts), "posts": posts}

# From file
config = yaml.load(open('config.yaml'))
posts = await collect_for_user(config['reddit']['subreddits'])
```

---

## 📋 API Patterns

### All Connectors Follow This Pattern:

```python
# 1. Config (credentials)
config = ConnectorClientConfig(api_credentials...)

# 2. Spec (what to collect)
spec = ConnectorCollectSpec(channels=..., max_items=...)

# 3. Collect
collector = Connector(config)
results = await collector.fetch(spec)

# 4. Process (results are Pydantic models)
for item in results:
    print(item.title, item.score)
```

### Dynamic Parameters You Can Pass

**Reddit:**
- `subreddits: List[str]` - Which subreddits to collect from
- `max_posts_per_subreddit: int` - How many posts
- `sort: str` - hot, new, top, rising
- `time_filter: str` - hour, day, week, month

**YouTube:**
- `channels: List[str]` - Which YouTube channels (@username)
- `urls: List[str]` - Or specific video URLs
- `max_videos_per_channel: int` - How many videos
- `days_back: int` - How far back to go

**Telegram:**
- `channels: List[str]` - Which Telegram channels
- `max_messages_per_channel: int` - How many messages
- `include_replies: bool` - Include replies or not

**Twitter:**
- `query: str` - Search query (keywords)
- `max_results: int` - How many tweets (10-100)
- `start_time: datetime` - Time range start
- `end_time: datetime` - Time range end

---

## 🔄 Return Types

All connectors return **Lists of Pydantic models:**

```python
# Reddit
List[RedditPost]
post.id, post.title, post.author, post.score, post.comments, ...

# YouTube
List[YouTubeVideo]
video.video_id, video.title, video.transcript, video.duration, ...

# Telegram
List[TelegramMessage]
message.message_id, message.text, message.channel, message.replies, ...

# Twitter
List[Tweet]
tweet.id, tweet.text, tweet.author_id, tweet.like_count, ...
```

### Convert to Dict/JSON

```python
# Single item
post_dict = post.model_dump()  # or .dict()

# List
posts_dicts = [p.model_dump() for p in posts]

# JSON
import json
json_str = json.dumps(posts_dicts, default=str)
```

---

## 🏗️ Integration Examples

### FastAPI Endpoint

```python
from fastapi import FastAPI
from connectors.reddit import RedditCollector, RedditClientConfig, RedditCollectSpec

app = FastAPI()

@app.post("/collect/reddit")
async def collect_reddit(subreddits: List[str], max_posts: int = 20):
    config = RedditClientConfig(...)
    spec = RedditCollectSpec(
        subreddits=subreddits,
        max_posts_per_subreddit=max_posts
    )

    collector = RedditCollector(config)
    posts = await collector.fetch(spec)

    return {
        "count": len(posts),
        "posts": [p.model_dump() for p in posts]
    }
```

### Celery Background Task

```python
from celery import Celery
from connectors.youtube import YouTubeCollector, YouTubeClientConfig, YouTubeCollectSpec

app = Celery('myapp')

@app.task
async def collect_youtube_task(channels: List[str]):
    config = YouTubeClientConfig(...)
    spec = YouTubeCollectSpec(channels=channels)

    collector = YouTubeCollector(config)
    videos = await collector.fetch(spec)

    # Save to database
    await db.save_videos(videos)
```

### Scheduled Collection

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from connectors.twitter import TwitterCollector, TwitterClientConfig, TwitterCollectSpec

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('interval', hours=6)
async def collect_tweets():
    # Get config from database
    keywords = await db.get_tracking_keywords()

    config = TwitterClientConfig(...)
    spec = TwitterCollectSpec(
        query=" OR ".join(keywords),
        max_results=100
    )

    collector = TwitterCollector(config)
    tweets = await collector.fetch(spec)

    await db.store_tweets(tweets)
```

---

## 🔐 Security - Credentials Management

### ✅ Correct - Credentials Separate from Code

```python
# In your application
config = RedditClientConfig(
    client_id=os.environ["REDDIT_CLIENT_ID"],  # From environment
    client_secret=os.environ["REDDIT_CLIENT_SECRET"],
    user_agent="MyApp/1.0"
)

# Or from secret manager
from your_secret_manager import get_secret

config = RedditClientConfig(
    client_id=get_secret("reddit_client_id"),
    client_secret=get_secret("reddit_client_secret"),
    user_agent="MyApp/1.0"
)
```

### ❌ Incorrect - Hardcoded Credentials

```python
# DON'T DO THIS
config = RedditClientConfig(
    client_id="abc123",  # Never hardcode!
    client_secret="secret123",
    user_agent="MyApp/1.0"
)
```

---

## 📊 Example: Multi-User Application

```python
"""Example: Multi-tenant app where each user has their own config."""

async def collect_for_user(user_id: int):
    """Collect data for a specific user based on their settings."""

    # Get user preferences from database
    user_prefs = await db.get_user_preferences(user_id)

    results = {}

    # Reddit - if user has enabled it
    if user_prefs.reddit_enabled:
        config = RedditClientConfig(
            client_id=os.environ["REDDIT_CLIENT_ID"],
            client_secret=os.environ["REDDIT_CLIENT_SECRET"],
            user_agent=f"MyApp/1.0 (user:{user_id})"
        )

        spec = RedditCollectSpec(
            subreddits=user_prefs.reddit_subreddits,  # User's choices
            max_posts_per_subreddit=user_prefs.reddit_max_posts,
            sort=user_prefs.reddit_sort
        )

        collector = RedditCollector(config)
        results['reddit'] = await collector.fetch(spec)

    # YouTube - if user has enabled it
    if user_prefs.youtube_enabled:
        config = YouTubeClientConfig(whisper_model="base")

        spec = YouTubeCollectSpec(
            channels=user_prefs.youtube_channels,  # User's channels
            max_videos_per_channel=user_prefs.youtube_max_videos,
            days_back=user_prefs.youtube_days_back
        )

        collector = YouTubeCollector(config)
        results['youtube'] = await collector.fetch(spec)

    # Save to user's collection
    await db.save_user_collection(user_id, results)

    return results
```

---

## 🚀 Ready for Production

### What's Included

✅ **Type Safety**
- All configs and return types are Pydantic models
- Full IDE autocomplete and type checking

✅ **Error Handling**
- Typed exceptions for all error cases
- Automatic retries with exponential backoff
- Rate limiting built-in

✅ **Testing**
- Comprehensive test suite
- Mock-friendly for unit testing your app
- Integration tests for real API calls

✅ **Documentation**
- API reference
- Usage examples
- Integration patterns

✅ **Security**
- No credentials in code
- `.env` properly gitignored
- Examples use environment variables

---

## 📖 Quick Reference

| Task | Code |
|------|------|
| **Install** | `pip install git+https://github.com/USER/connectors.git[all]` |
| **Import** | `from connectors.reddit import RedditCollector, RedditClientConfig, RedditCollectSpec` |
| **Configure** | `config = RedditClientConfig(client_id=..., client_secret=..., user_agent=...)` |
| **Specify** | `spec = RedditCollectSpec(subreddits=[...], max_posts_per_subreddit=...)` |
| **Collect** | `collector = RedditCollector(config); posts = await collector.fetch(spec)` |
| **Process** | `for post in posts: print(post.title, post.score)` |
| **To Dict** | `post_dict = post.model_dump()` |
| **To JSON** | `json.dumps([p.model_dump() for p in posts], default=str)` |

---

## 🔗 What to Update Before Publishing

1. **GitHub URL**: Replace `yourusername` in:
   - `README.md`
   - `pyproject.toml`
   - This file

2. **Author Info**: Update in `pyproject.toml`:
   ```toml
   authors = [{name = "Your Name", email = "your.email@example.com"}]
   ```

3. **Repository URLs**: Update all GitHub links to your actual repo

---

## ✅ Git Ready Status

- ✅ No credentials in code
- ✅ `.env` is gitignored
- ✅ Examples use `os.environ`
- ✅ Tests don't contain secrets
- ✅ Documentation is complete
- ✅ API is well-defined

**Ready to `git push`!**

See [GIT_READY_CHECKLIST.md](GIT_READY_CHECKLIST.md) for final verification steps.

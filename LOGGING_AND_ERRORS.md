# Logging and Error Handling Guide

This guide explains how the connectors library handles logging and errors, and how to use them in your application.

## Quick Start

### Enable Logging

```python
from connectors import setup_logging

# Simple setup with INFO level
setup_logging(level="INFO")

# Or DEBUG level for more detail
setup_logging(level="DEBUG")
```

### Disable Logging

```python
from connectors import disable_logging

# Disable all library logging (production)
disable_logging()
```

---

## Logging Levels

### DEBUG
- Shows detailed internal operations
- Useful for development and troubleshooting
- Example: Audio downloads, API calls, transcript processing

### INFO (Recommended)
- Shows high-level progress
- Useful for production monitoring
- Example: "Processing 10 videos...", "Collected 50 posts"

### WARNING
- Shows potential issues that didn't cause failures
- Example: "Invalid URL skipped", "Rate limit approaching"

### ERROR
- Shows failures with context
- Example: "Error processing video ABC: Transcript unavailable"

### CRITICAL
- Shows severe errors only
- Rarely used in this library

---

## Error Handling

### All Results Include Status

Every item returned from collectors has a `status` field:

```python
from connectors.youtube import YouTubeCollector, YouTubeClientConfig, YouTubeCollectSpec

collector = YouTubeCollector(config)
videos = await collector.fetch(spec)

# Videos include BOTH successes and failures
for video in videos:
    if video.status == 'success':
        print(f"✓ {video.title}")
        # Process the video
    else:  # status == 'failed'
        print(f"✗ {video.url}: {video.error}")
        # Handle failure (retry, log, alert, etc.)
```

### Filtering Results

```python
# Get only successful items
successful = [v for v in videos if v.status == 'success']

# Get only failed items
failed = [v for v in videos if v.status == 'failed']

# Count by status
success_count = sum(1 for v in videos if v.status == 'success')
fail_count = len(videos) - success_count
```

### Error Information

Failed items include an `error` field with details:

```python
for video in videos:
    if video.status == 'failed':
        print(f"URL: {video.url}")
        print(f"Error: {video.error}")

        # Decide what to do
        if "rate limit" in video.error.lower():
            # Retry later
            pass
        elif "transcript" in video.error.lower():
            # Skip, no transcript available
            pass
        else:
            # Log for investigation
            logger.error(f"Unexpected error: {video.error}")
```

---

## Exception Types

The library defines custom exceptions for different error scenarios:

```python
from connectors import (
    ConnectorError,         # Base exception
    AuthenticationError,    # Invalid credentials
    RateLimitError,        # API rate limit exceeded
    InvalidConfigError,    # Bad configuration
    DataFetchError,        # Failed to fetch data
)

try:
    collector = YouTubeCollector(config)
    videos = await collector.fetch(spec)
except AuthenticationError as e:
    # Handle auth issues
    print(f"Authentication failed: {e}")
except RateLimitError as e:
    # Wait and retry
    print(f"Rate limited: {e}")
except InvalidConfigError as e:
    # Fix configuration
    print(f"Invalid config: {e}")
except DataFetchError as e:
    # Handle fetch error
    print(f"Data fetch failed: {e}")
except ConnectorError as e:
    # Catch-all for other connector errors
    print(f"Connector error: {e}")
```

---

## Custom Logging Configuration

### Use Your Own Logger

```python
import logging

# Configure logging yourself
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# The library will use your configuration
from connectors.youtube import YouTubeCollector
# ... library will log using your settings
```

### Get Library Logger

```python
import logging

# Get the connectors logger
logger = logging.getLogger('connectors')

# Add custom handlers
handler = logging.FileHandler('connectors.log')
handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
logger.addHandler(handler)
```

### Module-Specific Logging

```python
import logging

# Control logging per module
logging.getLogger('connectors.youtube').setLevel(logging.DEBUG)
logging.getLogger('connectors.reddit').setLevel(logging.WARNING)
logging.getLogger('connectors.telegram').setLevel(logging.ERROR)
```

---

## Production Recommendations

### Option 1: INFO Level with Error Monitoring

```python
from connectors import setup_logging

# Show progress but not too verbose
setup_logging(level="INFO")

# Monitor for errors
videos = await collector.fetch(spec)
failed = [v for v in videos if v.status == 'failed']

if failed:
    # Alert/log to monitoring system
    alert_monitoring_system(f"{len(failed)} videos failed")
```

### Option 2: Custom Handler for Production

```python
import logging
from connectors import setup_logging

# Set up logging
setup_logging(level="WARNING")

# Add custom handler for errors
logger = logging.getLogger('connectors')
error_handler = YourErrorTrackingHandler()  # Sentry, CloudWatch, etc.
error_handler.setLevel(logging.ERROR)
logger.addHandler(error_handler)
```

### Option 3: Disable Library Logging

```python
from connectors import disable_logging

# Disable all library logs
disable_logging()

# Handle errors programmatically only
videos = await collector.fetch(spec)
for video in videos:
    if video.status == 'failed':
        # Your error handling
        log_to_your_system(video.error)
```

---

## Integration Examples

### With FastAPI

```python
from fastapi import FastAPI
from connectors import setup_logging
from connectors.youtube import YouTubeCollector, YouTubeClientConfig, YouTubeCollectSpec
import logging

app = FastAPI()

# Configure logging once at startup
@app.on_event("startup")
async def startup():
    setup_logging(level="INFO")

@app.post("/collect-videos")
async def collect_videos(channels: list[str]):
    config = YouTubeClientConfig(whisper_model="base")
    spec = YouTubeCollectSpec(channels=channels, max_videos_per_channel=5)

    collector = YouTubeCollector(config)
    videos = await collector.fetch(spec)

    # Return both successes and failures
    return {
        "total": len(videos),
        "successful": [v.dict() for v in videos if v.status == 'success'],
        "failed": [
            {"url": v.url, "error": v.error}
            for v in videos if v.status == 'failed'
        ]
    }
```

### With Celery Tasks

```python
from celery import Celery
from connectors import setup_logging
from connectors.reddit import RedditCollector, RedditClientConfig, RedditCollectSpec

app = Celery('tasks')

# Set up logging for workers
setup_logging(level="INFO")

@app.task
def collect_reddit_data(subreddits):
    config = RedditClientConfig(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent="MyApp/1.0"
    )
    spec = RedditCollectSpec(subreddits=subreddits, limit=100)

    collector = RedditCollector(config)
    posts = collector.fetch(spec)  # Note: Reddit is sync, not async

    # Save successful posts
    successful = [p for p in posts if p.status == 'success']
    save_to_database(successful)

    # Alert on failures
    failed = [p for p in posts if p.status == 'failed']
    if failed:
        alert_admin(f"{len(failed)} posts failed to collect")

    return {
        "success_count": len(successful),
        "fail_count": len(failed)
    }
```

---

## Debugging Tips

### Enable Debug Logging

```python
from connectors import setup_logging

# See everything
setup_logging(level="DEBUG")
```

### Check What Failed

```python
videos = await collector.fetch(spec)

# Print all errors
for video in videos:
    if video.status == 'failed':
        print(f"Failed: {video.url}")
        print(f"  Error: {video.error}")
        print(f"  Video ID: {video.video_id}")
```

### Log to File

```python
import logging
from connectors import setup_logging

setup_logging(level="DEBUG")

# Add file handler
logger = logging.getLogger('connectors')
file_handler = logging.FileHandler('debug.log')
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
```

---

## Summary

✅ **DO**:
- Use `setup_logging()` for simple configuration
- Check `status` field on all returned items
- Handle failures programmatically (retry, skip, alert)
- Use INFO level in production
- Use DEBUG level when troubleshooting

❌ **DON'T**:
- Assume all returned items are successful
- Ignore the `error` field on failed items
- Use DEBUG level in production (too verbose)
- Catch exceptions without re-raising or handling
- Filter out failures without checking them first

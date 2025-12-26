# Output Guide - What You Get & Where It's Saved

## 📁 Output Directory Structure

When you run `python examples\my_crypto_collector.py`, it creates:

```
output/
├── reddit_20251224_143022.json          # Reddit posts (JSON)
├── reddit_20251224_143022.csv           # Reddit posts (CSV)
├── telegram_20251224_143022.json        # Telegram messages (JSON)
├── telegram_20251224_143022.csv         # Telegram messages (CSV)
├── youtube_20251224_143022.json         # YouTube videos (JSON)
├── youtube_20251224_143022.csv          # YouTube videos (CSV)
├── combined_20251224_143022.json        # All data in one file
└── transcripts/                         # YouTube transcripts as text files
    ├── dQw4w9WgXcQ_Bitcoin_Analysis_2024.txt
    ├── abc123xyz_Crypto_Market_Update.txt
    └── ...
```

---

## 📊 Data Formats

### JSON Format (Structured, Machine-Readable)

**reddit_TIMESTAMP.json:**
```json
[
  {
    "id": "abc123",
    "title": "Bitcoin hits new ATH!",
    "text": "Post content here...",
    "author": "crypto_trader",
    "score": 1234,
    "num_comments": 567,
    "url": "https://reddit.com/r/CryptoCurrency/comments/...",
    "subreddit": "CryptoCurrency",
    "comments": ["Great news!", "To the moon!", ...],
    "created_at": "2025-12-24T14:30:22"
  },
  ...
]
```

**youtube_TIMESTAMP.json:**
```json
[
  {
    "video_id": "dQw4w9WgXcQ",
    "title": "Bitcoin Analysis 2024 - Bull Market Incoming?",
    "channel": "Coin Bureau",
    "duration": 1234,
    "view_count": 150000,
    "like_count": 5000,
    "upload_date": "20251224",
    "transcript": "Welcome back to Coin Bureau! Today we're analyzing...",
    "transcript_source": "youtube_api",
    "tags": ["bitcoin", "crypto", "analysis"],
    "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
    "status": "success"
  },
  ...
]
```

**telegram_TIMESTAMP.json:**
```json
[
  {
    "message_id": 12345,
    "channel": "CryptoSignals",
    "date": "2025-12-24T14:30:22",
    "text": "BTC LONG signal - Entry: 42000, Target: 45000, Stop: 41000",
    "author": 123456789,
    "replies": [
      {
        "message_id": 12346,
        "date": "2025-12-24T14:35:00",
        "text": "Thanks for the signal!",
        "author": 987654321
      }
    ]
  },
  ...
]
```

### CSV Format (Spreadsheet, Excel-Compatible)

**youtube_TIMESTAMP.csv:**
```
video_id,title,channel,duration,view_count,like_count,transcript_source,transcript,status,url,...
dQw4w9WgXcQ,"Bitcoin Analysis 2024","Coin Bureau",1234,150000,5000,youtube_api,"Welcome back...",success,https://...
abc123xyz,"Crypto Market Update","DataDash",890,75000,3200,whisper,"Today we discuss...",success,https://...
```

**reddit_TIMESTAMP.csv:**
```
id,title,subreddit,author,score,num_comments,comments,url,created_at,...
abc123,"Bitcoin hits new ATH!",CryptoCurrency,crypto_trader,1234,567,"[""Great news!""]",https://...,2025-12-24T14:30:22
```

### Text Files (YouTube Transcripts)

**transcripts/dQw4w9WgXcQ_Bitcoin_Analysis_2024.txt:**
```
Title: Bitcoin Analysis 2024 - Bull Market Incoming?
Channel: Coin Bureau
URL: https://youtube.com/watch?v=dQw4w9WgXcQ
Duration: 1234s
Views: 150,000
Transcript Source: youtube_api

================================================================================

Welcome back to Coin Bureau! Today we're analyzing Bitcoin's recent price
action and what it means for the broader crypto market. Let's dive in...

[Full transcript continues for thousands of words...]
```

---

## 🎯 YouTube Data - Detailed Breakdown

### What Each YouTube Video Contains

```python
YouTubeVideo(
    # Identifiers
    video_id="dQw4w9WgXcQ",           # YouTube video ID
    url="https://youtube.com/watch?v=dQw4w9WgXcQ",

    # Metadata
    title="Bitcoin Analysis 2024",    # Video title
    description="In this video...",    # Full description
    channel="Coin Bureau",             # Channel name
    channel_id="UCqK_GSMbpiV8spgD3ZGloSw",

    # Stats
    duration=1234,                     # Length in seconds
    view_count=150000,                 # Total views
    like_count=5000,                   # Total likes
    upload_date="20251224",            # Upload date (YYYYMMDD)

    # Content
    transcript="Welcome back to...",   # FULL video transcript
    transcript_source="youtube_api",   # How we got it
    language="en",                     # Detected language
    language_probability=0.99,         # Confidence

    # Metadata
    tags=["bitcoin", "crypto"],        # Video tags
    categories=["Education"],          # YouTube categories
    thumbnail="https://i.ytimg.com/vi/...",

    # Processing
    processed_at=datetime(...),        # When we processed it
    status="success",                  # "success" or "failed"
    error=None                         # Error message if failed
)
```

### YouTube Transcript Quality

**transcript_source values:**

1. **"youtube_api"** (Best Quality)
   - Official YouTube captions
   - Human-written or auto-generated by YouTube
   - Perfect punctuation, capitalization
   - Very fast (seconds)
   - Example: "Welcome back to Coin Bureau! Today we're analyzing..."

2. **"whisper"** (High Quality)
   - AI transcription using OpenAI Whisper
   - Very accurate speech-to-text
   - Good punctuation
   - Slower (30-60 sec per 5 min video)
   - Example: "welcome back to coin bureau today were analyzing"

### Transcript Length

- **Short video (5 min):** ~750-1000 words
- **Medium video (15 min):** ~2250-3000 words
- **Long video (1 hour):** ~9000-12000 words

---

## 📈 Combined JSON Format

**combined_TIMESTAMP.json:**
```json
{
  "collected_at": "2025-12-24T14:30:22",
  "sources": {
    "reddit": {
      "count": 40,
      "items": [...]
    },
    "telegram": {
      "count": 200,
      "items": [...]
    },
    "youtube": {
      "count": 9,
      "items": [...]
    }
  }
}
```

---

## 💡 How to Use the Output

### Option 1: Load JSON in Python
```python
import json

# Load Reddit data
with open('output/reddit_20251224_143022.json', 'r') as f:
    reddit_posts = json.load(f)

for post in reddit_posts:
    print(f"{post['title']} - Score: {post['score']}")
```

### Option 2: Open CSV in Excel/Google Sheets
1. Open Excel
2. File → Open → Select CSV file
3. Data will be in spreadsheet format
4. Sort, filter, analyze as needed

### Option 3: Read YouTube Transcripts
```bash
# View a transcript
cat output/transcripts/dQw4w9WgXcQ_Bitcoin_Analysis_2024.txt

# Search all transcripts
grep -r "bull market" output/transcripts/
```

### Option 4: Use in Your Code
```python
from my_crypto_collector import main
import asyncio

# Collect data
data = asyncio.run(main())

# Access directly
for video in data['youtube']:
    if video.status == 'success':
        print(f"Title: {video.title}")
        print(f"Transcript: {video.transcript[:200]}...")
```

---

## 🔍 Example: YouTube Video Data

When you collect from @CoinBureau, you get:

```json
{
  "video_id": "xyz789abc",
  "url": "https://youtube.com/watch?v=xyz789abc",
  "title": "Bitcoin Price Prediction 2025 - $100K Incoming?",
  "description": "In this video, we analyze Bitcoin's price action...",
  "channel": "Coin Bureau",
  "channel_id": "UCqK_GSMbpiV8spgD3ZGloSw",
  "duration": 1854,
  "view_count": 234567,
  "like_count": 12345,
  "upload_date": "20251223",
  "transcript": "Hey guys, welcome back to another Coin Bureau video! Today we're going to discuss Bitcoin's recent price movements and what this could mean for 2025. Let's start by looking at the charts. As you can see, Bitcoin has been consolidating in this range for the past few weeks. The key support level is at $40,000...",
  "transcript_source": "youtube_api",
  "language": "en",
  "language_probability": 0.99,
  "tags": ["bitcoin", "cryptocurrency", "bitcoin price prediction", "crypto", "btc"],
  "categories": ["Education"],
  "thumbnail": "https://i.ytimg.com/vi/xyz789abc/maxresdefault.jpg",
  "processed_at": "2025-12-24T14:35:22.123456",
  "status": "success",
  "error": null
}
```

**This gives you:**
- ✅ Full video transcript (thousands of words)
- ✅ All metadata (views, likes, duration)
- ✅ Channel information
- ✅ Upload date for filtering
- ✅ Tags for categorization

---

## 🚀 Quick Examples

### Find Most Popular Reddit Posts
```python
import json

with open('output/reddit_20251224_143022.json', 'r') as f:
    posts = json.load(f)

# Sort by score
top_posts = sorted(posts, key=lambda x: x['score'], reverse=True)[:10]

for post in top_posts:
    print(f"{post['score']:>6} | {post['title']}")
```

### Analyze YouTube Topics
```python
import json
from collections import Counter

with open('output/youtube_20251224_143022.json', 'r') as f:
    videos = json.load(f)

# Count tag frequency
all_tags = []
for video in videos:
    all_tags.extend(video['tags'])

top_tags = Counter(all_tags).most_common(10)
print("Top tags:", top_tags)
```

### Search Telegram for Keywords
```python
import json

with open('output/telegram_20251224_143022.json', 'r') as f:
    messages = json.load(f)

# Find messages mentioning "BTC"
btc_messages = [m for m in messages if m['text'] and 'BTC' in m['text']]

print(f"Found {len(btc_messages)} messages about BTC")
```

---

## 📝 Summary

**You Get:**
- ✅ JSON files (one per source + combined)
- ✅ CSV files (Excel-compatible)
- ✅ Text files (YouTube transcripts)
- ✅ All saved to `output/` directory
- ✅ Timestamped filenames
- ✅ Full metadata for every item

**YouTube Specifically:**
- ✅ Full video transcripts (thousands of words)
- ✅ Video metadata (views, likes, duration)
- ✅ Separate text files for easy reading
- ✅ Transcript source indicator (YouTube API vs Whisper)

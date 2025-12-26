"""Reddit connector example.

Shows how to collect posts from subreddits with comments.
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from connectors import setup_logging
from connectors.reddit import (
    RedditCollector,
    RedditClientConfig,
    RedditCollectSpec,
)


async def main():
    # Load environment variables from .env file
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)

    # Set up logging
    setup_logging(level="INFO")

    # Configuration (credentials from environment)
    config = RedditClientConfig(
        client_id=os.getenv("REDDIT_CLIENT_ID", "your_client_id"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET", "your_client_secret"),
        user_agent="ConnectorsExample/1.0",
        rate_limit=60,  # 60 requests per minute
    )

    # Collection specification
    spec = RedditCollectSpec(
        subreddits=["python", "learnpython"],
        sort="hot",  # hot, new, top, rising
        time_filter="day",  # hour, day, week, month, year, all
        max_posts_per_subreddit=10,
        include_comments=True,
    )

    # Collect data
    print(f"Collecting from r/{', r/'.join(spec.subreddits)}...")
    collector = RedditCollector(config)
    posts = await collector.fetch(spec)

    # Display results
    print(f"\nCollected {len(posts)} posts\n")

    for post in posts[:3]:  # Show first 3 posts
        print(f"[r/{post.subreddit}] {post.title}")
        print(f"  By: {post.author}")
        print(f"  Score: {post.score} | Comments: {post.num_comments}")
        print(f"  URL: {post.url}")
        if post.comments:
            print(f"  Top comment: {post.comments[0][:100]}...")
        print()

    # Save to files
    print("=" * 60)
    print("SAVING DATA")
    print("=" * 60)

    from save_collected_data import save_to_json, save_to_csv

    save_to_json({"reddit": posts})
    save_to_csv({"reddit": posts})

    print("=" * 60)
    print(f"\nData saved to output/ directory")
    print("  - reddit_TIMESTAMP.json")
    print("  - reddit_TIMESTAMP.csv\n")


if __name__ == "__main__":
    # Fix for Windows asyncio event loop policy
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())

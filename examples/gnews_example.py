"""GNews API connector example.

Shows how to collect news articles using GNews API.
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
from connectors import setup_logging
from connectors.gnews import (
    GNewsCollector,
    GNewsClientConfig,
    GNewsCollectSpec,
)


async def main():
    # Load environment variables from .env file
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)

    # Set up logging
    setup_logging(level="INFO")

    # Configuration (credentials from environment)
    config = GNewsClientConfig(
        api_key=os.getenv("GNEWS_API_KEY", "your_api_key"),
        timeout=30,
    )

    # Collection specification
    spec = GNewsCollectSpec(
        query="bitcoin OR cryptocurrency OR ethereum",  # Boolean operators supported
        language="en",  # en, es, fr, de, it, pt, ru, zh, ja, ko, ar, hi
        # country="us",  # Optional: us, gb, ca, au, de, fr, etc.
        # category="technology",  # Optional: general, world, nation, business, technology, entertainment, sports, science, health
        sort_by="publishedAt",  # publishedAt (newest first) or relevance
        max_results=10,  # Max 100
        # from_date=datetime.now() - timedelta(days=7),  # Optional: last 7 days
    )

    # Collect data
    print(f"Collecting news articles for: {spec.query}...")
    print(f"Language: {spec.language}, Max results: {spec.max_results}")
    print()

    collector = GNewsCollector(config)
    result = await collector.fetch(spec)

    # Display results
    if result.status == "success":
        print(f"Status: SUCCESS")
        print(f"Total articles: {result.total_articles}")
        print()

        print(f"Articles:\n")
        for i, article in enumerate(result.articles, 1):
            print(f"{i}. {article.title}")
            print(f"   Source: {article.source_name}")
            print(f"   Published: {article.published_at.strftime('%Y-%m-%d %H:%M')}")
            print(f"   URL: {article.url}")
            if article.description:
                desc = article.description[:150] + "..." if len(article.description) > 150 else article.description
                print(f"   Description: {desc}")
            print()

        # Show source distribution
        sources = {}
        for article in result.articles:
            sources[article.source_name] = sources.get(article.source_name, 0) + 1

        print("\nArticles by source:")
        for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {source}: {count}")

    else:
        print(f"Status: FAILED")
        print(f"Error: {result.error}")
        if "rate limit" in result.error.lower():
            print("\nNote: GNews free tier allows 100 requests per day")

    # Save to files
    print("\n" + "=" * 60)
    print("SAVING DATA")
    print("=" * 60)

    from save_collected_data import save_to_json, save_to_csv

    save_to_json({"gnews": [result]})
    save_to_csv({"gnews": [result]})

    print("=" * 60)
    print(f"\nData saved to output/ directory")
    print("  - gnews_TIMESTAMP.json")
    print("  - gnews_TIMESTAMP.csv\n")


if __name__ == "__main__":
    # Fix for Windows asyncio event loop policy
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())

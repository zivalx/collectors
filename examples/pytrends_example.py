"""Google Trends connector example.

Shows how to collect trend data for keywords.
"""

import asyncio
import sys
from pathlib import Path
from connectors import setup_logging
from connectors.pytrends import (
    PyTrendsCollector,
    PyTrendsClientConfig,
    PyTrendsCollectSpec,
)


async def main():
    # Set up logging
    setup_logging(level="INFO")

    # Configuration (no credentials needed for Google Trends)
    config = PyTrendsClientConfig(
        timeout=30,
        retries=3,
        backoff_factor=0.5,
    )

    # Collection specification
    spec = PyTrendsCollectSpec(
        keywords=["bitcoin", "ethereum", "crypto"],
        timeframe="today 3-m",  # Last 3 months
        geo="US",  # United States (leave empty for worldwide)
        category=0,  # All categories
        include_related_queries=True,
        include_interest_by_region=False,
    )

    # Collect data
    print(f"Collecting Google Trends data for: {', '.join(spec.keywords)}...")
    collector = PyTrendsCollector(config)
    result = await collector.fetch(spec)

    # Display results
    if result.status == "success":
        print(f"\nStatus: SUCCESS")
        print(f"Keywords: {', '.join(result.keywords)}")
        print(f"Timeframe: {result.timeframe}")
        print(f"Geo: {result.geo or 'Worldwide'}")
        print(f"\nTrend data points: {len(result.interest_over_time)}")

        # Show sample trend data
        if result.interest_over_time:
            print("\nSample trend data (first 5 points):")
            for trend in result.interest_over_time[:5]:
                print(f"  {trend.date.strftime('%Y-%m-%d')}: {trend.keyword} = {trend.interest}")

        # Show related queries
        if result.related_queries_top:
            print(f"\nRelated queries found for {len(result.related_queries_top)} keywords")
            for keyword, queries in result.related_queries_top.items():
                print(f"\n  Top queries for '{keyword}':")
                for query in queries[:3]:  # Show first 3
                    print(f"    - {query.query} (value: {query.value})")

        if result.related_queries_rising:
            print(f"\nRising queries found for {len(result.related_queries_rising)} keywords")
            for keyword, queries in result.related_queries_rising.items():
                print(f"\n  Rising queries for '{keyword}':")
                for query in queries[:3]:  # Show first 3
                    value_str = "Breakout" if query.value is None else str(query.value)
                    print(f"    - {query.query} (value: {value_str})")

        # Show regional data if included
        if result.interest_by_region:
            print(f"\nRegional interest data for {len(result.interest_by_region)} keywords")
            for keyword, regions in result.interest_by_region.items():
                top_regions = sorted(regions.items(), key=lambda x: x[1], reverse=True)[:3]
                print(f"\n  Top regions for '{keyword}':")
                for region, interest in top_regions:
                    print(f"    - {region}: {interest}")

    else:
        print(f"\nStatus: FAILED")
        print(f"Error: {result.error}")

    # Save to files
    print("\n" + "=" * 60)
    print("SAVING DATA")
    print("=" * 60)

    from save_collected_data import save_to_json, save_to_csv

    save_to_json({"pytrends": [result]})
    save_to_csv({"pytrends": [result]})

    print("=" * 60)
    print(f"\nData saved to output/ directory")
    print("  - pytrends_TIMESTAMP.json")
    print("  - pytrends_TIMESTAMP.csv\n")


if __name__ == "__main__":
    # Fix for Windows asyncio event loop policy
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())

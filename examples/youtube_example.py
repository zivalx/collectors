"""YouTube connector example.

Shows how to collect videos from channels or URLs with transcripts.
Demonstrates YouTube Transcript API → Whisper fallback.
"""

import asyncio
from connectors import setup_logging  # Import logging setup
from connectors.youtube import (
    YouTubeCollector,
    YouTubeClientConfig,
    YouTubeCollectSpec,
)


async def example_from_channels():
    """Example: Collect recent videos from YouTube channels."""

    # Configuration
    config = YouTubeClientConfig(
        whisper_model="base",  # tiny, base, small, medium, large
        use_transcript_api=True,  # Try YouTube API first, then Whisper
        max_video_length=3600,  # 1 hour maximum
        audio_format="m4a",  # m4a, webm, mp3
    )

    # Collection from channels
    spec = YouTubeCollectSpec(
        channels=["@JosephCarlsonShow"],
        max_videos_per_channel=3,
        days_back=14,  # Last 2 weeks
    )

    # Collect data
    print(f"Collecting from {len(spec.channels)} channel(s)...")
    collector = YouTubeCollector(config)
    videos = await collector.fetch(spec)

    # Display results
    print(f"\nCollected {len(videos)} videos\n")

    for video in videos:
        if video.status == 'success':
            print(f"OK {video.title}")
            print(f"  Channel: {video.channel}")
            print(f"  Duration: {video.duration}s | Views: {video.view_count:,}")
            print(f"  Transcript source: {video.transcript_source}")
            # Handle Unicode in transcript preview
            transcript_preview = video.transcript[:150].encode('ascii', errors='replace').decode('ascii')
            print(f"  Transcript preview: {transcript_preview}...")
        else:
            print(f"FAILED: {video.url}")
            print(f"  Error: {video.error}")
        print()

    return videos


async def example_from_urls():
    """Example: Process specific YouTube URLs."""

    config = YouTubeClientConfig(
        whisper_model="base",
        use_transcript_api=True,
    )

    # Collection from specific URLs
    spec = YouTubeCollectSpec(
        urls=[
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Example video
            # Add more URLs here
        ]
    )

    print("Processing specific URLs...")
    collector = YouTubeCollector(config)
    videos = await collector.fetch(spec)

    print(f"\nProcessed {len(videos)} video(s)\n")

    for video in videos:
        print(f"Title: {video.title}")
        print(f"Upload date: {video.upload_date}")
        # Handle Unicode in transcript preview
        transcript_preview = video.transcript[:100].encode('ascii', errors='replace').decode('ascii')
        print(f"Transcript ({video.transcript_source}): {transcript_preview}...")
        print()

    return videos


async def main():
    # Set up logging to see what's happening
    setup_logging(level="INFO")

    print("=== YouTube Connector Examples ===\n")

    # Example 1: From channels
    print("1. Collecting from channels...")
    channel_videos = await example_from_channels()

    print("\n" + "=" * 50 + "\n")

    # Example 2: From specific URLs
    print("2. Processing specific URLs...")
    url_videos = await example_from_urls()

    # Combine all videos
    all_videos = (channel_videos or []) + (url_videos or [])

    if all_videos:
        # Separate successes and failures
        successful = [v for v in all_videos if v.status == 'success']
        failed = [v for v in all_videos if v.status == 'failed']

        print("\n" + "=" * 60)
        print("RESULTS SUMMARY")
        print("=" * 60)
        print(f"Total: {len(all_videos)}")
        print(f"Successful: {len(successful)}")
        print(f"Failed: {len(failed)}")

        if failed:
            print("\nFailed videos:")
            for v in failed:
                print(f"  - {v.url}: {v.error}")

        # Save successful videos only
        if successful:
            print("\n" + "=" * 60)
            print("SAVING DATA")
            print("=" * 60)

            from save_collected_data import (
                save_to_json,
                save_to_csv,
                save_youtube_transcripts
            )

            save_to_json({"youtube": successful})
            save_to_csv({"youtube": successful})
            save_youtube_transcripts(successful)

            print("=" * 60)
            print(f"\nData saved to output/ directory")
            print("  - youtube_TIMESTAMP.json")
            print("  - youtube_TIMESTAMP.csv")
            print("  - output/transcripts/*.txt\n")
        else:
            print("\nNo successful videos to save.")


if __name__ == "__main__":
    asyncio.run(main())

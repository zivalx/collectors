"""Save collected data to various formats (JSON, CSV, Database).

Shows how to export data collected from Reddit, Telegram, YouTube, Twitter.
"""

import json
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any


def _get_project_root() -> Path:
    """Get the project root directory."""
    # This file is in examples/, so parent is project root
    return Path(__file__).parent.parent


def _resolve_output_path(output_dir: str) -> Path:
    """Resolve output directory relative to project root."""
    if Path(output_dir).is_absolute():
        return Path(output_dir)
    # Make relative paths relative to project root
    return _get_project_root() / output_dir


def save_to_json(data: Dict[str, List[Any]], output_dir: str = "output"):
    """Save collected data to JSON files.

    Creates separate JSON files for each connector:
    - output/reddit_YYYYMMDD_HHMMSS.json
    - output/telegram_YYYYMMDD_HHMMSS.json
    - output/youtube_YYYYMMDD_HHMMSS.json
    """
    output_path = _resolve_output_path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for source, items in data.items():
        if not items:
            continue

        filename = output_path / f"{source}_{timestamp}.json"

        # Convert Pydantic models to dicts
        if hasattr(items[0], 'model_dump'):
            items_dict = [item.model_dump() for item in items]
        else:
            items_dict = [item.dict() for item in items]

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(items_dict, f, indent=2, default=str)

        print(f"Saved {len(items)} {source} items to {filename}")

    return output_path


def save_to_csv(data: Dict[str, List[Any]], output_dir: str = "output"):
    """Save collected data to CSV files.

    Creates separate CSV files for each connector.
    """
    output_path = _resolve_output_path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for source, items in data.items():
        if not items:
            continue

        filename = output_path / f"{source}_{timestamp}.csv"

        # Convert Pydantic models to dicts
        if hasattr(items[0], 'model_dump'):
            items_dict = [item.model_dump() for item in items]
        else:
            items_dict = [item.dict() for item in items]

        # Get all unique keys
        all_keys = set()
        for item in items_dict:
            all_keys.update(item.keys())

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=sorted(all_keys))
            writer.writeheader()

            for item in items_dict:
                # Convert lists/dicts to strings for CSV
                row = {}
                for key, value in item.items():
                    if isinstance(value, (list, dict)):
                        row[key] = json.dumps(value)
                    else:
                        row[key] = value
                writer.writerow(row)

        print(f"Saved {len(items)} {source} items to {filename}")

    return output_path


def save_youtube_transcripts(videos: List[Any], output_dir: str = "output/transcripts"):
    """Save YouTube transcripts as individual text files.

    Creates one .txt file per video with the transcript.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for video in videos:
        if video.status != "success":
            continue

        # Clean filename
        safe_title = "".join(c for c in video.title if c.isalnum() or c in (' ', '-', '_'))
        safe_title = safe_title[:50]  # Limit length

        filename = output_path / f"{video.video_id}_{safe_title}.txt"

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"Title: {video.title}\n")
            f.write(f"Channel: {video.channel}\n")
            f.write(f"URL: {video.url}\n")
            f.write(f"Duration: {video.duration}s\n")
            f.write(f"Views: {video.view_count:,}\n")
            f.write(f"Transcript Source: {video.transcript_source}\n")
            f.write(f"\n{'=' * 80}\n\n")
            f.write(video.transcript)

        print(f"Saved transcript: {filename.name}")

    return output_path


def save_combined_json(data: Dict[str, List[Any]], output_dir: str = "output"):
    """Save all data to a single combined JSON file."""
    output_path = _resolve_output_path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = output_path / f"combined_{timestamp}.json"

    combined = {
        "collected_at": datetime.now().isoformat(),
        "sources": {}
    }

    for source, items in data.items():
        if hasattr(items[0], 'model_dump'):
            items_dict = [item.model_dump() for item in items]
        else:
            items_dict = [item.dict() for item in items]

        combined["sources"][source] = {
            "count": len(items),
            "items": items_dict
        }

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(combined, f, indent=2, default=str)

    print(f"Saved combined data to {filename}")
    return filename


def print_summary_table(data: Dict[str, List[Any]]):
    """Print a summary table of collected data."""
    print("\n" + "=" * 80)
    print("COLLECTED DATA SUMMARY")
    print("=" * 80)
    print(f"{'Source':<15} {'Count':<10} {'Sample':<55}")
    print("-" * 80)

    for source, items in data.items():
        if not items:
            print(f"{source:<15} {0:<10} No data collected")
            continue

        count = len(items)

        # Get sample title/text
        if source == "reddit":
            sample = items[0].title[:50] + "..." if len(items[0].title) > 50 else items[0].title
        elif source == "youtube":
            sample = items[0].title[:50] + "..." if len(items[0].title) > 50 else items[0].title
        elif source == "telegram":
            sample = (items[0].text[:50] + "...") if items[0].text and len(items[0].text) > 50 else (items[0].text or "No text")
        elif source == "twitter":
            sample = items[0].text[:50] + "..." if len(items[0].text) > 50 else items[0].text
        else:
            sample = str(items[0])[:50]

        print(f"{source:<15} {count:<10} {sample:<55}")

    print("=" * 80 + "\n")


def save_youtube_metadata(videos: List[Any], output_dir: str = "output"):
    """Save YouTube metadata as a detailed CSV."""
    output_path = _resolve_output_path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = output_path / f"youtube_metadata_{timestamp}.csv"

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Header
        writer.writerow([
            "Video ID",
            "Title",
            "Channel",
            "Duration (s)",
            "Views",
            "Likes",
            "Upload Date",
            "Transcript Source",
            "Transcript Length",
            "Status",
            "URL"
        ])

        # Data
        for video in videos:
            writer.writerow([
                video.video_id,
                video.title,
                video.channel,
                video.duration,
                video.view_count,
                video.like_count,
                video.upload_date,
                video.transcript_source,
                len(video.transcript) if video.status == "success" else 0,
                video.status,
                video.url
            ])

    print(f"Saved YouTube metadata to {filename}")
    return filename


# Example usage
if __name__ == "__main__":
    print("This module provides save/export functions.")
    print("\nImport and use like this:")
    print("""
    from save_collected_data import save_to_json, save_to_csv, save_youtube_transcripts

    # After collecting data:
    data = await main()  # from my_crypto_collector.py

    # Save to JSON
    save_to_json(data)

    # Save to CSV
    save_to_csv(data)

    # Save YouTube transcripts
    save_youtube_transcripts(data['youtube'])
    """)

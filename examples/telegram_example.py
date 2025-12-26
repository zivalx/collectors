"""Telegram connector example.

Shows how to collect messages from Telegram channels with auth callbacks.
"""

import asyncio
import os
from connectors.telegram import (
    TelegramCollector,
    TelegramClientConfig,
    TelegramCollectSpec,
)


# Auth callbacks for non-interactive authentication
async def get_code():
    """Get 2FA code from user.

    In production, this could fetch from an SMS gateway API.
    """
    return input("Enter the code sent to your Telegram app: ")


async def get_password():
    """Get 2FA password from user.

    In production, this could read from environment or secret manager.
    """
    password = os.environ.get("TELEGRAM_2FA_PASSWORD")
    if password:
        return password
    return input("Enter your Telegram 2FA password: ")


async def main():
    # Check environment variables
    required_vars = ["TELEGRAM_API_ID", "TELEGRAM_API_HASH", "TELEGRAM_PHONE"]
    missing_vars = [var for var in required_vars if not os.environ.get(var) or os.environ.get(var).startswith("your_")]

    if missing_vars:
        print("ERROR: Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease run: .\\load_env.ps1")
        print("Or set environment variables manually")
        return

    # Configuration with auth callbacks
    config = TelegramClientConfig(
        api_id=os.environ["TELEGRAM_API_ID"],
        api_hash=os.environ["TELEGRAM_API_HASH"],
        phone=os.environ["TELEGRAM_PHONE"],
        session_name="connector_session",  # Session file name
        auth_code_callback=get_code,
        auth_password_callback=get_password,
    )

    # Collection specification - your crypto channels
    spec = TelegramCollectSpec(
        channels=[
            "CryptoSignals",
            "Cryptoy",
            "crypto",
            "Cryptoinnercycles",
        ],
        max_messages_per_channel=10,  # Start small for testing
        include_replies=False,  # Faster without replies
    )

    # Collect data
    print(f"\nCollecting from {len(spec.channels)} Telegram channel(s)...")
    print(f"Channels: {', '.join(spec.channels)}")
    print("This may take a moment...\n")

    collector = TelegramCollector(config)
    messages = await collector.fetch(spec)

    # Display results
    print(f"\n{'=' * 60}")
    print(f"✓ Collected {len(messages)} total messages")
    print(f"{'=' * 60}\n")

    if len(messages) == 0:
        print("⚠️  No messages collected!")
        print("Possible reasons:")
        print("  - Channel names might be incorrect")
        print("  - You might not have access to these channels")
        print("  - Channels might be empty")
        print("\nTry joining the channels in Telegram app first.")
        return

    # Show sample messages
    for msg in messages[:5]:  # Show first 5 messages
        print(f"[{msg.channel}] Message ID: {msg.message_id}")
        print(f"  Date: {msg.date}")
        print(f"  Author: {msg.author}")
        if msg.text:
            print(f"  Text: {msg.text[:100]}...")
        if msg.replies:
            print(f"  Replies: {len(msg.replies)}")
            # Show first reply
            if msg.replies:
                reply = msg.replies[0]
                print(f"    → Reply: {reply.text[:80] if reply.text else 'No text'}...")
        print()

    # Save to files
    print("\n" + "=" * 60)
    print("SAVING DATA")
    print("=" * 60)

    from save_collected_data import save_to_json, save_to_csv

    # Save as JSON
    save_to_json({"telegram": messages})

    # Save as CSV
    save_to_csv({"telegram": messages})

    print("=" * 60)
    print(f"\n✓ Data saved to output/ directory")
    print("  - telegram_TIMESTAMP.json")
    print("  - telegram_TIMESTAMP.csv\n")


if __name__ == "__main__":
    asyncio.run(main())

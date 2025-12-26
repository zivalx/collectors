"""High-level Telegram data collector."""

from typing import List
from datetime import datetime
import logging

from connectors.telegram.client import TelegramClient
from connectors.telegram.models import (
    TelegramClientConfig,
    TelegramCollectSpec,
    TelegramMessage,
    TelegramReply,
)

logger = logging.getLogger(__name__)


class TelegramCollector:
    """High-level Telegram data collector.

    Public API for collecting Telegram data according to a specification.
    """

    def __init__(self, config: TelegramClientConfig):
        """Initialize Telegram collector.

        Args:
            config: Telegram client configuration with credentials and auth callbacks
        """
        self.config = config

    async def fetch(self, spec: TelegramCollectSpec) -> List[TelegramMessage]:
        """Fetch Telegram messages according to specification.

        Extracted from trender/app/services/telegram_collector.py lines 115-129
        and lines 85-113 (process_response).

        Args:
            spec: Collection specification (channels, max messages, include replies)

        Returns:
            List of TelegramMessage objects with typed fields

        Example:
            ```python
            async def get_code():
                return input("Enter code: ")

            async def get_password():
                return input("Enter password: ")

            config = TelegramClientConfig(
                api_id="...",
                api_hash="...",
                phone="+1234567890",
                auth_code_callback=get_code,
                auth_password_callback=get_password
            )
            spec = TelegramCollectSpec(
                channels=["channel1", "channel2"],
                max_messages_per_channel=200,
                include_replies=True
            )
            collector = TelegramCollector(config)
            messages = await collector.fetch(spec)
            ```
        """
        all_messages = []

        async with TelegramClient(self.config) as client:
            for channel in spec.channels:
                logger.info(f"Fetching from channel: {channel}")

                try:
                    # Fetch raw messages from client
                    raw_messages = await client.fetch_messages(
                        channel=channel,
                        limit=spec.max_messages_per_channel,
                        include_replies=spec.include_replies,
                    )

                    # Process messages into typed models (lines 85-113)
                    for msg in raw_messages:
                        try:
                            # Process replies if present
                            replies = []
                            if spec.include_replies and hasattr(msg, 'replies') and isinstance(msg.replies, list):
                                for reply in msg.replies:
                                    reply_obj = TelegramReply(
                                        message_id=reply.id,
                                        date=reply.date,
                                        text=reply.text,
                                        author=reply.sender_id,
                                    )
                                    replies.append(reply_obj)

                            # Create message object
                            message = TelegramMessage(
                                message_id=msg.id,
                                channel=channel,
                                date=msg.date,
                                text=msg.text,
                                author=msg.sender_id,
                                replies=replies,
                            )
                            all_messages.append(message)

                        except Exception as e:
                            logger.error(f"Error processing message {msg.id}: {e}")
                            # Continue with other messages

                except Exception as e:
                    logger.error(f"Error processing channel {channel}: {e}")
                    # Continue with other channels

        logger.info(
            f"Collected {len(all_messages)} messages from {len(spec.channels)} channels"
        )
        return all_messages

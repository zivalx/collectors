"""Low-level Telegram API client using Telethon."""

from telethon import TelegramClient as TelethonClient
from telethon.errors import SessionPasswordNeededError
from typing import List
import logging

from connectors.telegram.models import TelegramClientConfig
from connectors.common.exceptions import AuthenticationError, DataFetchError

logger = logging.getLogger(__name__)


class TelegramClient:
    """Low-level Telegram API client using Telethon.

    Handles connection lifecycle, non-interactive auth via callbacks,
    and raw API calls.

    Extracted from trender/app/services/telegram_collector.py lines 14-83.
    """

    def __init__(self, config: TelegramClientConfig):
        """Initialize Telegram client.

        Args:
            config: Telegram client configuration with credentials
        """
        self.config = config
        self._client = TelethonClient(
            config.session_name,
            config.api_id,
            config.api_hash,
        )

    async def __aenter__(self):
        """Async context manager entry - connect and authenticate.

        Replaces interactive input() calls with async callbacks.
        """
        await self._client.connect()

        if not await self._client.is_user_authorized():
            if not self.config.phone:
                raise AuthenticationError("Phone number required for authentication")

            try:
                # Send code request
                await self._client.send_code_request(self.config.phone)

                # Get code from callback (replaces input() at line 28)
                if self.config.auth_code_callback:
                    code = await self.config.auth_code_callback()
                    await self._client.sign_in(self.config.phone, code)
                else:
                    raise AuthenticationError(
                        "auth_code_callback required for authentication"
                    )

                if await self._client.is_user_authorized():
                    logger.info("Telegram client authorized successfully")

            except SessionPasswordNeededError:
                # 2FA enabled - get password from callback (replaces input() at line 33)
                if self.config.auth_password_callback:
                    password = await self.config.auth_password_callback()
                    await self._client.sign_in(password=password)
                    logger.info("Telegram 2FA authentication successful")
                else:
                    raise AuthenticationError(
                        "auth_password_callback required for 2FA authentication"
                    )

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - disconnect client."""
        await self._client.disconnect()
        logger.info("Telegram client disconnected")

    async def fetch_messages(
        self, channel: str, limit: int = 200, include_replies: bool = True
    ) -> List:
        """Fetch messages from a channel with optional replies.

        Extracted from trender/app/services/telegram_collector.py lines 54-83.

        Args:
            channel: Channel username or ID
            limit: Maximum messages to fetch
            include_replies: Whether to fetch replies for each message

        Returns:
            List of Telethon Message objects with replies attached

        Raises:
            DataFetchError: If fetching fails
        """
        try:
            # Get channel entity
            channel_entity = await self._client.get_entity(channel)

            # Fetch messages
            messages = await self._client.get_messages(channel_entity, limit=limit)

            # Fetch replies if requested (lines 62-78)
            if include_replies:
                for message in messages:
                    if message.replies and message.replies.replies > 0:
                        try:
                            replies = []
                            async for reply in self._client.iter_messages(
                                channel_entity, reply_to=message.id
                            ):
                                replies.append(reply)
                            message.replies = replies
                        except Exception as e:
                            logger.error(
                                f"Error fetching replies for message {message.id}: {e}"
                            )
                            message.replies = []

            logger.info(f"Fetched {len(messages)} messages from channel: {channel}")
            return messages

        except Exception as e:
            raise DataFetchError(f"Error fetching from channel {channel}: {e}")

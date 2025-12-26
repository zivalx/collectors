"""Tests for Telegram connector."""

import pytest
from connectors.telegram import (
    TelegramCollector,
    TelegramClientConfig,
    TelegramCollectSpec,
    TelegramMessage,
    TelegramReply,
)


class TestTelegramClientConfig:
    """Test Telegram client configuration."""

    def test_valid_config(self, telegram_api_id, telegram_api_hash, telegram_phone):
        """Test creating valid Telegram client config."""
        config = TelegramClientConfig(
            api_id=telegram_api_id,
            api_hash=telegram_api_hash,
            phone=telegram_phone,
        )
        assert config.api_id == telegram_api_id
        assert config.api_hash == telegram_api_hash
        assert config.phone == telegram_phone
        assert config.session_name == "connector_session"
        assert config.timeout == 30

    def test_custom_settings(self, telegram_api_id, telegram_api_hash):
        """Test custom session name and timeout."""
        config = TelegramClientConfig(
            api_id=telegram_api_id,
            api_hash=telegram_api_hash,
            phone="+1234567890",
            session_name="custom_session",
            timeout=60,
        )
        assert config.session_name == "custom_session"
        assert config.timeout == 60

    def test_auth_callbacks(self, telegram_api_id, telegram_api_hash, telegram_phone):
        """Test auth callbacks can be set."""
        async def get_code():
            return "12345"

        async def get_password():
            return "password"

        config = TelegramClientConfig(
            api_id=telegram_api_id,
            api_hash=telegram_api_hash,
            phone=telegram_phone,
            auth_code_callback=get_code,
            auth_password_callback=get_password,
        )
        assert config.auth_code_callback is not None
        assert config.auth_password_callback is not None


class TestTelegramCollectSpec:
    """Test Telegram collection specification."""

    def test_valid_spec(self):
        """Test creating valid collect spec."""
        spec = TelegramCollectSpec(
            channels=["channel1", "channel2"],
            max_messages_per_channel=100,
            include_replies=True,
        )
        assert spec.channels == ["channel1", "channel2"]
        assert spec.max_messages_per_channel == 100
        assert spec.include_replies is True

    def test_defaults(self):
        """Test default values."""
        spec = TelegramCollectSpec(channels=["test_channel"])
        assert spec.max_messages_per_channel == 200
        assert spec.include_replies is True


@pytest.mark.asyncio
class TestTelegramCollector:
    """Test Telegram collector (integration tests with real API).

    Note: These tests require valid Telegram credentials and may require
    interactive authentication if no session file exists.
    """

    async def test_fetch_messages_basic(
        self, telegram_api_id, telegram_api_hash, telegram_phone
    ):
        """Test fetching messages from a public channel."""
        # Mock auth callbacks that won't be called if session exists
        async def get_code():
            code = input("Enter Telegram code: ")
            return code

        async def get_password():
            return ""

        config = TelegramClientConfig(
            api_id=telegram_api_id,
            api_hash=telegram_api_hash,
            phone=telegram_phone,
            session_name="test_session",
            auth_code_callback=get_code,
            auth_password_callback=get_password,
        )

        # Using a well-known public Telegram channel
        spec = TelegramCollectSpec(
            channels=["telegram"],  # Official Telegram news channel
            max_messages_per_channel=5,
            include_replies=False,
        )

        collector = TelegramCollector(config)
        messages = await collector.fetch(spec)

        assert len(messages) > 0
        assert len(messages) <= 5

        for message in messages:
            assert isinstance(message, TelegramMessage)
            assert message.message_id
            assert message.channel
            assert message.date
            # Text may be None for media-only messages
            assert isinstance(message.text, (str, type(None)))

    async def test_fetch_messages_with_replies(
        self, telegram_api_id, telegram_api_hash, telegram_phone
    ):
        """Test fetching messages with replies."""
        async def get_code():
            code = input("Enter Telegram code: ")
            return code

        async def get_password():
            return ""

        config = TelegramClientConfig(
            api_id=telegram_api_id,
            api_hash=telegram_api_hash,
            phone=telegram_phone,
            session_name="test_session",
            auth_code_callback=get_code,
            auth_password_callback=get_password,
        )

        spec = TelegramCollectSpec(
            channels=["telegram"],
            max_messages_per_channel=10,
            include_replies=True,
        )

        collector = TelegramCollector(config)
        messages = await collector.fetch(spec)

        assert len(messages) > 0

        for message in messages:
            assert isinstance(message.replies, list)
            # Check reply structure if any exist
            for reply in message.replies:
                assert isinstance(reply, TelegramReply)
                assert reply.message_id
                assert reply.date

    async def test_fetch_multiple_channels(
        self, telegram_api_id, telegram_api_hash, telegram_phone
    ):
        """Test fetching from multiple channels."""
        async def get_code():
            code = input("Enter Telegram code: ")
            return code

        async def get_password():
            return ""

        config = TelegramClientConfig(
            api_id=telegram_api_id,
            api_hash=telegram_api_hash,
            phone=telegram_phone,
            session_name="test_session",
            auth_code_callback=get_code,
            auth_password_callback=get_password,
        )

        spec = TelegramCollectSpec(
            channels=["telegram", "durov"],  # Two official channels
            max_messages_per_channel=3,
            include_replies=False,
        )

        collector = TelegramCollector(config)
        messages = await collector.fetch(spec)

        assert len(messages) > 0

        # Check we got messages from channels
        channels = {msg.channel for msg in messages}
        assert len(channels) >= 1  # At least one channel returned data

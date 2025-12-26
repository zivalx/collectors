"""Pydantic models for Telegram connector."""

from pydantic import BaseModel, Field
from typing import List, Optional, Callable, Awaitable
from datetime import datetime
from connectors.common.config import BaseClientConfig, BaseCollectSpec


class TelegramClientConfig(BaseClientConfig):
    """Telegram API credentials and client settings.

    Uses callback pattern for non-interactive authentication.
    """
    api_id: str = Field(..., description="Telegram API ID")
    api_hash: str = Field(..., description="Telegram API hash")
    session_name: str = Field(
        default="connector_session",
        description="Session file name (stored locally)"
    )
    phone: Optional[str] = Field(
        default=None,
        description="Phone number for authentication (+1234567890)"
    )
    timeout: int = Field(default=30, description="Request timeout in seconds")

    # Callbacks for interactive auth (non-serializable)
    auth_code_callback: Optional[Callable[[], Awaitable[str]]] = Field(
        default=None,
        exclude=True,
        description="Async callback to get 2FA code from user"
    )
    auth_password_callback: Optional[Callable[[], Awaitable[str]]] = Field(
        default=None,
        exclude=True,
        description="Async callback to get 2FA password from user"
    )

    class Config:
        arbitrary_types_allowed = True  # Allow callable types


class TelegramCollectSpec(BaseCollectSpec):
    """Specification for Telegram data collection.

    Describes which channels to collect from and parameters.
    """
    channels: List[str] = Field(
        ...,
        min_length=1,
        description="List of channel usernames or IDs"
    )
    max_messages_per_channel: int = Field(
        default=200,
        ge=1,
        description="Maximum messages to fetch per channel"
    )
    include_replies: bool = Field(
        default=True,
        description="Whether to fetch replies to messages"
    )


class TelegramReply(BaseModel):
    """Telegram reply data model.

    Represents a reply to a Telegram message.
    """
    message_id: int = Field(..., description="Reply message ID")
    date: datetime = Field(..., description="Reply timestamp")
    text: Optional[str] = Field(default=None, description="Reply text content")
    author: Optional[int] = Field(default=None, description="Reply author ID (sender_id)")

    class Config:
        frozen = False


class TelegramMessage(BaseModel):
    """Telegram message data model.

    Represents a Telegram channel message with optional replies.
    """
    message_id: int = Field(..., description="Message ID")
    channel: str = Field(..., description="Channel username or ID")
    date: datetime = Field(..., description="Message timestamp")
    text: Optional[str] = Field(default=None, description="Message text content")
    author: Optional[int] = Field(
        default=None,
        description="Message author ID (sender_id)"
    )
    replies: List[TelegramReply] = Field(
        default_factory=list,
        description="List of replies to this message"
    )

    class Config:
        frozen = False

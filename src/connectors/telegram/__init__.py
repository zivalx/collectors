"""Telegram data connector."""

from connectors.telegram.collector import TelegramCollector
from connectors.telegram.models import (
    TelegramClientConfig,
    TelegramCollectSpec,
    TelegramMessage,
    TelegramReply,
)

__all__ = [
    'TelegramCollector',
    'TelegramClientConfig',
    'TelegramCollectSpec',
    'TelegramMessage',
    'TelegramReply',
]

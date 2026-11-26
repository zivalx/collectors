"""days_back handling for the Telegram connector (mocked Telethon, no network)."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from connectors.telegram import (
    TelegramClientConfig,
    TelegramCollectSpec,
    TelegramCollector,
)
from connectors.telegram.client import TelegramClient

NOW = datetime.now(timezone.utc)


def _msg(i, days_ago, naive=False):
    d = NOW - timedelta(days=days_ago)
    if naive:
        d = d.replace(tzinfo=None)
    return SimpleNamespace(id=i, date=d, text=f"m{i}", sender_id=1, replies=None)


def _client(messages):
    """TelegramClient whose Telethon layer is a fake serving `messages` newest-first."""
    cfg = TelegramClientConfig(api_id="1", api_hash="h", phone="+1")
    with patch("connectors.telegram.client.TelethonClient"):
        c = TelegramClient(cfg)
    pulled = []

    async def iter_messages(entity, limit=None, **kw):
        n = 0
        for m in messages:
            if limit is not None and n >= limit:
                return
            n += 1
            pulled.append(m.id)
            yield m

    c._client = MagicMock()
    c._client.get_entity = AsyncMock(return_value="ent")
    c._client.get_messages = AsyncMock(return_value=list(messages))
    c._client.iter_messages = iter_messages
    return c, pulled


class TestFetchMessagesSince:
    async def test_without_since_behaviour_unchanged(self):
        c, _ = _client([_msg(1, 1), _msg(2, 90)])
        out = await c.fetch_messages("ch", limit=5, include_replies=False)
        assert [m.id for m in out] == [1, 2]
        c._client.get_messages.assert_awaited_once()

    async def test_since_stops_at_first_older_message(self):
        msgs = [_msg(5, 0.5), _msg(4, 2), _msg(3, 10), _msg(2, 11), _msg(1, 12)]
        c, pulled = _client(msgs)
        out = await c.fetch_messages(
            "ch", limit=100, include_replies=False, since=NOW - timedelta(days=7)
        )
        assert [m.id for m in out] == [5, 4]
        assert pulled == [5, 4, 3]  # stopped iterating at the first old one

    async def test_since_keeps_limit_as_upper_bound(self):
        c, pulled = _client([_msg(i, 0.1) for i in range(10, 0, -1)])
        out = await c.fetch_messages(
            "ch", limit=3, include_replies=False, since=NOW - timedelta(days=7)
        )
        assert len(out) == 3 and len(pulled) == 3

    async def test_naive_message_dates_treated_as_utc(self):
        c, _ = _client([_msg(2, 1, naive=True), _msg(1, 30, naive=True)])
        out = await c.fetch_messages(
            "ch", limit=10, include_replies=False, since=NOW - timedelta(days=7)
        )
        assert [m.id for m in out] == [2]


class TestCollectorPassesWindow:
    def test_spec_days_back_optional_and_validated(self):
        assert TelegramCollectSpec(channels=["a"]).days_back is None
        assert TelegramCollectSpec(channels=["a"], days_back=3).days_back == 3
        with pytest.raises(ValueError):
            TelegramCollectSpec(channels=["a"], days_back=0)

    async def test_collector_passes_since_only_when_days_back_set(self):
        cfg = TelegramClientConfig(api_id="1", api_hash="h", phone="+1")
        fake = MagicMock()
        fake.__aenter__ = AsyncMock(return_value=fake)
        fake.__aexit__ = AsyncMock(return_value=False)
        fake.fetch_messages = AsyncMock(return_value=[_msg(1, 1)])
        with patch("connectors.telegram.collector.TelegramClient", return_value=fake):
            col = TelegramCollector(cfg)
            await col.fetch(TelegramCollectSpec(channels=["a"], include_replies=False))
            assert fake.fetch_messages.await_args.kwargs.get("since") is None
            await col.fetch(
                TelegramCollectSpec(channels=["a"], include_replies=False, days_back=7)
            )
            since = fake.fetch_messages.await_args.kwargs["since"]
        assert since.tzinfo is not None
        assert abs((NOW - timedelta(days=7)) - since) < timedelta(seconds=30)

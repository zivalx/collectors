"""Tests for Polymarket connector models."""

import pytest
from datetime import datetime


class TestPolymarketClientConfig:
    def test_defaults(self):
        from connectors.polymarket.models import PolymarketClientConfig
        config = PolymarketClientConfig()
        assert config.gamma_base_url == "https://gamma-api.polymarket.com"
        assert config.clob_base_url == "https://clob.polymarket.com"
        assert config.timeout == 30
        assert config.rate_limit is None

    def test_custom_values(self):
        from connectors.polymarket.models import PolymarketClientConfig
        config = PolymarketClientConfig(timeout=60, rate_limit=30)
        assert config.timeout == 60
        assert config.rate_limit == 30

    def test_frozen(self):
        from connectors.polymarket.models import PolymarketClientConfig
        config = PolymarketClientConfig()
        with pytest.raises(Exception):
            config.timeout = 99


class TestMarketCollectSpec:
    def test_defaults(self):
        from connectors.polymarket.models import MarketCollectSpec
        spec = MarketCollectSpec()
        assert spec.active is True
        assert spec.closed is False
        assert spec.limit == 100
        assert spec.offset == 0
        assert spec.query is None
        assert spec.tag is None
        assert spec.order is None

    def test_custom_values(self):
        from connectors.polymarket.models import MarketCollectSpec
        spec = MarketCollectSpec(
            query="bitcoin", tag="crypto", active=True, closed=False,
            order="volume", ascending=False, limit=50, offset=10,
        )
        assert spec.query == "bitcoin"
        assert spec.tag == "crypto"
        assert spec.limit == 50
        assert spec.offset == 10

    def test_validate_order(self):
        from connectors.polymarket.models import MarketCollectSpec
        for order in ["volume", "liquidity", "created_at", "end_date"]:
            spec = MarketCollectSpec(order=order)
            assert spec.order == order
        with pytest.raises(ValueError):
            MarketCollectSpec(order="invalid")

    def test_limit_constraints(self):
        from connectors.polymarket.models import MarketCollectSpec
        with pytest.raises(ValueError):
            MarketCollectSpec(limit=0)
        with pytest.raises(ValueError):
            MarketCollectSpec(limit=501)


class TestPriceCollectSpec:
    def test_requires_token_ids(self):
        from connectors.polymarket.models import PriceCollectSpec
        spec = PriceCollectSpec(token_ids=["abc123"])
        assert spec.token_ids == ["abc123"]

    def test_empty_token_ids_rejected(self):
        from connectors.polymarket.models import PriceCollectSpec
        with pytest.raises(ValueError):
            PriceCollectSpec(token_ids=[])

    def test_include_orderbook_default(self):
        from connectors.polymarket.models import PriceCollectSpec
        spec = PriceCollectSpec(token_ids=["abc"])
        assert spec.include_orderbook is False


class TestTradeHistorySpec:
    def test_requires_token_id(self):
        from connectors.polymarket.models import TradeHistorySpec
        spec = TradeHistorySpec(token_id="abc123")
        assert spec.token_id == "abc123"

    def test_optional_dates(self):
        from connectors.polymarket.models import TradeHistorySpec
        now = datetime.now()
        spec = TradeHistorySpec(token_id="abc", from_date=now, to_date=now)
        assert spec.from_date == now

    def test_interval_validation(self):
        from connectors.polymarket.models import TradeHistorySpec
        for interval in ["1h", "6h", "1d", "1w", "max"]:
            spec = TradeHistorySpec(token_id="abc", interval=interval)
            assert spec.interval == interval
        with pytest.raises(ValueError):
            TradeHistorySpec(token_id="abc", interval="5m")

    def test_fidelity_default(self):
        from connectors.polymarket.models import TradeHistorySpec
        spec = TradeHistorySpec(token_id="abc")
        assert spec.fidelity is None
        assert spec.interval == "1d"


class TestEventCollectSpec:
    def test_by_event_id(self):
        from connectors.polymarket.models import EventCollectSpec
        spec = EventCollectSpec(event_id="123")
        assert spec.event_id == "123"
        assert spec.include_markets is True

    def test_by_slug(self):
        from connectors.polymarket.models import EventCollectSpec
        spec = EventCollectSpec(slug="us-election-2026")
        assert spec.slug == "us-election-2026"

    def test_list_defaults(self):
        from connectors.polymarket.models import EventCollectSpec
        spec = EventCollectSpec()
        assert spec.limit == 100
        assert spec.offset == 0
        assert spec.active is True

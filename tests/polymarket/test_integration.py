"""Integration tests for Polymarket connector (hits real API).

These tests require network access. They use public endpoints (no auth).
Skip with: pytest -m "not integration"
"""

import pytest
from datetime import datetime

from connectors.polymarket import (
    PolymarketCollector,
    PolymarketClientConfig,
    MarketCollectSpec,
    PriceCollectSpec,
    TradeHistorySpec,
    EventCollectSpec,
    Market,
    EventInfo,
)


pytestmark = pytest.mark.integration


@pytest.fixture
def config():
    return PolymarketClientConfig(timeout=15)


@pytest.fixture
def collector(config):
    return PolymarketCollector(config)


@pytest.mark.asyncio
class TestMarketDiscovery:
    async def test_fetch_active_markets(self, collector):
        spec = MarketCollectSpec(active=True, limit=5)
        result = await collector.fetch_markets(spec)

        assert result.status == "success"
        assert len(result.markets) > 0
        for market in result.markets:
            assert isinstance(market, Market)
            assert market.question
            assert market.id
            assert len(market.outcomes) >= 2

    async def test_fetch_markets_sorted_by_volume(self, collector):
        spec = MarketCollectSpec(active=True, order="volume", ascending=False, limit=3)
        result = await collector.fetch_markets(spec)

        assert result.status == "success"
        assert len(result.markets) > 0
        if len(result.markets) >= 2:
            assert result.markets[0].volume >= result.markets[1].volume

    async def test_search_markets(self, collector):
        spec = MarketCollectSpec(query="president")
        result = await collector.fetch_markets(spec)

        assert result.status == "success"


@pytest.mark.asyncio
class TestPricing:
    async def test_fetch_prices(self, collector):
        market_spec = MarketCollectSpec(active=True, order="volume", limit=1)
        market_result = await collector.fetch_markets(market_spec)

        assert market_result.status == "success"
        assert len(market_result.markets) > 0

        token_ids = market_result.markets[0].clob_token_ids
        if not token_ids:
            pytest.skip("No CLOB token IDs found on market")

        price_spec = PriceCollectSpec(token_ids=token_ids[:1])
        result = await collector.fetch_prices(price_spec)

        assert result.status == "success"
        assert len(result.prices) > 0

    async def test_fetch_orderbook(self, collector):
        market_spec = MarketCollectSpec(active=True, order="liquidity", limit=1)
        market_result = await collector.fetch_markets(market_spec)

        if not market_result.markets or not market_result.markets[0].clob_token_ids:
            pytest.skip("No market with CLOB tokens found")

        token_id = market_result.markets[0].clob_token_ids[0]
        price_spec = PriceCollectSpec(token_ids=[token_id], include_orderbook=True)
        result = await collector.fetch_prices(price_spec)

        assert result.status == "success"
        assert len(result.orderbooks) > 0


@pytest.mark.asyncio
class TestTradeHistory:
    async def test_fetch_price_history(self, collector):
        market_spec = MarketCollectSpec(active=True, order="volume", limit=1)
        market_result = await collector.fetch_markets(market_spec)

        if not market_result.markets or not market_result.markets[0].clob_token_ids:
            pytest.skip("No market with CLOB tokens found")

        token_id = market_result.markets[0].clob_token_ids[0]
        spec = TradeHistorySpec(token_id=token_id, interval="1d")
        result = await collector.fetch_trade_history(spec)

        assert result.status == "success"
        assert result.trade_history is not None


@pytest.mark.asyncio
class TestEvents:
    async def test_fetch_events(self, collector):
        spec = EventCollectSpec(active=True, limit=3)
        result = await collector.fetch_events(spec)

        assert result.status == "success"
        assert len(result.events) > 0
        for event in result.events:
            assert isinstance(event, EventInfo)
            assert event.title
            assert event.id

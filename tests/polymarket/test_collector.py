"""Tests for Polymarket collector (high-level API)."""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from connectors.polymarket.models import (
    PolymarketClientConfig,
    MarketCollectSpec,
    PriceCollectSpec,
    TradeHistorySpec,
    EventCollectSpec,
)
from connectors.polymarket.collector import PolymarketCollector
from connectors.common.exceptions import DataFetchError


SAMPLE_MARKET_RAW = {
    "id": "12345",
    "conditionId": "cond_abc",
    "question": "Will BTC hit 100k?",
    "slug": "will-btc-hit-100k",
    "outcomes": '["Yes","No"]',
    "outcomePrices": '["0.65","0.35"]',
    "volume": "1234567.89",
    "liquidity": 50000.0,
    "openInterest": 25000.0,
    "bestBid": 0.64,
    "bestAsk": 0.66,
    "lastTradePrice": 0.65,
    "startDate": "2026-01-01T00:00:00Z",
    "endDate": "2026-12-31T00:00:00Z",
    "active": True,
    "closed": False,
    "clobTokenIds": '["token_yes","token_no"]',
    "negRisk": False,
    "category": "crypto",
}


class TestFetchMarkets:
    @pytest.mark.asyncio
    async def test_fetch_markets_success(self):
        config = PolymarketClientConfig()
        collector = PolymarketCollector(config)
        spec = MarketCollectSpec(active=True, limit=10)

        with patch("connectors.polymarket.collector.GammaClient") as MockGamma:
            mock_instance = AsyncMock()
            mock_instance.get_markets = AsyncMock(return_value=[SAMPLE_MARKET_RAW])
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockGamma.return_value = mock_instance

            result = await collector.fetch_markets(spec)

        assert result.status == "success"
        assert len(result.markets) == 1
        assert result.markets[0].question == "Will BTC hit 100k?"
        assert result.markets[0].outcomes == ["Yes", "No"]
        assert result.markets[0].outcome_prices == [0.65, 0.35]
        assert result.markets[0].clob_token_ids == ["token_yes", "token_no"]
        assert result.markets[0].volume == 1234567.89

    @pytest.mark.asyncio
    async def test_fetch_markets_with_search(self):
        config = PolymarketClientConfig()
        collector = PolymarketCollector(config)
        spec = MarketCollectSpec(query="bitcoin")

        with patch("connectors.polymarket.collector.GammaClient") as MockGamma:
            mock_instance = AsyncMock()
            mock_instance.search = AsyncMock(return_value=[SAMPLE_MARKET_RAW])
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockGamma.return_value = mock_instance

            result = await collector.fetch_markets(spec)

        assert result.status == "success"
        mock_instance.search.assert_awaited_once_with("bitcoin")

    @pytest.mark.asyncio
    async def test_fetch_markets_error_graceful(self):
        config = PolymarketClientConfig()
        collector = PolymarketCollector(config)
        spec = MarketCollectSpec()

        with patch("connectors.polymarket.collector.GammaClient") as MockGamma:
            mock_instance = AsyncMock()
            mock_instance.get_markets = AsyncMock(
                side_effect=DataFetchError("connection failed")
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockGamma.return_value = mock_instance

            result = await collector.fetch_markets(spec)

        assert result.status == "failed"
        assert "connection failed" in result.error


class TestFetchPrices:
    @pytest.mark.asyncio
    async def test_fetch_prices_success(self):
        config = PolymarketClientConfig()
        collector = PolymarketCollector(config)
        spec = PriceCollectSpec(token_ids=["token_yes", "token_no"])

        with patch("connectors.polymarket.collector.CLOBClient") as MockCLOB:
            mock_instance = AsyncMock()
            mock_instance.get_price = AsyncMock(
                side_effect=[{"price": "0.65"}, {"price": "0.35"}]
            )
            mock_instance.get_midpoint = AsyncMock(
                side_effect=[{"midpoint": "0.65"}, {"midpoint": "0.35"}]
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockCLOB.return_value = mock_instance

            result = await collector.fetch_prices(spec)

        assert result.status == "success"
        assert len(result.prices) == 2
        assert result.prices[0].token_id == "token_yes"

    @pytest.mark.asyncio
    async def test_fetch_prices_with_orderbook(self):
        config = PolymarketClientConfig()
        collector = PolymarketCollector(config)
        spec = PriceCollectSpec(token_ids=["token_yes"], include_orderbook=True)

        book_data = {
            "bids": [{"price": "0.64", "size": "1500"}],
            "asks": [{"price": "0.66", "size": "2000"}],
        }

        with patch("connectors.polymarket.collector.CLOBClient") as MockCLOB:
            mock_instance = AsyncMock()
            mock_instance.get_price = AsyncMock(return_value={"price": "0.65"})
            mock_instance.get_midpoint = AsyncMock(return_value={"midpoint": "0.65"})
            mock_instance.get_book = AsyncMock(return_value=book_data)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockCLOB.return_value = mock_instance

            result = await collector.fetch_prices(spec)

        assert result.status == "success"
        assert len(result.orderbooks) == 1
        assert len(result.orderbooks[0].bids) == 1
        assert result.orderbooks[0].bids[0].price == 0.64

    @pytest.mark.asyncio
    async def test_fetch_prices_partial_failure(self):
        config = PolymarketClientConfig()
        collector = PolymarketCollector(config)
        spec = PriceCollectSpec(token_ids=["good_token", "bad_token"])

        with patch("connectors.polymarket.collector.CLOBClient") as MockCLOB:
            mock_instance = AsyncMock()
            mock_instance.get_price = AsyncMock(
                side_effect=[{"price": "0.65"}, DataFetchError("not found")]
            )
            mock_instance.get_midpoint = AsyncMock(
                side_effect=[{"midpoint": "0.65"}, DataFetchError("not found")]
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockCLOB.return_value = mock_instance

            result = await collector.fetch_prices(spec)

        assert result.status == "success"
        assert len(result.prices) == 1


class TestFetchTradeHistory:
    @pytest.mark.asyncio
    async def test_fetch_trade_history_success(self):
        config = PolymarketClientConfig()
        collector = PolymarketCollector(config)
        spec = TradeHistorySpec(token_id="token_abc", interval="1d")

        history_data = {
            "history": [
                {"t": 1630454400, "p": "0.52"},
                {"t": 1630540800, "p": "0.55"},
            ]
        }

        with patch("connectors.polymarket.collector.CLOBClient") as MockCLOB:
            mock_instance = AsyncMock()
            mock_instance.get_price_history = AsyncMock(return_value=history_data)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockCLOB.return_value = mock_instance

            result = await collector.fetch_trade_history(spec)

        assert result.status == "success"
        assert result.trade_history is not None
        assert len(result.trade_history.history) == 2
        assert result.trade_history.history[0].price == 0.52

    @pytest.mark.asyncio
    async def test_fetch_trade_history_error(self):
        config = PolymarketClientConfig()
        collector = PolymarketCollector(config)
        spec = TradeHistorySpec(token_id="bad_token")

        with patch("connectors.polymarket.collector.CLOBClient") as MockCLOB:
            mock_instance = AsyncMock()
            mock_instance.get_price_history = AsyncMock(
                side_effect=DataFetchError("not found")
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockCLOB.return_value = mock_instance

            result = await collector.fetch_trade_history(spec)

        assert result.status == "failed"
        assert "not found" in result.error


class TestFetchEvents:
    @pytest.mark.asyncio
    async def test_fetch_events_success(self):
        config = PolymarketClientConfig()
        collector = PolymarketCollector(config)
        spec = EventCollectSpec()

        raw_event = {
            "id": "evt_123",
            "title": "Bitcoin Price Milestones",
            "slug": "bitcoin-milestones",
            "startDate": "2026-01-01T00:00:00Z",
            "endDate": "2026-12-31T00:00:00Z",
            "markets": [SAMPLE_MARKET_RAW],
        }

        with patch("connectors.polymarket.collector.GammaClient") as MockGamma:
            mock_instance = AsyncMock()
            mock_instance.get_events = AsyncMock(return_value=[raw_event])
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockGamma.return_value = mock_instance

            result = await collector.fetch_events(spec)

        assert result.status == "success"
        assert len(result.events) == 1
        assert result.events[0].title == "Bitcoin Price Milestones"
        assert len(result.events[0].markets) == 1

    @pytest.mark.asyncio
    async def test_fetch_single_event(self):
        config = PolymarketClientConfig()
        collector = PolymarketCollector(config)
        spec = EventCollectSpec(event_id="evt_123")

        raw_event = {
            "id": "evt_123",
            "title": "Bitcoin Milestones",
            "slug": "bitcoin-milestones",
            "markets": [SAMPLE_MARKET_RAW],
        }

        with patch("connectors.polymarket.collector.GammaClient") as MockGamma:
            mock_instance = AsyncMock()
            mock_instance.get_event = AsyncMock(return_value=raw_event)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockGamma.return_value = mock_instance

            result = await collector.fetch_events(spec)

        assert result.status == "success"
        assert len(result.events) == 1
        mock_instance.get_event.assert_awaited_once_with("evt_123")

"""Tests for Polymarket Gamma API client."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from connectors.polymarket.models import PolymarketClientConfig
from connectors.polymarket.gamma_client import GammaClient


SAMPLE_MARKET = {
    "id": "12345",
    "conditionId": "cond_abc",
    "question": "Will BTC hit 100k?",
    "slug": "will-btc-hit-100k",
    "outcomes": '["Yes","No"]',
    "outcomePrices": '["0.65","0.35"]',
    "volume": "1234567.89",
    "liquidity": 50000.0,
    "liquidityNum": 50000.0,
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

SAMPLE_EVENT = {
    "id": "evt_123",
    "title": "Bitcoin Price Milestones",
    "slug": "bitcoin-price-milestones",
    "startDate": "2026-01-01T00:00:00Z",
    "endDate": "2026-12-31T00:00:00Z",
    "markets": [SAMPLE_MARKET],
}


def _mock_response(json_data, status_code=200):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.text = str(json_data)
    return resp


class TestGammaClientGetMarkets:
    @pytest.mark.asyncio
    async def test_get_markets_basic(self):
        config = PolymarketClientConfig()
        async with GammaClient(config) as client:
            with patch.object(client, "_get_client") as mock_get:
                mock_http = AsyncMock()
                mock_http.get = AsyncMock(return_value=_mock_response([SAMPLE_MARKET]))
                mock_get.return_value = mock_http
                result = await client.get_markets()
        assert len(result) == 1
        assert result[0]["id"] == "12345"

    @pytest.mark.asyncio
    async def test_get_markets_with_params(self):
        config = PolymarketClientConfig()
        async with GammaClient(config) as client:
            with patch.object(client, "_get_client") as mock_get:
                mock_http = AsyncMock()
                mock_http.get = AsyncMock(return_value=_mock_response([]))
                mock_get.return_value = mock_http
                await client.get_markets(
                    active=True, closed=False, limit=50, offset=10, order="volume"
                )
                call_kwargs = mock_http.get.call_args
                params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
                assert params["active"] == "true"
                assert params["closed"] == "false"
                assert params["limit"] == 50
                assert params["offset"] == 10
                assert params["order"] == "volume"

    @pytest.mark.asyncio
    async def test_get_markets_http_error(self):
        config = PolymarketClientConfig()
        async with GammaClient(config) as client:
            with patch.object(client, "_get_client") as mock_get:
                mock_http = AsyncMock()
                mock_http.get = AsyncMock(return_value=_mock_response({"error": "bad"}, 500))
                mock_get.return_value = mock_http
                from connectors.common.exceptions import DataFetchError
                with pytest.raises(DataFetchError):
                    await client.get_markets()


class TestGammaClientSearch:
    @pytest.mark.asyncio
    async def test_search(self):
        config = PolymarketClientConfig()
        async with GammaClient(config) as client:
            with patch.object(client, "_get_client") as mock_get:
                mock_http = AsyncMock()
                mock_http.get = AsyncMock(return_value=_mock_response([SAMPLE_MARKET]))
                mock_get.return_value = mock_http
                result = await client.search("bitcoin")
                call_kwargs = mock_http.get.call_args
                url = call_kwargs.args[0] if call_kwargs.args else ""
                assert "search" in url or "keyword" in str(call_kwargs)


class TestGammaClientGetEvents:
    @pytest.mark.asyncio
    async def test_get_events(self):
        config = PolymarketClientConfig()
        async with GammaClient(config) as client:
            with patch.object(client, "_get_client") as mock_get:
                mock_http = AsyncMock()
                mock_http.get = AsyncMock(return_value=_mock_response([SAMPLE_EVENT]))
                mock_get.return_value = mock_http
                result = await client.get_events()
        assert len(result) == 1
        assert result[0]["title"] == "Bitcoin Price Milestones"

    @pytest.mark.asyncio
    async def test_get_event_by_id(self):
        config = PolymarketClientConfig()
        async with GammaClient(config) as client:
            with patch.object(client, "_get_client") as mock_get:
                mock_http = AsyncMock()
                mock_http.get = AsyncMock(return_value=_mock_response(SAMPLE_EVENT))
                mock_get.return_value = mock_http
                result = await client.get_event("evt_123")
        assert result["id"] == "evt_123"


class TestGammaClientContextManager:
    @pytest.mark.asyncio
    async def test_context_manager_closes_client(self):
        config = PolymarketClientConfig()
        client = GammaClient(config)
        mock_http = AsyncMock()
        mock_http.aclose = AsyncMock()
        client._client = mock_http
        async with client:
            pass
        mock_http.aclose.assert_awaited_once()

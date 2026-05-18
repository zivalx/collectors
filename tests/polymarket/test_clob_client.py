"""Tests for Polymarket CLOB API client."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from connectors.polymarket.models import PolymarketClientConfig
from connectors.polymarket.clob_client import CLOBClient
from connectors.common.exceptions import DataFetchError


def _mock_response(json_data, status_code=200):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.text = str(json_data)
    return resp


class TestCLOBClientGetPrice:
    @pytest.mark.asyncio
    async def test_get_price(self):
        config = PolymarketClientConfig()
        async with CLOBClient(config) as client:
            with patch.object(client, "_get_client") as mock_get:
                mock_http = AsyncMock()
                mock_http.get = AsyncMock(return_value=_mock_response({"price": "0.65"}))
                mock_get.return_value = mock_http
                result = await client.get_price("token_abc", side="BUY")
        assert result == {"price": "0.65"}

    @pytest.mark.asyncio
    async def test_get_price_passes_params(self):
        config = PolymarketClientConfig()
        async with CLOBClient(config) as client:
            with patch.object(client, "_get_client") as mock_get:
                mock_http = AsyncMock()
                mock_http.get = AsyncMock(return_value=_mock_response({"price": "0.65"}))
                mock_get.return_value = mock_http
                await client.get_price("token_abc", side="SELL")
                call_kwargs = mock_http.get.call_args
                params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
                assert params["token_id"] == "token_abc"
                assert params["side"] == "SELL"

    @pytest.mark.asyncio
    async def test_get_price_error(self):
        config = PolymarketClientConfig()
        async with CLOBClient(config) as client:
            with patch.object(client, "_get_client") as mock_get:
                mock_http = AsyncMock()
                mock_http.get = AsyncMock(return_value=_mock_response({}, 500))
                mock_get.return_value = mock_http
                with pytest.raises(DataFetchError):
                    await client.get_price("token_abc")


class TestCLOBClientGetBook:
    @pytest.mark.asyncio
    async def test_get_book(self):
        book_data = {
            "bids": [{"price": "0.64", "size": "1500"}],
            "asks": [{"price": "0.66", "size": "2000"}],
        }
        config = PolymarketClientConfig()
        async with CLOBClient(config) as client:
            with patch.object(client, "_get_client") as mock_get:
                mock_http = AsyncMock()
                mock_http.get = AsyncMock(return_value=_mock_response(book_data))
                mock_get.return_value = mock_http
                result = await client.get_book("token_abc")
        assert len(result["bids"]) == 1
        assert len(result["asks"]) == 1


class TestCLOBClientGetMidpoint:
    @pytest.mark.asyncio
    async def test_get_midpoint(self):
        config = PolymarketClientConfig()
        async with CLOBClient(config) as client:
            with patch.object(client, "_get_client") as mock_get:
                mock_http = AsyncMock()
                mock_http.get = AsyncMock(return_value=_mock_response({"midpoint": "0.65"}))
                mock_get.return_value = mock_http
                result = await client.get_midpoint("token_abc")
        assert result == {"midpoint": "0.65"}


class TestCLOBClientGetPriceHistory:
    @pytest.mark.asyncio
    async def test_get_price_history(self):
        history_data = {
            "history": [
                {"t": 1630454400, "p": "0.52"},
                {"t": 1630540800, "p": "0.55"},
            ]
        }
        config = PolymarketClientConfig()
        async with CLOBClient(config) as client:
            with patch.object(client, "_get_client") as mock_get:
                mock_http = AsyncMock()
                mock_http.get = AsyncMock(return_value=_mock_response(history_data))
                mock_get.return_value = mock_http
                result = await client.get_price_history("token_abc", interval="1d")
        assert len(result["history"]) == 2

    @pytest.mark.asyncio
    async def test_get_price_history_with_timestamps(self):
        config = PolymarketClientConfig()
        async with CLOBClient(config) as client:
            with patch.object(client, "_get_client") as mock_get:
                mock_http = AsyncMock()
                mock_http.get = AsyncMock(return_value=_mock_response({"history": []}))
                mock_get.return_value = mock_http
                await client.get_price_history(
                    "token_abc", start_ts=1000000, end_ts=2000000, fidelity=60
                )
                call_kwargs = mock_http.get.call_args
                params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
                assert params["startTs"] == 1000000
                assert params["endTs"] == 2000000
                assert params["fidelity"] == 60


class TestCLOBClientContextManager:
    @pytest.mark.asyncio
    async def test_context_manager(self):
        config = PolymarketClientConfig()
        client = CLOBClient(config)
        mock_http_client = AsyncMock()
        mock_http_client.aclose = AsyncMock()
        client._client = mock_http_client
        async with client:
            pass
        mock_http_client.aclose.assert_awaited_once()

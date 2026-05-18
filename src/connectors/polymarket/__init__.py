"""Polymarket prediction market data connector."""

from connectors.polymarket.collector import PolymarketCollector
from connectors.polymarket.models import (
    PolymarketClientConfig,
    MarketCollectSpec,
    PriceCollectSpec,
    TradeHistorySpec,
    EventCollectSpec,
    Market,
    OrderBookLevel,
    OrderBookSnapshot,
    PricePoint,
    PriceSnapshot,
    TradeHistory,
    EventInfo,
    PolymarketResult,
)

__all__ = [
    "PolymarketCollector",
    "PolymarketClientConfig",
    "MarketCollectSpec",
    "PriceCollectSpec",
    "TradeHistorySpec",
    "EventCollectSpec",
    "Market",
    "OrderBookLevel",
    "OrderBookSnapshot",
    "PricePoint",
    "PriceSnapshot",
    "TradeHistory",
    "EventInfo",
    "PolymarketResult",
]

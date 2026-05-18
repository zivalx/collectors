"""High-level Polymarket data collector."""

import json
import logging
from datetime import datetime
from typing import List

from connectors.polymarket.gamma_client import GammaClient
from connectors.polymarket.clob_client import CLOBClient
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

logger = logging.getLogger(__name__)


def _parse_market(raw: dict) -> Market:
    outcomes_raw = raw.get("outcomes", "[]")
    if isinstance(outcomes_raw, str):
        outcomes = json.loads(outcomes_raw)
    else:
        outcomes = outcomes_raw

    prices_raw = raw.get("outcomePrices", "[]")
    if isinstance(prices_raw, str):
        outcome_prices = [float(p) for p in json.loads(prices_raw)]
    else:
        outcome_prices = [float(p) for p in prices_raw]

    token_ids_raw = raw.get("clobTokenIds", "[]")
    if isinstance(token_ids_raw, str):
        clob_token_ids = json.loads(token_ids_raw)
    else:
        clob_token_ids = token_ids_raw or []

    start_date = None
    if raw.get("startDate"):
        try:
            start_date = datetime.fromisoformat(raw["startDate"].replace("Z", "+00:00"))
        except (ValueError, TypeError):
            pass

    end_date = None
    if raw.get("endDate"):
        try:
            end_date = datetime.fromisoformat(raw["endDate"].replace("Z", "+00:00"))
        except (ValueError, TypeError):
            pass

    return Market(
        id=raw["id"],
        condition_id=raw.get("conditionId", ""),
        question=raw.get("question", ""),
        slug=raw.get("slug", ""),
        outcomes=outcomes,
        outcome_prices=outcome_prices,
        volume=float(raw.get("volume", 0)),
        liquidity=float(raw.get("liquidity", 0)),
        open_interest=raw.get("openInterest"),
        best_bid=raw.get("bestBid"),
        best_ask=raw.get("bestAsk"),
        last_trade_price=raw.get("lastTradePrice"),
        start_date=start_date,
        end_date=end_date,
        active=raw.get("active", False),
        closed=raw.get("closed", False),
        clob_token_ids=clob_token_ids,
        neg_risk=raw.get("negRisk", False),
        category=raw.get("category"),
    )


def _parse_event(raw: dict) -> EventInfo:
    start_date = None
    if raw.get("startDate"):
        try:
            start_date = datetime.fromisoformat(raw["startDate"].replace("Z", "+00:00"))
        except (ValueError, TypeError):
            pass

    end_date = None
    if raw.get("endDate"):
        try:
            end_date = datetime.fromisoformat(raw["endDate"].replace("Z", "+00:00"))
        except (ValueError, TypeError):
            pass

    markets: List[Market] = []
    for m in raw.get("markets", []):
        try:
            markets.append(_parse_market(m))
        except Exception as e:
            logger.warning(f"Error parsing market in event {raw.get('id')}: {e}")

    return EventInfo(
        id=raw["id"],
        title=raw.get("title", ""),
        slug=raw.get("slug", ""),
        start_date=start_date,
        end_date=end_date,
        markets=markets,
    )


class PolymarketCollector:
    """High-level Polymarket data collector.

    All fetch methods return PolymarketResult with status and error handling.
    Never raises -- returns status='failed' on error.
    """

    def __init__(self, config: PolymarketClientConfig):
        self.config = config

    async def fetch_markets(self, spec: MarketCollectSpec) -> PolymarketResult:
        """Discover and list markets. Uses search if spec.query is set."""
        result = PolymarketResult(collected_at=datetime.now())
        try:
            async with GammaClient(self.config) as client:
                if spec.query:
                    raw_markets = await client.search(spec.query)
                else:
                    raw_markets = await client.get_markets(
                        active=spec.active,
                        closed=spec.closed,
                        limit=spec.limit,
                        offset=spec.offset,
                        order=spec.order,
                        ascending=spec.ascending,
                        tag_id=spec.tag,
                    )
                for raw in raw_markets:
                    try:
                        result.markets.append(_parse_market(raw))
                    except Exception as e:
                        logger.warning(f"Error parsing market {raw.get('id', '?')}: {e}")
                result.total_count = len(result.markets)
                result.status = "success"
                logger.info(f"Fetched {result.total_count} markets")
        except Exception as e:
            logger.error(f"Error fetching markets: {e}")
            result.status = "failed"
            result.error = str(e)
        return result

    async def fetch_prices(self, spec: PriceCollectSpec) -> PolymarketResult:
        """Fetch current prices and optionally orderbooks for tokens."""
        result = PolymarketResult(collected_at=datetime.now())
        try:
            async with CLOBClient(self.config) as client:
                for token_id in spec.token_ids:
                    try:
                        price_data = await client.get_price(token_id)
                        midpoint_data = await client.get_midpoint(token_id)
                        snapshot = PriceSnapshot(
                            token_id=token_id,
                            ask=float(price_data.get("price", 0)),
                            midpoint=float(midpoint_data.get("midpoint", 0)),
                        )
                        result.prices.append(snapshot)

                        if spec.include_orderbook:
                            book_data = await client.get_book(token_id)
                            orderbook = OrderBookSnapshot(
                                token_id=token_id,
                                bids=[
                                    OrderBookLevel(
                                        price=float(b["price"]), size=float(b["size"])
                                    )
                                    for b in book_data.get("bids", [])
                                ],
                                asks=[
                                    OrderBookLevel(
                                        price=float(a["price"]), size=float(a["size"])
                                    )
                                    for a in book_data.get("asks", [])
                                ],
                            )
                            result.orderbooks.append(orderbook)
                    except Exception as e:
                        logger.warning(f"Error fetching price for token {token_id}: {e}")
                result.total_count = len(result.prices)
                result.status = "success"
                logger.info(f"Fetched prices for {result.total_count} tokens")
        except Exception as e:
            logger.error(f"Error fetching prices: {e}")
            result.status = "failed"
            result.error = str(e)
        return result

    async def fetch_trade_history(self, spec: TradeHistorySpec) -> PolymarketResult:
        """Fetch historical price time-series for a token."""
        result = PolymarketResult(collected_at=datetime.now())
        try:
            async with CLOBClient(self.config) as client:
                start_ts = int(spec.from_date.timestamp()) if spec.from_date else None
                end_ts = int(spec.to_date.timestamp()) if spec.to_date else None
                raw = await client.get_price_history(
                    token_id=spec.token_id,
                    interval=spec.interval,
                    start_ts=start_ts,
                    end_ts=end_ts,
                    fidelity=spec.fidelity,
                )
                history_points = [
                    PricePoint(timestamp=point["t"], price=float(point["p"]))
                    for point in raw.get("history", [])
                ]
                result.trade_history = TradeHistory(
                    token_id=spec.token_id,
                    interval=spec.interval,
                    history=history_points,
                )
                result.total_count = len(history_points)
                result.status = "success"
                logger.info(
                    f"Fetched {result.total_count} price points for {spec.token_id}"
                )
        except Exception as e:
            logger.error(f"Error fetching trade history: {e}")
            result.status = "failed"
            result.error = str(e)
        return result

    async def fetch_events(self, spec: EventCollectSpec) -> PolymarketResult:
        """Fetch events (groups of related markets)."""
        result = PolymarketResult(collected_at=datetime.now())
        try:
            async with GammaClient(self.config) as client:
                if spec.event_id:
                    raw_event = await client.get_event(spec.event_id)
                    result.events.append(_parse_event(raw_event))
                elif spec.slug:
                    raw_event = await client.get_event(spec.slug)
                    result.events.append(_parse_event(raw_event))
                else:
                    raw_events = await client.get_events(
                        active=spec.active,
                        closed=not spec.active,
                        limit=spec.limit,
                        offset=spec.offset,
                    )
                    for raw in raw_events:
                        try:
                            result.events.append(_parse_event(raw))
                        except Exception as e:
                            logger.warning(
                                f"Error parsing event {raw.get('id', '?')}: {e}"
                            )
                result.total_count = len(result.events)
                result.status = "success"
                logger.info(f"Fetched {result.total_count} events")
        except Exception as e:
            logger.error(f"Error fetching events: {e}")
            result.status = "failed"
            result.error = str(e)
        return result

"""Polymarket connector example.

Shows how to discover markets, fetch prices, history, and events.
No API key needed — all endpoints are public.
"""

import asyncio
import sys
from connectors import setup_logging
from connectors.polymarket import (
    PolymarketCollector,
    PolymarketClientConfig,
    MarketCollectSpec,
    PriceCollectSpec,
    TradeHistorySpec,
    EventCollectSpec,
)


async def main():
    setup_logging(level="INFO")

    config = PolymarketClientConfig(timeout=30)
    collector = PolymarketCollector(config)

    # 1. Discover active markets sorted by volume
    print("=" * 60)
    print("DISCOVERING TOP MARKETS BY VOLUME")
    print("=" * 60)

    spec = MarketCollectSpec(active=True, order="volume", ascending=False, limit=5)
    result = await collector.fetch_markets(spec)

    if result.status == "success":
        for i, market in enumerate(result.markets, 1):
            prices_str = " / ".join(
                f"{o}: {p:.0%}"
                for o, p in zip(market.outcomes, market.outcome_prices)
            )
            print(f"\n{i}. {market.question}")
            print(f"   Prices: {prices_str}")
            print(f"   Volume: ${market.volume:,.0f} | Liquidity: ${market.liquidity:,.0f}")
            print(f"   Active: {market.active} | Token IDs: {market.clob_token_ids[:2]}")
    else:
        print(f"Failed: {result.error}")

    # 2. Fetch prices for the first market's tokens
    if result.markets and result.markets[0].clob_token_ids:
        token_ids = result.markets[0].clob_token_ids[:2]
        print(f"\n{'=' * 60}")
        print(f"FETCHING PRICES + ORDERBOOK FOR: {result.markets[0].question[:50]}")
        print(f"{'=' * 60}")

        price_spec = PriceCollectSpec(token_ids=token_ids, include_orderbook=True)
        price_result = await collector.fetch_prices(price_spec)

        if price_result.status == "success":
            for snap in price_result.prices:
                print(f"\n  Token: {snap.token_id[:16]}...")
                print(f"  Ask: {snap.ask} | Midpoint: {snap.midpoint}")

            for book in price_result.orderbooks:
                print(f"\n  Orderbook ({book.token_id[:16]}...):")
                for bid in book.bids[:3]:
                    print(f"    BID {bid.price:.4f} x {bid.size:.0f}")
                for ask in book.asks[:3]:
                    print(f"    ASK {ask.price:.4f} x {ask.size:.0f}")

        # 3. Fetch price history
        print(f"\n{'=' * 60}")
        print("PRICE HISTORY (1d interval)")
        print(f"{'=' * 60}")

        history_spec = TradeHistorySpec(token_id=token_ids[0], interval="1d")
        history_result = await collector.fetch_trade_history(history_spec)

        if history_result.status == "success" and history_result.trade_history:
            points = history_result.trade_history.history
            print(f"  {len(points)} data points")
            for point in points[-5:]:
                print(f"  ts={point.timestamp} price={point.price:.4f}")

    # 4. Fetch events
    print(f"\n{'=' * 60}")
    print("RECENT EVENTS")
    print(f"{'=' * 60}")

    event_spec = EventCollectSpec(active=True, limit=3)
    event_result = await collector.fetch_events(event_spec)

    if event_result.status == "success":
        for evt in event_result.events:
            print(f"\n  {evt.title}")
            print(f"  Slug: {evt.slug} | Markets: {len(evt.markets)}")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())

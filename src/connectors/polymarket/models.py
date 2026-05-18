"""Pydantic models for Polymarket API connector."""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime
from connectors.common.config import BaseClientConfig, BaseCollectSpec


class PolymarketClientConfig(BaseClientConfig):
    """Polymarket API client settings.

    No API key needed for read-only access.
    Gamma API: market discovery, events, search.
    CLOB API: prices, orderbooks, trades, history.
    """

    gamma_base_url: str = Field(
        default="https://gamma-api.polymarket.com",
        description="Gamma API base URL",
    )
    clob_base_url: str = Field(
        default="https://clob.polymarket.com",
        description="CLOB API base URL",
    )


class MarketCollectSpec(BaseCollectSpec):
    """Specification for discovering/searching Polymarket markets."""

    query: Optional[str] = Field(default=None, description="Search keyword")
    tag: Optional[str] = Field(default=None, description="Category tag filter")
    active: bool = Field(default=True, description="Filter active markets")
    closed: bool = Field(default=False, description="Include closed markets")
    order: Optional[str] = Field(
        default=None,
        description="Sort field: volume, liquidity, created_at, end_date",
    )
    ascending: bool = Field(default=False, description="Sort direction")
    limit: int = Field(default=100, ge=1, le=500, description="Page size")
    offset: int = Field(default=0, ge=0, description="Pagination offset")

    @field_validator("order")
    @classmethod
    def validate_order(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = ["volume", "liquidity", "created_at", "end_date"]
        if v not in allowed:
            raise ValueError(f"order must be one of {allowed}")
        return v


class PriceCollectSpec(BaseCollectSpec):
    """Specification for fetching prices and orderbooks."""

    token_ids: List[str] = Field(
        ..., min_length=1, description="CLOB token IDs to fetch prices for"
    )
    include_orderbook: bool = Field(
        default=False, description="Also fetch full orderbook depth"
    )


class TradeHistorySpec(BaseCollectSpec):
    """Specification for fetching price history time-series."""

    token_id: str = Field(..., min_length=1, description="CLOB token ID")
    interval: str = Field(default="1d", description="Time interval: 1h, 6h, 1d, 1w, max")
    fidelity: Optional[int] = Field(
        default=None, description="Granularity in minutes (e.g., 60=hourly)"
    )
    from_date: Optional[datetime] = Field(default=None, description="Start timestamp")
    to_date: Optional[datetime] = Field(default=None, description="End timestamp")

    @field_validator("interval")
    @classmethod
    def validate_interval(cls, v: str) -> str:
        allowed = ["1h", "6h", "1d", "1w", "max"]
        if v not in allowed:
            raise ValueError(f"interval must be one of {allowed}")
        return v


class EventCollectSpec(BaseCollectSpec):
    """Specification for fetching event lifecycle data."""

    event_id: Optional[str] = Field(default=None, description="Event ID")
    slug: Optional[str] = Field(default=None, description="Event slug")
    include_markets: bool = Field(
        default=True, description="Include nested market data"
    )
    active: bool = Field(default=True, description="Filter active events")
    limit: int = Field(default=100, ge=1, le=500, description="Page size")
    offset: int = Field(default=0, ge=0, description="Pagination offset")


class Market(BaseModel):
    """A Polymarket prediction market."""

    id: str
    condition_id: str
    question: str
    slug: str
    outcomes: List[str]
    outcome_prices: List[float]
    volume: float
    liquidity: float
    open_interest: Optional[float] = None
    best_bid: Optional[float] = None
    best_ask: Optional[float] = None
    last_trade_price: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    active: bool
    closed: bool
    clob_token_ids: List[str] = Field(default_factory=list)
    neg_risk: bool = False
    category: Optional[str] = None
    collected_at: datetime = Field(default_factory=datetime.now)

    class Config:
        frozen = False


class OrderBookLevel(BaseModel):
    """A single price level in an orderbook."""

    price: float
    size: float


class OrderBookSnapshot(BaseModel):
    """Full orderbook for a token."""

    token_id: str
    bids: List[OrderBookLevel] = Field(default_factory=list)
    asks: List[OrderBookLevel] = Field(default_factory=list)
    spread: Optional[float] = None
    midpoint: Optional[float] = None
    collected_at: datetime = Field(default_factory=datetime.now)

    class Config:
        frozen = False


class PricePoint(BaseModel):
    """A single price data point in a time series."""

    timestamp: int
    price: float


class PriceSnapshot(BaseModel):
    """Current price for a token."""

    token_id: str
    bid: Optional[float] = None
    ask: Optional[float] = None
    midpoint: Optional[float] = None
    last_trade_price: Optional[float] = None
    collected_at: datetime = Field(default_factory=datetime.now)

    class Config:
        frozen = False


class TradeHistory(BaseModel):
    """Historical price time-series for a token."""

    token_id: str
    interval: str
    history: List[PricePoint] = Field(default_factory=list)
    collected_at: datetime = Field(default_factory=datetime.now)

    class Config:
        frozen = False


class EventInfo(BaseModel):
    """A Polymarket event (group of related markets)."""

    id: str
    title: str
    slug: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    markets: List[Market] = Field(default_factory=list)
    collected_at: datetime = Field(default_factory=datetime.now)

    class Config:
        frozen = False


class PolymarketResult(BaseModel):
    """Wraps any Polymarket response with metadata and status."""

    markets: List[Market] = Field(default_factory=list)
    events: List[EventInfo] = Field(default_factory=list)
    prices: List[PriceSnapshot] = Field(default_factory=list)
    orderbooks: List[OrderBookSnapshot] = Field(default_factory=list)
    trade_history: Optional[TradeHistory] = None
    total_count: int = 0
    collected_at: datetime = Field(default_factory=datetime.now)
    status: str = Field(default="success")
    error: Optional[str] = None

    class Config:
        frozen = False

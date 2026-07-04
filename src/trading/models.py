"""Core domain types shared by every module.

Deliberately plain dataclasses/enums with no external dependencies, so the
risk and portfolio modules (the money-critical ones) stay trivially testable.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone


class Side(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"


class Signal(enum.Enum):
    """What a strategy wants its stance in an instrument to be."""

    LONG = "LONG"
    FLAT = "FLAT"
    HOLD = "HOLD"  # no opinion this bar; keep current stance


class OrderStatus(enum.Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


@dataclass
class Order:
    symbol: str
    side: Side
    quantity: int
    # limit_price=None means a market order
    limit_price: float | None = None
    status: OrderStatus = OrderStatus.PENDING
    reason: str = ""  # why it was placed, or why it was rejected — the audit trail
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Fill:
    symbol: str
    side: Side
    quantity: int
    price: float
    costs: float  # brokerage + taxes + slippage, in currency
    at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Position:
    symbol: str
    quantity: int = 0
    avg_price: float = 0.0

    def market_value(self, price: float) -> float:
        return self.quantity * price

    def unrealized_pnl(self, price: float) -> float:
        return (price - self.avg_price) * self.quantity


@dataclass
class Bar:
    """One OHLCV bar (daily or intraday)."""

    symbol: str
    at: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int

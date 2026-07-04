"""Broker adapter interface — the seam where new markets get added.

ZerodhaAdapter implements this for NSE now; an AlpacaAdapter implements the
same interface for US equities later; the currency-derivatives (forex) work
extends ZerodhaAdapter rather than adding a broker (see
architecture/07_SCALING_ROADMAP.md). Strategy/risk/portfolio code must never
import a concrete broker.
"""

from __future__ import annotations

import abc

from trading.models import Fill, Order, Position


class BrokerAdapter(abc.ABC):
    @abc.abstractmethod
    def place_order(self, order: Order) -> str:
        """Place an order; returns the broker's order id."""

    @abc.abstractmethod
    def get_positions(self) -> list[Position]:
        """Positions as the broker reports them — the reconciliation source of truth."""

    @abc.abstractmethod
    def get_quote(self, symbol: str) -> float:
        """Last traded price."""

    @abc.abstractmethod
    def get_fills(self, broker_order_id: str) -> list[Fill]:
        """Fills for a previously placed order (may be partial)."""

"""Order executor interface.

Two implementations behind the same interface — simulated (backtest/paper)
and real (broker) — so switching paper→live is a config flag, not a code
fork. That is what makes paper trading actually validate the live path.
"""

from __future__ import annotations

import abc

from trading.models import Fill, Order


class OrderExecutor(abc.ABC):
    @abc.abstractmethod
    def execute(self, order: Order, market_price: float) -> Fill:
        """Execute an approved order; returns the fill or raises on rejection."""

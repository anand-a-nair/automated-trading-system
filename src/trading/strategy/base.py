"""Strategy interface: bars in, signal out.

Strategies only express a desired stance (LONG/FLAT/HOLD). Position sizing
and limit enforcement belong to trading.risk — a strategy cannot size its
own orders past the risk limits by design.
"""

from __future__ import annotations

import abc

from trading.models import Bar, Signal


class Strategy(abc.ABC):
    name: str = "unnamed"

    @abc.abstractmethod
    def on_bar(self, history: list[Bar]) -> Signal:
        """Called once per bar with all history up to and including that bar."""

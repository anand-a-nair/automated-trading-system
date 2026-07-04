"""Market data interface.

Strategies consume this interface and never a concrete provider, so the same
strategy runs against Yahoo historical bars today, Kite live ticks in paper/
live trading, and Alpaca bars when US equities are added.
"""

from __future__ import annotations

import abc
from datetime import date

from trading.models import Bar


class MarketDataSource(abc.ABC):
    @abc.abstractmethod
    def get_historical(self, symbol: str, start: date, end: date) -> list[Bar]:
        """Daily bars for [start, end], oldest first."""

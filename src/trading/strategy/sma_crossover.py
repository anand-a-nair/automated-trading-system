"""Example strategy: simple moving-average crossover.

Deliberately simple enough to verify by hand — the point of the first
strategy is to validate the backtest/paper/live pipeline, not to make money.
"""

from __future__ import annotations

from trading.models import Bar, Signal
from trading.strategy.base import Strategy


class SmaCrossover(Strategy):
    def __init__(self, fast: int = 20, slow: int = 50) -> None:
        if fast >= slow:
            raise ValueError("fast window must be shorter than slow window")
        self.fast = fast
        self.slow = slow
        self.name = f"sma_{fast}_{slow}"

    def on_bar(self, history: list[Bar]) -> Signal:
        if len(history) < self.slow:
            return Signal.HOLD
        closes = [b.close for b in history]
        fast_ma = sum(closes[-self.fast:]) / self.fast
        slow_ma = sum(closes[-self.slow:]) / self.slow
        if fast_ma > slow_ma:
            return Signal.LONG
        return Signal.FLAT

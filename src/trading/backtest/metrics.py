"""Performance metrics, hand-rolled on purpose.

Each of these is a few lines; understanding them is part of the project's
learning goal (architecture/01_VISION.md). Inputs are an equity curve
(one value per bar) unless stated otherwise.
"""

from __future__ import annotations

import math

TRADING_DAYS_PER_YEAR = 252


def total_return(equity_curve: list[float]) -> float:
    """Fractional return over the whole period, e.g. 0.12 == +12%."""
    if len(equity_curve) < 2 or equity_curve[0] == 0:
        return 0.0
    return equity_curve[-1] / equity_curve[0] - 1


def max_drawdown(equity_curve: list[float]) -> float:
    """Largest peak-to-trough fall, as a positive fraction (0.25 == -25%)."""
    peak = float("-inf")
    worst = 0.0
    for value in equity_curve:
        peak = max(peak, value)
        if peak > 0:
            worst = max(worst, (peak - value) / peak)
    return worst


def sharpe_ratio(equity_curve: list[float], risk_free_rate: float = 0.0) -> float:
    """Annualized Sharpe from daily equity values.

    risk_free_rate is annual (e.g. 0.07 for 7%); it is converted to a daily
    rate internally.
    """
    if len(equity_curve) < 3:
        return 0.0
    daily_rf = (1 + risk_free_rate) ** (1 / TRADING_DAYS_PER_YEAR) - 1
    returns = [
        equity_curve[i] / equity_curve[i - 1] - 1 - daily_rf
        for i in range(1, len(equity_curve))
        if equity_curve[i - 1] != 0
    ]
    if not returns:
        return 0.0
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    std = math.sqrt(variance)
    if std == 0:
        return 0.0
    return mean / std * math.sqrt(TRADING_DAYS_PER_YEAR)


def win_rate(round_trip_pnls: list[float]) -> float:
    """Fraction of closed round-trip trades with positive PnL."""
    if not round_trip_pnls:
        return 0.0
    return sum(1 for p in round_trip_pnls if p > 0) / len(round_trip_pnls)

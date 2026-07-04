"""End-to-end backtest on synthetic bars — no network, no real data."""

from datetime import datetime, timedelta, timezone

from trading.backtest import BacktestEngine
from trading.config import RiskLimits
from trading.models import Bar, Signal
from trading.strategy.base import Strategy


def make_bars(closes: list[float], symbol: str = "TEST") -> list[Bar]:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return [
        Bar(
            symbol=symbol,
            at=start + timedelta(days=i),
            open=c,
            high=c * 1.01,
            low=c * 0.99,
            close=c,
            volume=1_000,
        )
        for i, c in enumerate(closes)
    ]


class BuyAndHold(Strategy):
    name = "buy_and_hold"

    def on_bar(self, history):
        return Signal.LONG


class AlwaysFlat(Strategy):
    name = "always_flat"

    def on_bar(self, history):
        return Signal.FLAT


def test_buy_and_hold_profits_in_uptrend():
    closes = [100 + i for i in range(30)]  # steady rise 100 -> 129
    result = BacktestEngine(starting_cash=100_000).run(BuyAndHold(), make_bars(closes))
    assert result.total_return > 0
    assert len(result.fills) == 1  # one entry, never exits
    assert result.equity_curve[-1] > result.equity_curve[0]


def test_always_flat_never_trades_and_equity_stays_cash():
    closes = [100 + i for i in range(10)]
    result = BacktestEngine(starting_cash=50_000).run(AlwaysFlat(), make_bars(closes))
    assert result.fills == []
    assert all(v == 50_000 for v in result.equity_curve)


def test_position_respects_risk_limit():
    closes = [100.0] * 10
    limits = RiskLimits(max_position_pct=0.10, max_deployed_pct=0.80, max_daily_loss_pct=0.02)
    result = BacktestEngine(starting_cash=100_000, limits=limits).run(
        BuyAndHold(), make_bars(closes)
    )
    assert len(result.fills) == 1
    fill = result.fills[0]
    assert fill.quantity * fill.price <= 0.10 * 100_000 * 1.01  # within limit + slippage


def test_round_trip_recorded_on_exit():
    class InThenOut(Strategy):
        name = "in_then_out"

        def on_bar(self, history):
            return Signal.LONG if len(history) < 5 else Signal.FLAT

    closes = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109]
    result = BacktestEngine(starting_cash=100_000).run(InThenOut(), make_bars(closes))
    assert len(result.fills) == 2
    assert len(result.round_trip_pnls) == 1


def test_sma_crossover_runs_end_to_end():
    from trading.strategy.sma_crossover import SmaCrossover

    # long uptrend then decline: should enter after warmup and exit on the way down
    closes = [100 + i * 0.5 for i in range(80)] + [140 - i for i in range(40)]
    result = BacktestEngine(starting_cash=100_000).run(
        SmaCrossover(fast=5, slow=20), make_bars(closes)
    )
    assert len(result.fills) >= 2  # at least one round trip
    assert len(result.equity_curve) == len(closes)

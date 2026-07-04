"""Bar-by-bar backtest engine for a single symbol.

Runs the exact same strategy/risk/execution/portfolio modules the paper and
live paths use — the only substitutions are historical bars for live data and
SimulatedExecutor for the broker. Fills happen at the close of the signal bar
(pessimistic slippage applied by the cost model).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from trading.backtest import metrics
from trading.config import RiskLimits
from trading.execution import SimulatedExecutor
from trading.models import Bar, Fill, Order, Side, Signal
from trading.portfolio import Portfolio
from trading.risk import RiskEngine
from trading.strategy import Strategy


@dataclass
class BacktestResult:
    strategy_name: str
    symbol: str
    equity_curve: list[float] = field(default_factory=list)
    fills: list[Fill] = field(default_factory=list)
    rejections: list[str] = field(default_factory=list)
    round_trip_pnls: list[float] = field(default_factory=list)

    @property
    def total_return(self) -> float:
        return metrics.total_return(self.equity_curve)

    @property
    def max_drawdown(self) -> float:
        return metrics.max_drawdown(self.equity_curve)

    @property
    def sharpe_ratio(self) -> float:
        return metrics.sharpe_ratio(self.equity_curve)

    @property
    def win_rate(self) -> float:
        return metrics.win_rate(self.round_trip_pnls)

    def summary(self) -> str:
        return (
            f"{self.strategy_name} on {self.symbol}: "
            f"return {self.total_return:+.2%}, "
            f"max drawdown {self.max_drawdown:.2%}, "
            f"sharpe {self.sharpe_ratio:.2f}, "
            f"win rate {self.win_rate:.0%} over {len(self.round_trip_pnls)} round trips "
            f"({len(self.fills)} fills, {len(self.rejections)} rejections)"
        )


class BacktestEngine:
    def __init__(
        self,
        starting_cash: float,
        limits: RiskLimits | None = None,
        executor: SimulatedExecutor | None = None,
    ) -> None:
        self.starting_cash = starting_cash
        self.limits = limits or RiskLimits()
        self.executor = executor or SimulatedExecutor()

    def run(self, strategy: Strategy, bars: list[Bar]) -> BacktestResult:
        if not bars:
            raise ValueError("no bars to backtest")
        symbol = bars[0].symbol
        portfolio = Portfolio(cash=self.starting_cash)
        risk = RiskEngine(self.limits)
        result = BacktestResult(strategy_name=strategy.name, symbol=symbol)
        realized_before = 0.0

        for i, bar in enumerate(bars):
            prices = {symbol: bar.close}
            if i == 0 or bar.at.date() != bars[i - 1].at.date():
                risk.start_of_day(portfolio.equity(prices))

            signal = strategy.on_bar(bars[: i + 1])
            held = portfolio.position(symbol).quantity

            order: Order | None = None
            if signal is Signal.LONG and held == 0:
                quantity = self._size_position(portfolio, prices, bar.close)
                if quantity > 0:
                    order = Order(symbol, Side.BUY, quantity, reason=f"signal LONG at {bar.close}")
            elif signal is Signal.FLAT and held > 0:
                order = Order(symbol, Side.SELL, held, reason=f"signal FLAT at {bar.close}")

            if order is not None:
                decision = risk.check(order, portfolio, prices)
                if decision:
                    fill = self.executor.execute(order, bar.close)
                    portfolio.apply_fill(fill)
                    result.fills.append(fill)
                    if fill.side is Side.SELL:
                        result.round_trip_pnls.append(portfolio.realized_pnl - realized_before)
                        realized_before = portfolio.realized_pnl
                else:
                    result.rejections.append(f"{bar.at.date()} {order.side.value}: {decision.reason}")

            result.equity_curve.append(portfolio.equity(prices))

        return result

    def _size_position(self, portfolio: Portfolio, prices: dict, price: float) -> int:
        """Size to the max single-position limit, capped by cash net of costs."""
        equity = portfolio.equity(prices)
        budget = min(self.limits.max_position_pct * equity, portfolio.cash)
        # leave headroom for slippage and fees so the fill can't overdraw cash
        friction = 1 + self.executor.cost_model.slippage_pct + self.executor.cost_model.fees_pct
        return int(budget / (price * friction))

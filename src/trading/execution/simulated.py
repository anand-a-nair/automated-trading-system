"""Simulated execution for backtesting and paper trading."""

from __future__ import annotations

from dataclasses import dataclass

from trading.execution.base import OrderExecutor
from trading.models import Fill, Order, OrderStatus, Side


@dataclass(frozen=True)
class CostModel:
    """Round-trip friction as fractions of trade value.

    Defaults approximate Zerodha equity delivery (zero brokerage, ~0.1% STT
    on both legs plus exchange/stamp charges) plus a conservative slippage
    assumption. Being pessimistic here is deliberate — an optimistic backtest
    is worse than no backtest.
    """

    fees_pct: float = 0.0015  # STT + exchange + stamp, roughly
    slippage_pct: float = 0.001

    def costs(self, quantity: int, price: float) -> float:
        return quantity * price * self.fees_pct

    def fill_price(self, side: Side, price: float) -> float:
        # slippage always works against you
        if side is Side.BUY:
            return price * (1 + self.slippage_pct)
        return price * (1 - self.slippage_pct)


class SimulatedExecutor(OrderExecutor):
    def __init__(self, cost_model: CostModel | None = None) -> None:
        self.cost_model = cost_model or CostModel()

    def execute(self, order: Order, market_price: float) -> Fill:
        price = self.cost_model.fill_price(order.side, market_price)
        fill = Fill(
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=price,
            costs=self.cost_model.costs(order.quantity, price),
        )
        order.status = OrderStatus.FILLED
        return fill

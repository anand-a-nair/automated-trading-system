"""Pre-order risk checks. Every order passes through here before execution.

This module is intentionally boring and independent of strategy code: a bug
in a strategy must not be able to bypass these checks. Keep it the
best-tested module in the codebase.
"""

from __future__ import annotations

from dataclasses import dataclass

from trading.config import RiskLimits
from trading.models import Order, Side
from trading.portfolio import Portfolio


@dataclass(frozen=True)
class RiskDecision:
    approved: bool
    reason: str

    def __bool__(self) -> bool:
        return self.approved


class RiskEngine:
    def __init__(self, limits: RiskLimits) -> None:
        self.limits = limits
        self.kill_switch = False
        self._halted_for_day = False
        self._day_start_equity: float | None = None

    # -- day lifecycle ----------------------------------------------------

    def start_of_day(self, equity: float) -> None:
        """Call once per trading day before any orders; resets the daily halt."""
        self._day_start_equity = equity
        self._halted_for_day = False

    @property
    def halted(self) -> bool:
        return self.kill_switch or self._halted_for_day

    # -- checks ------------------------------------------------------------

    def check(self, order: Order, portfolio: Portfolio, prices: dict[str, float]) -> RiskDecision:
        """Approve or reject an order against all limits. Never raises."""
        if self.kill_switch:
            return RiskDecision(False, "kill switch is on")

        equity = portfolio.equity(prices)
        if self._daily_loss_breached(equity):
            self._halted_for_day = True
            return RiskDecision(
                False,
                f"daily loss limit ({self.limits.max_daily_loss_pct:.1%}) breached — halted for the day",
            )

        if order.side is Side.SELL:
            held = portfolio.position(order.symbol).quantity
            if order.quantity > held:
                return RiskDecision(
                    False, f"sell of {order.quantity} exceeds held quantity {held}"
                )
            return RiskDecision(True, "sell within held quantity")

        price = order.limit_price if order.limit_price is not None else prices[order.symbol]
        order_value = order.quantity * price

        if order_value > self.limits.max_position_pct * equity:
            return RiskDecision(
                False,
                f"order value {order_value:.2f} exceeds "
                f"{self.limits.max_position_pct:.0%} of equity {equity:.2f}",
            )

        existing = portfolio.position(order.symbol).market_value(prices.get(order.symbol, price))
        if existing + order_value > self.limits.max_position_pct * equity:
            return RiskDecision(
                False,
                f"position in {order.symbol} would exceed "
                f"{self.limits.max_position_pct:.0%} of equity",
            )

        deployed = portfolio.deployed_value(prices)
        if deployed + order_value > self.limits.max_deployed_pct * equity:
            return RiskDecision(
                False,
                f"total deployed capital would exceed {self.limits.max_deployed_pct:.0%} of equity",
            )

        if order_value > portfolio.cash:
            return RiskDecision(
                False, f"order value {order_value:.2f} exceeds available cash {portfolio.cash:.2f}"
            )

        return RiskDecision(True, "within all limits")

    def _daily_loss_breached(self, equity: float) -> bool:
        if self._halted_for_day:
            return True
        if self._day_start_equity is None or self._day_start_equity <= 0:
            return False
        loss = (self._day_start_equity - equity) / self._day_start_equity
        return loss > self.limits.max_daily_loss_pct

"""Portfolio state: the system's single source of truth for what it holds.

When live, this must be reconciled against the broker's reported positions
(see architecture/06_KEY_CONSIDERATIONS.md) — the broker wins on mismatch,
but only after a human looks at why.
"""

from __future__ import annotations

from trading.models import Fill, Position, Side


class Portfolio:
    def __init__(self, cash: float) -> None:
        if cash < 0:
            raise ValueError("starting cash cannot be negative")
        self.cash = cash
        self.positions: dict[str, Position] = {}
        self.realized_pnl = 0.0
        self.total_costs = 0.0

    def position(self, symbol: str) -> Position:
        return self.positions.get(symbol, Position(symbol=symbol))

    def apply_fill(self, fill: Fill) -> None:
        """Update cash/positions/realized PnL for an executed fill."""
        if fill.quantity <= 0:
            raise ValueError("fill quantity must be positive")
        pos = self.positions.setdefault(fill.symbol, Position(symbol=fill.symbol))

        if fill.side is Side.BUY:
            cost = fill.quantity * fill.price + fill.costs
            if cost > self.cash + 1e-9:
                raise ValueError(
                    f"fill for {fill.symbol} costs {cost:.2f} but only {self.cash:.2f} cash available"
                )
            new_qty = pos.quantity + fill.quantity
            pos.avg_price = (
                (pos.avg_price * pos.quantity + fill.price * fill.quantity) / new_qty
            )
            pos.quantity = new_qty
            self.cash -= cost
        else:
            if fill.quantity > pos.quantity:
                raise ValueError(
                    f"cannot sell {fill.quantity} of {fill.symbol}; holding {pos.quantity}"
                )
            self.realized_pnl += (fill.price - pos.avg_price) * fill.quantity - fill.costs
            self.cash += fill.quantity * fill.price - fill.costs
            pos.quantity -= fill.quantity
            if pos.quantity == 0:
                pos.avg_price = 0.0
                del self.positions[fill.symbol]

        self.total_costs += fill.costs

    def deployed_value(self, prices: dict[str, float]) -> float:
        """Market value of all open positions."""
        return sum(p.market_value(prices[s]) for s, p in self.positions.items())

    def equity(self, prices: dict[str, float]) -> float:
        """Cash plus market value of open positions."""
        return self.cash + self.deployed_value(prices)

    def unrealized_pnl(self, prices: dict[str, float]) -> float:
        return sum(p.unrealized_pnl(prices[s]) for s, p in self.positions.items())

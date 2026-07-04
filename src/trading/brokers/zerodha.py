"""Zerodha Kite Connect adapter — Stage 2/3 work, stubbed until then.

Requires the paid Kite Connect subscription and the `kiteconnect` SDK
(`pip install .[live]`). Not needed for Stage 1 backtesting.
"""

from __future__ import annotations

from trading.brokers.base import BrokerAdapter
from trading.models import Fill, Order, Position


class ZerodhaAdapter(BrokerAdapter):
    def __init__(self, api_key: str, access_token: str) -> None:
        self.api_key = api_key
        self.access_token = access_token
        # Deferred: instantiate kiteconnect.KiteConnect here in Stage 2.

    def place_order(self, order: Order) -> str:
        raise NotImplementedError("Stage 3 — see architecture/05_IMPLEMENTATION_ROADMAP.md")

    def get_positions(self) -> list[Position]:
        raise NotImplementedError("Stage 3 — see architecture/05_IMPLEMENTATION_ROADMAP.md")

    def get_quote(self, symbol: str) -> float:
        raise NotImplementedError("Stage 2 — see architecture/05_IMPLEMENTATION_ROADMAP.md")

    def get_fills(self, broker_order_id: str) -> list[Fill]:
        raise NotImplementedError("Stage 3 — see architecture/05_IMPLEMENTATION_ROADMAP.md")

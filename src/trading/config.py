"""Settings loaded from environment variables (see .env.example)."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class RiskLimits:
    """Hard limits enforced by trading.risk on every order.

    All values are fractions of account equity.
    """

    max_position_pct: float = 0.20  # max value of a single position
    max_deployed_pct: float = 0.80  # max total capital in open positions
    max_daily_loss_pct: float = 0.02  # halt trading for the day past this loss


@dataclass(frozen=True)
class Settings:
    trading_mode: str = "backtest"  # backtest | paper | live
    database_url: str = "sqlite:///trading.db"
    risk: RiskLimits = RiskLimits()
    kite_api_key: str = ""
    kite_api_secret: str = ""
    kite_access_token: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    @classmethod
    def from_env(cls) -> "Settings":
        env = os.environ
        return cls(
            trading_mode=env.get("TRADING_MODE", "backtest"),
            database_url=env.get("DATABASE_URL", "sqlite:///trading.db"),
            risk=RiskLimits(
                max_position_pct=float(env.get("MAX_POSITION_PCT", "0.20")),
                max_deployed_pct=float(env.get("MAX_DEPLOYED_PCT", "0.80")),
                max_daily_loss_pct=float(env.get("MAX_DAILY_LOSS_PCT", "0.02")),
            ),
            kite_api_key=env.get("KITE_API_KEY", ""),
            kite_api_secret=env.get("KITE_API_SECRET", ""),
            kite_access_token=env.get("KITE_ACCESS_TOKEN", ""),
            telegram_bot_token=env.get("TELEGRAM_BOT_TOKEN", ""),
            telegram_chat_id=env.get("TELEGRAM_CHAT_ID", ""),
        )

"""Personal automated trading system.

Module layout mirrors architecture/03_ARCHITECTURE.md:

- data       — historical + live market data sources
- strategy   — signal generation
- risk       — pre-order risk checks (position/loss/capital limits)
- execution  — order executors (simulated for backtest/paper, real for live)
- portfolio  — position, cash, and PnL state
- brokers    — broker adapters (Zerodha now; Alpaca later)
- backtest   — bar-by-bar backtest engine and performance metrics
- db         — SQLAlchemy persistence
"""

__version__ = "0.1.0"

# Learnings from Stage 1 Build

Validated architectural and operational decisions from the initial backtesting skeleton implementation.

## Risk Engine Independence (Non-Negotiable)

Every order passes through the risk engine *before* execution. The risk engine runs independently of strategy code and cannot be bypassed.

**Why this matters**: The risk engine is the highest-leverage safety mechanism. A backtest can be wrong, a strategy can have a bug, but the risk engine is the failsafe that catches both before they hit real capital. This is the most-tested module and least-frequently changed.

**How it works**: RiskEngine.check() is called *after* strategy signal but *before* executor.execute(). Position sizing is handled by risk, not by the strategy — the strategy emits intent (LONG/FLAT), risk maps that to actual order size given position limits, deployed capital limits, and daily loss halts.

**Tests verify**: Position size limits, deployed capital limits, daily loss halt (sticky within a day, resets on start_of_day), kill switch, sell quantity validation.

---

## Module Boundaries Are Drawn for Future Service Extraction

Abstract interfaces (MarketDataSource, Strategy, OrderExecutor, BrokerAdapter, Portfolio) are intentionally designed so each can become a microservice later without rewriting strategy/risk code.

**Why this matters**: This isn't over-engineering for a solo project — it's intentional staging. When distributed system pain (resource contention, independent deploys) arrives, the code is already structured for extraction.

**How it works**: Every major module has a base class or ABC. MarketDataSource.get_historical() is abstract, not "always Yahoo." BrokerAdapter.place_order() is abstract, not "always Zerodha." Strategy interface is fixed (on_bar → Signal), but implementations can differ.

**Payoff**: Switching between backtest/paper/live mode is a config change (inject different executor), not a code change. Adding Alpaca for US equities later is a new adapter behind the same interface, not a rewrite.

---

## Cost Model: Deliberately Pessimistic, Not Premature Conservatism

The simulated executor uses a deliberately pessimistic cost model (0.15% fees + 0.1% slippage). This overshoots real Zerodha costs.

**Why this matters**: Backtests are inherently optimistic (perfect fills, no network failures). A strategy that barely breaks even after real commissions/slippage is a painful real-world surprise. Pessimistic backtesting ensures real results beat expectations.

**How it works**: 
- Base slippage: 0.1% (entry/exit cost of moving price)
- Fees: 0.15% (brokerage + STT + exchange fees)
- Combined: ~0.25% per round trip
- Applied as: fill_price adjusted for slippage, costs deducted from trade value

**Expectation when live**: Real results should beat backtest numbers (because real Zerodha costs are lower than modeled). If live results drop below backtest, investigate latency/fill quality issues, not the cost model.

---

## CSV Caching Is Sufficient; Avoid Premature Complexity

Simple filename-based caching (symbol_start_end.csv in data/cache/) is enough for backtesting. No Redis, Memcached, or in-memory cache layer.

**Why this matters**: Backtests are I/O-bound on the network (yfinance fetch time), not on disk reads. CSV is simple to inspect, debug, and cache-bust.

**How it works**: 
- First backtest of RELIANCE.NS for a date range downloads from Yahoo and saves to data/cache/RELIANCE.NS_2023-01-01_2024-12-31.csv
- Second backtest of the same range reads from disk (~milliseconds)
- No staleness issues because filename includes date range; different ranges get different files

**When to revisit**: If paper/live trading needs streaming ticks, that's handled by broker's real-time API (Zerodha Kite WebSocket), not cached historical data. Don't conflate the two layers.

---

## Hand-Rolled Metrics Teach the Mechanics

Metrics (Sharpe, max drawdown, win rate, total return) are written from scratch, not imported from backtesting.py or vectorbt.

**Why this matters**: Understanding what these metrics mean, where they break down, and what they don't capture is part of learning a trading system. A library function hides that.

**How it works**:
- total_return = (final_equity - initial_equity) / initial_equity
- max_drawdown = max peak-to-trough decline during the period
- sharpe_ratio = (return - risk_free_rate) / std_dev, annualized
- win_rate = (number of profitable round-trip trades) / (total round trips)

**Payoff**: Full control — you can later add metrics libraries don't have (Calmar ratio, recovery factor, underwater plot, Sortino). The code is also simple enough to audit before trusting it with real capital.

**When to reconsider**: After Stage 2 (paper trading), if a metrics library genuinely adds value beyond hand-rolled, revisit.

---

## Summary: Stage 1 Validated

These decisions were tested end-to-end: 27 pytest tests, real backtests against RELIANCE.NS (2023-2024), Docker Compose verification. They're not premature optimization or over-engineering — they're load-bearing patterns that will shape Stage 2 (paper trading) and Stage 3 (live trading) without major rewrite.

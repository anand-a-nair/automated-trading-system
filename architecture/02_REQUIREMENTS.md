# Requirements

Grouped by the stage they matter for (see [01_VISION.md](01_VISION.md) for stage definitions), so it's clear what's needed *now* vs. what to defer. Items marked **(later)** are real, specified requirements for the US/forex/distributed-system expansion — deferred, not dropped. Full detail on each is in [07_SCALING_ROADMAP.md](07_SCALING_ROADMAP.md).

## Stage 1 — Backtesting

- **R1.1**: Pull historical NSE daily/intraday OHLCV data (via `yfinance`, Zerodha's historical API, or downloaded NSE bhavcopy data) and cache it locally.
- **R1.2**: Define a strategy as plain Python (entry/exit rules, indicators) — no need for a DSL, config UI, or strategy marketplace.
- **R1.3**: Run a backtest that accounts for brokerage/STT/slippage, and produces: trade log, equity curve, return, max drawdown, win rate, Sharpe ratio.
- **R1.4**: Store backtest results (so you can compare strategy versions over time) — a local SQLite table is enough.

## Stage 2 — Paper Trading

- **R2.1**: Consume live NSE market data (Zerodha Kite Connect WebSocket, or free delayed data if avoiding the Kite subscription cost initially).
- **R2.2**: Simulate order fills against live prices (respecting bid/ask spread and basic slippage assumptions) without placing real broker orders.
- **R2.3**: Track a virtual portfolio (cash, positions, PnL) exactly as you would a real one.
- **R2.4**: Detect NSE market hours/holidays so the strategy only acts when the market is actually open.
- **R2.5**: Run continuously and survive a restart (positions/state persisted, not held only in memory).

## Stage 3 — Live Trading (small capital)

- **R3.1**: Place real orders (market/limit) via a broker API (Zerodha Kite Connect), with order status tracking (placed/filled/rejected/cancelled).
- **R3.2**: Hard-coded, enforced-in-code risk limits: max position size, max daily loss (auto-halt), max capital deployed at once.
- **R3.3**: Reconcile system-tracked positions against the broker's actual positions at least once a day (catch drift early).
- **R3.4**: Log every order and every risk-limit decision (why an order was placed, sized, or rejected) to a durable, append-only log — this is your audit trail and your debugging tool.
- **R3.5**: A manual kill switch — one command/button that immediately stops the strategy from placing new orders.
- **R3.6**: Basic alerting (at minimum: a Telegram/email message) on: order rejected, daily loss limit hit, system crashed/unreachable.

## Stage 4 — Always-on Deployment

- **R4.1**: Runs via Docker Compose identically on your laptop and on a cloud VM (no environment-specific code paths).
- **R4.2**: Secrets (API keys) come from environment variables / a `.env` file that's git-ignored, never committed.
- **R4.3**: Process supervision so a crash restarts the service automatically (Docker's `restart: unless-stopped` is enough — no need for Kubernetes).
- **R4.4**: Database backed up on a schedule (a daily `pg_dump`/SQLite file copy to cloud storage is enough).

## Deferred — US Equities **(later)** — see [07_SCALING_ROADMAP.md](07_SCALING_ROADMAP.md) Part 2

- Second broker adapter (Alpaca recommended — free paper trading built into their API, no $10K minimum, simple REST/WebSocket, much lower complexity than Interactive Brokers for a learning project).
- Timezone-aware scheduling so NSE and US strategies run independently without interfering.
- Currency-neutral portfolio reporting (positions in two currencies).
- RBI LRS remittance and Indian tax-reporting considerations for funding/holding a US account (not a system requirement, but a real prerequisite before going live — see [07_SCALING_ROADMAP.md](07_SCALING_ROADMAP.md)).

## Deferred — Forex **(later, lowest priority)** — see [07_SCALING_ROADMAP.md](07_SCALING_ROADMAP.md) Part 3

- **Not** an offshore global-forex broker integration — see the regulatory note in [07_SCALING_ROADMAP.md](07_SCALING_ROADMAP.md) on why that's not a legal retail channel for an Indian resident.
- Extend the existing `ZerodhaAdapter` to support NSE/BSE currency derivatives (INR-pair futures: USD/INR, EUR/INR, GBP/INR, JPY/INR) instead.
- Contract-expiry/rollover handling in the strategy and order-execution modules (futures, unlike equity cash trades, expire).
- Leverage-aware position sizing distinct from the equity risk-sizing formula.

## Deferred — Distributed System **(later, triggered by actual scale pain)** — see [07_SCALING_ROADMAP.md](07_SCALING_ROADMAP.md) Part 1

- Message bus (RabbitMQ or Redis Streams to start, not Kafka) once multiple strategy/market processes need to share data or be deployed independently.
- Market Data extracted as its own service first (most naturally shared across strategies/markets), then Order Execution per broker, then Kubernetes only once 5+ independent services make manual Docker Compose coordination genuinely painful.
- A centralized Risk Service that stays centralized even after everything else is distributed — the one gate every order from every strategy/market must clear.

## Not required, even at scale

- Multi-user auth, RBAC, OAuth2 — single user, so a basic API key or even no auth on a localhost-only dashboard is fine, distributed or not.
- Sub-100ms latency, tick-level HFT infrastructure — not the game this system is playing in any market.
- Kafka specifically (RabbitMQ/Redis Streams cover this project's actual throughput needs — see [07_SCALING_ROADMAP.md](07_SCALING_ROADMAP.md)), service mesh, multi-region HA.
- Equity options/derivatives, portfolio marketplace, ML-generated strategies.

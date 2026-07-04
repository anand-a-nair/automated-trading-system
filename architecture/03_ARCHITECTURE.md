# System Architecture

## Design principle: monolith first

This is one person, one broker account, a handful of strategies. A microservices architecture (separate Strategy/Order/Portfolio/Risk services talking over a message queue) would mean spending most of your time on plumbing instead of trading logic or learning.

Build **one Python application** with clear internal modules. Split it into separate processes/containers only when you actually feel pain from not doing so (e.g., the backtester hogging CPU while live trading needs to stay responsive) — not preemptively.

```
┌─────────────────────────────────────────────┐
│              Dashboard (simple)              │
│     Read-only view: positions, PnL, logs     │
│         (FastAPI + a couple HTML pages,      │
│          or a Streamlit app — see below)     │
└───────────────────┬───────────────────────────┘
                    │ reads
┌───────────────────▼───────────────────────────┐
│              Trading Application                │
│  (single Python process, internal modules)       │
│                                                  │
│  ┌────────────┐  ┌───────────────┐  ┌─────────┐│
│  │  Strategy  │→ │  Risk Checks  │→ │  Order  ││
│  │  (signals) │  │ (position/loss│  │ Execution││
│  │            │  │    limits)    │  │ (or sim) ││
│  └─────┬──────┘  └───────────────┘  └────┬─────┘│
│        │                                  │      │
│  ┌─────▼──────────┐              ┌───────▼─────┐│
│  │  Market Data    │              │  Portfolio   ││
│  │  (live feed or  │              │  State       ││
│  │  historical)    │              │  (positions, ││
│  └─────────────────┘              │   cash, PnL) ││
└───────────────────┬────────────────┴─────┬────────┘
                    │                        │
          ┌─────────▼─────────┐   ┌─────────▼────────┐
          │   Broker Adapter   │   │  SQLite/Postgres │
          │  (Zerodha Kite;    │   │  (orders, trades,│
          │  Alpaca later)     │   │   positions, logs)│
          └─────────┬──────────┘   └───────────────────┘
                    │
             ┌──────▼──────┐
             │ Zerodha Kite │
             │   Connect    │
             └──────────────┘
```

## Modules (inside the single application)

### Market Data
- Fetches historical data for backtesting; subscribes to live ticks for paper/live trading.
- One interface (`get_historical()`, `subscribe_live()`) with a Zerodha-backed implementation now, an Alpaca-backed one later — same interface, so strategies don't care which broker/market they're running against.

### Strategy
- Plain Python: given price data (and any indicators you compute), emits buy/sell/hold signals.
- No need for a "strategy engine" abstraction beyond a simple base class — you're writing a handful of strategies, not building a platform for others to write them.

### Risk Checks
- A single, boring, well-tested module that every order passes through before execution: position size limit, daily loss limit, max capital deployed.
- This is the module you should have the most unit tests for and the least cleverness in.

### Order Execution
- Two implementations behind one interface: a **simulated** executor (paper trading — fills against live/last price with a slippage assumption) and a **real** executor (places actual orders via the broker adapter).
- Switching between paper and live is a config flag, not a code fork — this is what makes paper trading actually validate your live path.

### Portfolio State
- Single source of truth for what the system *thinks* it holds: cash, positions, realized/unrealized PnL.
- Persisted to the database after every change — never held only in memory, so a crash/restart doesn't lose track of state.
- Reconciled against the broker's actual reported positions periodically (daily at minimum) when live.

### Broker Adapter
- Thin wrapper around Zerodha Kite Connect (place order, get positions, get quotes, get historical data).
- Deliberately kept separate from everything else so adding Alpaca later means writing one new adapter file, not touching strategy/risk/portfolio code.

## Repository layout

The package structure mirrors the modules above one-to-one, so the docs and the code stay navigable together:

```
src/trading/
  models.py        # shared domain types: Order, Fill, Position, Bar, Signal (no deps)
  config.py        # Settings + RiskLimits from environment (.env)
  data/            # MarketDataSource interface; yahoo.py (Stage 1), kite live feed (Stage 2)
  strategy/        # Strategy interface + concrete strategies (sma_crossover.py as the example)
  risk/            # RiskEngine — every order passes through here; most-tested module
  execution/       # OrderExecutor interface; simulated.py now, real broker executor in Stage 3
  portfolio/       # Portfolio state: cash, positions, realized/unrealized PnL
  brokers/         # BrokerAdapter interface; zerodha.py (stub until Stage 2/3)
  backtest/        # engine.py (bar-by-bar loop) + metrics.py (hand-rolled Sharpe/drawdown/etc.)
  db/              # SQLAlchemy models: orders + trades tables (append-only audit trail)
  __main__.py      # CLI: python -m trading backtest --symbol RELIANCE.NS
tests/             # concentrated on risk, portfolio, metrics, and end-to-end backtest
```

A key property the tests enforce implicitly: the backtest engine composes the *same* strategy/risk/execution/portfolio modules the paper and live paths will use — only the data source and executor implementations differ per mode.

## Data layer

- **Local development**: SQLite. Zero setup, a single file, perfectly adequate for one account's worth of orders/trades/positions and years of daily OHLCV data.
- **Cloud/live**: Postgres, once SQLite's single-writer limitation actually becomes a problem (it likely won't for a solo system, but Postgres is a one-line Docker Compose change away if needed).
- **No separate time-series database.** InfluxDB/TimescaleDB solve a scale problem (millions of ticks/sec across many instruments) you don't have. Daily/minute OHLCV bars for a watchlist of a few dozen symbols fit fine in a normal SQL table.
- **No message queue.** Python's own async/await, or even just a simple loop with a scheduler, is enough for one strategy pipeline. Add a queue only if you're running enough independent strategies that ordering/backpressure becomes a real problem.

## Deployment architecture

### Local (today)
```
docker compose up
  ├─ app        (the trading application)
  ├─ db         (Postgres, or skip this and use SQLite in a volume)
  └─ dashboard  (if run as a separate container; often just part of `app`)
```
Everything on your laptop. Kite Connect credentials in a git-ignored `.env` file. Market data flows in over the internet like it will in the cloud, so behavior should be nearly identical to production.

### Cloud (later, once live trading is stable)
- **One small VM** (see [TECHNOLOGY_STACK.md](04_TECHNOLOGY_STACK.md) for provider suggestions) running the same `docker compose` setup.
- No load balancer, no auto-scaling, no multi-region — a single instance with `restart: unless-stopped` and a daily backup cron job is the entire "production" story for a personal system.
- Dashboard exposed only over a VPN/SSH tunnel or behind basic auth — it doesn't need to be public.

## Evolution path (what changes when you add US equities, forex, or distribution later)

1. Add an `AlpacaAdapter` implementing the same broker-adapter interface as `ZerodhaAdapter` for US equities; extend `ZerodhaAdapter` itself to cover NSE/BSE currency derivatives for forex (see [07_SCALING_ROADMAP.md](07_SCALING_ROADMAP.md) for why forex is a Zerodha extension, not a new broker).
2. Add a scheduler that knows NSE hours (IST) and US market hours (ET) independently — two independent trading loops, not one that tries to be timezone-clever.
3. Portfolio state gains a currency dimension (or you simply run two separate portfolios/databases — often simpler than unifying).
4. If/when scale genuinely demands it, the modules below ("Market Data", "Order Execution", "Risk Checks", "Portfolio State") become the service boundaries of a distributed system — that's why they're already split as distinct modules with clear interfaces rather than one undifferentiated blob of code. Full extraction order and trigger conditions are in [07_SCALING_ROADMAP.md](07_SCALING_ROADMAP.md) Part 1.
5. Everything else (strategy interface, risk-checks logic itself, order-execution abstraction) is designed to not need to change shape, whether running as one process or several.

This is why the broker adapter and market-data interfaces matter even though only one broker is implemented today — they're the seam where multi-market support and, later, distribution get added without a rewrite.

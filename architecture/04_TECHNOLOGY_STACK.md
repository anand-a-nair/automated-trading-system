# Technology Stack

Optimized for: one developer, fast iteration, cheap to run, easy to reason about when something breaks at 9:16am IST.

## Backend

- **Python 3.11+** — the ecosystem for backtesting, data analysis, and broker SDKs is unmatched, and you already know it.
- **FastAPI** — for the dashboard's read-only API and for any webhook/alert endpoints. Not running multiple "services" — one FastAPI app is the whole backend.
- Plain `asyncio` for the live trading loop (poll/subscribe to prices, evaluate strategy, act). No Celery, no task queue — a single scheduled loop is enough at this scale.

## Strategy & Backtesting

- **`backtesting.py`** or **`vectorbt`** for fast, simple backtests — lighter weight than Zipline/Backtrader, less setup overhead, good fit for a learning project. (Backtrader is fine too if you prefer its event-driven model; either is a reasonable choice, don't agonize over it.)
- **`pandas` + `pandas-ta`** for indicators (moving averages, RSI, etc.) — skip `ta-lib` unless you hit a specific performance wall; it requires a C library install that adds friction for little benefit at this scale.
- **`numpy`** for the math; **`empyrical`** or hand-rolled functions for Sharpe/Sortino/max-drawdown (these are a few lines each — worth understanding rather than treating as a black box, given the learning goal).

## Market Data

- **Historical (backtesting)**: `yfinance` for a quick start (free, decent NSE coverage via `.NS` tickers), or Zerodha's historical data API once you have Kite Connect access (more accurate, includes volume/intraday).
- **Live (paper/live trading)**: Zerodha Kite Connect WebSocket (`kiteconnect` Python SDK) for real-time ticks. This requires the paid Kite Connect subscription (~₹2000/month) — see [KEY_CONSIDERATIONS.md](06_KEY_CONSIDERATIONS.md) for how to sequence this so you're not paying before you need to.
- **Timezones**: Python's built-in `zoneinfo` (`Asia/Kolkata`). No need for `pytz` on modern Python.

## Broker Integration

- **Zerodha Kite Connect** (`kiteconnect` official Python SDK) — order placement, positions, live quotes. This is the only broker integration for now.
- **(Later) Alpaca** (`alpaca-py` SDK) — when you add US equities. Chosen over Interactive Brokers specifically because it has free built-in paper trading, no account minimum, and a much simpler REST API — a better fit for a learning-first project than IBKR's more powerful but heavier TWS/gateway setup.

## Data Storage

- **SQLite** for local development — zero-config, one file, trivially backed up (just copy the file).
- **Postgres** (via Docker Compose) once deployed to the cloud, or immediately if you'd rather not deal with a SQLite→Postgres migration later. Either is fine; don't overthink this choice.
- **`SQLAlchemy`** as the ORM either way, so the SQLite→Postgres switch is a connection-string change, not a rewrite.
- No InfluxDB/TimescaleDB, no Redis, no message queue — see [ARCHITECTURE.md](03_ARCHITECTURE.md) for why these solve problems you don't have yet.

## Dashboard / Frontend

- **Streamlit** is worth seriously considering over React for this: a Python-only dashboard (tables, charts, a "kill switch" button) that you can build in an afternoon, with no separate frontend build step, no TypeScript, no API layer to maintain in lockstep with the UI.
- If you want a "real" web app for the learning experience (or plan to make it prettier later), a small **React + TypeScript + Vite** app talking to the FastAPI backend is fine — just don't let frontend polish compete for time with getting the trading logic right early on.
- Either way: a handful of read-only views (current positions, today's PnL, recent orders/logs, a strategy on/off toggle) is the entire UI surface needed. No user accounts, no multi-page app.

## Alerting

- **Telegram bot** (via `python-telegram-bot`) is the easiest zero-cost alert channel — a bot token and your chat ID, a few lines to send a message. Simpler to set up than email/SMS for a solo project.
- Email as a fallback/addition if you prefer (`smtplib` + a free-tier SMTP provider).

## Local Development

- **Docker Compose** — `app` (+ `db` if using Postgres locally). This is also exactly what runs in the cloud later, so "works on my machine" and "works in production" are the same thing by construction.
- **`uv`** or **Poetry** for dependency management — either is fine; `uv` is faster if you're starting fresh.
- **`pytest`** for tests — focus test effort on the risk-checks module and PnL/position calculations, since silent bugs there are the ones that cost real money.
- **`.env`** file (git-ignored) for Kite Connect API key/secret and any alert bot tokens. Never commit these — see the repo's `.gitignore`.

## Deployment (cloud, later)

- **A single small VM**: DigitalOcean Droplet, Hetzner Cloud, or AWS Lightsail — all in the $4-6/month range for a box that just needs to run a Python process during NSE market hours. No Kubernetes, no managed database service needed at this scale (Postgres in the same Docker Compose stack is fine).
- Deploy by `git pull` + `docker compose up -d` on the VM, or a simple GitHub Actions workflow that SSHes in and does the same — no need for a full CI/CD pipeline with staged rollouts.
- Daily backup: a cron job that copies the SQLite file (or runs `pg_dump`) to a cheap object storage bucket (Backblaze B2, S3). A few lines of shell, not infrastructure-as-code.

## Not using yet (deferred to specific triggers, not ruled out)

See [07_SCALING_ROADMAP.md](07_SCALING_ROADMAP.md) for exactly what triggers each of these and the order to introduce them in:

- **RabbitMQ or Redis Streams** — once multiple strategy/market processes need to share live data or be deployed independently of each other. (Kafka specifically stays off the list even at that point — its operational overhead isn't justified at this project's throughput.)
- **TimescaleDB** (a Postgres extension, not a separate InfluxDB) — once tick/bar storage across NSE + US + forex genuinely outgrows plain Postgres tables.
- **Redis** (as a cache, not a queue) — once multiple services need fast shared access to the same hot state (live prices, positions) rather than each hitting Postgres.
- **Kubernetes, Helm, Terraform** — only once running 5+ independent services makes manually coordinating Docker Compose across machines genuinely painful; unlikely to be needed even at full NSE+US+forex scope for a solo system.
- **Prometheus/Grafana/ELK** — a log file plus Telegram alerts covers this system through distribution; revisit only if you want historical trend queries a log file genuinely can't answer.
- **Interactive Brokers** — Alpaca is the better first (and likely only-needed) US broker for this project's goals; IBKR can be reconsidered later only if you outgrow Alpaca's feature set.
- **A separate offshore forex broker** — not planned at all; forex means NSE/BSE currency derivatives via the existing Zerodha adapter (see [07_SCALING_ROADMAP.md](07_SCALING_ROADMAP.md) for the regulatory reason).

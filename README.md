# Automated Trading System

A personal automated trading system for NSE equities (Indian markets), built to learn both trading itself and the engineering behind a trading system — and to actually trade with, not just as an exercise.

US equities, forex, and an eventual distributed-system architecture are all real, specified scope — see [architecture/07_SCALING_ROADMAP.md](architecture/07_SCALING_ROADMAP.md) — but deliberately sequenced *after* the NSE version is backtested, paper-traded, live with small capital, and running unattended. Nothing is dropped, just ordered.

## Status

**Stage 1 (backtesting) — skeleton working end-to-end.** The core modules (portfolio, risk checks, simulated execution, backtest engine + metrics) are implemented and tested; the broker adapter and live-data pieces are interfaces/stubs until Stage 2. A real backtest runs today:

```
$ python -m src.trading backtest --symbol RELIANCE.NS --start 2023-01-01 --end 2024-12-31
sma_20_50 on RELIANCE.NS: return +5.79%, max drawdown 1.97%, sharpe 1.01, win rate 50% over 4 round trips
```

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest                                              # 27 tests, no network needed
python -m src.trading backtest --symbol INFY.NS    # real backtest (fetches + caches Yahoo data)
```

Or with Docker: `cp .env.example .env`, then `docker compose up --build`.

## Layout

```
architecture/    design docs, numbered in reading order — start at architecture/README.md
src/trading/     the application (modules mirror architecture/03_ARCHITECTURE.md)
tests/           pytest suite, concentrated on the money-critical modules (risk, portfolio)
```

## Start here

Full design docs live in [architecture/](architecture/) — start with [architecture/README.md](architecture/README.md), which links to everything in reading order (vision → requirements → architecture → tech stack → roadmap → key considerations → scaling roadmap).

## Approach, in one paragraph

One Python application today, not a microservices platform — SQLite locally, Postgres if the cloud deployment wants it, Docker Compose everywhere (laptop today, a $5/month VPS later). No Kubernetes, no Kafka, no time-series database, no multi-tenant auth *yet* — none of that is needed for one person trading one broker account, but the module boundaries (market data, strategy, risk, order execution) are deliberately drawn so each can become a service later without a rewrite. Sequence: **backtest a strategy → paper-trade it against live data → run it live with small real capital → move it to an always-on VPS → (later) US equities via Alpaca, forex via NSE currency derivatives, and a distributed architecture if actual scale ever demands it.**

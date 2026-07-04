# Vision & Scope

## What this is

A personal automated trading system, built incrementally, that serves two goals at once:

1. **Learning** — understand trading mechanics (order types, backtesting, risk sizing, execution) and the engineering of a trading system (broker APIs, data pipelines, state reconciliation) by building it yourself rather than reading about it.
2. **Actually using it** — get to a point where a real strategy runs against real (small) capital in NSE, with a credible path to extend to US equities and forex later.

This is a **solo project**, not an institutional platform. Every decision in these docs is filtered through that lens: build the smallest thing that teaches you something and gets you closer to live trading, not the thing a 10-person trading firm would build.

## Order of attack

**NSE equities first.** You already have context here (timezone, likely broker account, market hours during your day). US equities and forex are deferred, not dropped — the architecture leaves room for both (a broker-adapter interface, not a hardcoded NSE-only design; see [07_SCALING_ROADMAP.md](07_SCALING_ROADMAP.md) for the full spec of each), but no code gets written for them until NSE is working end-to-end: backtest → paper trade → small live capital.

"Forex" for this system means **NSE/BSE currency derivatives (INR pairs)** through the same Zerodha adapter, not an offshore global-forex broker — see [07_SCALING_ROADMAP.md](07_SCALING_ROADMAP.md) for why: retail spot forex in non-INR pairs through overseas brokers isn't a legal channel for an Indian resident under FEMA. That correction aside, it's still lowest priority — a different instrument type (futures with expiries, leverage-aware sizing) that adds complexity without adding much learning value beyond what equities already teach.

## What "done" looks like at each stage

1. **Backtest stage**: a strategy you wrote runs against historical NSE data and produces a trade log + performance stats (return, drawdown, win rate) you trust.
2. **Paper stage**: the same strategy runs against live market data, simulates fills internally, and its virtual portfolio tracks what would have happened — running locally, unattended, for at least a couple of weeks.
3. **Live stage**: the same strategy places real orders through a broker API with a small amount of real capital, with hard position/loss limits enforced in code (not just intended).
4. **Always-on stage**: the live system runs on a small cloud VM instead of your laptop, so it isn't tied to your machine being on.

Only after (3) and (4) feel boring and reliable does it make sense to look at a second market.

## Deferred, not excluded

The items below are genuinely planned, just sequenced later — the architecture is deliberately drawn (see [03_ARCHITECTURE.md](03_ARCHITECTURE.md)'s broker-adapter and market-data interfaces) so none of them require a rewrite when their time comes. Full detail on each is in [07_SCALING_ROADMAP.md](07_SCALING_ROADMAP.md).

- **Distributed system** — splitting the monolith into independent services (market data, strategy runners, a centralized risk service, order execution per broker) behind a message bus, once running enough concurrent strategies/markets makes a single process a real bottleneck.
- **US equities** — via Alpaca, once NSE is stable; Alpaca's own paper trading covers that market's Stage 2 for free.
- **Kubernetes, message-queue clusters, a time-series database, horizontal auto-scaling** — introduced only when a specific pain point (listed in [07_SCALING_ROADMAP.md](07_SCALING_ROADMAP.md)) actually shows up, not preemptively.

## Non-goals (actually out of scope, not just deferred)

- Multi-user / multi-tenant support — this is for one person (you), even after the system is eventually distributed.
- High-frequency trading or sub-100ms latency guarantees — NSE retail execution over a home/cloud connection is realistically 200ms-1s; strategies should be chosen accordingly (not scalping/HFT), regardless of how distributed the system eventually gets.
- Equity options/derivatives — pure equity cash trades, plus currency *futures* for the forex piece (see above), but not equity options.
- A polished multi-page web app from day one — a simple dashboard is enough; invest in UI only once the trading logic is trustworthy.

## Success criteria (realistic, for a solo project)

1. You can explain, in your own words, why a strategy made or lost money on a given day, using the system's own logs.
2. A strategy has been backtested, then paper-traded, with results in the same ballpark (no wild after-the-fact surprises).
3. The system has traded real (small) capital for at least a month without a bug causing an unintended order or a blown risk limit.
4. You can restart the whole system from a clean checkout (`docker compose up`) and get back to a working state without hand-editing anything.
5. It runs unattended on a cheap VPS during market hours without you babysitting it.

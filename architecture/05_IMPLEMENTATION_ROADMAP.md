# Implementation Roadmap

Structured around the four stages from [VISION.md](01_VISION.md): Backtest → Paper → Live (small capital) → Always-on. No fixed sprint calendar — go at whatever pace fits around your schedule, but keep the ordering: each stage should feel solid before starting the next.

## Stage 1 — Backtesting (learn the mechanics)

**Goal**: Trust a strategy's historical performance numbers before risking anything.

- [x] Project skeleton: Python project (`pyproject.toml`), Docker Compose with a single `app` container, SQLite.
- [x] Pull historical NSE data via `yfinance` (with local caching) — `trading.data.yahoo`.
- [x] Implement one simple strategy from scratch — SMA crossover (`trading.strategy.sma_crossover`), simple enough to verify by hand.
- [x] Backtest engine that accounts for brokerage + STT + slippage (`CostModel` in `trading.execution.simulated`, deliberately pessimistic defaults).
- [x] Output: equity curve, trade log, Sharpe ratio, max drawdown, win rate (`trading.backtest.metrics`, hand-rolled per the learning goal).
- [ ] Run against a real watchlist (5-10 liquid large-caps) across different market regimes (trending, sideways, a crash period like early 2020) — and read the results critically.
- [ ] Iterate on the strategy a few times; persist backtest results (a `results` table using `trading.db`) so versions can be compared over time.

**You're done with this stage when**: you have a strategy whose backtest results you understand well enough to explain *why* it made money (or didn't) on specific days, not just what the aggregate numbers say.

## Stage 2 — Paper Trading (validate against reality)

**Goal**: See if the strategy's live behavior matches what the backtest predicted, with zero financial risk.

- [ ] Sign up for Zerodha Kite Connect (₹2000/month) — or delay this and use free delayed/EOD data if you want to paper-trade on a slower cadence first (see [KEY_CONSIDERATIONS.md](06_KEY_CONSIDERATIONS.md) for the cost-sequencing tradeoff).
- [ ] Build the live market-data subscriber (Kite WebSocket ticks).
- [ ] Build the simulated order executor: given a signal, "fill" it against the current price with a slippage assumption, update a virtual portfolio.
- [ ] Persist portfolio state (positions, cash, PnL) to SQLite after every change — so restarting the app doesn't lose your paper-trading history.
- [ ] Add NSE market-hours/holiday awareness so the strategy doesn't try to act when the market's closed.
- [ ] Let it run, untouched, for at least 2-3 weeks during market hours.
- [ ] Compare paper-trading results to what the backtest predicted for the same period. Big divergence → figure out why (data quality issue? backtest slippage assumption was unrealistic? look-ahead bias in the strategy?) before moving on.

**You're done with this stage when**: paper results are in the same ballpark as backtest results for the same period, and the system has run for multiple weeks without you needing to intervene or restart it manually more than a couple of times.

## Stage 3 — Live Trading, Small Capital (the real test)

**Goal**: Trade real money, small enough that mistakes are learning experiences, not disasters.

- [ ] Build the real order executor using Kite Connect's order placement API — behind the *same interface* as the paper executor, so switching is a config flag.
- [ ] Build the risk-checks module first, test it thoroughly, before wiring it to real orders: max position size (e.g., no more than 10-20% of capital in one name), max daily loss (e.g., auto-halt at -2% of capital for the day), max total capital deployed.
- [ ] Build the manual kill switch (a CLI command or dashboard button that flips a flag the trading loop checks before every action).
- [ ] Build daily reconciliation: compare system-tracked positions to Kite's actual reported positions each evening; alert on mismatch.
- [ ] Set up Telegram (or email) alerts for: order rejected, daily loss limit hit, reconciliation mismatch, unhandled exception/crash.
- [ ] Fund the account with an amount you're fully prepared to lose entirely (this is a real constraint worth setting explicitly for yourself, independent of the system) and go live.
- [ ] Watch it closely for the first week or two — don't walk away yet.

**You're done with this stage when**: it's traded real capital for a month without a bug causing an unintended order, a blown risk limit, or a state mismatch you didn't catch until reconciliation surprised you.

## Stage 4 — Always-on Deployment

**Goal**: Stop needing your laptop open and your terminal running during market hours.

- [ ] Confirm the whole thing runs identically via `docker compose up` on a fresh machine (a VM, or even just a clean clone on your laptop) — no hidden local-only assumptions.
- [ ] Provision a small VPS (DigitalOcean/Hetzner/Lightsail, ~$5/month).
- [ ] Move `.env` secrets to the VM (never commit them; use the VM's environment or a secrets file with tight file permissions).
- [ ] Set `restart: unless-stopped` on the containers so a crash self-heals.
- [ ] Set up a daily backup cron job (copy SQLite file / `pg_dump` to object storage).
- [ ] Run live trading from the VM for a couple of weeks in parallel with (or instead of) your laptop, confirming behavior matches.
- [ ] Decommission the laptop-as-trading-server workflow once you trust the VM.

**You're done with this stage when**: the system runs unattended on the VM through a full trading day, alerts you if something goes wrong, and you don't feel the need to check on it constantly.

---

## Command reference

Throughout: `python -m src.trading <command>` with the module structure under `src/`:

```bash
python -m src.trading backtest \
  --symbol RELIANCE.NS \
  --start 2023-01-01 \
  --end 2024-12-31 \
  --cash 100000 \
  --fast 20 --slow 50
```

Flags: `--cash` (starting equity, default 100k), `--fast` and `--slow` (SMA windows for the example strategy).

---

## Phase 5: US Equities (later, lowest priority until NSE feels boring)

Full spec in [07_SCALING_ROADMAP.md](07_SCALING_ROADMAP.md) Part 2. Only start once live NSE trading has been stable for a while and you're looking for the next thing to learn/build:

- [ ] Add an Alpaca adapter behind the same broker interface.
- [ ] Alpaca's own paper trading (built into their API) means you can skip straight to a paper-trading loop for US equities without building your own simulator again.
- [ ] Add a second, independent scheduling loop for US market hours (ET) — don't try to unify NSE and US scheduling into one clever timezone-aware loop; two simple loops are easier to reason about than one complicated one.
- [ ] Decide whether to run one strategy adapted to both markets, or genuinely different strategies per market — often the latter, since NSE and US market microstructure/liquidity differ.
- [ ] Before funding a live US account: understand RBI LRS remittance limits/TCS and the Schedule FA foreign-asset tax reporting requirement (see [07_SCALING_ROADMAP.md](07_SCALING_ROADMAP.md)) — a financial/legal prerequisite, not a coding task, but don't skip it.

## Phase 6: Forex (later, lowest priority — and a different shape than you might expect)

Full spec in [07_SCALING_ROADMAP.md](07_SCALING_ROADMAP.md) Part 3. The short version: this is **not** an offshore forex broker integration — retail spot forex in non-INR pairs through overseas brokers isn't a legal channel for an Indian resident under FEMA. It means extending the existing `ZerodhaAdapter` to trade NSE/BSE currency derivatives (INR-pair futures), which is simpler in some ways (same broker, same NSE hours) and different in others (contract expiry/rollover, leverage-aware sizing).

- [ ] Extend `ZerodhaAdapter` for the currency derivatives segment.
- [ ] Add expiry/rollover handling to strategy and order-execution logic.
- [ ] Add a leverage-aware variant of the position-sizing formula.

## Phase 7: Distributed System (triggered by actual scale pain, not a calendar date)

Full spec, trigger conditions, and extraction order in [07_SCALING_ROADMAP.md](07_SCALING_ROADMAP.md) Part 1. Don't start this because it seems like the "next logical step" after Phases 5-6 — start it only when you actually feel one of the documented pain points (resource contention between strategies, wanting independent deploys, data volume straining Postgres). In short: introduce a message bus (RabbitMQ/Redis Streams), extract Market Data first, then Order Execution per broker, keep Risk Service centralized always, and reach for Kubernetes only if you're managing 5+ independent services by hand.

---

## Risk mitigation (sized for a solo project, not an institution)

| Risk | Mitigation |
|------|-----------|
| Bug causes unintended/oversized order | Risk-checks module runs before every order, independent of strategy code; unit-tested heavily |
| Strategy overfit to backtest | Walk-forward / out-of-sample check before going live; paper-trade before risking capital |
| Broker API downtime mid-position | Reconciliation catches drift next check; kill switch available; start with small enough capital that a missed exit isn't catastrophic |
| You forget the system is running and it does something dumb while you're not watching | Telegram alerts on anything unusual; daily loss limit auto-halts regardless of whether you're watching |
| VPS goes down | `restart: unless-stopped`; daily backups mean at most a day's state is at risk, not the whole history |
| Losing more than you can afford | Fund the live account with an amount you've explicitly decided you can afford to lose entirely — a personal/financial decision the system's risk limits reinforce but don't replace |

## Testing priorities (where bugs actually cost money)

1. **Risk-checks module** — the highest-value tests you'll write. Position sizing, daily loss halt, capital limits.
2. **Portfolio/PnL calculations** — silent arithmetic bugs here are the hardest to notice and the most costly.
3. **Order state machine** — placed → filled/partially-filled/rejected/cancelled transitions, especially partial fills.
4. Everything else (strategy signal logic, data fetching) matters less for safety and more for "does it make money," which backtesting/paper-trading validates anyway.

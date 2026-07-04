# Scaling Roadmap: Distributed System, US Equities, Forex

This document exists so that "start with a monolith" doesn't quietly turn into "never support the rest." Everything here is real, planned future scope — not built now, but the current design (interfaces in [03_ARCHITECTURE.md](03_ARCHITECTURE.md)) is deliberately shaped so none of this requires a rewrite. Revisit this doc once the checklist at the end of each earlier stage is genuinely done, not before — premature distribution/multi-market work is the single easiest way to stall the project.

## Part 1 — Distributed System Evolution

### Trigger conditions (don't split before you hit one of these)
- Running enough concurrent strategies that they visibly contend for CPU/memory on one process.
- Wanting to add markets/instruments fast enough that a single market-data subscriber becomes a bottleneck or single point of failure for everything else.
- Wanting independent deploy/restart of, say, order execution without bouncing the strategy engine (e.g., you're actively iterating on strategies but don't want that to risk a live order-execution restart).
- Data volume (tick/bar storage across many instruments and markets) genuinely straining a single Postgres instance.

None of these are likely at "one account, NSE, a handful of strategies" scale. They become plausible once you're running NSE + US + forex concurrently with several strategies each.

### Target shape

The monolith's internal modules ([03_ARCHITECTURE.md](03_ARCHITECTURE.md)) map directly onto future services — this is why those module boundaries were chosen:

```
Market Data Service  →  independent process per market (NSE, US, Forex),
                        publishes ticks/bars to a message bus
Strategy Runner(s)   →  one process per strategy (or strategy group),
                        subscribes to relevant market data, emits signals
Risk Service         →  single, centralized (even when everything else is
                        distributed) — one place all orders must clear,
                        so a bug in one strategy process can't bypass it
Order Execution      →  one process per broker (Zerodha, Alpaca, forex
                        provider), consumes approved orders, places them
Portfolio Service     →  aggregates positions/PnL across all brokers/markets
                        into one place you actually look at
```

### Introduction order (extract one piece at a time, in this order)
1. **Message bus** — start with **Redis Streams or RabbitMQ**, not Kafka. Kafka's operational overhead (Zookeeper/KRaft, partition management) isn't justified until you have genuinely high-throughput, multi-consumer needs. RabbitMQ or even Redis pub/sub covers "a few strategy processes and a few market feeds" comfortably.
2. **Market Data Service** extracted first — it's the most naturally shared/reusable piece (multiple strategies want the same NSE ticks; no reason to fetch them redundantly per-strategy).
3. **Order Execution** extracted per-broker next, if isolation between markets' execution reliability matters (an Alpaca outage shouldn't affect NSE order placement).
4. **Risk Service** — keep this centralized even after everything else is distributed. It's the one place you want a single, auditable gate that every order from every market/strategy passes through. Distributing risk checks per-strategy defeats their purpose (catching cross-strategy over-exposure).
5. **Kubernetes** — only if you're now running enough independent services (5+) that `docker compose` across multiple machines/restarts genuinely gets painful to manage by hand. A handful of Docker Compose stacks on one or two VMs, coordinated manually, will comfortably outlast most solo projects' actual needs. Terraform becomes worth it around the same point (multiple VMs/environments to provision repeatably).

### Data layer at this scale
- **TimescaleDB** (a Postgres extension, not a separate database to operate) once bar/tick storage across NSE + US + forex genuinely outgrows plain Postgres tables — this preserves SQL/SQLAlchemy familiarity rather than introducing InfluxDB's separate query language.
- **Redis** for hot-path state (latest prices, current positions) once multiple services need fast shared access to the same live state rather than each hitting Postgres.

## Part 2 — US Equities (full spec, for when promoted from deferred to active)

### Functional requirements
- **US1.1**: `AlpacaAdapter` implementing the same broker-adapter interface as `ZerodhaAdapter` (place order, get positions, get quotes, get historical data).
- **US1.2**: Alpaca's built-in paper trading covers Stage 2 for this market — no need to rebuild a simulated executor from scratch the way NSE required.
- **US1.3**: Independent scheduler loop for US market hours (9:30am-4:00pm ET) — a second simple loop, not a unified timezone-clever one (see [03_ARCHITECTURE.md](03_ARCHITECTURE.md) evolution path).
- **US1.4**: Portfolio reporting either kept as two separate portfolios (NSE in INR, US in USD) or unified with explicit FX conversion for a combined view — the former is simpler and arguably more honest (mixing currencies into one number hides real exposure).

### Regulatory reality specific to trading US markets as an Indian resident
This is worth knowing before funding a US account, not after:
- Direct US equity trading by an Indian resident requires remitting funds abroad under **RBI's Liberalised Remittance Scheme (LRS)** — currently up to $250,000/year per person. This isn't a system design concern, but it's a real constraint on how you fund an Alpaca (or any US broker) account.
- **Tax Collected at Source (TCS)** applies on LRS remittances above a threshold (the exact threshold and rate have changed in recent years — check current rules before remitting, don't rely on this doc for the current number).
- Foreign holdings need to be reported in your Indian income tax return (**Schedule FA** — foreign assets), separate from the trade-level record-keeping the system itself produces.
- US-sourced capital gains have their own tax treatment (both US withholding considerations, depending on account type/broker, and Indian tax on the same gains, moderated by the India-US tax treaty) — worth a real conversation with a CA before this stage, not something to solve in code.

None of this blocks building the *system* — Alpaca's paper trading needs none of it. It matters at the point you'd fund a live US account.

## Part 3 — Forex (full spec, for when promoted from deferred to active)

**Read this before building anything forex-related — it changes what "Forex" should even mean for this system.**

### The regulatory constraint that matters most
Under India's **FEMA (Foreign Exchange Management Act)** rules, Indian residents generally **cannot legally trade spot forex in non-INR currency pairs (e.g., EUR/USD, GBP/JPY) through overseas retail forex/CFD brokers** — this is a genuinely common misconception, and a number of offshore forex brokers market to Indian residents anyway despite it being outside permitted channels. Doing so is a FEMA violation, not just a grey area, regardless of what an offshore broker's marketing implies.

What **is** legal and RBI-permitted for Indian retail residents: trading **currency derivatives (futures/options) on INR-pair contracts** — USD/INR, EUR/INR, GBP/INR, JPY/INR — on NSE's or BSE's currency derivatives segment, through a SEBI-registered broker. Zerodha Kite Connect already supports this segment.

**Practical implication for this project**: "Forex" should almost certainly mean **NSE/BSE currency derivatives (INR pairs)** via the same Zerodha Kite Connect adapter already being built for NSE equities — not a separate offshore forex broker integration. This is good news for the architecture (no new broker adapter needed, same `ZerodhaAdapter`, just a different instrument type) but means the original "EUR/USD, GBP/USD, USD/JPY" framing from earlier drafts of these docs was the wrong target for an Indian resident and has been corrected here.

If there's a specific reason to want genuine global spot forex exposure (not currency derivatives), that requires its own research into RBI-authorized routes — flag it explicitly and treat it as a separate decision, not an assumption baked into the system design.

### Functional requirements (revised to INR-pair currency derivatives via NSE/BSE)
- **FX1.1**: Extend the existing `ZerodhaAdapter` to support the currency derivatives segment (futures on USD/INR, EUR/INR, GBP/INR, JPY/INR) — not a new broker integration.
- **FX1.2**: Currency derivatives are futures contracts with expiries and lot sizes, unlike equity cash trades — the strategy and risk-checks modules need to account for contract expiry/rollover, which equity strategies don't.
- **FX1.3**: Leverage-aware position sizing — currency futures carry margin/leverage different from equity delivery trades; the risk-checks module's position-sizing formula (see [06_KEY_CONSIDERATIONS.md](06_KEY_CONSIDERATIONS.md)) needs a leverage-aware variant for this instrument type.
- **FX1.4**: 24-hour-ish awareness is *not* needed here (unlike global forex) — NSE currency derivatives trade during NSE hours (9:00am-5:00pm IST), similar in shape to equities, which is another reason this is the simpler and correct path for an Indian-resident system.

## Summary: what stays true across all of this

The reason [03_ARCHITECTURE.md](03_ARCHITECTURE.md) insists on a broker-adapter interface and a market-data interface *now*, even with only one broker implemented, is exactly so that this document's contents (a second broker, a distributed topology, a new instrument type) slot in without touching strategy/risk/portfolio code. If a future change to any of those three core modules turns out to be required in order to add US equities, forex, or distribution, that's a signal the original interface was drawn in the wrong place — worth stopping and reconsidering rather than patching around it.

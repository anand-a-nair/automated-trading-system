# Architecture & Design Docs

Read in this order (files are numbered accordingly):

1. **[01_VISION.md](01_VISION.md)** — what this is, why it's shaped as a solo learning-and-live-trading project, what "done" looks like at each stage, explicit non-goals.
2. **[02_REQUIREMENTS.md](02_REQUIREMENTS.md)** — requirements grouped by stage (backtest → paper → live → always-on), with US/forex explicitly marked as deferred.
3. **[03_ARCHITECTURE.md](03_ARCHITECTURE.md)** — monolith-first system design, modules, data layer, deployment shape, and the evolution path for adding a second market later.
4. **[04_TECHNOLOGY_STACK.md](04_TECHNOLOGY_STACK.md)** — specific tools and libraries, and what's deliberately *not* being used (Kubernetes, Kafka, InfluxDB, etc.) and why.
5. **[05_IMPLEMENTATION_ROADMAP.md](05_IMPLEMENTATION_ROADMAP.md)** — the actual build order, stage by stage (including later phases for US equities, forex, and distribution), with a completion checklist per stage.
6. **[06_KEY_CONSIDERATIONS.md](06_KEY_CONSIDERATIONS.md)** — practical specifics: Kite Connect cost sequencing, realistic latency expectations, retail tax/compliance notes, position sizing, reconciliation.
7. **[07_SCALING_ROADMAP.md](07_SCALING_ROADMAP.md)** — the full future-scope spec: how the monolith evolves into a distributed system (triggers, extraction order), the full US equities requirements (including RBI/LRS considerations), and the full forex requirements (including the FEMA regulatory constraint that shapes what "forex" actually means here).

## TL;DR

Solo project, two goals: learn trading + learn to build trading systems, and actually trade with it. NSE equities first (via Zerodha Kite Connect). US equities (Alpaca) and forex (NSE/BSE currency derivatives via Zerodha — not an offshore forex broker, see doc 7 for why) are deferred until NSE is boring and reliable, but fully specified now so they don't get built wrong or forgotten later. Same for eventually splitting the monolith into a distributed system — deferred until a real scale trigger, but planned for. One Python application today (not microservices), SQLite/Postgres (not a time-series DB), Docker Compose locally and on a $5/month VPS later (not Kubernetes) — until doc 7's triggers say otherwise. Sequence: **backtest → paper trade → small live capital → always-on deployment → (later) US equities / forex / distribution.**

These docs are living — update them as real decisions get made and diverge from the plan.

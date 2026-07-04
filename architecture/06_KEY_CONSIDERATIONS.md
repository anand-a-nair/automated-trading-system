# Key Considerations

Practical issues specific to building this solo, for NSE-first, with a path to US equities. Skip straight to the section that's relevant to where you are.

## Zerodha Kite Connect: cost sequencing

Kite Connect is a paid API (~₹2000/month), and unlike some brokers, Zerodha does **not** offer a free official paper-trading sandbox with live market data. That has a real implication for how you sequence Stage 1→2:

- **Stage 1 (backtesting)** doesn't need Kite Connect at all — `yfinance` or downloaded NSE bhavcopy data is free and sufficient for historical backtesting.
- **Stage 2 (paper trading)** is where you have a choice:
  - Pay for Kite Connect now, get real live tick data, and paper-trade with maximum realism (recommended once you're fairly confident in the strategy from backtesting — the ₹2000/month is a small cost relative to what you'll learn and it's the same feed you'll use live anyway).
  - Or delay the subscription: paper-trade against free delayed/EOD data at a slower cadence (e.g., end-of-day decisions rather than intraday) until you're ready to commit to the subscription. This is slower to validate but costs nothing.
- **Stage 3 (live)** requires Kite Connect regardless, since you need it to place real orders.

Given you already have some trading experience, paying for Kite Connect at the start of Stage 2 (rather than delaying) is probably worth it — the realism of live tick data matters more than the ₹2000/month for validating a strategy you're about to trust with real capital.

## Regulatory reality for a retail algo trader (India)

SEBI's algorithmic trading rules are aimed primarily at brokers and institutional participants, not individual retail traders running their own scripts through a broker's official API. Practically, for this project:

- You're trading through a SEBI-registered broker (Zerodha) via their official, sanctioned API — this is standard retail algo trading, not a grey area.
- No separate SEBI registration or reporting is required for an individual retail trader at this scale.
- What *does* matter for you directly: **tax record-keeping**. Keep the trade log (which the system should already produce as its audit trail) detailed enough to reconstruct short-term capital gains/losses at tax time — timestamps, quantities, prices, brokerage paid.
- If a strategy ever involves shorting or F&O (out of scope here, but worth flagging), different margin/reporting rules kick in — pure cash equity long/short-covered-only trading keeps things simple.

This is meaningfully lighter than the institutional compliance framework in the original draft of these docs — you don't need an audit-trail system designed for a broker-dealer, just good records for your own tax filing.

## Realistic latency expectations

Retail order execution from a home connection or a cheap cloud VM to NSE via Zerodha's API is realistically **200ms to a couple of seconds**, not the sub-100ms figures relevant to co-located institutional systems. This should shape strategy choice, not just infrastructure:

- Fine for: swing trading (holding hours to days), end-of-day strategies, moderate-frequency intraday (a handful of decisions per hour).
- Not viable for: scalping, latency arbitrage, anything assuming you can beat other participants on speed. Don't chase this — it's not where a solo retail system can compete, and it's not necessary for the learning or usage goals here.

No latency optimization work (co-location, binary protocols, etc.) is warranted at this scale — a few hundred milliseconds of execution delay is immaterial for the strategy types above.

## Data integrity: reconciliation, sized down

You still need to make sure the system's idea of "what I hold" matches reality — this doesn't go away just because it's a solo project. But it can be simple:

```python
# Once a day, e.g., after market close
system_positions = db.get_positions()
broker_positions = kite.positions()

if system_positions != broker_positions:
    send_telegram_alert(f"Position mismatch: {diff}")
    # Investigate manually — at this scale, an automatic "trust the broker
    # and overwrite" is risky without you looking at *why* first.
```

A daily check (not real-time, not event-sourced, not requiring an immutable append-only event store) is proportionate here. If you start trading intraday frequently enough that a day's drift feels too risky, tighten the check to hourly — still just a scheduled comparison, not new infrastructure.

## Error handling that actually matters at this scale

- **Order rejections** (insufficient margin, circuit limit, market closed): log the reason, alert, don't blindly retry — a rejected order almost always means the strategy's assumption was wrong, not that retrying will help.
- **Partial fills**: track filled quantity vs. intended quantity explicitly; decide upfront whether your strategy chases the remainder or accepts the partial position.
- **Broker API downtime**: fall back to read-only (can't place new orders); alert; if you have an open position and can't reach the broker, that's exactly the scenario the kill switch and small position sizing are meant to make survivable rather than catastrophic.
- **Your own bugs**: assume there will be one that tries to place a bad order eventually — this is what the risk-checks module is for. It should be boring, obviously correct, and independent enough from strategy code that a strategy bug can't bypass it.

## NSE market hours

| | Open (IST) | Close (IST) | Days |
|---|---|---|---|
| NSE Equity | 9:15 AM | 3:30 PM | Mon-Fri, excluding NSE holidays |

Pre-market session (9:00-9:15) and post-market session exist too if you want to eventually handle them, but the core continuous session above is what matters to start. Use `zoneinfo("Asia/Kolkata")` and pull the NSE holiday calendar (published annually) rather than hardcoding a weekday check — Diwali, Republic Day, etc. will otherwise trip up a supposedly-simple "is the market open" function.

## Position sizing (personal capital, not institutional)

A simple, conservative rule is enough — no need for Kelly Criterion optimization or portfolio-optimization solvers at this stage:

```
risk_per_trade = 1% of account capital  (adjust down if you want to be more conservative)
position_size  = risk_per_trade_amount / (entry_price - stop_loss_price)
```

Example: ₹100,000 account, 1% risk = ₹1,000 per trade. Stop-loss 20 points away → position size = 50 shares.

Combine with a hard cap regardless of the formula's output — e.g., never more than 20% of capital in a single name, never more than (some number) of positions open at once — so a mis-set stop-loss distance can't accidentally size a position at 80% of your account.

## Leverage

Zerodha's intraday margin (MIS) can offer several times leverage; for a learning-first system, strongly consider trading **without leverage (CNC/delivery orders)** initially, or with Zerodha's standard equity delivery margin only. Leverage multiplies both the learning curve's mistakes and the financial ones — add it later, deliberately, once the unleveraged system has proven itself.

## Monitoring, sized for one person

You don't need Prometheus/Grafana/ELK to watch a system trading a handful of NSE names. You need:

- **A structured log file** (one line per event: signal generated, risk check result, order placed/filled/rejected) — `grep`-able, and the raw material for the tax/audit trail too.
- **Telegram alerts** for anything that should interrupt your day: daily loss limit hit, reconciliation mismatch, crash, order rejected.
- **A simple dashboard** (Streamlit or a couple of FastAPI + HTML pages) showing today's PnL, open positions, and recent log lines — checked when you want to, not push-alerted for routine operation.

Add real metrics/dashboarding infrastructure only if you find yourself wanting historical trends across months that a log file genuinely can't answer well — plausible eventually, not needed on day one.

## Pre-live-capital checklist

- [ ] Backtest results you understand and trust for the specific strategy going live
- [ ] At least 2-3 weeks of paper trading with results in the same ballpark as the backtest
- [ ] Risk-checks module unit-tested: position limits, daily loss halt, capital cap
- [ ] Manual kill switch tested (confirm it actually stops new orders when triggered)
- [ ] Daily reconciliation implemented and alerting on mismatch
- [ ] Telegram/email alerts confirmed working (send yourself a test alert)
- [ ] Capital committed is an amount you've explicitly decided you can afford to lose entirely
- [ ] You've decided your leverage stance (recommendation: none, to start)

## Further reading

- **Zerodha Varsity** (free, excellent — covers both trading fundamentals and Kite Connect specifics) — the single best resource given you already have some trading background and want to go deeper on both trading and the API.
- **Kite Connect API docs** (kite.trade) — the authoritative reference for order types, margin rules, and the WebSocket tick format.
- **"A Man for All Markets" — Edward Thorp** — practical, first-person perspective on systematic trading, worth reading once for the mindset even though the strategies are dated.
- **Alpaca API docs** — when you get to the US-equities phase; their docs double as a good tutorial on paper-trading workflows generally.

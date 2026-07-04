import pytest

from trading.config import RiskLimits
from trading.models import Fill, Order, Side
from trading.portfolio import Portfolio
from trading.risk import RiskEngine

LIMITS = RiskLimits(max_position_pct=0.20, max_deployed_pct=0.80, max_daily_loss_pct=0.02)
PRICES = {"RELIANCE": 100.0}


def engine_and_portfolio(cash=100_000.0):
    e = RiskEngine(LIMITS)
    p = Portfolio(cash=cash)
    e.start_of_day(p.equity(PRICES))
    return e, p


def test_approves_order_within_all_limits():
    e, p = engine_and_portfolio()
    decision = e.check(Order("RELIANCE", Side.BUY, 100), p, PRICES)  # 10% of equity
    assert decision.approved


def test_rejects_single_position_over_limit():
    e, p = engine_and_portfolio()
    decision = e.check(Order("RELIANCE", Side.BUY, 250), p, PRICES)  # 25% > 20%
    assert not decision.approved
    assert "exceeds" in decision.reason


def test_rejects_when_existing_position_would_breach_limit():
    e, p = engine_and_portfolio()
    p.apply_fill(Fill("RELIANCE", Side.BUY, 150, 100.0, 0.0))  # 15% held
    decision = e.check(Order("RELIANCE", Side.BUY, 100), p, PRICES)  # +10% -> 25%
    assert not decision.approved


def test_rejects_when_total_deployed_would_breach_limit():
    limits = RiskLimits(max_position_pct=0.90, max_deployed_pct=0.50, max_daily_loss_pct=0.02)
    e = RiskEngine(limits)
    prices = {"A": 100.0, "B": 100.0}
    p = Portfolio(cash=100_000)
    e.start_of_day(p.equity(prices))
    p.apply_fill(Fill("A", Side.BUY, 400, 100.0, 0.0))  # 40% deployed
    decision = e.check(Order("B", Side.BUY, 200), p, prices)  # +20% -> 60% > 50%
    assert not decision.approved
    assert "deployed" in decision.reason


def test_daily_loss_limit_halts_for_the_day():
    e, p = engine_and_portfolio()
    # equity drops >2%: simulate by checking against lower prices
    crashed = {"RELIANCE": 100.0}
    p.cash -= 3_000  # 3% loss on 100k day-start equity
    decision = e.check(Order("RELIANCE", Side.BUY, 10), p, crashed)
    assert not decision.approved
    assert e.halted
    # stays halted even if equity recovers within the same day
    p.cash += 3_000
    decision2 = e.check(Order("RELIANCE", Side.BUY, 10), p, crashed)
    assert not decision2.approved


def test_start_of_day_resets_daily_halt():
    e, p = engine_and_portfolio()
    p.cash -= 3_000
    e.check(Order("RELIANCE", Side.BUY, 10), p, PRICES)
    assert e.halted
    e.start_of_day(p.equity(PRICES))
    assert not e.halted
    assert e.check(Order("RELIANCE", Side.BUY, 10), p, PRICES).approved


def test_kill_switch_blocks_everything_and_survives_new_day():
    e, p = engine_and_portfolio()
    e.kill_switch = True
    assert not e.check(Order("RELIANCE", Side.BUY, 1), p, PRICES).approved
    e.start_of_day(p.equity(PRICES))
    assert e.halted  # kill switch is manual-off only, not reset by a new day


def test_sell_allowed_only_up_to_held_quantity():
    e, p = engine_and_portfolio()
    p.apply_fill(Fill("RELIANCE", Side.BUY, 50, 100.0, 0.0))
    assert e.check(Order("RELIANCE", Side.SELL, 50), p, PRICES).approved
    assert not e.check(Order("RELIANCE", Side.SELL, 51), p, PRICES).approved


def test_cash_check_backstops_leverage_style_misconfiguration():
    # With max_deployed_pct <= 1.0 the deployed check already implies the cash
    # check (equity = cash + deployed). The cash check exists as a backstop for
    # a bad config that would otherwise allow buying with money we don't have.
    limits = RiskLimits(max_position_pct=1.0, max_deployed_pct=2.0, max_daily_loss_pct=0.5)
    e = RiskEngine(limits)
    p = Portfolio(cash=100_000)
    prices = {"A": 100.0, "RELIANCE": 100.0}
    e.start_of_day(p.equity(prices))
    p.apply_fill(Fill("A", Side.BUY, 950, 100.0, 0.0))  # cash down to 5k
    decision = e.check(Order("RELIANCE", Side.BUY, 100), p, prices)  # needs 10k
    assert not decision.approved
    assert "cash" in decision.reason

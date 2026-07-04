import pytest

from trading.models import Fill, Side
from trading.portfolio import Portfolio


def buy(symbol="RELIANCE", qty=10, price=100.0, costs=1.0):
    return Fill(symbol=symbol, side=Side.BUY, quantity=qty, price=price, costs=costs)


def sell(symbol="RELIANCE", qty=10, price=110.0, costs=1.0):
    return Fill(symbol=symbol, side=Side.SELL, quantity=qty, price=price, costs=costs)


def test_buy_reduces_cash_and_opens_position():
    p = Portfolio(cash=10_000)
    p.apply_fill(buy(qty=10, price=100.0, costs=5.0))
    assert p.cash == pytest.approx(10_000 - 1_000 - 5.0)
    assert p.position("RELIANCE").quantity == 10
    assert p.position("RELIANCE").avg_price == pytest.approx(100.0)


def test_buy_averages_price_across_fills():
    p = Portfolio(cash=10_000)
    p.apply_fill(buy(qty=10, price=100.0, costs=0.0))
    p.apply_fill(buy(qty=10, price=120.0, costs=0.0))
    assert p.position("RELIANCE").quantity == 20
    assert p.position("RELIANCE").avg_price == pytest.approx(110.0)


def test_sell_realizes_pnl_net_of_costs():
    p = Portfolio(cash=10_000)
    p.apply_fill(buy(qty=10, price=100.0, costs=0.0))
    p.apply_fill(sell(qty=10, price=110.0, costs=2.0))
    assert p.realized_pnl == pytest.approx(10 * 10.0 - 2.0)
    assert p.position("RELIANCE").quantity == 0
    assert p.cash == pytest.approx(10_000 - 1_000 + 1_100 - 2.0)


def test_partial_sell_keeps_remainder_at_same_avg_price():
    p = Portfolio(cash=10_000)
    p.apply_fill(buy(qty=10, price=100.0, costs=0.0))
    p.apply_fill(sell(qty=4, price=110.0, costs=0.0))
    assert p.position("RELIANCE").quantity == 6
    assert p.position("RELIANCE").avg_price == pytest.approx(100.0)


def test_cannot_sell_more_than_held():
    p = Portfolio(cash=10_000)
    p.apply_fill(buy(qty=5, price=100.0, costs=0.0))
    with pytest.raises(ValueError, match="cannot sell"):
        p.apply_fill(sell(qty=6))


def test_cannot_buy_beyond_cash():
    p = Portfolio(cash=500)
    with pytest.raises(ValueError, match="cash available"):
        p.apply_fill(buy(qty=10, price=100.0))


def test_equity_and_unrealized_pnl():
    p = Portfolio(cash=10_000)
    p.apply_fill(buy(qty=10, price=100.0, costs=0.0))
    prices = {"RELIANCE": 105.0}
    assert p.equity(prices) == pytest.approx(9_000 + 1_050)
    assert p.unrealized_pnl(prices) == pytest.approx(50.0)

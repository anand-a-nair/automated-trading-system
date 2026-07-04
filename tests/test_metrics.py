import pytest

from trading.backtest.metrics import max_drawdown, sharpe_ratio, total_return, win_rate


def test_total_return():
    assert total_return([100, 110, 121]) == pytest.approx(0.21)
    assert total_return([100]) == 0.0
    assert total_return([]) == 0.0


def test_max_drawdown_simple_peak_to_trough():
    # peak 120 -> trough 90 = 25% drawdown, later recovery doesn't erase it
    assert max_drawdown([100, 120, 90, 130]) == pytest.approx(0.25)


def test_max_drawdown_monotonic_rise_is_zero():
    assert max_drawdown([100, 110, 120]) == 0.0


def test_sharpe_positive_for_steady_gains():
    curve = [100 * (1.001**i) for i in range(100)]
    assert sharpe_ratio(curve) > 0


def test_sharpe_zero_for_flat_curve():
    assert sharpe_ratio([100.0] * 50) == 0.0


def test_win_rate():
    assert win_rate([10, -5, 3, -1]) == pytest.approx(0.5)
    assert win_rate([]) == 0.0

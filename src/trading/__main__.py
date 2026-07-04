"""CLI entry point.

Stage 1 usage:
    python -m trading backtest --symbol RELIANCE.NS --start 2022-01-01 --end 2024-12-31

Paper/live modes arrive in Stages 2-3 (architecture/05_IMPLEMENTATION_ROADMAP.md).
"""

from __future__ import annotations

import argparse
import sys
from datetime import date


def cmd_backtest(args: argparse.Namespace) -> int:
    from trading.backtest import BacktestEngine
    from trading.config import Settings
    from trading.data.yahoo import YahooDataSource
    from trading.strategy.sma_crossover import SmaCrossover

    bars = YahooDataSource().get_historical(
        args.symbol, date.fromisoformat(args.start), date.fromisoformat(args.end)
    )
    strategy = SmaCrossover(fast=args.fast, slow=args.slow)
    engine = BacktestEngine(starting_cash=args.cash, limits=Settings.from_env().risk)
    result = engine.run(strategy, bars)
    print(result.summary())
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="trading")
    sub = parser.add_subparsers(dest="command", required=True)

    bt = sub.add_parser("backtest", help="run a backtest against historical data")
    bt.add_argument("--symbol", required=True, help="e.g. RELIANCE.NS (NSE via Yahoo)")
    bt.add_argument("--start", default="2022-01-01")
    bt.add_argument("--end", default=date.today().isoformat())
    bt.add_argument("--cash", type=float, default=100_000.0)
    bt.add_argument("--fast", type=int, default=20)
    bt.add_argument("--slow", type=int, default=50)
    bt.set_defaults(func=cmd_backtest)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

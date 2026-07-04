"""Historical daily bars from Yahoo Finance (free; NSE symbols use the .NS suffix).

Good enough for Stage 1 backtesting. Replace/augment with Zerodha's historical
API once Kite Connect access exists (more accurate, intraday available).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from trading.data.base import MarketDataSource
from trading.models import Bar

CACHE_DIR = Path("data/cache")


class YahooDataSource(MarketDataSource):
    def __init__(self, cache_dir: Path = CACHE_DIR) -> None:
        self.cache_dir = cache_dir

    def get_historical(self, symbol: str, start: date, end: date) -> list[Bar]:
        import pandas as pd

        cache_file = self.cache_dir / f"{symbol}_{start}_{end}.csv"
        if cache_file.exists():
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        else:
            import yfinance as yf

            df = yf.download(
                symbol, start=start, end=end, interval="1d",
                auto_adjust=True, progress=False, multi_level_index=False,
            )
            if df is None or df.empty:
                raise ValueError(f"no data returned for {symbol} ({start}..{end})")
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            df.to_csv(cache_file)

        return [
            Bar(
                symbol=symbol,
                at=idx.to_pydatetime(),
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=int(row["Volume"]),
            )
            for idx, row in df.iterrows()
        ]

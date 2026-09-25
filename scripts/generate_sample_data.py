#!/usr/bin/env python
"""Deterministic sample data generator - writes curated Parquet for demo/development.

The repo intentionally ships without market data (data/ is gitignored).  This
script creates a small, deterministic NSE-style 5-minute dataset for a dozen
well-known symbols, with a few planted unusual-activity events so the
detectors, alerts and dashboards have something real to chew on.

Usage:
    python scripts/generate_sample_data.py [--days 4] [--curated-dir data/curated]
"""
from __future__ import annotations

import argparse
import logging
import math
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from marketwatch.ingestion.parquet_store import (  # noqa: E402
    write_quality_metadata,
    write_symbol_parquet,
)
from marketwatch.ingestion.validator import validate_ohlcv  # noqa: E402

logger = logging.getLogger("sample-data")
IST = ZoneInfo("Asia/Kolkata")
BARS_PER_DAY = 75  # 09:15 -> 15:25 IST, 5-minute bars


def _rng(seed: int):
    """Park-Miller LCG -> deterministic floats in (0, 1)."""
    state = seed % 2147483647 or 1
    while True:
        state = (state * 16807) % 2147483647
        yield (state - 1) / 2147483646


# symbol, display base price, seed, events: (day_offset_from_last, bar, kind, size)
UNIVERSE: list[tuple[str, float, int, list[tuple[int, int, str, float]]]] = [
    ("ADANIENT", 3020.0, 7, [(0, 50, "pump", 0.028)]),
    ("YESBANK", 23.4, 11, [(0, 45, "dump", 0.022)]),
    ("TATAMOTORS", 968.0, 19, [(0, 57, "pump", 0.016)]),
    ("IRFC", 171.0, 23, [(0, 42, "volume", 0.0), (0, 66, "pump", 0.02)]),
    ("PAYTM", 712.0, 29, [(0, 61, "dump", 0.026)]),
    ("RELIANCE", 2915.0, 31, [(1, 33, "volume", 0.0)]),
    ("HDFCBANK", 1642.0, 37, []),
    ("INFY", 1876.0, 41, [(0, 69, "squeeze", 0.012)]),
    ("TCS", 4210.0, 43, []),
    ("ZOMATO", 262.0, 47, [(0, 53, "volume", 0.0)]),
    ("SBIN", 812.0, 53, [(2, 28, "pump", 0.014)]),
    ("SUZLON", 71.2, 59, [(0, 47, "pump", 0.024)]),
]


def trading_days(days: int) -> list[date]:
    """Return the last `days` weekdays ending 2026-09-24 for determinism."""
    end = date(2026, 9, 24)
    out: list[date] = []
    cursor = end
    while len(out) < days:
        if cursor.weekday() < 5:
            out.append(cursor)
        cursor -= timedelta(days=1)
    return sorted(out)


def make_frame(symbol: str, base: float, seed: int, days: list[date],
               events: list[tuple[int, int, str, float]]) -> pd.DataFrame:
    rnd = _rng(seed * 977 + 13)
    n_days = len(days)
    rows: list[tuple[datetime, float, float, float, float, float]] = []
    price = base
    for d_idx, day in enumerate(days):
        for i in range(BARS_PER_DAY):
            ts = datetime.combine(day, time(9, 15), tzinfo=IST) + timedelta(minutes=5 * i)
            event = next(
                (e for e in events if e[0] == (n_days - 1 - d_idx) and e[1] <= i < e[1] + 4),
                None,
            )
            first = event is not None and i == event[1]
            tod = 1 + 0.9 * math.exp(-i / 6) + 0.6 * math.exp(-(BARS_PER_DAY - 1 - i) / 5)
            drift = (next(rnd) - 0.5) * 0.0072
            if next(rnd) < 0.04:
                drift += (next(rnd) - 0.5) * 0.014
            vol_mul = math.exp((next(rnd) + next(rnd) + next(rnd) - 1.5) * 0.45)
            wick = 0.0018
            close_bias = 0.0
            if event is not None:
                kind, size = event[2], event[3]
                sign = -1.0 if kind == "dump" else 1.0
                if kind == "volume":
                    vol_mul = 6.5 if first else 3.0
                    drift = (next(rnd) - 0.5) * 0.004
                elif kind == "squeeze":
                    drift = sign * (size if first else size * 0.4)
                    vol_mul = 4.2 if first else 2.2
                    wick = 0.004
                    close_bias = 0.8
                else:
                    drift = sign * (size if first else size * 0.3)
                    vol_mul = 6.1 if first else 2.6 + next(rnd)
                    wick = 0.006
                    close_bias = 0.85
            open_ = price
            close = price * (1 + drift)
            high = max(open_, close) * (1 + next(rnd) * wick)
            low = min(open_, close) * (1 - next(rnd) * wick)
            if close_bias and event is not None:
                if close > open_:
                    high = close * (1 + (1 - close_bias) * 0.003)
                else:
                    low = close * (1 - (1 - close_bias) * 0.003)
            volume = round(tod * vol_mul * (80000 + seed * 1500))
            rows.append((ts, open_, high, low, close, float(volume)))
            price = close
    df = pd.DataFrame(rows, columns=["Datetime", "Open", "High", "Low", "Close", "Volume"])
    return df.set_index("Datetime")


def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministic sample data generator")
    parser.add_argument("--days", type=int, default=4)
    parser.add_argument("--curated-dir", default="data/curated")
    args = parser.parse_args()

    curated_dir = Path(args.curated_dir)
    days = trading_days(args.days)
    logger.info("Writing %d trading days (%s .. %s) for %d symbols",
                len(days), days[0], days[-1], len(UNIVERSE))

    total_rows = 0
    loaded: list[str] = []
    for symbol, base, seed, events in UNIVERSE:
        df = make_frame(symbol, base, seed, days, events)
        clean, result = validate_ohlcv(symbol, df)
        if clean.empty:
            raise SystemExit(f"generated data for {symbol} failed validation: {result.invalid_reasons}")
        write_symbol_parquet(symbol, clean, curated_dir)
        total_rows += result.valid_rows
        loaded.append(symbol)
        logger.info("[%s] %d rows", symbol, result.valid_rows)

    write_quality_metadata(
        {
            "source_type": "sample",
            "universe_id": "sample12",
            "requested_symbols": loaded,
            "loaded_symbols": loaded,
            "missing_symbols": [],
            "coverage_pct": 100.0,
            "date_range_start": datetime.combine(days[0], time(9, 15), tzinfo=IST).isoformat(),
            "date_range_end": datetime.combine(days[-1], time(15, 25), tzinfo=IST).isoformat(),
            "total_rows": total_rows,
            "is_offline_confirmed": True,
        },
        curated_dir,
    )
    logger.info("Done: %d rows across %d symbols -> %s", total_rows, len(loaded), curated_dir)
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
    raise SystemExit(main())

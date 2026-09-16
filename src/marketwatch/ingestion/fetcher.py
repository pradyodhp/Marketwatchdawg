"""yfinance-based 5-minute candle fetcher with exponential backoff.

This module is STRICTLY an offline pre-fetch tool.  It must never be called
during replay or inference.  All network access is confined here.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import pandas as pd

logger = logging.getLogger(__name__)

# yfinance is an optional dependency — only used during curation
try:
    import yfinance as yf
    _YF_AVAILABLE = True
except ImportError:
    _YF_AVAILABLE = False


# ── Constants ─────────────────────────────────────────────────────────────────

FETCH_PERIOD = "60d"          # Maximum 5-minute history yfinance provides
FETCH_INTERVAL = "5m"
INITIAL_BACKOFF_SEC = 2.0     # First retry wait (seconds)
MAX_BACKOFF_SEC = 60.0        # Cap per-symbol retry delay
MAX_RETRIES = 3               # Attempts per symbol
INTER_SYMBOL_DELAY_SEC = 1.0  # Polite delay between symbols

REQUIRED_COLUMNS = {"Open", "High", "Low", "Close", "Volume"}


@dataclass
class FetchResult:
    """Result of fetching 5-minute data for a single symbol."""

    symbol: str
    success: bool
    df: pd.DataFrame | None = None   # Raw OHLCV DataFrame, None on failure
    error: str | None = None
    row_count: int = 0
    date_range: tuple[str, str] = field(default=("", ""))


def fetch_symbol(symbol: str, *, period: str = FETCH_PERIOD, interval: str = FETCH_INTERVAL) -> FetchResult:
    """Fetch 5-minute OHLCV data for a single symbol with exponential backoff.

    Args:
        symbol: NSE ticker (e.g. "HDFCBANK.NS") or benchmark (e.g. "^NSEI").
        period: yfinance period string.
        interval: yfinance interval string.

    Returns:
        FetchResult with df on success, error message on failure.
    """
    if not _YF_AVAILABLE:
        return FetchResult(symbol=symbol, success=False, error="yfinance not installed")

    backoff = INITIAL_BACKOFF_SEC
    last_error: str = ""

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.debug("Fetching %s (attempt %d/%d)", symbol, attempt, MAX_RETRIES)
            ticker = yf.Ticker(symbol)
            df: pd.DataFrame = ticker.history(period=period, interval=interval, auto_adjust=True)

            if df is None or df.empty:
                last_error = "Empty response from yfinance"
                logger.warning("[%s] %s", symbol, last_error)
            else:
                # Verify required columns present
                missing_cols = REQUIRED_COLUMNS - set(df.columns)
                if missing_cols:
                    last_error = f"Missing columns: {missing_cols}"
                    logger.warning("[%s] %s", symbol, last_error)
                else:
                    # Success — drop Dividends and Stock Splits if present
                    df = df[list(REQUIRED_COLUMNS)].copy()
                    df.index.name = "Datetime"
                    ts_min = str(df.index.min())
                    ts_max = str(df.index.max())
                    logger.info("[%s] Fetched %d rows (%s → %s)", symbol, len(df), ts_min, ts_max)
                    return FetchResult(
                        symbol=symbol,
                        success=True,
                        df=df,
                        row_count=len(df),
                        date_range=(ts_min, ts_max),
                    )

        except (AttributeError, TypeError, ValueError, RuntimeError) as exc:
            last_error = str(exc)
            logger.warning("[%s] Attempt %d failed: %s", symbol, attempt, last_error)

        if attempt < MAX_RETRIES:
            logger.debug("[%s] Waiting %.1fs before retry", symbol, backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, MAX_BACKOFF_SEC)

    return FetchResult(symbol=symbol, success=False, error=last_error)


def fetch_universe(
    symbols: list[str],
    *,
    inter_symbol_delay: float = INTER_SYMBOL_DELAY_SEC,
) -> list[FetchResult]:
    """Fetch 5-minute data for all symbols with polite inter-symbol delay.

    Args:
        symbols: List of ticker strings.
        inter_symbol_delay: Seconds to wait between symbols.

    Returns:
        List of FetchResult (one per symbol, in order).
    """
    results: list[FetchResult] = []

    for i, symbol in enumerate(symbols):
        logger.info("Fetching %d/%d: %s", i + 1, len(symbols), symbol)
        result = fetch_symbol(symbol)
        results.append(result)
        if i < len(symbols) - 1:
            time.sleep(inter_symbol_delay)

    succeeded = sum(1 for r in results if r.success)
    logger.info(
        "Fetch complete: %d/%d symbols successful (%.1f%%)",
        succeeded,
        len(symbols),
        100 * succeeded / len(symbols) if symbols else 0.0,
    )
    return results

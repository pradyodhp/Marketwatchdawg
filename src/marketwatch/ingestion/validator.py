"""OHLCV data validation and quality-check logic.

Validates raw yfinance DataFrames against MarketWatch invariants:
- Positive prices (open/high/low/close > 0)
- Non-negative volume
- Standard OHLC geometric relationships (high >= low, high >= open/close, low <= open/close)
- IST timezone presence
- 5-minute bar frequency
- No duplicate timestamps
- NSE trading hours (09:15–15:30 IST, slot_index 0..74)
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo

import pandas as pd

from marketwatch.models.candle import compute_slot_index

logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")
FIVE_MIN_FREQ_SECONDS = 300  # 5 minutes in seconds


@dataclass
class ValidationResult:
    """Result of validating one symbol's OHLCV DataFrame."""

    symbol: str
    total_rows: int = 0
    valid_rows: int = 0
    dropped_rows: int = 0
    invalid_reasons: dict[str, int] = field(default_factory=dict)
    trading_days: int = 0
    date_range: tuple[str, str] = field(default=("", ""))
    duplicate_timestamps: int = 0
    out_of_hours_rows: int = 0
    zero_volume_rows: int = 0


def _add_reason(result: ValidationResult, reason: str, count: int = 1) -> None:
    result.invalid_reasons[reason] = result.invalid_reasons.get(reason, 0) + count


def validate_ohlcv(symbol: str, df: pd.DataFrame) -> tuple[pd.DataFrame, ValidationResult]:
    """Validate and clean a raw yfinance OHLCV DataFrame.

    Returns a cleaned DataFrame (valid rows only, IST-normalized index)
    and a ValidationResult describing what was accepted/dropped.

    Args:
        symbol: Ticker string for logging.
        df: Raw DataFrame with columns Open/High/Low/Close/Volume and DatetimeIndex.

    Returns:
        (clean_df, result) — clean_df may be empty if nothing passes.
    """
    result = ValidationResult(symbol=symbol, total_rows=len(df))

    if df.empty:
        logger.warning("[%s] Empty DataFrame — nothing to validate", symbol)
        return df.copy(), result

    # ── 1. Ensure IST timezone ───────────────────────────────────────────────
    if df.index.tz is None:
        df = df.copy()
        df.index = df.index.tz_localize(IST)
    else:
        df = df.copy()
        df.index = df.index.tz_convert(IST)

    # ── 2. Drop duplicate timestamps ─────────────────────────────────────────
    n_before = len(df)
    df = df[~df.index.duplicated(keep="first")]
    dupes = n_before - len(df)
    if dupes > 0:
        _add_reason(result, "duplicate_timestamp", dupes)
        result.duplicate_timestamps = dupes

    # ── 3. Ensure columns are float64 ────────────────────────────────────────
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # ── 4. Row-level financial invariant checks ──────────────────────────────
    valid_mask = pd.Series(True, index=df.index)

    # Positive prices
    price_cols = ["Open", "High", "Low", "Close"]
    nonpos = (df[price_cols] <= 0).any(axis=1) | df[price_cols].isna().any(axis=1)
    if nonpos.any():
        _add_reason(result, "non_positive_price", int(nonpos.sum()))
        valid_mask &= ~nonpos

    # Non-negative volume
    neg_vol = (df["Volume"] < 0) | df["Volume"].isna()
    if neg_vol.any():
        _add_reason(result, "negative_volume", int(neg_vol.sum()))
        valid_mask &= ~neg_vol

    # OHLC geometric bounds
    bad_hl = df["High"] < df["Low"]
    if bad_hl.any():
        _add_reason(result, "high_lt_low", int(bad_hl.sum()))
        valid_mask &= ~bad_hl

    bad_high = (df["High"] < df["Open"]) | (df["High"] < df["Close"])
    if bad_high.any():
        _add_reason(result, "high_lt_open_close", int(bad_high.sum()))
        valid_mask &= ~bad_high

    bad_low = (df["Low"] > df["Open"]) | (df["Low"] > df["Close"])
    if bad_low.any():
        _add_reason(result, "low_gt_open_close", int(bad_low.sum()))
        valid_mask &= ~bad_low

    # Finite float check
    inf_mask = df[price_cols + ["Volume"]].map(lambda x: not math.isfinite(x) if isinstance(x, float) else False).any(axis=1)
    if inf_mask.any():
        _add_reason(result, "non_finite_value", int(inf_mask.sum()))
        valid_mask &= ~inf_mask

    df_clean = df[valid_mask].copy()

    # ── 5. Filter to NSE trading hours (09:15–15:30 IST) ────────────────────
    valid_hours_mask = []
    for ts in df_clean.index:
        try:
            compute_slot_index(ts)
            valid_hours_mask.append(True)
        except ValueError:
            valid_hours_mask.append(False)

    hours_mask = pd.Series(valid_hours_mask, index=df_clean.index)
    out_of_hours = (~hours_mask).sum()
    if out_of_hours > 0:
        _add_reason(result, "out_of_trading_hours", int(out_of_hours))
        result.out_of_hours_rows = int(out_of_hours)
    df_clean = df_clean[hours_mask]

    # ── 6. Count zero-volume rows (keep but flag) ────────────────────────────
    zero_vol = (df_clean["Volume"] == 0).sum()
    result.zero_volume_rows = int(zero_vol)

    # ── 7. Compute summary stats ──────────────────────────────────────────────
    result.valid_rows = len(df_clean)
    result.dropped_rows = result.total_rows - result.valid_rows
    if not df_clean.empty:
        result.trading_days = df_clean.index.normalize().nunique()
        result.date_range = (
            df_clean.index.min().isoformat(),
            df_clean.index.max().isoformat(),
        )

    logger.info(
        "[%s] Validation: %d/%d rows valid (%d dropped), %d trading days",
        symbol,
        result.valid_rows,
        result.total_rows,
        result.dropped_rows,
        result.trading_days,
    )
    return df_clean, result

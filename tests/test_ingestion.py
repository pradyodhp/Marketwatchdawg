"""Unit tests for Phase 2 ingestion: fetcher, validator, parquet store.

All tests are fully offline — no network calls.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

IST = ZoneInfo("Asia/Kolkata")


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_df(rows: list[dict], tz: str = "Asia/Kolkata") -> pd.DataFrame:
    """Build a minimal OHLCV DataFrame with IST timestamps."""
    timestamps = [r.pop("ts") for r in rows]
    df = pd.DataFrame(rows, index=pd.DatetimeIndex(timestamps, name="Datetime"))
    df.index = df.index.tz_localize(tz) if df.index.tz is None else df.index.tz_convert(tz)
    return df


def _valid_row(ts: datetime, open_=100.0, high=102.0, low=99.0, close=101.0, vol=50000.0) -> dict:
    return {"ts": ts, "Open": open_, "High": high, "Low": low, "Close": close, "Volume": vol}


# valid 09:15–09:45 IST window (slots 0, 1, 2)
T0 = datetime(2024, 1, 15, 9, 15, tzinfo=IST)
T1 = datetime(2024, 1, 15, 9, 20, tzinfo=IST)
T2 = datetime(2024, 1, 15, 9, 25, tzinfo=IST)


# ── Validator tests ───────────────────────────────────────────────────────────

class TestValidator:
    def test_valid_rows_pass(self):
        from marketwatch.ingestion.validator import validate_ohlcv
        df = _make_df([_valid_row(T0), _valid_row(T1), _valid_row(T2)])
        _clean, result = validate_ohlcv("TEST.NS", df)
        assert result.valid_rows == 3
        assert result.dropped_rows == 0

    def test_non_positive_price_dropped(self):
        from marketwatch.ingestion.validator import validate_ohlcv
        bad = _valid_row(T0, open_=-1.0)  # negative open
        df = _make_df([bad, _valid_row(T1)])
        _clean, result = validate_ohlcv("TEST.NS", df)
        assert result.valid_rows == 1
        assert "non_positive_price" in result.invalid_reasons

    def test_zero_price_dropped(self):
        from marketwatch.ingestion.validator import validate_ohlcv
        bad = _valid_row(T0, open_=0.0)
        df = _make_df([bad, _valid_row(T1)])
        _clean, result = validate_ohlcv("TEST.NS", df)
        assert result.valid_rows == 1

    def test_high_lt_low_dropped(self):
        from marketwatch.ingestion.validator import validate_ohlcv
        # high < low is geometrically invalid
        bad = _valid_row(T0, high=98.0, low=101.0)
        df = _make_df([bad, _valid_row(T1)])
        _clean, result = validate_ohlcv("TEST.NS", df)
        assert result.valid_rows == 1
        assert "high_lt_low" in result.invalid_reasons

    def test_out_of_trading_hours_dropped(self):
        from marketwatch.ingestion.validator import validate_ohlcv
        # 08:00 IST is before market open
        t_early = datetime(2024, 1, 15, 8, 0, tzinfo=IST)
        df = _make_df([_valid_row(t_early), _valid_row(T0)])
        _clean, result = validate_ohlcv("TEST.NS", df)
        assert result.valid_rows == 1
        assert result.out_of_hours_rows == 1

    def test_duplicate_timestamps_deduplicated(self):
        from marketwatch.ingestion.validator import validate_ohlcv
        df = _make_df([_valid_row(T0), _valid_row(T0)])  # duplicate
        _clean, result = validate_ohlcv("TEST.NS", df)
        assert result.valid_rows == 1
        assert result.duplicate_timestamps == 1

    def test_empty_dataframe(self):
        from marketwatch.ingestion.validator import validate_ohlcv
        df = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
        df.index = pd.DatetimeIndex([], name="Datetime")
        _clean, result = validate_ohlcv("TEST.NS", df)
        assert result.valid_rows == 0

    def test_negative_volume_dropped(self):
        from marketwatch.ingestion.validator import validate_ohlcv
        bad = _valid_row(T0, vol=-100.0)
        df = _make_df([bad, _valid_row(T1)])
        _clean, result = validate_ohlcv("TEST.NS", df)
        assert result.valid_rows == 1
        assert "negative_volume" in result.invalid_reasons

    def test_zero_volume_kept_but_flagged(self):
        from marketwatch.ingestion.validator import validate_ohlcv
        # zero volume is valid (halted ticks) — kept
        zero_vol = _valid_row(T0, vol=0.0)
        df = _make_df([zero_vol, _valid_row(T1)])
        _clean, result = validate_ohlcv("TEST.NS", df)
        assert result.valid_rows == 2
        assert result.zero_volume_rows == 1

    def test_trading_days_counted(self):
        from marketwatch.ingestion.validator import validate_ohlcv
        t_day2 = datetime(2024, 1, 16, 9, 15, tzinfo=IST)
        df = _make_df([_valid_row(T0), _valid_row(T1), _valid_row(t_day2)])
        _clean, result = validate_ohlcv("TEST.NS", df)
        assert result.trading_days == 2

    def test_ist_normalization(self):
        from marketwatch.ingestion.validator import validate_ohlcv
        # Supply UTC timestamps — should be converted to IST (09:15 IST = 03:45 UTC)
        t_utc = datetime(2024, 1, 15, 3, 45, tzinfo=ZoneInfo("UTC"))
        df = _make_df([_valid_row(t_utc)], tz="UTC")
        _clean, result = validate_ohlcv("TEST.NS", df)
        # 03:45 UTC = 09:15 IST → valid slot 0
        assert result.valid_rows == 1


# ── Parquet Store tests ───────────────────────────────────────────────────────

class TestParquetStore:
    def test_write_and_read_roundtrip(self, tmp_path):
        from marketwatch.ingestion.parquet_store import (
            read_symbol_parquet,
            write_symbol_parquet,
        )
        df = _make_df([_valid_row(T0), _valid_row(T1), _valid_row(T2)])
        write_symbol_parquet("HDFC.NS", df, curated_dir=tmp_path)
        result = read_symbol_parquet("HDFC.NS", curated_dir=tmp_path)
        assert result is not None
        assert len(result) == 3
        assert set(result.columns) == {"open", "high", "low", "close", "volume"}

    def test_read_missing_symbol_returns_none(self, tmp_path):
        from marketwatch.ingestion.parquet_store import read_symbol_parquet
        result = read_symbol_parquet("NONEXISTENT.NS", curated_dir=tmp_path)
        assert result is None

    def test_parquet_index_is_ist(self, tmp_path):
        from marketwatch.ingestion.parquet_store import (
            read_symbol_parquet,
            write_symbol_parquet,
        )
        df = _make_df([_valid_row(T0)])
        write_symbol_parquet("TEST.NS", df, curated_dir=tmp_path)
        result = read_symbol_parquet("TEST.NS", curated_dir=tmp_path)
        assert result is not None
        assert str(result.index.tz) == "Asia/Kolkata"

    def test_quality_metadata_roundtrip(self, tmp_path):
        from marketwatch.ingestion.parquet_store import (
            read_quality_metadata,
            write_quality_metadata,
        )
        meta = {"loaded_symbols": ["A.NS", "B.NS"], "coverage_pct": 98.5}
        write_quality_metadata(meta, curated_dir=tmp_path)
        result = read_quality_metadata(curated_dir=tmp_path)
        assert result is not None
        assert result["coverage_pct"] == 98.5
        assert "generated_at" in result

    def test_quality_metadata_missing_returns_none(self, tmp_path):
        from marketwatch.ingestion.parquet_store import read_quality_metadata
        result = read_quality_metadata(curated_dir=tmp_path)
        assert result is None

    def test_benchmark_symbol_safe_naming(self, tmp_path):
        from marketwatch.ingestion.parquet_store import write_symbol_parquet
        df = _make_df([_valid_row(T0)])
        path = write_symbol_parquet("^NSEI", df, curated_dir=tmp_path)
        assert path.exists()
        assert "_CARET_" in path.name

    def test_parquet_values_float64(self, tmp_path):
        from marketwatch.ingestion.parquet_store import (
            read_symbol_parquet,
            write_symbol_parquet,
        )
        df = _make_df([_valid_row(T0, open_=1234.5678)])
        write_symbol_parquet("TEST.NS", df, curated_dir=tmp_path)
        result = read_symbol_parquet("TEST.NS", curated_dir=tmp_path)
        assert result is not None
        assert result["open"].dtype == "float64"
        assert abs(result["open"].iloc[0] - 1234.5678) < 0.001

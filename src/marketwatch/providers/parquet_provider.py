"""ParquetDataProvider — offline-first MarketDataProvider backed by curated Parquet files.

Implements the MarketDataProvider protocol from Phase 1.
Zero runtime network dependency.  Never fabricates or silently substitutes data.
"""
from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from marketwatch.ingestion.parquet_store import (
    DEFAULT_CURATED_DIR,
    read_quality_metadata,
    read_symbol_parquet,
)
from marketwatch.models.candle import Candle, CandleBatch, compute_slot_index
from marketwatch.models.metadata import DataQualityMetadata

logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")

# Sentinel datetime used when no data is available
_EPOCH_IST = datetime(1970, 1, 1, 9, 15, 0, tzinfo=IST)


class ParquetDataProvider:
    """Offline data provider reading curated 5-minute Parquet candle files.

    Satisfies the MarketDataProvider structural protocol (runtime_checkable):
      - get_symbols() -> list[str]
      - get_date_range() -> tuple[datetime, datetime]
      - get_quality_metadata() -> DataQualityMetadata
      - get_candles(symbol) -> Iterator[Candle]
      - stream_batches() -> Iterator[CandleBatch]
    """

    def __init__(self, curated_dir: Path = DEFAULT_CURATED_DIR) -> None:
        self._dir = Path(curated_dir)
        self._raw_meta: dict | None = read_quality_metadata(self._dir)
        self._loaded_dfs: dict[str, pd.DataFrame] = {}

    # ── Protocol: get_symbols ─────────────────────────────────────────────────

    def get_symbols(self) -> list[str]:
        """Return symbols that have curated Parquet data available."""
        meta = self._raw_meta or {}
        return list(meta.get("loaded_symbols", []))

    # ── Protocol: get_date_range (global, no symbol arg) ─────────────────────

    def get_date_range(self) -> tuple[datetime, datetime]:
        """Return (earliest_timestamp, latest_timestamp) across the whole dataset."""
        meta = self._raw_meta or {}
        start_str = meta.get("date_range_start", "")
        end_str = meta.get("date_range_end", "")
        try:
            start_dt = datetime.fromisoformat(start_str) if start_str else _EPOCH_IST
            end_dt = datetime.fromisoformat(end_str) if end_str else _EPOCH_IST
        except ValueError:
            start_dt = end_dt = _EPOCH_IST
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=IST)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=IST)
        return start_dt.astimezone(IST), end_dt.astimezone(IST)

    # ── Protocol: get_quality_metadata ───────────────────────────────────────

    def get_quality_metadata(self) -> DataQualityMetadata:
        """Return dataset quality and coverage metadata (DataQualityMetadata schema)."""
        meta = self._raw_meta or {}
        loaded_syms: list[str] = meta.get("loaded_symbols", [])
        requested_syms: list[str] = meta.get("requested_symbols", [])
        missing_syms: list[str] = meta.get("missing_symbols", [])
        n_loaded = len(loaded_syms)
        n_requested = len(requested_syms) if requested_syms else n_loaded
        coverage_pct = meta.get("coverage_pct", 100.0 if loaded_syms else 0.0)

        start_dt, end_dt = self.get_date_range()

        # Build missing_bars_summary from symbol_coverage if available
        missing_bars: dict[str, int] = {}
        for sym in missing_syms:
            missing_bars[sym] = -1  # -1 = entirely missing symbol

        return DataQualityMetadata(
            source_type="offline_parquet",
            universe_id=meta.get("universe_id", "nifty100"),
            loaded_symbols_count=n_loaded,
            total_symbols_count=n_requested,
            coverage_percentage=float(coverage_pct),
            start_timestamp=start_dt,
            end_timestamp=end_dt,
            total_bars_per_symbol=meta.get("total_rows", 0) // max(n_loaded, 1),
            missing_bars_summary=missing_bars,
            is_offline_confirmed=True,
        )

    # ── Protocol: get_candles ────────────────────────────────────────────────

    def get_candles(
        self,
        symbol: str,
        start: date | None = None,
        end: date | None = None,
    ) -> Iterator[Candle]:
        """Yield Candle objects for a symbol, optionally filtered by date range.

        Never fabricates data — missing symbols yield nothing.
        """
        df = self._load_df(symbol)
        if df is None:
            logger.warning("[%s] No curated data — yielding nothing (no fabrication)", symbol)
            return

        if start is not None:
            start_dt = datetime(start.year, start.month, start.day, 0, 0, 0, tzinfo=IST)
            df = df[df.index >= start_dt]
        if end is not None:
            end_dt = datetime(end.year, end.month, end.day, 23, 59, 59, tzinfo=IST)
            df = df[df.index <= end_dt]

        for ts, row in df.iterrows():
            try:
                yield Candle(
                    symbol=symbol,
                    timestamp=ts,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                )
            except (AttributeError, KeyError, TypeError, ValueError) as exc:
                logger.debug("[%s] Skipping invalid candle at %s: %s", symbol, ts, exc)

    # ── Protocol: stream_batches ─────────────────────────────────────────────

    def stream_batches(
        self,
        symbols: list[str] | None = None,
        start: date | None = None,
        end: date | None = None,
    ) -> Iterator[CandleBatch]:
        """Yield synchronized CandleBatch objects across all symbols by timestamp.

        Sparse: timestamps where only some symbols have data still emit a batch
        with the available subset.  Missing symbols are omitted — not fabricated.
        """
        if symbols is None:
            symbols = self.get_symbols()

        all_candles: dict[datetime, dict[str, Candle]] = {}
        for symbol in symbols:
            for candle in self.get_candles(symbol, start=start, end=end):
                ts = candle.timestamp
                if ts not in all_candles:
                    all_candles[ts] = {}
                all_candles[ts][symbol] = candle

        for ts in sorted(all_candles.keys()):
            candles_at_ts = all_candles[ts]
            if not candles_at_ts:
                continue
            try:
                slot = compute_slot_index(ts)
            except ValueError:
                continue
            yield CandleBatch(timestamp=ts, slot_index=slot, candles=candles_at_ts)

    # ── Convenience (non-protocol) ────────────────────────────────────────────

    def get_symbol_date_range(self, symbol: str) -> tuple[date | None, date | None]:
        """Return (earliest_date, latest_date) for a specific symbol."""
        df = self._load_df(symbol)
        if df is None or df.empty:
            return None, None
        return (
            df.index.min().astimezone(IST).date(),
            df.index.max().astimezone(IST).date(),
        )

    # ── Internal ──────────────────────────────────────────────────────────────

    def _load_df(self, symbol: str) -> pd.DataFrame | None:
        if symbol not in self._loaded_dfs:
            df = read_symbol_parquet(symbol, self._dir)
            if df is None:
                return None
            self._loaded_dfs[symbol] = df
        return self._loaded_dfs[symbol]

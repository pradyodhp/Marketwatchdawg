"""Unit tests for ParquetDataProvider (fully offline, no network calls)."""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd

from marketwatch.models.candle import Candle, CandleBatch

IST = ZoneInfo("Asia/Kolkata")
T0 = datetime(2024, 1, 15, 9, 15, tzinfo=IST)
T1 = datetime(2024, 1, 15, 9, 20, tzinfo=IST)
T2 = datetime(2024, 1, 15, 9, 25, tzinfo=IST)
T3 = datetime(2024, 1, 16, 9, 15, tzinfo=IST)


def _make_df(*timestamps, open_=100.0, high=102.0, low=99.0, close=101.0, vol=50000.0):
    rows = [{"Open": open_, "High": high, "Low": low, "Close": close, "Volume": vol}
            for _ in timestamps]
    idx = pd.DatetimeIndex(list(timestamps), name="Datetime", tz="Asia/Kolkata")
    return pd.DataFrame(rows, index=idx)


def _seed_provider(tmp_path, symbol_data: dict, metadata: dict | None = None):
    """Write Parquet files + optional metadata, return ParquetDataProvider."""
    from marketwatch.ingestion.parquet_store import (
        write_quality_metadata,
        write_symbol_parquet,
    )
    from marketwatch.providers.parquet_provider import ParquetDataProvider

    for symbol, df in symbol_data.items():
        write_symbol_parquet(symbol, df, curated_dir=tmp_path)

    if metadata is not None:
        write_quality_metadata(metadata, curated_dir=tmp_path)

    return ParquetDataProvider(curated_dir=tmp_path)


class TestParquetDataProvider:
    def test_get_candles_yields_typed_candles(self, tmp_path):
        provider = _seed_provider(tmp_path, {"HDFC.NS": _make_df(T0, T1, T2)})
        candles = list(provider.get_candles("HDFC.NS"))
        assert len(candles) == 3
        assert all(isinstance(c, Candle) for c in candles)

    def test_get_candles_chronological_order(self, tmp_path):
        provider = _seed_provider(tmp_path, {"HDFC.NS": _make_df(T2, T0, T1)})
        candles = list(provider.get_candles("HDFC.NS"))
        timestamps = [c.timestamp for c in candles]
        assert timestamps == sorted(timestamps)

    def test_get_candles_missing_symbol_yields_nothing(self, tmp_path):
        from marketwatch.providers.parquet_provider import ParquetDataProvider
        provider = ParquetDataProvider(curated_dir=tmp_path)
        candles = list(provider.get_candles("NOSUCHSYMBOL.NS"))
        assert candles == []  # no fabrication

    def test_get_candles_date_filter_start(self, tmp_path):
        provider = _seed_provider(tmp_path, {"HDFC.NS": _make_df(T0, T3)})
        candles = list(provider.get_candles("HDFC.NS", start=date(2024, 1, 16)))
        assert len(candles) == 1
        assert candles[0].timestamp.date() == date(2024, 1, 16)

    def test_get_candles_date_filter_end(self, tmp_path):
        provider = _seed_provider(tmp_path, {"HDFC.NS": _make_df(T0, T3)})
        candles = list(provider.get_candles("HDFC.NS", end=date(2024, 1, 15)))
        assert len(candles) == 1
        assert candles[0].timestamp.date() == date(2024, 1, 15)

    def test_candle_fields_correct(self, tmp_path):
        provider = _seed_provider(tmp_path, {"INFY.NS": _make_df(T0, open_=1500.0, high=1520.0, low=1490.0, close=1510.0, vol=200000.0)})
        candles = list(provider.get_candles("INFY.NS"))
        c = candles[0]
        assert c.symbol == "INFY.NS"
        assert c.open == 1500.0
        assert c.high == 1520.0
        assert c.low == 1490.0
        assert c.close == 1510.0
        assert c.volume == 200000.0
        assert c.slot_index == 0  # 09:15

    def test_candle_ist_timezone(self, tmp_path):
        provider = _seed_provider(tmp_path, {"TEST.NS": _make_df(T0)})
        candles = list(provider.get_candles("TEST.NS"))
        assert str(candles[0].timestamp.tzinfo) == "Asia/Kolkata"

    def test_stream_batches_synchronized(self, tmp_path):
        df_a = _make_df(T0, T1)
        df_b = _make_df(T0, T2)   # T0 shared, T1 only A, T2 only B
        provider = _seed_provider(tmp_path, {"A.NS": df_a, "B.NS": df_b})
        batches = list(provider.stream_batches(["A.NS", "B.NS"]))
        # Timestamps: T0, T1, T2
        timestamps = [b.timestamp for b in batches]
        assert len(timestamps) == 3
        assert timestamps == sorted(timestamps)
        # T0 batch should have both symbols
        t0_batch = next(b for b in batches if b.timestamp == T0)
        assert "A.NS" in t0_batch
        assert "B.NS" in t0_batch
        # T1 batch — only A
        t1_batch = next(b for b in batches if b.timestamp == T1)
        assert "A.NS" in t1_batch
        assert "B.NS" not in t1_batch

    def test_stream_batches_typed(self, tmp_path):
        provider = _seed_provider(tmp_path, {"TEST.NS": _make_df(T0, T1)})
        batches = list(provider.stream_batches(["TEST.NS"]))
        assert all(isinstance(b, CandleBatch) for b in batches)

    def test_stream_batches_slot_index_correct(self, tmp_path):
        provider = _seed_provider(tmp_path, {"TEST.NS": _make_df(T0, T1)})
        batches = list(provider.stream_batches(["TEST.NS"]))
        assert batches[0].slot_index == 0   # T0 = 09:15 → slot 0
        assert batches[1].slot_index == 1   # T1 = 09:20 → slot 1

    def test_stream_batches_missing_symbol_skipped(self, tmp_path):
        provider = _seed_provider(tmp_path, {"A.NS": _make_df(T0)})
        batches = list(provider.stream_batches(["A.NS", "MISSING.NS"]))
        assert len(batches) == 1
        assert "MISSING.NS" not in batches[0]

    def test_get_quality_metadata_with_metadata_file(self, tmp_path):
        meta = {
            "requested_symbols": ["A.NS", "B.NS"],
            "loaded_symbols": ["A.NS"],
            "missing_symbols": ["B.NS"],
            "coverage_pct": 50.0,
            "date_range_start": "2024-01-15T09:15:00+05:30",
            "date_range_end": "2024-01-16T15:25:00+05:30",
        }
        provider = _seed_provider(tmp_path, {"A.NS": _make_df(T0)}, metadata=meta)
        qm = provider.get_quality_metadata()
        assert qm.source_type == "offline_parquet"
        assert qm.coverage_percentage == 50.0
        assert "B.NS" in qm.missing_bars_summary  # B.NS recorded as missing symbol
        assert qm.loaded_symbols_count == 1
        assert qm.total_symbols_count == 2

    def test_get_quality_metadata_without_file(self, tmp_path):
        from marketwatch.providers.parquet_provider import ParquetDataProvider
        provider = ParquetDataProvider(curated_dir=tmp_path)
        qm = provider.get_quality_metadata()
        assert qm.source_type == "offline_parquet"
        assert qm.coverage_percentage == 0.0

    def test_get_date_range(self, tmp_path):
        provider = _seed_provider(tmp_path, {"HDFC.NS": _make_df(T0, T3)})
        start, end = provider.get_symbol_date_range("HDFC.NS")
        assert start == date(2024, 1, 15)
        assert end == date(2024, 1, 16)

    def test_get_date_range_missing_returns_none(self, tmp_path):
        from marketwatch.providers.parquet_provider import ParquetDataProvider
        provider = ParquetDataProvider(curated_dir=tmp_path)
        start, end = provider.get_symbol_date_range("MISSING.NS")
        assert start is None
        assert end is None

    def test_protocol_conformance(self, tmp_path):
        """ParquetDataProvider satisfies the MarketDataProvider protocol at runtime."""
        from marketwatch.protocols.provider import MarketDataProvider
        from marketwatch.providers.parquet_provider import ParquetDataProvider
        provider = ParquetDataProvider(curated_dir=tmp_path)
        assert isinstance(provider, MarketDataProvider)

    def test_no_fabrication_on_missing(self, tmp_path):
        """Verify zero fabrication: missing symbol yields zero candles, not fake data."""
        from marketwatch.providers.parquet_provider import ParquetDataProvider
        provider = ParquetDataProvider(curated_dir=tmp_path)
        candles = list(provider.get_candles("FABRICATED.NS"))
        assert candles == []

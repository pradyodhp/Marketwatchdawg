# Phase 2 — Plan 02-01 Summary
# Free Data Ingestion & Curated Parquet Pipeline

**Executed:** 2026-09-16
**Status:** COMPLETE
**Tests:** 35 new tests + 21 Phase 1 tests = 56/56 passed
**Lint:** ruff clean (0 errors)

## Deliverables

### Source Files Created
- `src/marketwatch/ingestion/__init__.py` — ingestion package
- `src/marketwatch/ingestion/fetcher.py` — yfinance fetcher with exponential backoff (3 retries, 2s→60s)
- `src/marketwatch/ingestion/validator.py` — OHLCV validator: positive prices, OHLC bounds, IST normalization, 09:15-15:30 trading hours, duplicate deduplication, zero-volume flagging
- `src/marketwatch/ingestion/parquet_store.py` — Parquet read/write layer (snappy compression, typed schema, IST-aware index)
- `src/marketwatch/providers/__init__.py` — providers package
- `src/marketwatch/providers/parquet_provider.py` — ParquetDataProvider: implements MarketDataProvider protocol, get_symbols(), get_date_range(), get_quality_metadata(), get_candles(), stream_batches()
- `scripts/ingest_data.py` — CLI ingestion entrypoint with --benchmarks-only, --dry-run, --symbols overrides

### Dataset Created
- Location: `data/curated/` (108 Parquet files + quality_metadata.json)
- Symbols: 108/111 NIFTY 100 equities + 11 benchmarks (97.3% coverage)
- Missing: LTIM.NS, TATAMOTORS.NS, ZOMATO.NS (yfinance returned empty — NOT fabricated)
- Date range: 2026-06-25 to 2026-09-16 (58 trading days)
- Total rows: 462,875
- File size: 12.7 MB
- Format: Snappy-compressed Parquet, pyarrow schema, Asia/Kolkata timestamp index

### Tests Created
- `tests/test_ingestion.py` — 18 tests: validator (11) + parquet store (7)
- `tests/test_parquet_provider.py` — 17 tests: ParquetDataProvider get_candles, stream_batches, quality metadata, date range, protocol conformance, no-fabrication guarantee

## Success Criteria Verification

1. PASS — Ingestion ran with exponential backoff; 108/111 symbols downloaded; missing symbols logged explicitly; zero fabrication confirmed
2. PASS — quality_metadata.json written with loaded_symbols, missing_symbols, coverage_pct, date_range_start, date_range_end, generated_at
3. PASS — ParquetDataProvider reads 100% offline, yields typed Candle objects, satisfies MarketDataProvider protocol at runtime

## Key Decisions Made

- D-P2-01: yfinance period="60d" interval="5m", 1s inter-symbol delay, exponential backoff
- D-P2-02: One Parquet file per symbol in data/curated/; safe file naming (^ -> _CARET_, . -> _)
- D-P2-03: quality_metadata.json in data/curated/ with full symbol-level coverage map
- D-P2-04: Missing/failed symbols recorded in metadata; no fabrication; no silent substitution
- D-P2-05: ParquetDataProvider satisfies MarketDataProvider structurally (runtime_checkable protocol)
- D-P2-06: All tests use in-memory synthetic fixtures; zero network calls in test suite

## Limitations

- LTIM.NS, TATAMOTORS.NS, ZOMATO.NS returned empty from yfinance free tier (rate limit / delisted).
  These are recorded in quality_metadata.json as missing_symbols. Phase 3 ParquetDataProvider
  will simply yield zero candles for these symbols (no fabrication).
- yfinance free 5-minute data covers ~58 trading days (not always a full 60 due to holidays and
  partial current day). This is the maximum available from the free API.

## Phase 3 Readiness

ParquetDataProvider is ready to be consumed by the Phase 3 Replay Engine:
- get_symbols() returns available symbols list
- get_candles(symbol, start, end) yields Candle objects in chronological IST order
- stream_batches(symbols, start, end) yields synchronized CandleBatch objects by timestamp
- All candles pass Candle model validation (IST tz, slot_index 0..74, OHLC invariants)

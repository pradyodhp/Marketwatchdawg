---
phase: 01-project-scaffolding-nifty-100-specification
plan: 01
subsystem: scaffolding
tags: [pydantic-v2, hatchling, python310, nifty100, protocols, pytest]

requires: []
provides:
  - PEP 621 packaging with hatchling and editable install
  - Declarative NIFTY 100 universe config with 100 constituents and benchmark index mappings
  - Application runtime settings loader with YAML and MARKETWATCH_* environment variable overrides
  - Immutable Pydantic v2 domain models (Candle, CandleBatch, FeatureSet, AnomalySignal, Alert, DataQualityMetadata)
  - Abstract MarketDataProvider protocol with single-ticker and cross-sectional batch generators
  - 21 automated unit tests verifying models, configuration, slot calculations, and invariants
affects:
  - phase-2-ingestion
  - phase-3-replay
  - phase-4-features
  - phase-5-detectors
  - phase-6-ml
  - phase-7-scoring
  - phase-8-explainability
  - phase-9-alerts
  - phase-11-api
  - phase-12-dashboard

tech-stack:
  added: [hatchling, pydantic, pydantic-settings, pyyaml, pytest, pyarrow, pandas, numpy]
  patterns:
    - Immutable Pydantic v2 value objects with frozen=True and extra="forbid"
    - Strict financial invariants (OHLC bounds, positive prices, non-negative volume)
    - Timezone normalization to Asia/Kolkata with 5-minute diurnal slot indexing (0..74)
    - Declarative universe JSON configuration with fallback to ^NSEI
    - Synchronous typing.Protocol interface for decoupled market data replay

key-files:
  created:
    - pyproject.toml
    - requirements.txt
    - README.md
    - configs/universe_nifty100.json
    - configs/settings.yaml
    - src/marketwatch/__init__.py
    - src/marketwatch/config/__init__.py
    - src/marketwatch/config/universe.py
    - src/marketwatch/config/settings.py
    - src/marketwatch/models/__init__.py
    - src/marketwatch/models/candle.py
    - src/marketwatch/models/features.py
    - src/marketwatch/models/signals.py
    - src/marketwatch/models/alerts.py
    - src/marketwatch/models/metadata.py
    - src/marketwatch/protocols/__init__.py
    - src/marketwatch/protocols/provider.py
    - tests/conftest.py
    - tests/test_domain_models.py
    - tests/test_universe_config.py
  modified: []

key-decisions:
  - "D-01: Single unified configs/universe_nifty100.json with broad benchmark (^NSEI), sector benchmark mappings, and 100 constituent equities"
  - "D-02: Explicit yfinance symbol string with base symbol stored alongside metadata"
  - "D-03: Fallback to ^NSEI when an equity's sector lacks a dedicated benchmark index"
  - "D-04: Strict Pydantic v2 validation enforcing unique symbols, non-empty sector tags, valid benchmark references, and trading hours (09:15–15:30 IST)"
  - "D-05: Aware datetime normalized to Asia/Kolkata (IST) with 5m slot index 0..74"
  - "D-06: Standard float (float64) for prices, returns, ratios, and scores for zero-copy NumPy/Pandas interoperability"
  - "D-07: Immutable domain models (frozen=True) with extra='forbid'"
  - "D-08: Strict model-level validation on Candle (high >= max(open, close), low <= min(open, close), volume >= 0, positive prices)"
  - "D-09: Synchronous typing.Protocol interface for MarketDataProvider"
  - "D-10: Cross-sectional batch method stream_batches() -> Iterator[CandleBatch] alongside get_candles(symbol)"
  - "D-11: Sparse dictionary mapping symbol -> Candle within CandleBatch omitting missing tickers"
  - "D-12: Mandatory lifecycle and metadata methods on MarketDataProvider protocol"
  - "D-13: Modern src-layout (src/marketwatch/...)"
  - "D-14: hatchling build-backend in pyproject.toml"
  - "D-15: pyproject.toml optional-dependencies with root requirements.txt (-e .)"
  - "D-16: pydantic-settings BaseSettings loading configs/settings.yaml with MARKETWATCH_* overrides"

patterns-established:
  - "Pattern 1: Immutable Domain Core — all models inherit BaseModel with frozen=True, extra='forbid', finite float assertions"
  - "Pattern 2: NSE Time Alignment — 75 slots per trading day (09:15 to 15:30 IST), helper properties for slot_index and trading_date"
  - "Pattern 3: Sparse Cross-Sectional Batches — missing tickers are omitted rather than fabricated with zero/carried-over values"
  - "Pattern 4: Decoupled Data Providers — MarketDataProvider Protocol allows zero-dependency mock testing and offline Parquet streaming"

requirements-completed:
  - DATA-01
  - DATA-02

duration: 12min
completed: 2026-09-15
---

# Phase 1: Project Scaffolding & NIFTY 100 Specification Summary

**Established production-grade Python packaging, declarative NIFTY 100 universe specification, runtime configuration loaders, immutable Pydantic v2 domain models with 75-slot IST diurnal calculation, and abstract MarketDataProvider protocol with 100% passing automated test suite.**

## Performance

- **Tasks:** 6 completed
- **Files created:** 20 files
- **Automated tests:** 21 passed (0.13s execution time)

## Accomplishments

1. **Packaging & Scaffolding:** Configured PEP 621 `pyproject.toml` with `hatchling` build backend and `src/marketwatch` layout. Successfully installed in editable mode (`pip install -e .`).
2. **NIFTY 100 Universe Specification:** Created `configs/universe_nifty100.json` specifying 100 liquid Indian equities with `.NS` tickers, broad market benchmark `^NSEI`, 11 sector index mappings (`^NSEBANK`, `^CNXIT`, `^CNXAUTO`, etc.), and fallback to `^NSEI`.
3. **Configuration Schemas & Loaders:** Implemented `UniverseConfig` and `Settings(BaseSettings)` in `src/marketwatch/config/` validating constituent uniqueness, 75 slots/day, sector links, and environment variable overrides (`MARKETWATCH_*`).
4. **Immutable Domain Models:** Implemented `Candle`, `CandleBatch`, `FeatureSet`, `AnomalySignal`, `Alert`, and `DataQualityMetadata` with strict immutability (`frozen=True`, `extra="forbid"`), strict financial invariants (`high >= max(open, close)`, `low <= min(open, close)`, `volume >= 0`), `float64` compatibility, and `Asia/Kolkata` slot calculation (`0..74`).
5. **Market Data Protocol:** Created `@runtime_checkable` `MarketDataProvider` protocol decoupling data ingestion/replay from surveillance algorithms.
6. **Automated Test Suite:** Created 21 unit tests across `tests/test_domain_models.py` and `tests/test_universe_config.py` verifying all domain constraints and config loaders.

## Files Created/Modified

- `pyproject.toml` — Declarative PEP 621 packaging metadata and tool configurations.
- `requirements.txt` — Editable installation pointer (`-e .[dev,api,dashboard,ingestion]`).
- `README.md` — Project package summary.
- `configs/universe_nifty100.json` — 100 NIFTY equities with benchmark mappings.
- `configs/settings.yaml` — Default detection thresholds, scoring weights, and directories.
- `src/marketwatch/__init__.py` — Package root exporting `__version__ = "0.1.0"`.
- `src/marketwatch/config/__init__.py` — Configuration exports.
- `src/marketwatch/config/universe.py` — Pydantic schema and loader for universe JSON.
- `src/marketwatch/config/settings.py` — Pydantic BaseSettings loader with env overrides.
- `src/marketwatch/models/__init__.py` — Domain models exports.
- `src/marketwatch/models/candle.py` — `Candle` and `CandleBatch` models with slot indexing.
- `src/marketwatch/models/features.py` — `FeatureSet` scale-invariant feature model.
- `src/marketwatch/models/signals.py` — `AnomalySignal` detector output model.
- `src/marketwatch/models/alerts.py` — `Alert` risk-scored entity with non-manipulation disclaimer.
- `src/marketwatch/models/metadata.py` — `DataQualityMetadata` dataset audit model.
- `src/marketwatch/protocols/__init__.py` — Protocol exports.
- `src/marketwatch/protocols/provider.py` — `MarketDataProvider` interface protocol.
- `tests/conftest.py` — Shared pytest fixtures for candles and IST datetimes.
- `tests/test_domain_models.py` — 16 unit tests for domain models and protocol.
- `tests/test_universe_config.py` — 5 unit tests for universe and settings loaders.

## Decisions Made

Followed all finalized decisions D-01 through D-16 verbatim without modification.

## Deviations from Plan

### Auto-fixed Issues

**1. Settings Loader Environment Variable Merging**
- **Found during:** Task 6 verification (`test_settings_env_override`).
- **Issue:** `Settings.model_validate(raw_data)` did not merge `MARKETWATCH_*` environment variables when loading from a dictionary.
- **Fix:** Implemented deep merge logic in `load_settings()` extracting `MARKETWATCH_*` environment variables and overriding corresponding nested dictionary keys before Pydantic validation.
- **Verification:** `pytest tests/test_universe_config.py -k test_settings_env_override` passed.

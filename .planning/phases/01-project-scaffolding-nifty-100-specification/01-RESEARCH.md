# Phase 1: Project Scaffolding & NIFTY 100 Specification - Research

**Researched:** 2026-09-15
**Domain:** Python packaging, Pydantic v2 domain modeling, Market data protocols, NSE/NIFTY 100 specification
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Single unified JSON file (`configs/universe_nifty100.json`) defining broad benchmark (`^NSEI`), sector benchmark mappings (`^NSEBANK`, `^CNXIT`, `^CNXAUTO`, etc.), and equity objects with ticker, lot size, and sector/industry tags.
- **D-02:** Explicit yfinance symbol string (e.g., `"RELIANCE.NS"`) with base symbol `"RELIANCE"` stored alongside metadata in the config object.
- **D-03:** Fallback to broad market (`^NSEI`) for sector-relative metrics when an equity's sector lacks a dedicated benchmark index.
- **D-04:** Strict Pydantic v2 validation enforcing unique symbols, non-empty sector tags, valid benchmark references, and trading hours (09:15–15:30 IST) at startup.
- **D-05:** Aware `datetime` normalized to `Asia/Kolkata` (IST), with ISO 8601 serialization and helper properties for trading date and 5-minute slot index (`0..74`).
- **D-06:** Standard float (`float64`) for prices, returns, ratios, and scores to ensure zero-copy NumPy/Pandas/Scikit-learn interoperability and high performance.
- **D-07:** Immutable domain models (`frozen=True`) with `extra="forbid"` to guarantee thread-safe replay pipelines and prevent silent schema bugs.
- **D-08:** Strict model-level validation on `Candle` (`high >= max(open, close)`, `low <= min(open, close)`, `volume >= 0`, positive prices) rejecting corrupted bars.
- **D-09:** Synchronous `typing.Protocol` interface (Iterator/Generator yielding `Candle` or `CandleBatch`) for low-overhead local replay, with optional async wrappers if needed by FastAPI.
- **D-10:** Cross-sectional batch method `stream_batches() -> Iterator[CandleBatch]` containing all active tickers at timestamp $t$, alongside single-ticker `get_candles(symbol)`.
- **D-11:** Sparse dictionary mapping `symbol -> Candle` within `CandleBatch`, omitting missing tickers so downstream engines never receive fabricated or zero-filled data.
- **D-12:** Mandatory lifecycle and metadata methods (`get_symbols() -> list[str]`, `get_date_range() -> tuple[datetime, datetime]`, `get_quality_metadata() -> DataQualityMetadata`) defined directly on `MarketDataProvider`.
- **D-13:** Modern src-layout (`src/marketwatch/...`) preventing accidental local module import shadowing and enforcing clean packaging.
- **D-14:** `hatchling` build-backend (PEP 621 compliant, clean declarative packaging with `pyproject.toml`, standard in Python 3.10+).
- **D-15:** `pyproject.toml` optional-dependencies (`[dev]`, `[api]`, `[dashboard]`, `[ingestion]`) with root `requirements.txt` referencing `pyproject.toml` (`-e .`) for one-command installation.
- **D-16:** `pydantic-settings` `BaseSettings` model loading from `configs/settings.yaml` with `MARKETWATCH_*` environment variable overrides and sensible defaults.

### The Agent's Discretion
- Exact directory hierarchy under `src/marketwatch/` (`models/`, `protocols/`, `config/`).
- Specific Pydantic custom validators and property decorators.
- Granular test suites in `tests/` covering domain models, universe configuration, and settings.

### Deferred Ideas (OUT OF SCOPE)
- None — all decisions remain strictly within Phase 1 scope.
</user_constraints>

<architectural_responsibility_map>
## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Domain Models (`Candle`, `FeatureSet`, etc.) | Domain Core (`src/marketwatch/models`) | — | Pure Pydantic v2 value objects with zero IO or external dependencies |
| Abstract Data Protocols (`MarketDataProvider`) | Domain Core (`src/marketwatch/protocols`) | — | Decouples data ingestion and replay from surveillance algorithms |
| Universe & Settings Config Loader | Configuration (`src/marketwatch/config`) | File System (`configs/`) | Declarative JSON/YAML parsing validated with Pydantic v2 schemas |
| Project Packaging & Scaffolding | Tooling / Build (`pyproject.toml`) | — | Modern PEP 621 Hatchling packaging supporting editable installs |
</architectural_responsibility_map>

<research_summary>
## Summary

Phase 1 establishes the bedrock of MarketWatch AI. Under a strict $0 budget and offline execution model, all downstream components (data ingestion, replay streaming, TOD baselines, anomaly detectors, risk scoring, explainability, REST API, and Streamlit UI) communicate exclusively through standardized, immutable domain models and abstract protocols.

Key findings:
1. **Modern Packaging:** Using `pyproject.toml` with `hatchling` and a `src/`-layout provides clean import isolation and allows editable installation (`pip install -e .`).
2. **Pydantic v2 Performance & Immutability:** Pydantic v2 with `model_config = ConfigDict(frozen=True, extra="forbid")` provides immutable value objects with sub-microsecond validation overhead.
3. **IST Timezone & 75-Slot Diurnal Alignment:** Indian market hours run from 09:15 to 15:30 IST (375 trading minutes per day = exactly 75 5-minute bars, indexed `0..74`). Standardizing timestamps to `Asia/Kolkata` with a computed `slot_index` eliminates timezone drift and daylight saving complexities.
4. **NSE Sector Indexing:** NIFTY 100 stocks map to specific sectoral indices (`^NSEBANK`, `^CNXIT`, `^CNXAUTO`, `^CNXENERGY`, `^CNXFMCG`, `^CNXPHARMA`, `^CNXMETAL`, `^CNXREALTY`, `^CNXINFRA`). Equities without a dedicated sectoral index fall back to `^NSEI` (Nifty 50 broad market).
</research_summary>

<standard_stack>
## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **Python** | >=3.10 | Core Runtime | Modern typing (`typing.Protocol`, `|` union syntax), match-case, zoneinfo. |
| **pydantic** | >=2.6.0 | Domain Model Contracts | Fast Rust core, strict schema enforcement, frozen immutability, JSON schema generation. |
| **pydantic-settings** | >=2.2.0 | Settings Management | Type-safe environment variable parsing with YAML/JSON source loading. |
| **pyyaml** | >=6.0.1 | YAML Parser | Safe loading of `configs/settings.yaml`. |
| **hatchling** | >=1.21.0 | Build Backend | Standard PEP 621 declarative build backend for `pyproject.toml`. |

### Supporting (Optional Groups)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **pytest** | >=8.0.0 | Unit Testing | In `[dev]` extra: rigorous automated verification of models, configs, and protocols. |
| **pandas** | >=2.0.0 | Tabular Processing | In core dependencies: DataFrame conversions from/to domain candles. |
| **numpy** | >=1.24.0 | Numerical Operations | In core dependencies: zero-copy float64 array operations. |
</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Directory Structure
```
marketwatchdawg/
├── configs/
│   ├── universe_nifty100.json   # 100 NSE equities + benchmark mappings
│   └── settings.yaml            # Runtime settings & detection thresholds
├── src/
│   └── marketwatch/
│       ├── __init__.py          # Package root & __version__
│       ├── config/
│       │   ├── __init__.py
│       │   ├── settings.py      # BaseSettings for settings.yaml + env
│       │   └── universe.py      # Pydantic schemas for universe config
│       ├── models/
│       │   ├── __init__.py      # Re-exports all domain models
│       │   ├── candle.py        # Candle, CandleBatch, slot_index
│       │   ├── features.py      # FeatureSet
│       │   ├── signals.py       # AnomalySignal, AnomalySeverity
│       │   ├── alerts.py        # Alert, AlertSeverity
│       │   └── metadata.py      # DataQualityMetadata
│       └── protocols/
│           ├── __init__.py
│           └── provider.py      # MarketDataProvider(Protocol)
├── tests/
│   ├── conftest.py              # Shared fixtures
│   ├── test_domain_models.py    # Unit tests for models
│   └── test_universe_config.py  # Unit tests for universe JSON & loader
├── pyproject.toml               # Hatchling build & dependencies
└── requirements.txt             # -e .[dev,api,dashboard,ingestion]
```

### 5-Minute Slot Calculation (0..74)
```python
def compute_slot_index(dt: datetime) -> int:
    dt_ist = dt.astimezone(ZoneInfo("Asia/Kolkata"))
    minutes_from_open = (dt_ist.hour * 60 + dt_ist.minute) - (9 * 60 + 15)
    slot = minutes_from_open // 5
    if slot < 0 or slot >= 75:
        raise ValueError(f"Timestamp {dt_ist} is outside NSE trading hours (09:15 - 15:30 IST)")
    return slot
```
</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

| Capability | Don't Hand-Roll | Use Instead | Why |
|------------|-----------------|-------------|-----|
| Timezone management | Custom UTC offset arithmetic | `zoneinfo.ZoneInfo("Asia/Kolkata")` | Handles leap seconds, historical offsets, standard library native. |
| Schema validation | Custom dictionary type-checking | Pydantic v2 `BaseModel` + `Field` | Vectorized, compile-time/runtime validation with clear error messages. |
| Configuration hierarchy | Manual `os.environ` parsing | `pydantic-settings` | Handles env overrides, type casting, default fallbacks cleanly. |
| Packaging metadata | `setup.py` / `distutils` | `pyproject.toml` (PEP 621) | Modern standard, reproducible, isolated builds. |
</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

1. **Naive Datetime Objects:** Storing datetime without timezone leads to ambiguous comparisons and replay clock drift. Every timestamp must be timezone-aware or explicitly normalized to `Asia/Kolkata`.
2. **Fabricating Missing Ticker Bars:** In cross-sectional batches at timestamp $t$, if a stock did not trade or is halted, do NOT insert synthetic zero-price or carry-forward bars into the raw candle batch. Store a sparse dict (`dict[str, Candle]`) so downstream detectors handle absence explicitly.
3. **Floating Point NaN Leaks:** When calculating ratios or returns, division by zero can produce `NaN` or `Inf`. Pydantic models must forbid or cleanly handle NaN in validation.
4. **Extra Fields Shadowing:** Mutable dictionary access allows typos like `candle.volum` instead of `candle.volume`. Enforce `extra="forbid"` on all Pydantic models.
</common_pitfalls>

<validation_architecture>
## Validation Architecture

### Framework
- **Test Runner:** `pytest >= 8.0.0`
- **Unit Test Files:** `tests/test_domain_models.py`, `tests/test_universe_config.py`
- **Fixtures:** `tests/conftest.py`

### Test Verification Commands
- Quick test command: `pytest tests/test_domain_models.py -q`
- Full test command: `pytest tests/ -v`

### Coverage Goals
- 100% schema validation of all 100 constituents in `configs/universe_nifty100.json`.
- Strict rejection of corrupted candles (`high < low`, `volume < 0`, invalid timestamps).
- Immutability verification (`frozen=True`) preventing runtime field mutation.
- Verified slot indexing (`09:15 -> 0`, `09:20 -> 1`, `15:25 -> 74`).
- Serialization round-trip verification (`model_dump` -> JSON -> `model_validate`).
</validation_architecture>

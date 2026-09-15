# Phase 1: Project Scaffolding & NIFTY 100 Specification - Context

**Gathered:** 2026-09-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Establish clean modular project structure, Pydantic v2 domain models (Candle, CandleBatch, FeatureSet, AnomalySignal, Alert, DataQualityMetadata), abstract MarketDataProvider protocol, and declarative universe configuration for the NIFTY 100 universe and benchmarks. Delivers the foundational types and interfaces for all subsequent phases without implementing live market replay or offline data ingestion logic (which belong to Phases 2 and 3).

</domain>

<decisions>
## Implementation Decisions

### Universe Configuration Structure
- **D-01:** Single unified JSON file (configs/universe_nifty100.json) defining broad benchmark (^NSEI), sector benchmark mappings (e.g., ^NSEBANK, ^CNXIT, ^CNXAUTO), and equity objects with ticker, lot size, and sector/industry tags.
- **D-02:** Explicit yfinance symbol string (e.g., RELIANCE.NS) with base symbol RELIANCE stored alongside metadata in the config object.
- **D-03:** Fallback to broad market (^NSEI) for sector-relative metrics when an equity's sector lacks a dedicated benchmark index.
- **D-04:** Strict Pydantic v2 validation enforcing unique symbols, non-empty sector tags, valid benchmark references, and trading hours (09:15–15:30 IST) at startup.

### Domain Model Design & Validation
- **D-05:** Aware datetime normalized to Asia/Kolkata (IST), with ISO 8601 serialization and helper properties for trading date and 5-minute slot index (0..74).
- **D-06:** Standard float (loat64) for prices, returns, ratios, and scores to ensure zero-copy NumPy/Pandas/Scikit-learn interoperability and high-performance computation.
- **D-07:** Immutable domain models (rozen=True) with extra=forbid to guarantee thread-safe replay pipelines and prevent silent schema bugs.
- **D-08:** Strict model-level validation on Candle (high >= max(open, close), low <= min(open, close), olume >= 0, positive prices) rejecting corrupted bars.

### MarketDataProvider Protocol Contract
- **D-09:** Synchronous 	yping.Protocol interface (Iterator/Generator yielding Candle or CandleBatch) for low-overhead local replay, with optional async wrappers if needed by FastAPI.
- **D-10:** Cross-sectional batch method stream_batches() -> Iterator[CandleBatch] containing all active tickers at timestamp $, alongside single-ticker get_candles(symbol).
- **D-11:** Sparse dictionary mapping symbol -> Candle within CandleBatch, omitting missing tickers so downstream engines never receive fabricated or zero-filled data.
- **D-12:** Mandatory lifecycle and metadata methods (get_symbols() -> list[str], get_date_range() -> tuple[datetime, datetime], get_quality_metadata() -> DataQualityMetadata) defined directly on the MarketDataProvider protocol.

### Project Layout & Packaging
- **D-13:** Modern src-layout (src/marketwatch/...) preventing accidental local module import shadowing and enforcing clean packaging.
- **D-14:** hatchling build-backend (PEP 621 compliant, clean declarative packaging with pyproject.toml, standard in Python 3.10+).
- **D-15:** pyproject.toml optional-dependencies ([dev], [api], [dashboard]) with a root equirements.txt referencing pyproject.toml (-e .) for one-command installation.
- **D-16:** pydantic-settings BaseSettings model loading from configs/settings.yaml with MARKETWATCH_* environment variable overrides and sensible defaults.

### the agent's Discretion
- Exact naming and organization of submodules inside src/marketwatch/ (e.g. src/marketwatch/models/, src/marketwatch/protocols/, src/marketwatch/config/).
- Specific Pydantic v2 field aliases and serialization serializers for JSON string compatibility.
- Unit testing framework setup (pytest) with initial test suites for domain models and config validation.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Core & Requirements
- .planning/PROJECT.md — Core value, constraints, and architecture foundations
- .planning/REQUIREMENTS.md — DATA-01, DATA-02 functional requirements
- .planning/ROADMAP.md — Phase 1 scope, mode, and success criteria

### Architectural & Stack Standards
- .planning/research/ARCHITECTURE.md §2-§4 — Component architecture and data contracts
- .planning/research/STACK.md — Tech stack versions (Python 3.10+, Pydantic v2, Hatchling, PyArrow)

### Target Artifact Specifications
- configs/universe_nifty100.json — Declarative NIFTY 100 universe specification
- configs/settings.yaml — Declarative application settings and risk parameters

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None (Phase 1 is the initial greenfield scaffolding phase).

### Established Patterns
- Pydantic v2 BaseModel with strict type validation, frozen immutability, and explicit schema constraints.
- Python 	yping.Protocol for runtime decoupling of market data sources.

### Integration Points
- src/marketwatch/models/ will be imported by all downstream modules (Phase 2 ingestion, Phase 3 replay, Phase 4 features, Phase 5-6 detectors, Phase 7 scoring, Phase 8 explainability, Phase 9 alerts).
- src/marketwatch/protocols/ defines MarketDataProvider implemented by ParquetDataProvider in Phase 2.
- configs/universe_nifty100.json will be consumed by data pre-fetcher (Phase 2) and replay engine (Phase 3).

</code_context>

<specifics>
## Specific Ideas
- The 75 daily 5-minute slots span exactly 09:15 to 15:30 IST. Helper property slot_index on Candle computes integer 0..74 from timestamp.
- Universe configuration must explicitly map all 100 tickers to broad benchmark ^NSEI and sector benchmarks (^NSEBANK, ^CNXIT, ^CNXAUTO, etc.), falling back to ^NSEI when no sector index exists.
- In CandleBatch, halted or missing tickers are simply absent from the dict, adhering to the never fabricate data rule.

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed strictly within Phase 1 scope.

</deferred>

---

*Phase: 01-project-scaffolding-nifty-100-specification*
*Context gathered: 2026-09-15*

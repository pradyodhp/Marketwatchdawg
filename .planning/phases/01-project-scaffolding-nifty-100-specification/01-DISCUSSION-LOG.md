# Phase 1: Project Scaffolding & NIFTY 100 Specification - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-15
**Phase:** 01-project-scaffolding-nifty-100-specification
**Areas discussed:** Universe Configuration Structure, Domain Model Design & Validation, MarketDataProvider Protocol Contract, Project Layout & Packaging

---

## Universe Configuration Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Single unified JSON | configs/universe_nifty100.json with broad benchmark (^NSEI), sector benchmark mappings, and equity objects with sector/industry tags | ✓ |
| Split configs | universe_nifty100.json for equities and enchmarks.json for broad and sector indices | |
| YAML configuration | configs/universe_nifty100.yaml with human-friendly comments and multi-level hierarchy | |

**User's choice:** Single unified JSON (configs/universe_nifty100.json)
**Notes:** Explicit yfinance symbol string (e.g., RELIANCE.NS) with base symbol stored alongside metadata. Fallback to broad market (^NSEI) when sector lacks dedicated index. Strict Pydantic v2 validation on startup.

---

## Domain Model Design & Validation

| Option | Description | Selected |
|--------|-------------|----------|
| Aware datetime normalized to Asia/Kolkata (IST) | ISO 8601 serialization with trading date and 5m slot index (0..74) helpers | ✓ |
| UTC datetime internally | Conversion to Asia/Kolkata only when presenting or exporting | |
| Naive datetime | Local IST time without timezone overhead | |

**User's choice:** Aware datetime normalized to Asia/Kolkata (IST)
**Notes:** Standard float (loat64) for zero-copy NumPy/Pandas interoperability. Immutable domain models (rozen=True, extra=forbid). Strict model-level validation on Candle (high >= max(open, close), low <= min(open, close), olume >= 0).

---

## MarketDataProvider Protocol Contract

| Option | Description | Selected |
|--------|-------------|----------|
| Synchronous typing.Protocol | Iterator/Generator yielding Candle or CandleBatch for local replay | ✓ |
| Pure async protocol | async/await matching ASGI/FastAPI conventions | |
| Dual protocols | BaseSyncMarketDataProvider and BaseAsyncMarketDataProvider | |

**User's choice:** Synchronous typing.Protocol
**Notes:** Cross-sectional batch method stream_batches() -> Iterator[CandleBatch]. Sparse dictionary mapping symbol -> Candle for missing/halted ticker bars. Mandatory lifecycle/metadata methods (get_symbols, get_date_range, get_quality_metadata).

---

## Project Layout & Packaging

| Option | Description | Selected |
|--------|-------------|----------|
| Modern src-layout (src/marketwatch/...) | Prevents accidental local module import shadowing and enforces clean packaging | ✓ |
| Flat layout (marketwatch/...) | Directly in project root for simpler relative paths | |
| Namespace layout | src/marketwatch/core, src/marketwatch/api, etc. | |

**User's choice:** Modern src-layout (src/marketwatch/...)
**Notes:** hatchling build backend in pyproject.toml. Optional-dependencies ([dev], [api], [dashboard]) with root equirements.txt (-e .). pydantic-settings BaseSettings loading from configs/settings.yaml with MARKETWATCH_* env overrides.

---

## the agent's Discretion

- Exact organization of submodules under src/marketwatch/.
- Specific Pydantic v2 field serializers and validation decorators.
- Initial pytest test suite structure for domain models and config validation.

## Deferred Ideas

None — discussion remained strictly within Phase 1 scope.

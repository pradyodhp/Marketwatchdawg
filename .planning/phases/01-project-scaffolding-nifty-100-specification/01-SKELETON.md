# Walking Skeleton — MarketWatch AI

**Phase:** 1
**Generated:** 2026-09-15

## Capability Proven End-to-End

A consumer can initialize the NIFTY 100 universe configuration, load strict Pydantic v2 domain models (`Candle`, `CandleBatch`, `FeatureSet`, `AnomalySignal`, `Alert`, `DataQualityMetadata`), and query the abstract `MarketDataProvider` interface with zero lookahead bias or live network dependency.

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Runtime & Packaging | Python 3.10+ with `hatchling` and `src/` layout | Clean packaging standard (PEP 621), prevents unbuilt import pollution, editable installs (`pip install -e .`). |
| Domain Models | Pydantic v2 immutable value objects (`frozen=True`, `extra="forbid"`) | High-throughput Rust core, zero mutation bugs during replay, strict financial invariants. |
| Timezone & Slotting | `Asia/Kolkata` (IST) with 75 5m slots (`0..74`) | Eliminates daylight-saving ambiguity; maps exactly to NSE 09:15–15:30 trading day. |
| Data Provider Interface | Synchronous `typing.Protocol` | Zero network overhead for local replay; yields single-symbol and cross-sectional `CandleBatch` slices. |
| Universe Specification | Declarative `configs/universe_nifty100.json` | 100 liquid Indian equities with `.NS` tickers, benchmark index mappings, and fallback to `^NSEI`. |
| Runtime Settings | `pydantic-settings` with `configs/settings.yaml` | Hierarchical configuration with `MARKETWATCH_*` environment variable overrides. |

## Stack Touched in Phase 1

- [x] Project scaffold (`pyproject.toml`, `requirements.txt`, `src/marketwatch/`)
- [x] Universe configuration (`configs/universe_nifty100.json`)
- [x] Runtime settings (`configs/settings.yaml`, `pydantic-settings`)
- [x] Domain models (`Candle`, `CandleBatch`, `FeatureSet`, `AnomalySignal`, `Alert`, `DataQualityMetadata`)
- [x] Abstract protocol definitions (`MarketDataProvider`)
- [x] Automated test suite (`pytest`)

## Out of Scope (Deferred to Later Slices)

- **Phase 2:** Historical yfinance pre-fetch script and offline `ParquetDataProvider` implementation.
- **Phase 3:** Synchronized clock controller, playback state management, and 75-bar replay stream iterator.
- **Phase 4:** Scale-invariant feature calculation, 75-slot TOD diurnal baselines, and anti-contamination logic.
- **Phase 5:** Rolling Z-score and EWMA statistical anomaly detectors.
- **Phase 6:** Multivariate Isolation Forest calibration, persistence, and temporal validation tests.
- **Phase 7:** Transparent 0–100 risk scoring engine and saturation curves.
- **Phase 8:** Regulatory-oriented explainability text generator and non-manipulation disclaimers.
- **Phase 9:** Alert severity tiering, cooldown engine, and active queryable registry.
- **Phase 10:** Interactive Surveillance Controller (deterministic raw candle anomaly injection).
- **Phase 11:** Headless core decoupling verification and FastAPI REST service.
- **Phase 12:** Streamlit + Plotly analyst workstation and presenter demo dashboard.

## Subsequent Slice Plan

Each later phase adds one vertical slice on top of this skeleton without altering its architectural decisions:

- **Phase 2:** Offline Parquet Data Pipeline — downloads 60-day 5m data and implements `ParquetDataProvider`.
- **Phase 3:** Synchronized Replay Engine — streams 5m cross-sectional `CandleBatch` slices across 100 tickers.
- **Phase 4:** Feature Engineering & TOD Baselines — computes relative features and slot-bucketed baselines.
- **Phase 5:** Statistical Anomaly Detectors — emits structured z-score and EWMA `AnomalySignal` records.
- **Phase 6:** Multivariate Isolation Forest — scores compound anomalies on pre-calibrated models.
- **Phase 7:** Transparent 0–100 Risk Scoring — blends detectors into unified risk score.
- **Phase 8:** Surveillance Explainability — generates evidence narratives and disclaimers.
- **Phase 9:** Alert Lifecycle Management — applies cooldowns and manages active alerts.
- **Phase 10:** Surveillance Controller — injects raw candle anomalies into the stream.
- **Phase 11:** Headless Core & FastAPI — exposes surveillance state via REST routes.
- **Phase 12:** Streamlit Analyst Dashboard — renders interactive multi-track charts and controller.

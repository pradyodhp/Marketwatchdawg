# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-09-15)

**Core value:** Empower market surveillance analysts with immediate, explainable, and statistically grounded intelligence on what is abnormal about a stock right now, how abnormal it is, and why it was flagged — without black-box opacity or unsubstantiated claims of manipulation.  
**Current focus:** Phase 1: Project Scaffolding & NIFTY 100 Specification

## Current Position

Phase: 5 of 12 (Statistical Anomaly Detector (Z-Scores & EWMA)) Complete
Plan: 1 of 1 in Phase 5 complete (05-01)
Status: Phase 5 Complete (Ready for Phase 6)
Last activity: 2026-09-17 — Phase 5 executed: rolling z-score detector, EWMA detector, and structured anomaly output contract with explicit anti-leakage safeguards.

Progress: [█████░░░░░] 42%

## Performance Metrics

**Velocity:**
- Total plans completed: 3
- Average duration: ~30 min
- Total execution time: 1.75 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Scaffolding & NIFTY 100 | 1/1 | 15m | 15m |
| 2. Free Data Ingestion | 1/1 | 75m | 75m |
| 3. Replay Engine | 1/1 | 15m | 15m |

**Recent Trend:**
- Last 5 plans: 01-01, 02-01, 03-01
- Trend: Fast & Stable

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Init]: NIFTY 100 is the sole MVP universe with Nifty 50 (`^NSEI`) and sector benchmarks; US100 deferred to v2 via config.
- [Init]: Locally curated Parquet is the runtime source of truth; `yfinance` is strictly an offline pre-fetch tool. Real data policy (never fabricate).
- [Init]: Dataset quality and coverage metadata exposed to API and Dashboard with OFFLINE PARQUET confirmation.
- [Init]: 5-minute candles across 75 daily slots (09:15 to 15:30 IST) for Indian market hours.
- [Init]: Time-of-Day (TOD) 75-slot baselines with anti-contamination protection against anomaly distortion.
- [Init]: Strict temporal separation between pre-replay calibration data and replay evaluation data, with automated leakage tests.
- [Init]: Pure headless core engine in `marketwatch/`; Streamlit and FastAPI are decoupled consumer layers.
- [Init]: Documented, mathematically transparent 0–100 risk scoring with justifiable saturation curves.
- [Init]: Regulatory-oriented surveillance alert text with mandatory non-manipulation disclaimer; removed hard <0.1ms constraint.
- [Init]: Dedicated Surveillance Controller injecting raw candles before feature extraction; SIMULATED flag never bypasses scoring.
- [Init]: Comprehensive 10-area Production Evolution Backlog cleanly separated from MVP.

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Deferred Items

*(none)*

## Session Continuity
 
Last session: 2026-09-16 23:27 IST
Stopped at: Phase 3 executed and verified (Plan 03-01 complete, 94/94 tests passing)
Next step: Phase 4: Feature Engineering & Time-of-Day (TOD) Baselines (`/gsd-plan-phase 4`)

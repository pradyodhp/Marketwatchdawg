# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-09-15)

**Core value:** Empower market surveillance analysts with immediate, explainable, and statistically grounded intelligence on what is abnormal about a stock right now, how abnormal it is, and why it was flagged — without black-box opacity or unsubstantiated claims of manipulation.  
**Current focus:** Phase 1: Project Scaffolding & NIFTY 100 Specification

## Current Position

Phase: 1 of 12 (Project Scaffolding & NIFTY 100 Specification)  
Plan: 0 of 1 in current phase (Plan 01-01 ready to execute)  
Status: Ready to execute  
Last activity: 2026-09-15 — Plan 01-01 generated and verified against requirements DATA-01, DATA-02 and decisions D-01 through D-16.  

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: - min
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Scaffolding & NIFTY 100 | 0/1 | - | - |

**Recent Trend:**
- Last 5 plans: -
- Trend: Stable

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

Last session: 2026-09-15 21:20 IST
Stopped at: Phase 1 planned (01-01 ready to execute)
Resume file: .planning/phases/01-project-scaffolding-nifty-100-specification/01-01-PLAN.md

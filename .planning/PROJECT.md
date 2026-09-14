# MarketWatch AI — Explainable Real-Time Market Surveillance

## What This Is

MarketWatch AI is an explainable market surveillance and behavioral anomaly detection platform designed for compliance teams and quantitative surveillance analysts. Operating on continuous 5-minute equity candles across the NIFTY 100 universe, it monitors trading behavior, detects statistically significant and multivariate abnormal activity relative to historical time-of-day (TOD) baselines, assigns a transparent 0–100 risk score, and generates human-readable evidence-based explanations for every alert.

The system is strictly an analyst decision-support tool for detecting statistical anomalies. It does NOT make legal, fraud, or intent determinations, and explicitly disclaims that an alert establishes market manipulation, misconduct, or fraud.

## Core Value

Empower market surveillance analysts with immediate, explainable, and statistically grounded intelligence on what is abnormal about a stock right now, how abnormal it is, and why it was flagged — without black-box opacity or unsubstantiated claims of manipulation.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] **NIFTY 100 Universe & Benchmark Configuration**: Support the liquid constituents of the NIFTY 100 index with matched broad-market (`^NSEI` / Nifty 50) and sector benchmarks defined in declarative configuration (`configs/universe_nifty100.json`).
- [ ] **Data Robustness & Ingestion Transparency**: Attempt full NIFTY 100 curation via `yfinance` without ever fabricating or silently substituting missing data; report coverage metrics and missing symbols gracefully.
- [ ] **Offline Parquet as Runtime Truth**: Isolate data ingestion behind an abstract `MarketDataProvider` protocol; runtime engine reads strictly from local curated Parquet files with zero live API or network dependencies.
- [ ] **Dataset Quality & Coverage Metadata**: Expose data quality metrics to API and Dashboard (loaded symbols count, coverage percentage, missing data status, date/time range, and confirmation of OFFLINE PARQUET mode).
- [ ] **Deterministic Replay Engine**: In-memory synchronized emission of 5-minute candles across the universe in chronological order (75 bars/day, 09:15 to 15:30 IST), supporting play, pause, resume, step-forward, and variable speed throttling.
- [ ] **Strict Temporal Anti-Leakage**: Enforce strict causal boundaries where state, feature computation, preprocessing/scalers, and detectors at timestamp $t$ have zero access to $t' > t$ or replay-period evaluation data.
- [ ] **Feature Engineering Pipeline**: Computation of scale-invariant price return, volume ratio, Parkinson volatility, and market/sector-relative excess returns per candle.
- [ ] **Time-of-Day (TOD) Baselines & Anti-Contamination**: 75-slot diurnal baselines calibrated per stock to eliminate market open/close false alarms, with protection ensuring anomalous candles do not contaminate baseline distributions.
- [ ] **Statistical Anomaly Detector**: Multi-metric rolling z-scores and EWMA shock detectors producing structured deviation signals with magnitude, ratio, baseline, and severity.
- [ ] **Multivariate Isolation Forest Detector**: Scikit-learn `IsolationForest` trained strictly on pre-replay historical calibration data using scale-invariant relative features.
- [ ] **Mathematically Transparent Signal Fusion**: Documented, configurable 0–100 risk scoring combining statistical deviations, ML scores, and market context via clear saturation curves.
- [ ] **Regulatory-Oriented Surveillance Explainability**: Lightweight, deterministic evidence generation detailing contributing factors and market context, with mandatory non-manipulation disclaimer.
- [ ] **Alert Management & Lifecycle**: Severity tiering (LOW/MEDIUM/HIGH/CRITICAL), per-ticker cooldown windows, and active queryable alert registry.
- [ ] **Surveillance Controller (Deterministic Anomaly Injection)**: Interactive injection modifying raw candles before feature extraction; SIMULATED/INJECTED flag labels events but never alters scoring logic.
- [ ] **Headless Core & FastAPI Service**: Pure Python core domain engine (`marketwatch/`) usable independently, wrapped by FastAPI REST routes with strict Pydantic v2 schemas.
- [ ] **Streamlit + Plotly Analyst Dashboard**: Responsive presentation layer with active alert feed, interactive Plotly charts, data quality indicators, and the Surveillance Controller UI.
- [ ] **Comprehensive Test Suite**: Automated tests covering scale-invariance, temporal anti-leakage, baseline anti-contamination, detector accuracy, and end-to-end injection without shortcuts.

### Out of Scope (MVP)

- **Stock Price Forecasting & Prediction**: Surveillance detects unusual behavior; forecasting prices is algorithmic trading/speculation.
- **Automated Trading Bot Execution**: System provides decision support for human analysts; automated order execution introduces out-of-scope financial risk.
- **Legal/Fraud Claims ("Manipulation Confirmed")**: Statistical outliers warrant investigation; they do not establish legal guilt, fraud, misconduct, or intent.
- **US Equities in MVP**: US100 is deferred; the architecture remains universe-agnostic via configuration.
- **Runtime Live API Dependencies**: Live calls to external APIs during replay are strictly prohibited.
- **Synthetic/Faked Order Book (L2 Depth)**: Real exchange L2 ticks for 100 stocks are not free; synthesizing fake order books ruins institutional credibility.
- **Distributed Infrastructure (Kafka, Spark, Kubernetes, Redis)**: Unnecessary complexity; local vectorized execution and Parquet provide sub-second latency and zero operational failure modes.
- **Paid Cloud / LLM APIs**: Explanations are compiled using deterministic quantitative attribution, ensuring zero latency, zero hallucination, and $0 cost.

## Context

- **Hackathon Delivery**: Scheduled for September 26, 2026.
- **Budget**: Strict $0 constraint. Every tool, dataset, and library must be free and open-source.
- **Market Specifics**: National Stock Exchange of India (NSE). Hours: 09:15 – 15:30 IST (75 5-minute candles per day). Market benchmark: Nifty 50 (`^NSEI`).
- **Financial Semantics**: Adheres to correct microstructure terminology (e.g. "aggressive buying/selling pressure" or "order-flow imbalance" rather than naive "more buyers than sellers").
- **Reliability Strategy**: Curated local Parquet datasets in `data/curated/` guarantee 100% deterministic and instantaneous replay with zero reliance on venue Wi-Fi or API uptime.

## Constraints

- **Budget**: $0 — Only free open-source software and legitimately free data access.
- **Universe**: NIFTY 100 (100 liquid Indian equities + Nifty 50 + sector benchmarks).
- **Intraday Resolution**: 5-minute candles (75 bars/day, 60 days of historical depth).
- **Temporal Leakage**: Strict prohibition of lookahead bias. At time $t$, baseline and detector calculations only consume data available at or prior to $t$.
- **Environment**: Local-first Python 3.10+ execution on Windows/Linux/macOS.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| NIFTY 100 sole MVP universe | Focuses data acquisition and market-specific diurnal models on a single liquid universe; architecture remains universe-agnostic. | — Pending |
| Offline curated Parquet source of truth | Eliminates presentation-day rate-limiting, Wi-Fi crashes, and API downtime while maintaining realistic streaming semantics. | — Pending |
| Transparent data completeness policy | Never fabricate missing market data; report real symbol coverage and handle rate limits gracefully. | — Pending |
| 5-minute intraday candles (75 bars/day) | Mitigates microstructure tick noise, fits within free 60-day limits, guarantees smooth chart rendering. | — Pending |
| Time-of-Day (TOD) baselines (75 slots) | Eliminates false-positive alerts caused by natural 09:15 AM open and 15:25 PM close volume surges. | — Pending |
| Baseline anti-contamination | Prevents extreme anomalous observations from corrupting future baseline estimates. | — Pending |
| Strict calibration vs replay split | ML models, scalers, and baselines train strictly on historical calibration data with zero lookahead into replay. | — Pending |
| Headless core domain engine | Separates business logic from Streamlit and FastAPI; enables CLI, script, and UI execution without coupling. | — Pending |
| Transparent, documented 0–100 risk scoring | Replaces arbitrary weights with documented linear and non-linear saturation curves. | — Pending |
| Regulatory-oriented surveillance alert framing | Avoids claims of "manipulation" or "fraud"; disclaims legal intent; reports objective statistical evidence. | — Pending |
| Raw candle Anomaly Injection | Intercepts stream before feature extraction; SIMULATED flag never bypasses detection or influences scoring logic. | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-09-15 after final pre-implementation refinement*

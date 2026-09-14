# MarketWatch AI — Explainable Real-Time Market Surveillance

## What This Is

MarketWatch AI is an explainable market surveillance and behavioral anomaly detection platform designed for compliance teams and quantitative surveillance analysts. Operating on continuous 5-minute equity candles across the NIFTY 100 universe, it monitors trading behavior, detects statistically significant and multivariate abnormal activity relative to historical time-of-day (TOD) baselines, assigns a transparent 0–100 risk score, and generates human-readable evidence-based explanations for every alert.

## Core Value

Empower market surveillance analysts with immediate, explainable, and statistically grounded intelligence on what is abnormal about a stock right now, how abnormal it is, and why it was flagged — without black-box opacity or unsubstantiated claims of manipulation.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] **NIFTY 100 Universe & Benchmark Configuration**: Support the 100 liquid constituents of the NIFTY 100 index with matched broad-market (`^NSEI` / Nifty 50) and sector benchmarks defined in declarative configuration (`configs/universe_nifty100.json`).
- [ ] **Abstract Market Data Provider**: Isolate data providers behind an abstract `MarketDataProvider` interface; implement an offline-first `ParquetDataProvider` reading locally cached 60-day 5-minute data with zero runtime internet dependency.
- [ ] **Deterministic Replay Engine**: In-memory synchronized emission of 5-minute candles across 100 stocks in chronological order, supporting play, pause, resume, step-forward, and variable speed throttling with zero future temporal leakage.
- [ ] **Feature Engineering Pipeline**: Computation of scale-invariant price return, volume ratio, Parkinson volatility, and market/sector-relative excess returns at each candle $t$.
- [ ] **Time-of-Day (TOD) Aware Baselines**: Stock-specific rolling baselines bucketed by intraday 5-minute slot (75 slots per trading day from 09:15 to 15:30 IST) to eliminate diurnal market open/close false alarms.
- [ ] **Statistical Anomaly Detector**: Multi-metric rolling z-scores and EWMA deviations producing structured anomaly signals with magnitude, ratio, baseline, and severity.
- [ ] **Unsupervised ML Anomaly Detector**: Global scikit-learn `IsolationForest` trained exclusively on scale-invariant relative features without lookahead bias.
- [ ] **Mathematically Transparent Signal Fusion**: Calibrated, weighted scoring engine mapping statistical, ML, and market context signals into an auditable 0–100 risk score with non-linear saturation curves.
- [ ] **Evidence-Based Explainability Engine**: Generation of regulatory-oriented surveillance alert text citing top contributing deviations and market context, with mandatory disclaimer stating that unusual activity does not establish manipulation or misconduct.
- [ ] **Alert Management & Lifecycle**: Alert generation with severity categorization (LOW/MEDIUM/HIGH/CRITICAL), ticker cooldown windows, and deduplication.
- [ ] **Surveillance Controller (Deterministic Anomaly Injection)**: Interactive UI controller allowing presenters to inject raw candle anomalies (volume surge, price gap, volatility blast, combined) directly into the stream before feature extraction.
- [ ] **Headless Core & FastAPI Service**: Pure Python core domain engine (`marketwatch/`) usable independently, wrapped by FastAPI REST routes with strict Pydantic v2 schemas.
- [ ] **Streamlit + Plotly Analyst Dashboard**: Interactive workstation featuring active alert feed, interactive price/volume/volatility charts, anomaly progression timeline, evidence inspection, and the Surveillance Controller UI.
- [ ] **Comprehensive Test Suite**: Automated unit, integration, and edge-case tests covering feature calculation, zero temporal leakage, TOD false positives, scoring, and injection round-trip.

### Out of Scope

- **Stock Price Prediction & Automated Trading**: Explicitly non-predictive; system does not forecast prices or execute orders.
- **Legal/Fraud Adjudication**: System flags statistical anomalies for analyst review; it never declares illegal manipulation, misconduct, or intent.
- **US Equities in MVP**: US100 is deferred; the architecture remains universe-agnostic via configuration for post-hackathon expansion.
- **Live API Dependency during Demo**: Free APIs (yfinance, Twelve Data) are strictly for pre-fetching/caching; live API calls are prohibited in the runtime replay loop.
- **Exchange-Grade Level 2 / Order Book Ticks**: Real exchange L2 order books are not legitimately free for 100 stocks. Faking or synthesizing fake exchange order books is prohibited.
- **Distributed Infrastructure (Kafka, Spark, Kubernetes, Redis)**: Unnecessary complexity; local vectorized pandas/numpy and Parquet provide sub-second latency and zero operational failure modes.
- **Paid Cloud / LLM API Dependencies**: Alert explanations are synthesized dynamically using deterministic quantitative attribution, ensuring zero latency, zero hallucination, and $0 cost.

## Context

- **Hackathon Delivery**: Scheduled for September 26, 2026.
- **Budget**: Strict $0 constraint. Every tool, dataset, and library must be free and open-source.
- **Market Specifics**: Indian National Stock Exchange (NSE). Trading hours: 09:15 – 15:30 IST (75 5-minute candles per day). Market benchmark: Nifty 50 (`^NSEI`).
- **Financial Rigor**: Adheres to strict market microstructure semantics (e.g., "aggressive buying/selling pressure" or "order-flow imbalance" rather than naive "more buyers than sellers").
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
| 5-minute intraday candles (75 bars/day) | Mitigates microstructure tick noise, fits within free 60-day limits, guarantees smooth chart rendering. | — Pending |
| Time-of-Day (TOD) baselines (75 slots) | Eliminates false-positive alerts caused by natural 09:15 AM open and 15:25 PM close volume surges. | — Pending |
| Headless core domain engine | Separates business logic from Streamlit and FastAPI; enables CLI, script, and UI execution without coupling. | — Pending |
| Single shared Isolation Forest on scale-invariant features | Scalable across 100 stocks without training 100 separate models; mathematically sound when inputs are normalized ratios. | — Pending |
| Transparent, documented 0–100 risk scoring | Replaces arbitrary weights with documented linear and non-linear saturation curves. | — Pending |
| Regulatory-oriented surveillance alert framing | Avoids claims of "manipulation" or "fraud"; disclaims legal intent; reports objective statistical evidence. | — Pending |
| Raw candle Anomaly Injection | Intercepts stream before feature extraction to prove the genuine detection pipeline discovers the anomaly. | — Pending |

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
*Last updated: 2026-09-15 after roadmap revision*

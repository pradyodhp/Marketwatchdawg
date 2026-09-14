# MarketWatch AI — Explainable Real-Time Market Surveillance

## What This Is

MarketWatch AI is an explainable market surveillance and behavioral anomaly detection system designed for financial analysts and surveillance teams. Operating on continuous 5-minute equity candles across a ~100-stock universe, it monitors trading behavior, detects statistically significant and multivariate abnormal activity relative to historical time-of-day baselines, assigns a transparent 0–100 risk score, and generates human-readable evidence-based explanations for every alert.

## Core Value

Empower market surveillance analysts with immediate, explainable, and statistically grounded intelligence on what is abnormal about a stock right now, how abnormal it is, and why it was flagged — without black-box opacity or unsubstantiated claims of manipulation.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] **Configurable Universe & Benchmarks**: Support ~100 liquid stocks with matched broad-market (e.g., SPY/NIFTY) and sector benchmark indices defined in external configuration.
- [ ] **Abstract Market Data Provider**: Isolate data providers behind an abstract `MarketDataProvider` interface; implement an offline-first Parquet dataset loader using free historical 5-minute data.
- [ ] **Deterministic Replay Engine**: Sequential emission of 5-minute candles supporting real-time, accelerated, pause/resume, and step-by-step playback with zero future temporal leakage.
- [ ] **Feature Engineering Pipeline**: Computation of scale-invariant price, volume, volatility, and market/sector-relative metrics at each candle $t$.
- [ ] **Time-of-Day (TOD) Aware Baselines**: Stock-specific rolling baselines adjusted for intraday diurnal U-curve volume/volatility effects (e.g., market open/close volume surges).
- [ ] **Statistical Anomaly Detector**: Multi-metric rolling z-scores and EWMA deviations producing structured anomaly signals with magnitude and severity.
- [ ] **Unsupervised ML Anomaly Detector**: Single global scikit-learn `IsolationForest` trained on scale-invariant relative features without lookahead bias.
- [ ] **Signal Fusion & Transparent Risk Scoring**: Rule-guided, weighted composite scoring engine mapping statistical, ML, and market context signals into a justified 0–100 risk score.
- [ ] **Explainability Engine**: Generation of structured, natural-language evidence summaries highlighting top contributing factors and market context without causal overreach.
- [ ] **Alert Management & Lifecycle**: Alert generation with severity categorization (LOW/MEDIUM/HIGH/CRITICAL), deduplication, and cooldowns.
- [ ] **Surveillance Controller (Deterministic Anomaly Injection)**: Interactive UI controller allowing presenters to inject raw candle anomalies (volume spike, price shock, volatility surge, combined) that flow through the genuine detection pipeline.
- [ ] **FastAPI Backend Services**: Clean REST contracts for health, stock data, replay control, features, signals, and alerts.
- [ ] **Streamlit + Plotly Analyst Dashboard**: Interactive workstation featuring active alert feed, interactive price/volume/volatility charts, anomaly progression timeline, evidence inspection, and the Surveillance Controller.
- [ ] **Comprehensive Test Suite**: Automated unit, integration, and edge-case tests covering feature calculation, leakage prevention, detector accuracy, and injection round-trip.

### Out of Scope

- **Stock Price Prediction & Automated Trading**: Explicitly non-predictive; system does not forecast prices or execute orders.
- **Legal/Fraud Adjudication**: System flags statistical anomalies for analyst review; it never declares illegal manipulation or fraud intent.
- **Paid / Proprietary Data Feeds**: Strictly $0 budget; no Bloomberg, Refinitiv, or paid exchange tick feeds.
- **Exchange-Grade Level 2 / Order Book Ticks**: Real exchange L2 order books are not legitimately free for 100 stocks. Faking or synthesizing fake exchange order books is prohibited.
- **Distributed Streaming Infrastructure (Kafka, Spark, Kubernetes, Redis)**: Unnecessary complexity for local hackathon demo; local vectorized pandas/numpy and Parquet provide superior sub-second speed and zero operational failure modes.
- **Paid Cloud / LLM API Dependencies**: Alert explanations are synthesized dynamically using deterministic, template-driven quantitative attribution, ensuring zero latency, zero hallucination, and $0 cost.

## Context

- **Hackathon Delivery**: Scheduled for September 26, 2026.
- **Budget**: Strict $0 constraint. Every tool, dataset, and library must be free and open-source.
- **Financial Rigor**: Adheres to strict market microstructure semantics (e.g., "aggressive buying/selling pressure" or "order-flow imbalance" rather than naive "more buyers than sellers").
- **Reliability Strategy**: Live API calls during presentations risk rate limits or venue Wi-Fi failure; offline-first curated Parquet files guarantee 100% deterministic and instantaneous replay.

## Constraints

- **Budget**: $0 — Only free open-source software and free data access.
- **Intraday Resolution**: 5-minute candles for the MVP (balances computational efficiency, visualization clarity, and historical availability).
- **Temporal Leakage**: Strict prohibition of lookahead bias. At time $t$, baseline and detector calculations only consume data available at or prior to $t$.
- **Environment**: Local-first Python 3.10+ execution on Windows/Linux/macOS.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 5-minute intraday candles | Mitigates microstructure tick noise, fits within free 60-day limits, guarantees smooth chart rendering. | — Pending |
| Time-of-Day (TOD) baselines | Eliminates false-positive alerts caused by natural market open and close volume surges (U-curve). | — Pending |
| 100-stock universe with sector benchmarks | Delivers comprehensive sector diversity and realistic surveillance scale. | — Pending |
| Offline curated Parquet replay | Eliminates presentation-day rate-limiting, Wi-Fi crashes, and API downtime while maintaining realistic streaming semantics. | — Pending |
| Abstract `MarketDataProvider` interface | Cleanly decouples data ingestion from replay and detection, enabling future live WebSocket feeds without refactoring. | — Pending |
| Single shared Isolation Forest on scale-invariant features | Scalable across 100 stocks without training 100 separate models; mathematically sound when inputs are normalized ratios. | — Pending |
| Quantitative rule-based explanation engine | Generates sub-millisecond, hallucination-free explanations without expensive TreeSHAP or paid LLM APIs. | — Pending |
| Interactive Surveillance Controller | Allows hackathon judges to inject raw market anomalies and observe the end-to-end detection pipeline react in real time. | — Pending |

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
*Last updated: 2026-09-15 after initialization*

# Requirements: MarketWatch AI

**Defined:** 2026-09-15  
**Core Value:** Empower market surveillance analysts with immediate, explainable, and statistically grounded intelligence on what is abnormal about a stock right now, how abnormal it is, and why it was flagged — without black-box opacity or unsubstantiated claims of manipulation.

## v1 Requirements

### Data Management & Ingestion

- [ ] **DATA-01**: System can load and validate universe configuration supporting the liquid constituents of the NIFTY 100 index with matched market (`^NSEI`) and sector benchmarks.
- [ ] **DATA-02**: System provides an abstract `MarketDataProvider` interface decoupling data sources from downstream engines, enabling provider-agnostic expansion.
- [ ] **DATA-03**: System implements an offline-first `ParquetDataProvider` reading curated 60-day 5-minute OHLCV candle datasets from `data/curated/` with zero runtime internet dependency, never fabricating or silently substituting missing data.
- [ ] **DATA-04**: System exposes dataset quality and coverage metadata (loaded symbols count, coverage percentage, missing-data status, timestamp range, and confirmation of offline Parquet source).

### Replay Engine & Streaming

- [ ] **REPL-01**: User can stream synchronized 5-minute candles across the NIFTY universe in sequential order (75 bars per trading day, 09:15 to 15:30 IST).
- [ ] **REPL-02**: User can control replay execution (play, pause, resume, step-forward, and variable speed throttling).
- [ ] **REPL-03**: System guarantees strict causal temporal anti-leakage — state, feature buffers, and detectors at timestamp $t$ have zero access to future data.

### Feature Engineering & Time-of-Day Baselines

- [ ] **FEAT-01**: System computes scale-invariant relative features per candle (log return, volume ratio, Parkinson volatility, market-relative return).
- [ ] **FEAT-02**: System calculates Time-of-Day (TOD) slot-bucketed rolling baselines (75 slots) to eliminate 09:15 AM open and 15:25 PM close diurnal U-curve false alarms.
- [ ] **FEAT-03**: System protects historical and TOD baselines against contamination so anomalous observations do not distort subsequent baseline distributions.
- [ ] **FEAT-04**: System calculates sector-relative and market-relative excess returns against configured benchmark indices or constituent averages.

### Statistical Anomaly Detection

- [ ] **STAT-01**: System calculates multi-metric rolling z-scores for volume, price return, and volatility against TOD baselines.
- [ ] **STAT-02**: System computes exponential moving average (EWMA) deviations for rapid shock detection.
- [ ] **STAT-03**: System emits structured anomaly signals containing current value, baseline, ratio, z-score, and severity tag.

### Machine Learning & Isolation Forest

- [ ] **ML-01**: System trains a global scikit-learn `IsolationForest` exclusively on pre-replay historical calibration data using scale-invariant relative feature vectors, with zero access to replay/evaluation data.
- [ ] **ML-02**: System persists calibrated model artifacts and scaler parameters for deterministic offline inference.
- [ ] **ML-03**: System generates multivariate anomaly scores identifying non-linear compound deviations across features.

### Signal Fusion & Risk Scoring

- [ ] **FUSE-01**: System combines statistical detector signals, ML anomaly scores, and market context into an auditable 0–100 risk score using transparent, documented mathematical formulations.
- [ ] **FUSE-02**: System applies non-linear saturation curves ensuring extreme single-metric shocks (e.g. 8x volume) produce high-risk alerts through genuine pipeline evaluation.
- [ ] **FUSE-03**: System allows transparent adjustment of component weights via declarative configuration (`settings.yaml`).

### Evidence-Based Explainability

- [ ] **EXPL-01**: System generates lightweight, deterministic evidence-based explanations detailing top contributing features without external LLM/API calls.
- [ ] **EXPL-02**: System includes sector and broad-market context in explanations to distinguish idiosyncratic anomalies from macro movements.
- [ ] **EXPL-03**: System appends an auditable evidence schema and explicit disclaimer stating that unusual activity does not establish manipulation, fraud, misconduct, or intent.

### Alert Management & Lifecycle

- [ ] **ALRT-01**: System classifies alerts into structured severity tiers (LOW: 0–49, MEDIUM: 50–69, HIGH: 70–84, CRITICAL: 85–100).
- [ ] **ALRT-02**: System enforces configurable cooldown windows per ticker to prevent alert spam during sustained volatility.
- [ ] **ALRT-03**: System maintains an active in-memory alert registry queryable by symbol, severity, and timestamp.

### Surveillance Controller (Deterministic Anomaly Injection)

- [ ] **CTRL-01**: User can select a target stock and inject controlled anomaly scenarios (Flash Volume Surge, Price Shock, Volatility Blast, Combined).
- [ ] **CTRL-02**: System injects anomalies directly into raw candle data before feature extraction, requiring the entire downstream pipeline to discover the event without scoring shortcuts.
- [ ] **CTRL-03**: System explicitly labels injected events and resulting alerts as "SIMULATED / INJECTED" while guaranteeing the flag never influences anomaly scoring or severity.

### Headless Core & FastAPI Service

- [ ] **API-01**: System encapsulates all surveillance domain logic in a headless, self-contained Python package (`marketwatch/`) usable without web or UI services.
- [ ] **API-02**: System exposes FastAPI REST endpoints for system health, dataset quality metadata, universe info, replay control, and active alert feeds with Pydantic v2 schemas.
- [ ] **API-03**: System provides interactive Swagger/OpenAPI documentation for external client integration.

### Streamlit + Plotly Analyst Dashboard

- [ ] **DASH-01**: User can view a real-time surveillance dashboard with active alert feed, severity badges, replay status, and dataset quality/coverage metadata.
- [ ] **DASH-02**: User can inspect interactive Plotly charts (candlesticks, volume bars, volatility bands, and anomaly markers) for any selected stock.
- [ ] **DASH-03**: User can view structured evidence breakdowns and natural language explanations with the non-manipulation disclaimer.
- [ ] **DASH-04**: Presenter can operate the interactive Surveillance Controller panel to inject anomalies and observe live alert generation.

### Testing & Verification

- [ ] **TEST-01**: Automated test suite verifies mathematical correctness of scale-invariant features and TOD diurnal baselines.
- [ ] **TEST-02**: Automated test verifies zero temporal leakage across calibration, preprocessing, baselines, and replay iterations.
- [ ] **TEST-03**: Automated test verifies baseline anti-contamination (anomalous events do not distort future baselines).
- [ ] **TEST-04**: Automated integration test verifies that an injected 8x volume anomaly produces a CRITICAL alert via the actual scoring pipeline with no special-casing.

## v2 Requirements & Production Evolution Backlog

See full Post-MVP / Production Evolution roadmap section for details:
- **EVOL-01**: Licensed real-time market data feed (trades, quotes, L2 order book, order lifecycle).
- **EVOL-02**: Corporate action adjustments and historical point-in-time universe tracking.
- **EVOL-03**: Persistent alert storage, audit trail, and analyst investigation case management.
- **EVOL-04**: Production MLOps (model registry, automated drift monitoring, retrain triggers).
- **EVOL-05**: Enterprise security, RBAC, CI/CD, and horizontally scalable streaming infrastructure.

## Out of Scope (MVP)

| Feature | Reason |
|---------|--------|
| US100 Equities in MVP | Scope control for Sept 26 hackathon; focus on high-quality NIFTY 100 execution. |
| Stock Price Forecasting & Prediction | Surveillance detects unusual behavior; price forecasting is trading/speculation. |
| Automated Trading Bot Execution | Surveillance is decision support for human analysts; automated execution introduces financial risk. |
| Legal/Fraud Determinations ("Manipulation") | Statistical outliers indicate anomalies for investigation, not legal guilt or proof of market manipulation. |
| Live API Dependency during Demo | Violates offline reliability; venue Wi-Fi drops and rate limits break demos. |
| Synthetic/Faked Level 2 Order Books | Real L2 exchange tick depth for 100 stocks is not freely available; fabricating fake order books ruins institutional credibility. |
| Paid Cloud / Third-Party LLM APIs | Violates strict $0 budget constraint; rule-based quantitative attribution is faster and hallucination-free. |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1 | Pending |
| DATA-02 | Phase 1 | Pending |
| DATA-03 | Phase 2 | Pending |
| DATA-04 | Phase 2 | Pending |
| REPL-01 | Phase 3 | Pending |
| REPL-02 | Phase 3 | Pending |
| REPL-03 | Phase 3 | Pending |
| FEAT-01 | Phase 4 | Pending |
| FEAT-02 | Phase 4 | Pending |
| FEAT-03 | Phase 4 | Pending |
| FEAT-04 | Phase 4 | Pending |
| STAT-01 | Phase 5 | Pending |
| STAT-02 | Phase 5 | Pending |
| STAT-03 | Phase 5 | Pending |
| ML-01 | Phase 6 | Complete |
| ML-02 | Phase 6 | Complete |
| ML-03 | Phase 6 | Complete |
| FUSE-01 | Phase 7 | Complete |
| FUSE-02 | Phase 7 | Complete |
| FUSE-03 | Phase 7 | Complete |
| EXPL-01 | Phase 8 | Complete |
| EXPL-02 | Phase 8 | Complete |
| EXPL-03 | Phase 8 | Complete |
| ALRT-01 | Phase 9 | Complete |
| ALRT-02 | Phase 9 | Complete |
| ALRT-03 | Phase 9 | Complete |
| CTRL-01 | Phase 10 | Complete |
| CTRL-02 | Phase 10 | Complete |
| CTRL-03 | Phase 10 | Complete |
| API-01 | Phase 11 | Complete |
| API-02 | Phase 11 | Complete |
| API-03 | Phase 11 | Complete |
| DASH-01 | Phase 12 | Pending |
| DASH-02 | Phase 12 | Pending |
| DASH-03 | Phase 12 | Pending |
| DASH-04 | Phase 12 | Pending |
| TEST-01 | Phase 4 | Pending |
| TEST-02 | Phase 6 | Complete |
| TEST-03 | Phase 4 | Pending |
| TEST-04 | Phase 10 | Pending |

**Coverage:**
- v1 requirements: 37 total
- Mapped to phases: 37
- Unmapped: 0 ✓

---
*Requirements defined: 2026-09-15*  
*Last updated: 2026-09-17 after Phase 11 completion*

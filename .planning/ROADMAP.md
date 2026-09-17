# Roadmap: MarketWatch AI

## Overview

MarketWatch AI is an explainable, real-time market surveillance and behavioral anomaly detection platform built for the September 26, 2026 hackathon under a strict $0 budget. Operating on continuous 5-minute equity candles across the NIFTY 100 universe with matched broad-market (`^NSEI`) and sector benchmarks, the system executes locally against curated Parquet datasets with zero live API dependencies during presentations. Following a Vertical MVP structure, the roadmap progresses through robust offline data curation, synchronized 75-bar/day replay streaming, time-of-day feature engineering with baseline anti-contamination, dual statistical/ML anomaly detectors with strict temporal isolation, transparent 0–100 risk scoring, regulatory-oriented evidence explanations, and an interactive Streamlit analyst workstation featuring a raw-candle Surveillance Controller for deterministic anomaly injection.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3...): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [x] **Phase 1: Project Scaffolding & NIFTY 100 Specification** - Establish headless domain models, provider-agnostic interfaces, and declarative NIFTY 100 universe configuration.
- [x] **Phase 2: Free Data Ingestion & Curated Parquet Pipeline** - Pre-fetch 60 days of 5m candles for NIFTY 100 via yfinance without data fabrication, reporting coverage and establishing offline Parquet as the sole runtime truth.
- [x] **Phase 3: Deterministic Replay Engine & Stream Architecture** - Implement synchronized 5m candle replay across 100 stocks (75 bars/day, 09:15-15:30 IST) with strict temporal causal boundaries.
- [x] **Phase 4: Feature Engineering & Time-of-Day (TOD) Baselines** - Build scale-invariant relative features, 75-slot diurnal baselines, and baseline anti-contamination protection.
- [x] **Phase 5: Statistical Anomaly Detector (Z-Scores & EWMA)** - Implement multi-metric rolling z-score and EWMA shock detectors producing structured deviation signals.
- [x] **Phase 6: Multivariate Isolation Forest Detector & Temporal Validation** - Train scikit-learn Isolation Forest strictly on pre-replay historical calibration data, verifying zero lookahead leakage with automated tests.
- [x] **Phase 7: Transparent 0–100 Risk Scoring & Signal Fusion** - Mathematically formulated, documented scoring engine combining statistical, ML, and market context signals with saturation curves.
- [x] **Phase 8: Regulatory-Oriented Surveillance Explainability** - Generate lightweight, deterministic evidence summaries citing exact feature deviations, sector context, and mandatory non-manipulation disclaimers.
- [ ] **Phase 9: Alert Engine & Lifecycle Management** - Implement alert severity tiers (LOW/MED/HIGH/CRIT), per-ticker cooldown windows, and active queryable alert registry.
- [ ] **Phase 10: Surveillance Controller (Deterministic Anomaly Injection)** - Build interactive middleware injecting raw candle distortions into the stream to verify genuine pipeline detection without shortcuts.
- [ ] **Phase 11: Headless Core Decoupling & FastAPI Service** - Ensure core engine is completely independent, wrapped cleanly by FastAPI REST routes exposing quality metadata and alert feeds with Pydantic v2 schemas.
- [ ] **Phase 12: Streamlit + Plotly Analyst Dashboard & Hackathon Demo** - Deliver a responsive surveillance UI with active alert feed, multi-track Plotly charts, data quality indicators, and the presenter Surveillance Controller.

---

## Phase Details

### Phase 1: Project Scaffolding & NIFTY 100 Specification
**Goal**: Establish clean modular project structure, Pydantic v2 domain models (`Candle`, `FeatureSet`, `AnomalySignal`, `Alert`, `DataQualityMetadata`), abstract `MarketDataProvider` protocol, and declarative universe configuration for the NIFTY 100 universe and benchmarks.  
**Mode**: mvp  
**Depends on**: Nothing (first phase)  
**Requirements**: DATA-01, DATA-02  
**Success Criteria** (what must be TRUE):
  1. Project installs cleanly in a fresh Python 3.10+ virtual environment with zero missing dependency errors.
  2. Universe configuration file (`configs/universe_nifty100.json`) defines 100 liquid Indian equities with NSE `.NS` tickers, Nifty 50 (`^NSEI`), and sector benchmark mappings.
  3. Domain models and `MarketDataProvider` protocol are strictly universe-agnostic, headless, and support Pydantic v2 serialization.
**Plans**: 1 plan

Plans:
- [x] 01-01: Scaffolding, dependencies, domain models, abstract protocols, and NIFTY 100 universe configs.

### Phase 2: Free Data Ingestion & Curated Parquet Pipeline
**Goal**: Implement an offline data curation pipeline using `yfinance` to pre-fetch 60 days of 5-minute candles for the NIFTY 100 universe and benchmarks. Handle rate limits and missing symbols gracefully without fabricating data, generate data quality/coverage metadata, and save to partitioned Parquet files in `data/curated/` as the sole runtime source of truth.  
**Mode**: mvp  
**Depends on**: Phase 1  
**Requirements**: DATA-03, DATA-04  
**Success Criteria** (what must be TRUE):
  1. Ingestion script executes with rate-limit backoff and downloads 60 days of 5-minute candles for NIFTY 100 tickers, logging real coverage and never fabricating or silently substituting missing data.
  2. Data validator handles missing bars, zero volume intervals, and market holidays gracefully, outputting a `quality_metadata.json` summary (loaded symbols, coverage %, date range).
  3. `ParquetDataProvider` loads local Parquet data into standardized domain `Candle` streams with zero runtime network dependency, operating 100% offline.
**Plans**: 1 plan

Plans:
- [x] 02-01: Historical data pre-fetcher, rate-limiting backoff, data validation, coverage reporting, and `ParquetDataProvider` implementation.

### Phase 3: Deterministic Replay Engine & Stream Architecture
**Goal**: Build a stateful, in-memory replay generator that synchronizes and emits 5-minute candle batches across all 100 NIFTY stocks (75 bars per trading day, 09:15 to 15:30 IST) at timestamp $t$ with play, pause, resume, step-forward, and variable speed throttling, guaranteeing zero lookahead leakage.  
**Mode**: mvp  
**Depends on**: Phase 2  
**Requirements**: REPL-01, REPL-02, REPL-03  
**Success Criteria** (what must be TRUE):
  1. Replay engine emits synchronized 5-minute bars across all 100 NIFTY tickers in chronological order matching NSE trading hours.
  2. Replay execution supports play, pause, resume, step-forward, and variable replay speeds.
  3. Engine strictly forbids access to future data: buffers at timestamp $t$ contain strictly zero information from $t' > t$.
**Plans**: 1 plan

Plans:
- [x] 03-01: Synchronized Replay Engine, clock controller, playback state management, and stream iterator.

### Phase 4: Feature Engineering & Time-of-Day (TOD) Baselines
**Goal**: Build vectorized calculation of scale-invariant features (returns, volume ratios, Parkinson volatility, market-relative excess returns), a 75-slot Time-of-Day (TOD) baseline engine that eliminates diurnal market open/close false alarms, and baseline anti-contamination logic.  
**Mode**: mvp  
**Depends on**: Phase 3  
**Requirements**: FEAT-01, FEAT-02, FEAT-03, FEAT-04, TEST-01, TEST-03  
**Success Criteria** (what must be TRUE):
  1. System computes scale-invariant relative features for any incoming 5-minute candle batch across all 100 tickers.
  2. TOD baseline engine compares current 5-minute bar against historical distribution of identical intraday slots (e.g. Slot 0 = 09:15–09:20).
  3. Baseline anti-contamination logic ensures extreme anomalous observations do not automatically contaminate baseline distributions used for subsequent candles.
  4. Automated unit tests verify that natural 09:15 AM market open and 15:25 PM market close volume surges do NOT produce false anomaly ratios.
**Plans**: 1 plan

Plans:
- [x] 04-01: Scale-invariant feature pipeline, 75-slot TOD baseline engine, anti-contamination logic, and diurnal calibration tests.

### Phase 5: Statistical Anomaly Detector (Z-Scores & EWMA)
**Goal**: Implement statistical anomaly detection calculating rolling z-scores and EWMA deviations per feature against TOD baselines, outputting structured deviation signals with magnitude, ratio, and severity.  
**Mode**: mvp  
**Depends on**: Phase 4  
**Requirements**: STAT-01, STAT-02, STAT-03  
**Success Criteria** (what must be TRUE):
  1. Statistical detector computes z-scores for volume, return, and volatility across all active tickers in <5ms per step.
  2. Detector emits structured `AnomalySignal` records specifying feature, value, baseline, ratio, z-score, and severity.
  3. EWMA detector captures rapid price/volume velocity spikes that standard rolling averages lag behind.
**Plans**: 1 plan

Plans:
- [x] 05-01: Rolling Z-score and EWMA statistical detector implementations with structured signal schemas.

### Phase 6: Multivariate Isolation Forest Detector & Temporal Validation
**Goal**: Implement scikit-learn `IsolationForest` pipeline trained exclusively on scale-invariant relative features from a pre-replay historical calibration window, persisting model artifacts, scoring non-linear compound deviations in real time, and verifying zero temporal leakage with automated tests.  
**Mode**: mvp  
**Depends on**: Phase 5  
**Requirements**: ML-01, ML-02, ML-03, TEST-02  
**Success Criteria** (what must be TRUE):
  1. Calibration script trains `IsolationForest` and scalers strictly on pre-replay historical partition, with zero access to replay/evaluation data.
  2. Calibrated model and scalers persist to disk and load deterministically at application startup.
  3. Detector scores multi-feature vectors in real time, successfully flagging multi-signal anomalies that univariate detectors miss.
  4. Automated temporal leakage test verifies that model training, scalers, baselines, and inference at timestamp $t$ contain zero data from $t' > t$.
**Plans**: 1 plan

Plans:
- [x] 06-01: Isolation Forest training pipeline, deterministic multivariate scoring engine, and temporal leakage test suite.

### Phase 7: Transparent 0–100 Risk Scoring & Signal Fusion
**Goal**: Design a mathematically transparent, documented scoring engine that blends statistical z-scores, Isolation Forest scores, and sector/market context into an auditable 0–100 risk score using justifiable weights and non-linear saturation curves.  
**Mode**: mvp  
**Depends on**: Phase 6  
**Requirements**: FUSE-01, FUSE-02, FUSE-03  
**Success Criteria** (what must be TRUE):
  1. Fusion engine produces a calibrated 0–100 risk score for every evaluated stock at each time step.
  2. Scoring components, normalization math, saturation functions, and tier thresholds are fully documented in code and architecture docs.
  3. Component weights and thresholds can be adjusted dynamically via `settings.yaml` without changing code.
**Plans**: 1 plan

Plans:
- [x] 07-01: Transparent scoring mathematics, bounded detector fusion, severity mapping, and structured risk assessment contract.

### Phase 8: Regulatory-Oriented Surveillance Explainability
**Goal**: Build a lightweight, deterministic quantitative explanation engine that synthesizes feature deviations, detector ratios, and sector context into human-readable regulatory-oriented surveillance alert text with mandatory non-manipulation disclaimers.  
**Mode**: mvp  
**Depends on**: Phase 7  
**Requirements**: EXPL-01, EXPL-02, EXPL-03  
**Success Criteria** (what must be TRUE):
  1. Explanation engine generates deterministic evidence summaries with negligible latency relative to the pipeline, without external LLM/API calls.
  2. Summary explicitly details top contributing factors (e.g. *"Volume is 7.8x baseline, price deviation 3.1σ, sector flat (+0.1%)"*).
  3. Every alert explicitly includes a disclaimer stating that unusual activity does not establish manipulation, fraud, misconduct, or intent.
**Plans**: 1 plan

Plans:
- [x] 08-01: Deterministic quantitative explanation generator, regulatory framing, and non-manipulation disclaimer compiler.

### Phase 9: Alert Engine & Lifecycle Management
**Goal**: Implement an alert management service that applies severity tiers (LOW, MEDIUM, HIGH, CRITICAL), enforces configurable per-ticker cooldown windows, and maintains an active queryable alert registry.  
**Mode**: mvp  
**Depends on**: Phase 8  
**Requirements**: ALRT-01, ALRT-02, ALRT-03  
**Success Criteria** (what must be TRUE):
  1. Alerts are classified accurately into severity tiers according to risk score thresholds.
  2. Cooldown mechanism prevents duplicate alert flooding for the same ticker across consecutive candles.
  3. In-memory alert registry stores active alerts with filtering by ticker, severity, and timestamp.
**Plans**: 1 plan

Plans:
- [ ] 09-01: Alert state machine, severity tiering, cooldown logic, and active registry.

### Phase 10: Surveillance Controller (Deterministic Anomaly Injection)
**Goal**: Build an interactive injection middleware that modifies raw 5-minute candle data (flash volume surge, price gap, volatility blast, combined) to demonstrate that injected events genuinely travel through the entire detection pipeline without scoring shortcuts.  
**Mode**: mvp  
**Depends on**: Phase 9  
**Requirements**: CTRL-01, CTRL-02, CTRL-03, TEST-04  
**Success Criteria** (what must be TRUE):
  1. Controller allows selecting target ticker, anomaly scenario, and intensity.
  2. Injected distortions mutate raw candle values *before* feature computation, with zero alert-engine shortcutting.
  3. Injected events and resulting alerts are clearly labeled as "SIMULATED / INJECTED" in domain entities, but this flag NEVER alters detection scores or severity.
  4. End-to-end automated test verifies an injected 8x volume surge triggers a CRITICAL alert solely because of genuine scoring pipeline evaluation.
**Plans**: 1 plan

Plans:
- [ ] 10-01: Anomaly injection middleware, scenario generators, labeling, and end-to-end round-trip test.

### Phase 11: Headless Core Decoupling & FastAPI Service
**Goal**: Ensure the entire surveillance engine (`marketwatch/`) is headless and independently runnable without UI/web servers, and wrap it with FastAPI REST routes exposing health, quality metadata, replay control, features, and active alert feeds with strict Pydantic v2 schemas.  
**Mode**: mvp  
**Depends on**: Phase 10  
**Requirements**: API-01, API-02, API-03  
**Success Criteria** (what must be TRUE):
  1. Core surveillance engine runs headlessly from CLI/scripts without requiring FastAPI or Streamlit.
  2. FastAPI application starts cleanly and exposes `/health`, `/quality`, `/stocks`, `/replay`, and `/alerts` endpoints.
  3. All request/response contracts validate against Pydantic v2 models with complete OpenAPI documentation at `/docs`.
**Plans**: 1 plan

Plans:
- [ ] 11-01: Headless engine decoupling verification, FastAPI service integration, quality metadata route, and API tests.

### Phase 12: Streamlit + Plotly Analyst Dashboard & Hackathon Demo
**Goal**: Build a responsive Streamlit analyst workstation (pure presentation layer) featuring live alert tables, interactive Plotly WebGL candlestick/volume/volatility charts, dataset quality indicators, deep-dive explanation panels, and the presenter Surveillance Controller.  
**Mode**: mvp  
**Depends on**: Phase 11  
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04  
**Success Criteria** (what must be TRUE):
  1. Analyst dashboard displays active alert feed with color-coded severity badges, replay controls, and explicit data quality/offline Parquet indicators.
  2. Plotly multi-panel chart renders candlestick price action, volume bars with baseline overlays, and anomaly markers.
  3. Explanation card shows quantitative evidence, sector context, and the non-manipulation disclaimer for the selected stock.
  4. Surveillance Controller panel allows live injection of anomalies during a presentation with instantaneous visual reaction.
**Plans**: 1 plan

Plans:
- [ ] 12-01: Streamlit dashboard application, Plotly financial components, data quality badge, Surveillance Controller panel, and demo guide.

---

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12

| Phase | Mode | Plans Complete | Status | Completed |
|-------|------|----------------|--------|-----------|
| 1. Project Scaffolding & NIFTY 100 Specification | mvp | 1/1 | Complete | 2026-09-15 |
| 2. Free Data Ingestion & Curated Parquet Pipeline | mvp | 1/1 | Complete | 2026-09-16 |
| 3. Deterministic Replay Engine & Stream Architecture | mvp | 1/1 | Complete | 2026-09-16 |
| 4. Feature Engineering & Time-of-Day (TOD) Baselines | mvp | 1/1 | Complete | 2026-09-16 |
| 5. Statistical Anomaly Detector (Z-Scores & EWMA) | mvp | 1/1 | Complete | 2026-09-17 |
| 6. Multivariate Isolation Forest Detector & Temporal Validation | mvp | 1/1 | Complete | 2026-09-17 |
| 7. Transparent 0–100 Risk Scoring & Signal Fusion | mvp | 1/1 | Complete | 2026-09-17 |
| 8. Regulatory-Oriented Surveillance Explainability | mvp | 1/1 | Complete | 2026-09-17 |
| 9. Alert Engine & Lifecycle Management | mvp | 0/1 | Not started | - |
| 10. Surveillance Controller (Deterministic Anomaly Injection) | mvp | 0/1 | Not started | - |
| 11. Headless Core Decoupling & FastAPI Service | mvp | 0/1 | Not started | - |
| 12. Streamlit + Plotly Analyst Dashboard & Hackathon Demo | mvp | 0/1 | Not started | - |

---

## Post-MVP / Production Evolution Backlog

The following capabilities are deliberately excluded from the hackathon MVP to maintain aggressive scope control, zero budget, and zero demo failure points. They form the architectural evolution roadmap for converting MarketWatch AI into an institutional-grade production surveillance platform:

### 1. Licensed Real-Time Market Data Ingestion
- **Direct Exchange Feeds:** Integration with NSE multicast/co-location tick feeds or licensed vendors (Bloomberg B-PIPE, Refinitiv Real-Time, Morningstar) via high-throughput WebSocket / FIX protocol.
- **Microstructure Coverage:** Ingestion of Layer 2 quote depth (bid/ask book), Layer 3 tick-by-tick order lifecycle (order placements, cancellations, modifications), and trade execution direction.

### 2. Corporate Actions & Point-in-Time Universe Management
- **Corporate Action Normalization:** Automated historical price and volume adjustments for stock splits, bonus issues, rights offerings, and cash dividends.
- **Survivorship Bias Mitigation:** Point-in-time universe configuration tracking historical index additions and deletions, preventing lookahead survivor bias during long-term surveillance backtesting.

### 3. Production Data Quality Gates
- **Automated Ingestion Sanity:** Real-time circuit breakers detecting tick drops, stale quotes, inverted bid-ask spreads, and timestamp jitter before ingestion into the feature pipeline.
- **Automated Imputation & Backfill:** Graceful failover between primary and secondary market data feeds.

### 4. Persistent Alert Storage & Immutable Audit Trail
- **Time-Series & Relational Storage:** Deployment of ClickHouse / TimescaleDB for sub-millisecond historical candle retrieval, and PostgreSQL for persistent alert records.
- **Regulatory Audit Logging:** Append-only cryptographic audit logging of every alert, parameter change, and analyst disposition for compliance record-keeping (SEC Rule 17a-4 / SEBI surveillance compliance).

### 5. Analyst Investigation & Case Management Workflow
- **Surveillance Workbench:** Analyst workflow for alert dispositioning (True Positive / False Positive / Escalated), notes recording, and collaborative case reviews.
- **Regulatory Reporting:** One-click export of structured Suspicious Transaction Reports (STRs) / Suspicious Activity Reports (SARs) with complete evidence attachments.

### 6. MLOps, Model Versioning & Drift Monitoring
- **Model Registry:** MLflow / DVC integration for versioning Isolation Forest weights, calibration datasets, and scaler parameters.
- **Concept Drift Detection:** Automated Kolmogorov-Smirnov (KS) testing and Population Stability Index (PSI) monitoring to detect market regime shifts (e.g. low-volatility summer lull to crisis volatility) and trigger automated retraining.

### 7. Formal Quantitative Evaluation & Benchmark Suite
- **Historical Event Testing:** Standardized benchmark evaluation on historical market shock days (e.g. March 2020 COVID crash, Adani short-seller report day, budget announcement days).
- **Analyst-Reviewed Ground Truth:** Benchmark dataset of synthetic and historical anomalies with precision, recall, false discovery rate (FDR), and time-to-detection metrics.

### 8. Enterprise Security, RBAC & Secrets Management
- **Identity & Access Management:** OAuth2 / OpenID Connect (OIDC) integration with Role-Based Access Control (Junior Analyst, Senior Compliance Officer, System Admin).
- **Secrets Management:** Vault / AWS Secrets Manager integration for secure API keys and database credentials; automated TLS certificate rotation.

### 9. Horizontally Scalable Streaming Architecture
- **Distributed Event Streaming:** Apache Kafka / Redpanda streaming layer decoupling exchange ingestion from parallel detection worker pools.
- **Stream Processing:** Apache Flink or Faust stateful streaming workers computing per-stock TOD baselines and feature vectors across 5,000+ equities in parallel.

### 10. CI/CD & Deployment Infrastructure
- **Containerization & Orchestration:** Production Docker multi-stage builds and Helm charts for Kubernetes deployment with auto-scaling worker pods.
- **Automated Testing Gates:** Automated CI pipelines running end-to-end regression tests, temporal leakage checks, and latency benchmarks on every commit.

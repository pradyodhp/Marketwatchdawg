# Roadmap: MarketWatch AI

## Overview

MarketWatch AI is an explainable, real-time market surveillance and behavioral anomaly detection platform built for the September 26, 2026 hackathon under a strict $0 budget. The system operates on continuous 5-minute equity candles across a 100-stock universe with matched market and sector benchmarks. Following a Vertical MVP structure, the roadmap progresses from offline curated data management and deterministic replay streaming, through time-of-day feature engineering and dual statistical/ML anomaly detectors, to transparent 0–100 risk scoring, quantitative natural-language explainability, and an interactive Streamlit analyst dashboard equipped with a live Surveillance Controller for deterministic anomaly injection.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3...): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [ ] **Phase 1: Project Scaffolding & Universe Specification** - Define domain models, abstract interfaces, configuration loader, and 100-stock universe specs.
- [ ] **Phase 2: Free Data Ingestion & Curated Parquet Pipeline** - Build pre-fetching pipeline for 60-day 5m candles, validation, and partitioned Parquet caching.
- [ ] **Phase 3: Deterministic Replay Engine & Stream Architecture** - Implement stateful in-memory replay generator with play/pause/step controls and zero lookahead leakage.
- [ ] **Phase 4: Feature Engineering & Time-of-Day (TOD) Baselines** - Build scale-invariant relative features and diurnal slot-bucketed baselines to eliminate market open/close false alarms.
- [ ] **Phase 5: Statistical Anomaly Detector (Z-Scores & EWMA)** - Implement multi-metric rolling z-score and EWMA shock detectors producing structured deviation signals.
- [ ] **Phase 6: Multivariate Isolation Forest Detector** - Build scikit-learn Isolation Forest pipeline trained on scale-invariant features for non-linear multi-signal detection.
- [ ] **Phase 7: Signal Fusion & 0–100 Risk Scoring** - Blends statistical signals, ML anomaly scores, and market context into a calibrated, weighted 0–100 risk score.
- [ ] **Phase 8: Evidence-Based Explainability Engine** - Generate human-readable quantitative evidence breakdowns citing exact feature deviations and sector context.
- [ ] **Phase 9: Alert Engine & Lifecycle Management** - Implement alert severity tiers (LOW/MED/HIGH/CRIT), ticker cooldown windows, and alert state management.
- [ ] **Phase 10: Surveillance Controller (Deterministic Anomaly Injection)** - Build interactive middleware injecting raw candle anomalies into the stream to verify real pipeline detection.
- [ ] **Phase 11: FastAPI Surveillance Service** - Expose REST endpoints for health, universe metadata, replay control, features, and active alert feeds with Pydantic v2 schemas.
- [ ] **Phase 12: Streamlit + Plotly Analyst Dashboard & Hackathon Demo** - Deliver an interactive surveillance workstation with live alert tables, multi-track Plotly charts, and the presenter Surveillance Controller.

---

## Phase Details

### Phase 1: Project Scaffolding & Universe Specification
**Goal**: Establish clean modular project structure, Pydantic v2 domain models (`Candle`, `FeatureSet`, `AnomalySignal`, `Alert`), abstract `MarketDataProvider` protocol, and declarative universe configuration for 100 stocks and benchmarks.  
**Mode**: mvp  
**Depends on**: Nothing (first phase)  
**Requirements**: DATA-01, DATA-02  
**Success Criteria** (what must be TRUE):
  1. Project installs cleanly in a fresh Python 3.10+ virtual environment with zero missing dependency errors.
  2. Universe configuration files (`universe_us100.json` and `universe_nifty100.json`) load and validate 100 liquid stocks with matched market and sector benchmark tickers.
  3. Domain models serialize and deserialize without schema errors under Pydantic v2.
**Plans**: 1 plan

Plans:
- [ ] 01-01: Scaffolding, dependencies, domain models, abstract protocols, and universe configs.

### Phase 2: Free Data Ingestion & Curated Parquet Pipeline
**Goal**: Implement free data ingestion using `yfinance` to pre-fetch 60 days of 5-minute candles for the 100-stock universe and benchmarks, validate data integrity, and save to partitioned Parquet files in `data/curated/`.  
**Mode**: mvp  
**Depends on**: Phase 1  
**Requirements**: DATA-03  
**Success Criteria** (what must be TRUE):
  1. Ingestion script executes with rate-limit backoff and downloads 60 days of 5-minute candles for 100 stocks and benchmark tickers.
  2. Data validator identifies and handles missing bars, zero volumes, and market closures without corrupting output.
  3. `ParquetDataProvider` loads local Parquet data into standardized domain `Candle` streams with zero network dependency.
**Plans**: 1 plan

Plans:
- [ ] 02-01: Historical data pre-fetcher, data validation/cleaning, and `ParquetDataProvider` implementation.

### Phase 3: Deterministic Replay Engine & Stream Architecture
**Goal**: Build a stateful, in-memory replay generator that synchronizes and emits 5-minute candle batches across all 100 stocks at timestamp $t$ with play, pause, resume, step-forward, and variable speed throttling, guaranteeing zero lookahead leakage.  
**Mode**: mvp  
**Depends on**: Phase 2  
**Requirements**: REPL-01, REPL-02, REPL-03, TEST-02  
**Success Criteria** (what must be TRUE):
  1. Replay engine emits synchronized 5-minute bars across all 100 tickers in chronological order.
  2. Replay execution supports play, pause, resume, step-forward, and variable replay speeds.
  3. Automated test verifies that at timestamp $t$, engine state and buffers contain strictly zero data from $t' > t$.
**Plans**: 1 plan

Plans:
- [ ] 03-01: Synchronized Replay Engine, clock controller, playback state management, and temporal anti-leakage test.

### Phase 4: Feature Engineering & Time-of-Day (TOD) Baselines
**Goal**: Build vectorized calculation of scale-invariant features (returns, volume ratios, Parkinson volatility, market-relative excess returns) and slot-bucketed Time-of-Day (TOD) baselines that eliminate market open/close false alarms.  
**Mode**: mvp  
**Depends on**: Phase 3  
**Requirements**: FEAT-01, FEAT-02, FEAT-03, TEST-01  
**Success Criteria** (what must be TRUE):
  1. System computes scale-invariant relative features for any incoming 5-minute candle batch.
  2. TOD baseline engine compares current 5-minute bar against historical distribution of identical time-of-day slots (e.g. 09:35 AM).
  3. Automated unit tests prove that standard 09:30 AM market open volume surges do NOT produce false anomaly ratios.
**Plans**: 1 plan

Plans:
- [ ] 04-01: Scale-invariant feature pipeline, TOD slot baseline engine, and diurnal calibration tests.

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
- [ ] 05-01: Rolling Z-score and EWMA statistical detector implementations with structured signal schemas.

### Phase 6: Multivariate Isolation Forest Detector
**Goal**: Implement scikit-learn `IsolationForest` pipeline trained exclusively on scale-invariant relative features from a calibration window, persisting model artifacts and scoring non-linear compound deviations in real time.  
**Mode**: mvp  
**Depends on**: Phase 5  
**Requirements**: ML-01, ML-02, ML-03  
**Success Criteria** (what must be TRUE):
  1. Calibration script trains `IsolationForest` on historical training partition without data leakage.
  2. Calibrated model and scalers persist to disk and load deterministically at application startup.
  3. Detector scores multi-feature vectors in real time, successfully flagging multi-signal anomalies that univariate detectors miss.
**Plans**: 1 plan

Plans:
- [ ] 06-01: Isolation Forest training pipeline, artifact persistence, and real-time multivariate scoring engine.

### Phase 7: Signal Fusion & 0–100 Risk Scoring
**Goal**: Design a transparent, configurable scoring engine that blends statistical z-scores, Isolation Forest scores, and sector/market context into an auditable 0–100 risk score using declarative weights and non-linear saturation curves.  
**Mode**: mvp  
**Depends on**: Phase 6  
**Requirements**: FUSE-01, FUSE-02, FUSE-03  
**Success Criteria** (what must be TRUE):
  1. Fusion engine produces a calibrated 0–100 risk score for every evaluated stock at each time step.
  2. Extreme individual shocks (e.g. 8x volume surge) correctly saturate the score into high-risk tiers (>80).
  3. Component weights and thresholds can be adjusted dynamically via `settings.yaml` without changing code.
**Plans**: 1 plan

Plans:
- [ ] 07-01: Signal fusion mathematics, saturation functions, and declarative configuration loader.

### Phase 8: Evidence-Based Explainability Engine
**Goal**: Build a quantitative explanation engine that synthesizes feature deviations, detector ratios, and sector context into human-readable evidence summaries and regulatory-compliant alert text.  
**Mode**: mvp  
**Depends on**: Phase 7  
**Requirements**: EXPL-01, EXPL-02, EXPL-03  
**Success Criteria** (what must be TRUE):
  1. Explanation engine generates natural language evidence summaries in <0.1ms without external LLM API calls.
  2. Summary explicitly details top contributing factors (e.g. *"Volume is 7.8x baseline, price deviation 3.1σ, sector flat (+0.1%)"*).
  3. Mandatory regulatory surveillance disclaimer is appended to every explanation payload.
**Plans**: 1 plan

Plans:
- [ ] 08-01: Template-driven quantitative explanation generator and structured evidence compiler.

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
**Goal**: Build an interactive injection middleware that modifies raw 5-minute candle data (flash volume surge, price gap, volatility blast, combined) to demonstrate that injected events genuinely travel through the entire detection pipeline.  
**Mode**: mvp  
**Depends on**: Phase 9  
**Requirements**: CTRL-01, CTRL-02, CTRL-03, TEST-03  
**Success Criteria** (what must be TRUE):
  1. Controller allows selecting target ticker, anomaly scenario, and intensity.
  2. Injected distortions mutate raw candle values *before* feature computation, with zero alert-engine shortcutting.
  3. Injected events and resulting alerts are clearly labeled as "SIMULATED / INJECTED" in domain entities and logs.
  4. End-to-end automated test verifies an injected 8x volume surge travels through the pipeline and produces a CRITICAL alert.
**Plans**: 1 plan

Plans:
- [ ] 10-01: Anomaly injection middleware, scenario generators, labeling, and end-to-end round-trip test.

### Phase 11: FastAPI Surveillance Service
**Goal**: Expose the surveillance engine via clean REST endpoints for system health, universe metadata, replay execution, stock feature inspection, and active alert feeds with strict Pydantic v2 schemas and interactive OpenAPI docs.  
**Mode**: mvp  
**Depends on**: Phase 10  
**Requirements**: API-01, API-02, API-03  
**Success Criteria** (what must be TRUE):
  1. FastAPI application starts cleanly and exposes `/health`, `/stocks`, `/replay`, and `/alerts` endpoints.
  2. Replay control endpoints (`/replay/start`, `/replay/pause`, `/replay/step`) successfully control the background engine.
  3. All request/response contracts validate against Pydantic v2 models with complete OpenAPI documentation at `/docs`.
**Plans**: 1 plan

Plans:
- [ ] 11-01: FastAPI application setup, modular route controllers, and API integration tests.

### Phase 12: Streamlit + Plotly Analyst Dashboard & Hackathon Demo
**Goal**: Build a responsive Streamlit analyst workstation featuring live alert tables, interactive Plotly WebGL candlestick/volume/volatility charts, deep-dive explanation panels, and the presenter Surveillance Controller.  
**Mode**: mvp  
**Depends on**: Phase 11  
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04  
**Success Criteria** (what must be TRUE):
  1. Analyst dashboard displays active alert feed with color-coded severity badges and instant search/filtering.
  2. Plotly multi-panel chart renders candlestick price action, volume bars with baseline overlays, and anomaly markers.
  3. Explanation card shows quantitative evidence and market context for the selected stock.
  4. Surveillance Controller panel allows live injection of anomalies during a presentation with instantaneous visual reaction.
**Plans**: 1 plan

Plans:
- [ ] 12-01: Streamlit dashboard application, Plotly financial components, Surveillance Controller panel, and demo guide.

---

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12

| Phase | Mode | Plans Complete | Status | Completed |
|-------|------|----------------|--------|-----------|
| 1. Project Scaffolding & Universe Specification | mvp | 0/1 | Not started | - |
| 2. Free Data Ingestion & Curated Parquet Pipeline | mvp | 0/1 | Not started | - |
| 3. Deterministic Replay Engine & Stream Architecture | mvp | 0/1 | Not started | - |
| 4. Feature Engineering & Time-of-Day (TOD) Baselines | mvp | 0/1 | Not started | - |
| 5. Statistical Anomaly Detector (Z-Scores & EWMA) | mvp | 0/1 | Not started | - |
| 6. Multivariate Isolation Forest Detector | mvp | 0/1 | Not started | - |
| 7. Signal Fusion & 0–100 Risk Scoring | mvp | 0/1 | Not started | - |
| 8. Evidence-Based Explainability Engine | mvp | 0/1 | Not started | - |
| 9. Alert Engine & Lifecycle Management | mvp | 0/1 | Not started | - |
| 10. Surveillance Controller (Deterministic Anomaly Injection) | mvp | 0/1 | Not started | - |
| 11. FastAPI Surveillance Service | mvp | 0/1 | Not started | - |
| 12. Streamlit + Plotly Analyst Dashboard & Hackathon Demo | mvp | 0/1 | Not started | - |

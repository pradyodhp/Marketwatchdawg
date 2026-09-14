# Roadmap: MarketWatch AI

## Overview

MarketWatch AI is an explainable, real-time market surveillance and behavioral anomaly detection platform built for the September 26, 2026 hackathon under a strict $0 budget. Operating on continuous 5-minute equity candles across the NIFTY 100 universe with matched broad-market (`^NSEI`) and sector benchmarks, the system executes locally against curated Parquet datasets with zero live API dependencies during presentations. Following a Vertical MVP structure, the roadmap progresses through offline data curation, synchronized 75-bar/day replay streaming, time-of-day feature engineering, dual statistical/ML anomaly detectors, transparent 0–100 risk scoring, regulatory-oriented evidence explanations, and an interactive Streamlit analyst workstation featuring a raw-candle Surveillance Controller for deterministic anomaly injection.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3...): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [ ] **Phase 1: Project Scaffolding & NIFTY 100 Specification** - Establish headless domain models, provider-agnostic interfaces, and declarative NIFTY 100 universe configuration.
- [ ] **Phase 2: Free Data Ingestion & Curated Parquet Pipeline** - Pre-fetch 60 days of 5m candles for NIFTY 100 via yfinance and establish offline Parquet as the runtime source of truth.
- [ ] **Phase 3: Deterministic Replay Engine & Stream Architecture** - Implement synchronized 5m candle replay across 100 stocks (75 bars/day, 09:15-15:30 IST) with zero temporal leakage.
- [ ] **Phase 4: Feature Engineering & Time-of-Day (TOD) Baselines** - Build scale-invariant relative features and 75-slot diurnal baselines to eliminate market open/close false alarms.
- [ ] **Phase 5: Statistical Anomaly Detector (Z-Scores & EWMA)** - Implement multi-metric rolling z-score and EWMA shock detectors producing structured deviation signals.
- [ ] **Phase 6: Multivariate Isolation Forest Detector** - Train scikit-learn Isolation Forest exclusively on scale-invariant features for non-linear multi-signal anomaly detection.
- [ ] **Phase 7: Transparent 0–100 Risk Scoring & Signal Fusion** - Mathematically formulated, documented scoring engine combining statistical, ML, and market context signals with saturation curves.
- [ ] **Phase 8: Regulatory-Oriented Surveillance Explainability** - Generate human-readable evidence summaries citing exact feature deviations, sector context, and non-manipulation disclaimers.
- [ ] **Phase 9: Alert Engine & Lifecycle Management** - Implement alert severity tiers (LOW/MED/HIGH/CRIT), per-ticker cooldown windows, and active alert registry.
- [ ] **Phase 10: Surveillance Controller (Deterministic Anomaly Injection)** - Build interactive middleware injecting raw candle distortions into the stream to verify real pipeline detection.
- [ ] **Phase 11: Headless Core Decoupling & FastAPI Service** - Ensure core engine is completely independent, wrapped cleanly by FastAPI REST routes with Pydantic v2 schemas.
- [ ] **Phase 12: Streamlit + Plotly Analyst Dashboard & Hackathon Demo** - Deliver a responsive surveillance UI with active alert feed, multi-track Plotly charts, and the presenter Surveillance Controller.

---

## Phase Details

### Phase 1: Project Scaffolding & NIFTY 100 Specification
**Goal**: Establish clean modular project structure, Pydantic v2 domain models (`Candle`, `FeatureSet`, `AnomalySignal`, `Alert`), abstract `MarketDataProvider` protocol, and declarative universe configuration for the NIFTY 100 universe and benchmarks.  
**Mode**: mvp  
**Depends on**: Nothing (first phase)  
**Requirements**: DATA-01, DATA-02  
**Success Criteria** (what must be TRUE):
  1. Project installs cleanly in a fresh Python 3.10+ virtual environment with zero missing dependency errors.
  2. Universe configuration file (`configs/universe_nifty100.json`) defines 100 liquid Indian equities with NSE `.NS` tickers, Nifty 50 (`^NSEI`), and sector benchmark mappings.
  3. Domain models and `MarketDataProvider` protocol are strictly universe-agnostic and support Pydantic v2 serialization.
**Plans**: 1 plan

Plans:
- [ ] 01-01: Scaffolding, dependencies, domain models, abstract protocols, and NIFTY 100 universe configs.

### Phase 2: Free Data Ingestion & Curated Parquet Pipeline
**Goal**: Implement an offline data curation pipeline using `yfinance` to pre-fetch 60 days of 5-minute candles for the NIFTY 100 universe and benchmarks, validate data integrity, and save to partitioned Parquet files in `data/curated/` as the sole runtime source of truth.  
**Mode**: mvp  
**Depends on**: Phase 1  
**Requirements**: DATA-03  
**Success Criteria** (what must be TRUE):
  1. Ingestion script executes with rate-limit backoff and downloads 60 days of 5-minute candles for 100 NIFTY stocks and benchmark tickers.
  2. Data validator handles missing bars, zero volume intervals, and market holidays without corrupting output.
  3. `ParquetDataProvider` loads local Parquet data into standardized domain `Candle` streams with zero runtime network dependency.
**Plans**: 1 plan

Plans:
- [ ] 02-01: Historical data pre-fetcher, data validation/cleaning, and `ParquetDataProvider` implementation.

### Phase 3: Deterministic Replay Engine & Stream Architecture
**Goal**: Build a stateful, in-memory replay generator that synchronizes and emits 5-minute candle batches across all 100 NIFTY stocks (75 bars per trading day, 09:15 to 15:30 IST) at timestamp $t$ with play, pause, resume, step-forward, and variable speed throttling, guaranteeing zero lookahead leakage.  
**Mode**: mvp  
**Depends on**: Phase 2  
**Requirements**: REPL-01, REPL-02, REPL-03, TEST-02  
**Success Criteria** (what must be TRUE):
  1. Replay engine emits synchronized 5-minute bars across all 100 NIFTY tickers in chronological order matching NSE trading hours.
  2. Replay execution supports play, pause, resume, step-forward, and variable replay speeds.
  3. Automated test verifies that at timestamp $t$, engine state and buffers contain strictly zero data from $t' > t$.
**Plans**: 1 plan

Plans:
- [ ] 03-01: Synchronized Replay Engine, clock controller, playback state management, and temporal anti-leakage test.

### Phase 4: Feature Engineering & Time-of-Day (TOD) Baselines
**Goal**: Build vectorized calculation of scale-invariant features (returns, volume ratios, Parkinson volatility, market-relative excess returns) and a 75-slot Time-of-Day (TOD) baseline engine that eliminates diurnal market open/close false alarms.  
**Mode**: mvp  
**Depends on**: Phase 3  
**Requirements**: FEAT-01, FEAT-02, FEAT-03, TEST-01  
**Success Criteria** (what must be TRUE):
  1. System computes scale-invariant relative features for any incoming 5-minute candle batch across all 100 tickers.
  2. TOD baseline engine compares current 5-minute bar against historical distribution of identical intraday slots (e.g. Slot 0 = 09:15-09:20).
  3. Automated unit tests prove that natural 09:15 AM market open and 15:25 PM market close volume surges do NOT produce false anomaly ratios.
**Plans**: 1 plan

Plans:
- [ ] 04-01: Scale-invariant feature pipeline, 75-slot TOD baseline engine, and diurnal calibration tests.

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
**Goal**: Implement scikit-learn `IsolationForest` pipeline trained exclusively on scale-invariant relative features from a historical calibration window, persisting model artifacts and scoring non-linear compound deviations in real time.  
**Mode**: mvp  
**Depends on**: Phase 5  
**Requirements**: ML-01, ML-02, ML-03  
**Success Criteria** (what must be TRUE):
  1. Calibration script trains `IsolationForest` on historical training partition without lookahead data leakage.
  2. Calibrated model and scalers persist to disk and load deterministically at application startup.
  3. Detector scores multi-feature vectors in real time, successfully flagging multi-signal anomalies that univariate detectors miss.
**Plans**: 1 plan

Plans:
- [ ] 06-01: Isolation Forest training pipeline, artifact persistence, and real-time multivariate scoring engine.

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
- [ ] 07-01: Transparent scoring mathematics, saturation functions, documentation, and declarative config loader.

### Phase 8: Regulatory-Oriented Surveillance Explainability
**Goal**: Build a quantitative explanation engine that synthesizes feature deviations, detector ratios, and sector context into human-readable regulatory-oriented surveillance alert text with mandatory non-manipulation disclaimers.  
**Mode**: mvp  
**Depends on**: Phase 7  
**Requirements**: EXPL-01, EXPL-02, EXPL-03  
**Success Criteria** (what must be TRUE):
  1. Explanation engine generates natural language evidence summaries in <0.1ms without external LLM API calls.
  2. Summary explicitly details top contributing factors (e.g. *"Volume is 7.8x baseline, price deviation 3.1σ, sector flat (+0.1%)"*).
  3. Every alert explicitly includes a disclaimer stating that unusual activity does not establish manipulation, misconduct, or intent.
**Plans**: 1 plan

Plans:
- [ ] 08-01: Quantitative explanation generator, regulatory framing, and non-manipulation disclaimer compiler.

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

### Phase 11: Headless Core Decoupling & FastAPI Service
**Goal**: Ensure the entire surveillance engine (`marketwatch/`) is headless and independently runnable without UI/web servers, and wrap it with FastAPI REST routes exposing health, replay control, features, and active alert feeds with strict Pydantic v2 schemas.  
**Mode**: mvp  
**Depends on**: Phase 10  
**Requirements**: API-01, API-02, API-03  
**Success Criteria** (what must be TRUE):
  1. Core surveillance engine runs headlessly from CLI/scripts without requiring FastAPI or Streamlit.
  2. FastAPI application starts cleanly and exposes `/health`, `/stocks`, `/replay`, and `/alerts` endpoints.
  3. All request/response contracts validate against Pydantic v2 models with complete OpenAPI documentation at `/docs`.
**Plans**: 1 plan

Plans:
- [ ] 11-01: Headless engine decoupling verification, FastAPI service integration, and API tests.

### Phase 12: Streamlit + Plotly Analyst Dashboard & Hackathon Demo
**Goal**: Build a responsive Streamlit analyst workstation (pure presentation layer) featuring live alert tables, interactive Plotly WebGL candlestick/volume/volatility charts, deep-dive explanation panels, and the presenter Surveillance Controller.  
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
| 1. Project Scaffolding & NIFTY 100 Specification | mvp | 0/1 | Not started | - |
| 2. Free Data Ingestion & Curated Parquet Pipeline | mvp | 0/1 | Not started | - |
| 3. Deterministic Replay Engine & Stream Architecture | mvp | 0/1 | Not started | - |
| 4. Feature Engineering & Time-of-Day (TOD) Baselines | mvp | 0/1 | Not started | - |
| 5. Statistical Anomaly Detector (Z-Scores & EWMA) | mvp | 0/1 | Not started | - |
| 6. Multivariate Isolation Forest Detector | mvp | 0/1 | Not started | - |
| 7. Transparent 0–100 Risk Scoring & Signal Fusion | mvp | 0/1 | Not started | - |
| 8. Regulatory-Oriented Surveillance Explainability | mvp | 0/1 | Not started | - |
| 9. Alert Engine & Lifecycle Management | mvp | 0/1 | Not started | - |
| 10. Surveillance Controller (Deterministic Anomaly Injection) | mvp | 0/1 | Not started | - |
| 11. Headless Core Decoupling & FastAPI Service | mvp | 0/1 | Not started | - |
| 12. Streamlit + Plotly Analyst Dashboard & Hackathon Demo | mvp | 0/1 | Not started | - |

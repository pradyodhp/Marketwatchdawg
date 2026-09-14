# Project Research Summary

**Project:** MarketWatch AI — Explainable Real-Time Market Surveillance  
**Domain:** Quantitative Market Surveillance & Behavioral Anomaly Detection  
**Researched:** 2026-09-15  
**Confidence:** HIGH  

## Executive Summary

MarketWatch AI is an explainable market surveillance platform designed for financial compliance teams and quantitative analysts. Operating on 5-minute equity candles across a ~100-stock universe, it monitors trading behavior, detects statistically abnormal volume and price volatility relative to time-of-day (TOD) baselines, evaluates non-linear multi-signal patterns using scikit-learn's `IsolationForest`, assigns an auditable 0–100 risk score, and delivers evidence-based natural language explanations without black-box opacity.

To satisfy the strict **$0 budget** and ensure flawless reliability during the September 26, 2026 hackathon, the system utilizes an **offline-first curated Parquet architecture**. Rather than depending on fragile, rate-limited free live APIs during the presentation, 60 days of historical 5-minute candles are curated locally. An in-memory **Replay Engine** emits these candles sequentially, simulating a real-time exchange feed with zero lookahead leakage. An interactive **Surveillance Controller** allows presenters or judges to inject raw candle distortions (flash volume surges, volatility spikes, price gaps) that pass through the genuine detection pipeline.

The architecture strictly avoids common pitfalls: diurnal U-curve false alarms at market open are prevented via TOD-slot baselining; ML scale distortion is eliminated by training exclusively on scale-invariant relative features; and regulatory compliance is preserved by reporting objective statistical deviations rather than making unsubstantiated claims of "fraud" or "manipulation".

## Key Findings

### Recommended Stack

The application is built on a lightweight, local-first Python stack with zero paid infrastructure dependencies:

- **Core & Data:** Python 3.10+, `pandas` (>=2.0), `numpy` (>=1.24), `pyarrow` (>=15.0) for high-throughput Parquet storage and vectorized time-series math.
- **Machine Learning:** `scikit-learn` (>=1.3) utilizing `IsolationForest` and `RobustScaler` for multivariate unsupervised outlier detection.
- **Backend & Contracts:** `FastAPI` (>=0.110) with `pydantic` (>=2.6) for typed domain validation, REST endpoints, and WebSocket streaming.
- **Frontend & Visualization:** `Streamlit` (>=1.35) combined with `Plotly` (>=5.20) for interactive financial candlestick charts, baseline bands, and the Surveillance Controller UI.
- **Testing:** `pytest` with fixtures verifying scale-invariance, temporal anti-leakage, and anomaly injection round-trip.

### Expected Features

**Must Have (Table Stakes for MVP):**
- 100-stock universe configuration with matched broad-market and sector benchmarks.
- Curated 5-minute OHLCV Parquet dataset.
- Deterministic Replay Engine with play, pause, resume, and step controls.
- Time-of-Day (TOD) slot-bucketed baselines.
- Multi-metric Statistical Anomaly Detector (Z-scores and EWMA).
- Multivariate Isolation Forest on scale-invariant relative features.
- Transparent Signal Fusion producing a 0–100 Risk Score.
- Quantitative Evidence Explanation Engine (sub-millisecond, hallucination-free).
- Alert Engine with multi-tier severity (LOW/MEDIUM/HIGH/CRITICAL) and cooldowns.
- Surveillance Controller for deterministic raw anomaly injection.
- Streamlit + Plotly Analyst Dashboard with active alert table and multi-track charts.
- Automated test suite covering features, leakage, detectors, and injection.

**Anti-Features (Explicitly Excluded):**
- Stock price prediction or automated trading bots.
- Legal or regulatory claims of "manipulation" or "fraud".
- Synthesized or faked Level 2 order-book ticks.
- Direct alert injection that bypasses the detection pipeline.
- Heavy per-candle TreeSHAP or paid external LLM API calls.

### Architecture Approach

The system follows a clean, decoupled modular design:
1. `MarketDataProvider` abstracts data ingestion.
2. `ReplayEngine` coordinates synchronized 5-minute candle delivery across all 100 stocks.
3. `AnomalyInjector` middleware intercepts raw candles if an anomaly is triggered.
4. `FeaturePipeline` computes returns, volume ratios, and Parkinson volatility.
5. `TODBaselineEngine` retrieves slot-specific historical distributions.
6. `StatisticalDetector` & `IsolationForest` independently score univariate and multivariate deviations.
7. `SignalFusionEngine` blends signals into a 0–100 risk score.
8. `ExplanationEngine` formats the top deviations into human-readable evidence.
9. `AlertEngine` issues deduplicated alerts to the FastAPI backend and Streamlit dashboard.

### Critical Pitfalls

1. **Diurnal U-Curve Blindness:** Solved by comparing 5-minute bars against the same historical time-of-day slots (e.g. 09:35 AM vs trailing 09:35 AM bars).
2. **Temporal Lookahead Leakage:** Solved by strict causal windowing ($X_{\le t}$) and separate calibration vs replay data splits.
3. **Scale Poisoning in Shared ML:** Solved by standardizing all features into stock-relative ratios before feeding to Isolation Forest.
4. **Venue Network Drops & Rate Limits:** Solved by bundling local curated Parquet datasets, requiring zero network access during the pitch.
5. **Direct Alert Injection Cheating:** Solved by mutating raw candle inputs before feature extraction so alerts are genuinely discovered by the ML pipeline.

## Implications for Roadmap

Based on the fine granularity setting (8–12 focused phases), the recommended roadmap decomposes the project into a logical progression:

### Phase 1: Project Scaffolding & Universe Specification
- **Delivers:** Repository structure, dependency configuration (`pyproject.toml`), domain data models (`Candle`, `FeatureSet`, `Alert`), and universe config files (100 liquid stocks + benchmarks).
- **Avoids:** Configuration hardcoding; establishes clear architectural contracts early.

### Phase 2: Free Data Ingestion & Curated Parquet Pipeline
- **Delivers:** Ingestion scripts using `yfinance` to pre-fetch 60 days of 5-minute candles, data hygiene/validation, and partitioned Parquet generation in `data/curated/`.
- **Avoids:** Rate-limit traps, missing data gaps, and venue Wi-Fi failure during presentations.

### Phase 3: Deterministic Replay Engine & Stream Architecture
- **Delivers:** Stateful replay generator emitting synchronized multi-ticker 5-minute bars with play, pause, resume, step, and speed controls.
- **Avoids:** Temporal lookahead leakage; guarantees zero future data leakage.

### Phase 4: Feature Engineering & Time-of-Day (TOD) Baselines
- **Delivers:** Scale-invariant feature calculations (log return, volume ratio, Parkinson volatility, market-relative excess return) and slot-bucketed diurnal baseline engine.
- **Avoids:** Diurnal U-curve false alarms at market open/close.

### Phase 5: Statistical Anomaly Detector (Z-Scores & EWMA)
- **Delivers:** Univariate statistical anomaly engine outputting structured deviation signals with magnitude, ratio, and baseline references.
- **Avoids:** Black-box opacity; provides transparent statistical baselines.

### Phase 6: Multivariate Isolation Forest Detector
- **Delivers:** Calibration/training pipeline on scale-invariant relative features, model persistence, and real-time anomaly scoring.
- **Avoids:** Scale distortion between mega-cap and small-cap tickers.

### Phase 7: Signal Fusion & 0–100 Risk Scoring
- **Delivers:** Configurable weighted fusion engine combining statistical z-scores, Isolation Forest scores, and market context into a unified 0–100 risk score.
- **Avoids:** Arbitrary scoring; establishes clear mathematical saturation curves.

### Phase 8: Explainability Engine & Regulatory Framing
- **Delivers:** Template-driven quantitative explanation generator extracting top contributing features, ratios, and sector context with mandatory surveillance disclaimers.
- **Avoids:** Legal overreach ("manipulation") and high-latency LLM/TreeSHAP calls.

### Phase 9: Alert Engine & Lifecycle Management
- **Delivers:** Alert generator with LOW/MEDIUM/HIGH/CRITICAL thresholds, deduplication, and configurable cooldown windows.
- **Avoids:** Alert fatigue and duplicate notification flooding.

### Phase 10: Surveillance Controller (Deterministic Anomaly Injection)
- **Delivers:** Interactive middleware injecting raw candle distortions (flash volume surge, price shock, volatility blast, combined) into the replay stream.
- **Avoids:** Direct alert cheating; validates that the real pipeline detects injected anomalies.

### Phase 11: FastAPI Surveillance Backend
- **Delivers:** REST routes for health, stocks, replay control, features, and active alerts with comprehensive Pydantic v2 schemas.
- **Avoids:** Monolithic tight coupling; enables decoupled frontend consumption.

### Phase 12: Streamlit + Plotly Analyst Dashboard & Hackathon Demo
- **Delivers:** Multi-panel reactive surveillance workstation with live alert stream, Plotly WebGL candlestick/volume/volatility charts, deep-dive explanation views, and the interactive Surveillance Controller.
- **Avoids:** Cluttered UI; delivers a polished, judge-ready pitch demo.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Python, Pandas, Scikit-learn, FastAPI, Streamlit, and Parquet are industry-proven. |
| Features | HIGH | Feature set strictly matches institutional surveillance practices without unfeasible L2 dependencies. |
| Architecture | HIGH | Decoupled modular architecture guarantees $0 cost, offline execution, and high maintainability. |
| Pitfalls | HIGH | Diurnal curve, leakage, and rate-limit traps are proactively engineered around. |

**Overall confidence:** HIGH

---
*Research completed: 2026-09-15*  
*Ready for roadmap: yes*  

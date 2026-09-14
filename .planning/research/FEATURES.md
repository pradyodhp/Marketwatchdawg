# Feature Research

**Domain:** Financial Market Surveillance & Explainable Anomaly Detection  
**Researched:** 2026-09-15  
**Confidence:** HIGH  

## Feature Landscape

### Table Stakes (Users Expect These)

Features surveillance analysts assume exist in any modern surveillance workstation. Missing these makes the system feel ungrounded.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Multi-Stock Live/Replay Ticker Feed** | Analysts monitor a whole market segment or watchlist at a glance. | MEDIUM | Stream 5-minute candles across 100 stocks simultaneously. |
| **Statistical Anomaly Scores (Z-Scores)** | Standard industry baseline for identifying volume or price volatility deviations. | LOW | Rolling mean and standard deviation per feature, producing normalized deviations. |
| **Multi-Tier Severity Alerts** | Analysts triage high-priority risks first (LOW, MEDIUM, HIGH, CRITICAL). | LOW | Clear classification based on fused risk score thresholds. |
| **Interactive Price & Volume Charts** | Visual inspection is required to confirm whether an anomaly is meaningful. | MEDIUM | Candlestick + volume bar charts with overlayed baseline bands. |
| **Alert History & Filterable Table** | Ability to filter alerts by ticker, severity, anomaly type, and time window. | LOW | Streamlit data table with instant search and sort. |
| **Replay Controls (Play, Pause, Speed)** | Deterministic evaluation of historical events without waiting for market hours. | MEDIUM | Replay speed toggles (1x, 5x, 10x, step-by-step). |

### Differentiators (Competitive Advantage)

Features that set MarketWatch AI apart from naive anomaly detection demos.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Time-of-Day (TOD) Diurnal Baselining** | Solves the classic intraday U-curve problem. Does not flag market open/close surges as anomalies unless anomalous *for that time of day*. | HIGH | Computes baselines bucketed by 5-minute bar slot (e.g. 09:35 AM today vs trailing 09:35 AM bars). |
| **Interactive Surveillance Controller** | Hackathon demo superpower: allows judges to inject raw market anomalies and observe the real detection pipeline trigger. | MEDIUM | Injects raw candle distortions (volume surge, price gap, volatility blast); strictly flows through real feature/detector pipeline. |
| **Hybrid Explainability Engine** | Generates human-readable, evidence-based explanations in <0.1ms without LLM hallucination or heavy TreeSHAP overhead. | MEDIUM | Structured quantitative breakdown: *"Volume 8.2x baseline, price deviation 3.1σ, sector movement +0.2%"*. |
| **Multivariate Isolation Forest on Relative Features** | Detects non-linear combinations of moderate anomalies that single-variable z-scores miss. | MEDIUM | Trained on scale-invariant relative features (volume ratio, return z-score, realized vol ratio). |
| **Market & Sector Context Filtering** | Distinguishes idiosyncratic stock anomalies from macro-driven moves (e.g., market-wide CPI selloff). | MEDIUM | Calculates stock-relative excess return ($r_{stock} - r_{market}$) and sector excess return. |
| **Strict Anti-Leakage Temporal Architecture** | Academic and institutional credibility: guarantees zero future information leaks into baselines, models, or feature calculation. | MEDIUM | Features at time $t$ strictly computed using $X_{\le t}$. |

### Anti-Features (Commonly Requested, Deliberately Excluded)

Features that seem appealing on the surface but compromise integrity or feasibility.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Stock Price Forecasting (Price Prediction)** | Users often conflate surveillance with algorithmic trading. | Predictive models have low signal-to-noise ratio, encourage trading bias, and violate surveillance neutrality. | Focus strictly on *unusual behavior detection* relative to historical norms. |
| **Automated Trading Bot Execution** | Demo looks active and exciting. | Out of scope; creates liability; misrepresents surveillance systems as hedge fund trading engines. | Focus on decision support and alert generation for human analysts. |
| **Legal/Fraud Claims ("Manipulation Confirmed")** | Sounds decisive in pitch presentations. | An anomaly is a statistical outlier, not proof of illegal intent (e.g., could be legitimate surprise earnings or index rebalancing). | Use objective regulatory framing: *"High-risk unusual activity detected; warrants review."* |
| **Synthetic/Faked Order Book (L2 Depth)** | Sounds technically sophisticated. | Exchange-grade L2 ticks for 100 stocks are not free; synthesizing fake order books destroys institutional credibility. | Implement Layer 1 (5-minute OHLCV) with full rigor; designate L2 as an explicit future integration. |
| **Paid LLM Summaries for Alerts** | Popular hackathon trend. | Adds network latency, API costs, and risk of hallucinations on financial data. | Use deterministic, template-driven quantitative explainability derived directly from feature deviations. |
| **Direct Alert Injection** | Easiest way to fake a demo alert. | Bypasses the detection engine, meaning the demo proves nothing about the ML system. | Injected raw candle anomalies MUST pass through the real feature engineering and detector pipeline. |

## Feature Dependencies

```
[Curated 5m Parquet Data]
       ↓
[Abstract MarketDataProvider]
       ↓
[Replay Engine] ──(optional inject)──> [Surveillance Controller]
       ↓
[Feature Engineering]
       ↓
[Time-of-Day (TOD) Baselines]
       ↓
┌──────────────────────┴──────────────────────┐
↓                                             ↓
[Statistical Detector (Z-Scores)]     [Isolation Forest (Multivariate)]
└──────────────────────┬──────────────────────┘
                       ↓
              [Signal Fusion Engine]
                       ↓
             [0-100 Risk Scoring]
                       ↓
         ┌─────────────┴─────────────┐
         ↓                           ↓
[Explainability Engine]      [Alert Engine]
         └─────────────┬─────────────┘
                       ↓
              [FastAPI Backend]
                       ↓
         [Streamlit / Plotly Dashboard]
```

### Dependency Notes

- **TOD Baselines require Feature Engineering:** Baselines compute rolling distributions of features across historical bars.
- **Statistical Detector & Isolation Forest feed Signal Fusion:** Fused risk score combines normalized z-scores with Isolation Forest decision function.
- **Explainability requires Detector Outputs:** Explanations cite the top contributing z-scores and relative ratios calculated by detectors.
- **Surveillance Controller acts on Replay Stream:** Injected events alter raw candle inputs *before* feature extraction, testing the entire stack end-to-end.

## MVP Definition

### Launch With (MVP — Hackathon September 26, 2026)

- [ ] **Universe Configuration**: 100 liquid stocks with matched market (e.g., SPY/NIFTY) and sector benchmarks.
- [ ] **Curated Parquet Data Ingestion**: Offline-first storage of 60 days of 5-minute candles.
- [ ] **Deterministic Replay Engine**: In-memory replay generator supporting play, pause, resume, and variable speeds.
- [ ] **Feature Engineering**: Scale-invariant price return, volume ratio, Parkinson volatility, and market-relative returns.
- [ ] **TOD Rolling Baselines**: Slot-bucketed moving averages eliminating opening/closing surge false alarms.
- [ ] **Statistical Detector**: Multi-metric z-scores and EWMA deviations.
- [ ] **Isolation Forest Model**: Scikit-learn model trained on scale-invariant relative features.
- [ ] **Signal Fusion & 0–100 Risk Score**: Transparent weighted composite scoring.
- [ ] **Explainability Engine**: Rule-based natural language evidence generator citing exact deviations.
- [ ] **Alert Management**: Deduplicated alert stream with LOW/MEDIUM/HIGH/CRITICAL severities.
- [ ] **Surveillance Controller**: Interactive UI component for injecting volume, price, and volatility anomalies.
- [ ] **FastAPI Endpoints**: REST API exposing health, replay, stocks, signals, and alerts.
- [ ] **Streamlit + Plotly Dashboard**: Unified analyst UI with alert table, multi-panel charts, and injection controller.
- [ ] **Test Suite**: Automated tests for features, baselines, detectors, replay, leakage, and injection round-trip.

### Add After Validation (Post-Hackathon v1.1)

- [ ] **Historical Alert Archive**: SQLite persistence for historical alert lookup across past sessions.
- [ ] **Free News / Sentiment Ingestion**: RSS feed / Finnhub free news sentiment overlay on flagged tickers.
- [ ] **Advanced Multi-Day Pattern Detection**: Detection of multi-day volume accumulation before earnings.

### Future Consideration (v2.0+)

- [ ] **Live WebSocket Exchange Ingestion**: Real-time socket stream replacing the replay generator.
- [ ] **Level 2 / Order Book Microstructure**: Bid-ask spread, quote depth, and order-flow imbalance when licensed data is acquired.
- [ ] **Multi-Tenant Analyst Workflow**: Role-based alert assignment, case notes, and regulatory audit trail export.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Replay Engine (5-minute Parquet) | HIGH | MEDIUM | P1 |
| Time-of-Day (TOD) Baselines | HIGH | MEDIUM | P1 |
| Statistical Anomaly Detector (Z-Scores) | HIGH | LOW | P1 |
| Isolation Forest Anomaly Scoring | HIGH | MEDIUM | P1 |
| Signal Fusion & 0-100 Risk Score | HIGH | LOW | P1 |
| Evidence-Based Natural Language Explanation | HIGH | LOW | P1 |
| Surveillance Controller (Anomaly Injection) | HIGH | MEDIUM | P1 |
| Streamlit + Plotly Surveillance Dashboard | HIGH | MEDIUM | P1 |
| FastAPI Backend Integration | MEDIUM | LOW | P1 |
| Comprehensive Unit & Leakage Tests | HIGH | MEDIUM | P1 |
| SQLite Persistent Alert History | MEDIUM | LOW | P2 |
| Sector Benchmark Relative Returns | MEDIUM | MEDIUM | P2 |
| Free News Sentiment Overlay | LOW | MEDIUM | P3 |

---
*Feature research for: MarketWatch AI*  
*Researched: 2026-09-15*  

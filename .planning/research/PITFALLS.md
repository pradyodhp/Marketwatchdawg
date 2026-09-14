# Pitfalls Research

**Domain:** Financial Market Surveillance & Explainable Anomaly Detection  
**Researched:** 2026-09-15  
**Confidence:** HIGH  

## Critical Pitfalls

### Pitfall 1: Diurnal U-Curve Blindness (The "Market Open" False Alarm Trap)

**What goes wrong:**  
Every morning between 09:30 and 10:00 AM, the system triggers a barrage of false "CRITICAL" volume and volatility alerts on almost every stock in the universe.

**Why it happens:**  
Intraday equity volume and volatility follow a steep U-shaped diurnal curve: market open volume is naturally 5x–10x higher than the midday lunch lull. A naive rolling moving average (e.g. trailing 20 candles) compares 09:35 AM against yesterday's sleepy afternoon close, flagging standard opening order execution as an extreme statistical anomaly.

**How to avoid:**  
Implement **Time-of-Day (TOD) slot-bucketed baselines**. A 09:35 AM bar is strictly compared against the historical distribution of 09:35 AM bars across the trailing $K$ trading days.

**Warning signs:**  
Alert spikes clustered heavily in the first 30 minutes of the trading day; silence during midday even when unusual volume occurs.

**Phase to address:**  
Phase 3 (Time-of-Day Baselines & Feature Engineering).

---

### Pitfall 2: Temporal Lookahead Leakage (The ML Illusion)

**What goes wrong:**  
The model achieves near-flawless anomaly detection scores during development, but fails or behaves erratically during sequential replay.

**Why it happens:**  
Feature normalization, rolling means, or Isolation Forest training sets unintentionally incorporate data from timestamps $t' > t$ (e.g. centering with global dataset standard deviation, or training ML on the entire historical dataset before replaying it).

**How to avoid:**  
Strictly enforce causal windowing. At time $t$, features and baselines can only read $X_{\le t}$. Partition data into a historical calibration window (e.g. Days 1–30) for baseline warm-up and Isolation Forest training, and a separate evaluation/replay window (Days 31–60).

**Warning signs:**  
Baseline statistics that shift before a major price shock occurs; test metrics that degrade sharply when candles are emitted one-by-one.

**Phase to address:**  
Phase 2 (Replay Engine) & Phase 4 (Isolation Forest Pipeline).

---

### Pitfall 3: Raw Scale Poisoning in Shared Isolation Forest

**What goes wrong:**  
A single Isolation Forest trained across 100 stocks only flags large-cap mega-caps (like AAPL or NVDA) for volume, and only flags penny/small-cap stocks for percentage price movement, while completely ignoring mid-caps.

**Why it happens:**  
Feeding raw absolute values (e.g. raw volume of 50M shares, raw price of $500) into a single model. The tree partitioning splits almost exclusively on high-magnitude stocks.

**How to avoid:**  
Ensure every feature fed to Isolation Forest is strictly **scale-invariant and stock-relative**:
- Volume Ratio: $V_t / \text{TOD\_Median\_Volume}_t$
- Return Z-Score: $(r_t - \mu_t) / \sigma_t$
- Realized Volatility Ratio: $\text{Vol}_t / \text{Baseline\_Vol}_t$
- Market-Relative Excess Return: $r_{stock, t} - r_{market, t}$

**Warning signs:**  
Anomaly score distributions that vary dramatically depending on the stock's market capitalization or average volume.

**Phase to address:**  
Phase 4 (Isolation Forest ML Detector).

---

### Pitfall 4: Venue Network Failure & Free API Rate Limiting

**What goes wrong:**  
During the live hackathon presentation, the demo freezes, charts crash, or error toasts pop up stating `429 Too Many Requests` or `Connection Timed Out`.

**Why it happens:**  
Free APIs (Twelve Data, Alpha Vantage, Finnhub) have strict rate limits (5 calls/min or 25 calls/day). Hitting live endpoints for 100 stocks during a 5-minute presentation guarantees immediate throttling. Furthermore, venue Wi-Fi is notoriously congested.

**How to avoid:**  
Architect the system as **offline-first**. Pre-fetch and curate 60 days of 5-minute candles into compressed Parquet files in `data/curated/`. The replay engine runs 100% locally with zero internet dependency during the pitch.

**Warning signs:**  
Any direct HTTP requests to external market data APIs inside the replay loop.

**Phase to address:**  
Phase 1 (Data Ingestion & Parquet Curation).

---

### Pitfall 5: Regulatory & Legal Overreach in Explanations

**What goes wrong:**  
Alert text states: *"Manipulation detected: Bad actor spoofing AAPL to pump price."* Judges or financial reviewers dismiss the project as legally reckless and amateurish.

**Why it happens:**  
Conflating statistical outlier detection with legal determination of intent. Market anomalies occur naturally during earnings surprises, index rebalancing, analyst upgrades, or block trades.

**How to avoid:**  
Enforce objective, evidence-based surveillance language:
- *"High-risk unusual activity detected: Volume is 7.8x the 09:45 AM baseline, price movement is 3.2σ above expected range."*
- Include an explicit surveillance disclaimer on all alerts.

**Warning signs:**  
Any string containing "manipulation", "fraud", "illegal", "guaranteed", or "bad actor" in the codebase.

**Phase to address:**  
Phase 5 (Explanation Engine & Alerting).

---

### Pitfall 6: Direct Alert Injection (The "Cheating Demo" Trap)

**What goes wrong:**  
The demo has an "Inject Anomaly" button that simply posts a pre-fabricated alert directly to the alert feed. Savvy technical judges ask to see the feature pipeline or detector logs and realize the ML engine was bypassed.

**Why it happens:**  
Developers run out of time and shortcut the connection between the UI button and the detection pipeline.

**How to avoid:**  
The Surveillance Controller MUST inject the anomaly into the **raw candle stream** (e.g. multiply `candle.volume` by 8.0x). The distorted candle must then flow through Feature Engineering, TOD Baselines, Statistical Detector, Isolation Forest, and Signal Fusion before an alert is emitted.

**Warning signs:**  
Code where the inject button calls `alert_engine.create_alert()` directly.

**Phase to address:**  
Phase 6 (Surveillance Controller & Full-Stack Integration).

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| In-Memory Replay Generator | Trivial setup, zero infrastructure. | Limited to available RAM (100 stocks x 60 days = ~10MB, easily fits). | Fully acceptable for Hackathon MVP. |
| Rule-Based Quantitative Explainability | Instant execution (<0.1ms), $0 cost, zero hallucination. | Does not produce freeform conversational prose. | Recommended standard for financial compliance. |
| Hardcoded Initial Fusion Weights | Avoids complex meta-optimization models. | Weights must be manually calibrated. | Acceptable for MVP; expose via `settings.yaml`. |

## "Looks Done But Isn't" Checklist

- [ ] **Time-of-Day Baselining:** Verify that 09:30 AM open does NOT generate an alert on normal trading days.
- [ ] **Temporal Anti-Leakage:** Verify that running replay up to 11:00 AM has zero access to data after 11:00 AM.
- [ ] **Shared ML Scale Invariance:** Verify that a $5 stock and a $500 stock have comparable anomaly score distributions.
- [ ] **Anomaly Injection Round-Trip:** Verify that clicking "Inject Volume Spike" increases raw volume and triggers the real statistical/ML detectors.
- [ ] **Zero Network Dependency:** Verify the entire demo runs with Wi-Fi disabled.

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Diurnal U-Curve Blindness | Phase 3 | Unit test comparing 09:30 AM vs 12:30 PM volume normalization. |
| Temporal Lookahead Leakage | Phase 2 & 4 | Automated test verifying feature values at timestamp $t$ match isolated historical slicing. |
| Raw Scale Poisoning | Phase 4 | Model score distribution test across top and bottom quintile market-cap stocks. |
| Venue Rate Limiting / Network Drop | Phase 1 | Offline test: run complete replay pipeline with internet disconnected. |
| Legal / Regulatory Overreach | Phase 5 | Linter test scanning for forbidden terms ("fraud", "manipulation"). |
| Direct Alert Injection Shortcut | Phase 6 | End-to-end integration test verifying injection modifies raw candle and triggers ML detector. |

---
*Pitfalls research for: MarketWatch AI*  
*Researched: 2026-09-15*  

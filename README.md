# 📊 MarketWatch AI

## Explainable Real-Time Market Surveillance

> **An AI-powered market surveillance system that monitors trading activity, detects unusual market behavior, assigns a transparent risk score, and explains why an alert was generated.**

MarketWatch AI is a market-surveillance and analyst decision-support platform designed to continuously monitor securities for statistically unusual activity.

The system combines **statistical anomaly detection, multivariate machine learning, deterministic historical replay, transparent risk scoring, and explainability** into a single surveillance pipeline.

It is designed to answer:

> **"What unusual activity is happening, how unusual is it, and why was it flagged?"**

---

## 🚨 Problem Statement

### Unusual Activity Watchdog

Modern financial markets generate enormous amounts of trading data. Manually monitoring every security for unusual behavior is difficult and does not scale effectively.

MarketWatch AI addresses this problem by continuously analyzing market activity and identifying behavior that significantly deviates from expected patterns.

The system monitors signals such as:

- 📈 Unusual price movements
- 📊 Abnormal trading volume
- 🌊 Sudden volatility changes
- 🔄 Unusual trading activity
- ⚖️ Buying/selling pressure
- ⏱️ Abnormal trading frequency
- 🏦 Market-relative behavior
- 🏭 Sector-relative behavior

The goal is **not to predict prices**.

The goal is to identify activity that is unusual enough to warrant **further analyst investigation**.

---

# 🎯 Core Objective

MarketWatch AI transforms raw market data into an explainable surveillance alert:

```text
Raw Market Data
      │
      ▼
Data Quality & Curation
      │
      ▼
Historical / Real-Time Stream
      │
      ▼
Feature Engineering
      │
      ├───────────────┐
      ▼               ▼
Statistical       ML Anomaly
Detection         Detection
      │               │
      └───────┬───────┘
              ▼
       Signal Fusion
              │
              ▼
       Risk Score 0–100
              │
              ▼
        Explainability
              │
              ▼
        Alert Engine
              │
              ▼
       Analyst Dashboard


Detection Engine

MarketWatch AI uses multiple detection techniques rather than depending on a single model.

Statistical Detection

The first layer uses rolling statistical baselines.

Z-Score

A simplified representation is:

Z = (X - μ) / σ

where:

X = current observation
μ = historical mean
σ = historical standard deviation

Large absolute z-scores indicate that the observation is far from its expected baseline.

EWMA

Exponentially Weighted Moving Average methods allow the system to give more importance to recent observations.

This helps the system adapt to changing market conditions without completely abandoning historical context.


Multivariate Machine Learning

MarketWatch AI also uses an Isolation Forest for unsupervised anomaly detection.

Unlike a single-variable statistical test, Isolation Forest considers multiple features simultaneously.

🚨 HIGH-RISK UNUSUAL ACTIVITY

Risk Score: 91 / 100

Evidence
────────────────────────────────

Volume              8.2× baseline
Price deviation     3.1σ
Volatility          4.1× baseline
Order-flow          +0.89
ML anomaly          HIGH

Primary reasons
────────────────────────────────

• Extreme volume deviation
• Significant price deviation
• Elevated volatility
• Abnormal combined feature pattern

System Architecture

                         MARKETWATCH AI
                              │
                              ▼
                  ┌───────────────────────┐
                  │     Market Data       │
                  └───────────┬───────────┘
                              │
                              ▼
                  ┌───────────────────────┐
                  │ Data Ingestion        │
                  │ & Validation          │
                  └───────────┬───────────┘
                              │
                              ▼
                  ┌───────────────────────┐
                  │ Curated Parquet       │
                  │ Offline Dataset       │
                  └───────────┬───────────┘
                              │
                              ▼
                  ┌───────────────────────┐
                  │ Deterministic Replay  │
                  │ / Stream              │
                  └───────────┬───────────┘
                              │
                              ▼
                  ┌───────────────────────┐
                  │ Feature Engineering   │
                  │ + TOD Baselines       │
                  └───────────┬───────────┘
                              │
                 ┌────────────┴────────────┐
                 │                         │
                 ▼                         ▼
       ┌──────────────────┐      ┌──────────────────┐
       │ Statistical      │      │ Isolation Forest │
       │ Detection        │      │ Detection        │
       └────────┬─────────┘      └────────┬─────────┘
                │                         │
                └────────────┬────────────┘
                             ▼
                  ┌───────────────────────┐
                  │ Signal Fusion         │
                  └───────────┬───────────┘
                              │
                              ▼
                  ┌───────────────────────┐
                  │ Risk Score 0–100      │
                  └───────────┬───────────┘
                              │
                              ▼
                  ┌───────────────────────┐
                  │ Explainability        │
                  └───────────┬───────────┘
                              │
                              ▼
                  ┌───────────────────────┐
                  │ Alert Engine          │
                  └───────────┬───────────┘
                              │
                              ▼
                  ┌───────────────────────┐
                  │ FastAPI Service       │
                  └───────────┬───────────┘
                              │
                              ▼
                  ┌───────────────────────┐
                  │ Streamlit + Plotly    │
                  │ Analyst Dashboard     │
                  └───────────────────────┘



Project Structure

Marketwatchdawg/
│
├── .agent/
│   └── GSD configuration
│
├── configs/
│   ├── universe_nifty100.json
│   └── settings.yaml
│
├── data/
│   └── curated/
│       ├── *.parquet
│       └── quality_metadata.json
│
├── src/
│   └── marketwatch/
│       │
│       ├── config/
│       │   ├── universe.py
│       │   └── settings.py
│       │
│       ├── models/
│       │   ├── candle.py
│       │   ├── features.py
│       │   ├── signals.py
│       │   ├── alerts.py
│       │   └── metadata.py
│       │
│       ├── protocols/
│       │   └── provider.py
│       │
│       ├── ingestion/
│       ├── replay/
│       ├── features/
│       ├── detection/
│       ├── scoring/
│       ├── explainability/
│       ├── alerts/
│       ├── api/
│       └── dashboard/
│
├── tests/
│
├── pyproject.toml
├── requirements.txt
└── README.md

Data Architecture

MarketWatch AI separates data acquisition from runtime processing.
External Data
     │
     ▼
Offline Acquisition
     │
     ▼
Validation
     │
     ▼
Curation
     │
     ▼
Parquet
     │
     ▼
Runtime Provider
     │
     ▼
Replay / Detection

---

## 📥 Adding Your Own Market Data

The monitored universe is not fixed. Upload 5-minute OHLCV bars for any symbol
and it flows through the same detectors, risk scoring, and alerting:

- **API:** `POST /ingest?symbol=RELIANCE.NS` with a CSV or Parquet body
  (datetime column plus Open/High/Low/Close/Volume, any column case).
- **Dashboard:** "Add your own market data" panel on the overview screen.

Rows are validated with the same rules as the offline pipeline (positive
prices, OHLC geometry, NSE trading hours 09:15-15:30 IST, duplicate removal);
dropped rows are reported back, never silently discarded.

`GET /candles?symbol=...` returns the stored series for charting, and the
Security Investigation screen renders it as a candlestick + volume chart.

## 🔔 Alert Delivery

High-severity alerts no longer live only on the dashboard. Set a webhook to
get notified when sudden unusual activity is detected:

```yaml
# configs/settings.yaml
notifications:
  webhook_url: "https://your-endpoint.example/hook"   # or MARKETWATCH_NOTIFICATIONS__WEBHOOK_URL
  min_severity: HIGH
```

Every newly created HIGH/CRITICAL alert is POSTed once as JSON (symbol,
0-100 risk score, severity, explanation summary). Delivery failures are
logged and never interrupt the surveillance pipeline.

## ⚖️ Buying/Selling Pressure (Order-Imbalance Proxy)

True order-book imbalance requires level-2 trade data, which OHLCV does not
carry. As a documented proxy, the feature pipeline computes per-bar
buying/selling pressure: `(close - open) / (high - low)`, in [-1, 1], where
+1 means the bar closed at its high (buying pressure) and -1 at its low.
It feeds the Z-score, EWMA, and Isolation Forest detectors alongside price,
volume, and volatility features.

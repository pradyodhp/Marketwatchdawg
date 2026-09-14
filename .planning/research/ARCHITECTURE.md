# Architecture Research

**Domain:** Financial Market Surveillance & Explainable Anomaly Detection  
**Researched:** 2026-09-15  
**Confidence:** HIGH  

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PRESENTATION LAYER                                 │
│  ┌─────────────────────────────────┐   ┌─────────────────────────────────┐  │
│  │   Streamlit Surveillance UI     │   │     Surveillance Controller     │  │
│  │   (Alert Feed, Plotly Charts)   │   │  (Interactive Anomaly Injector) │  │
│  └────────────────┬────────────────┘   └────────────────┬────────────────┘  │
└───────────────────┼─────────────────────────────────────┼───────────────────┘
                    │ REST / WebSocket                    │ Event Injection
┌───────────────────▼─────────────────────────────────────▼───────────────────┐
│                          APPLICATION & API LAYER                            │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                         FastAPI Service Router                        │  │
│  │   GET /alerts  │  GET /stocks/{symbol}  │  POST /replay/{action}      │  │
│  └───────────────────────────────────┬───────────────────────────────────┘  │
└──────────────────────────────────────┼──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                           SURVEILLANCE CORE DOMAIN                          │
│                                                                             │
│  ┌────────────────────────┐                   ┌──────────────────────────┐  │
│  │   Alert Engine         │                   │   Explanation Engine     │  │
│  │   (Severity/Cooldown)  │◄──────────────────┤   (Quantitative Evidence)│  │
│  └───────────▲────────────┘                   └─────────────▲────────────┘  │
│              │                                              │               │
│              └──────────────────────┬───────────────────────┘               │
│                                     │                                       │
│                       ┌─────────────┴─────────────┐                         │
│                       │   Signal Fusion Engine    │                         │
│                       │   (0-100 Weighted Score)  │                         │
│                       └─────────────▲─────────────┘                         │
│                                     │                                       │
│             ┌───────────────────────┴───────────────────────┐               │
│             │                                               │               │
│  ┌──────────┴───────────────┐                   ┌───────────┴────────────┐  │
│  │   Statistical Detector   │                   │    Isolation Forest    │  │
│  │   (Z-Scores & EWMA)      │                   │    (Multivariate ML)   │  │
│  └──────────▲───────────────┘                   └───────────▲────────────┘  │
│             │                                               │               │
│             └───────────────────────┬───────────────────────┘               │
│                                     │                                       │
│                       ┌─────────────┴─────────────┐                         │
│                       │  Time-of-Day (TOD) Engine │                         │
│                       │  (Diurnal Baseline Model) │                         │
│                       └─────────────▲─────────────┘                         │
│                                     │                                       │
│                       ┌─────────────┴─────────────┐                         │
│                       │ Feature Engineering Engine│                         │
│                       │ (Scale-Invariant Ratios)  │                         │
│                       └─────────────▲─────────────┘                         │
│                                     │                                       │
│                       ┌─────────────┴─────────────┐                         │
│                       │   Replay & Stream Engine  │                         │
│                       │   (Temporal Anti-Leakage) │                         │
│                       └─────────────▲─────────────┘                         │
└─────────────────────────────────────┼───────────────────────────────────────┘
                                      │
┌─────────────────────────────────────▼───────────────────────────────────────┐
│                            DATA & STORAGE LAYER                             │
│  ┌───────────────────────────┐                 ┌─────────────────────────┐  │
│  │ Abstract MarketDataProvider│                │ Curated Parquet Dataset │  │
│  │ (Interface / Protocol)    │                 │ (100 Stocks + Benchmarks│  │
│  └───────────────────────────┘                 └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **`MarketDataProvider`** | Ingests market candle data behind a standardized interface. | Abstract Base Class / Protocol returning standardized `Candle` Pydantic models. |
| **`ParquetDataProvider`** | Concrete implementation reading local 5-minute Parquet files. | Fast PyArrow reader partitioned by date or symbol. |
| **`ReplayEngine`** | Emits synchronized 5-minute candles across all 100 stocks at timestamp $t$. | In-memory generator with time-step coordination, pause/resume, and speed throttling. |
| **`AnomalyInjector`** | Intercepts raw candle streams to inject controlled synthetic anomalies on demand. | Pipeline middleware that mutates raw volume, price, or high/low before feature extraction. |
| **`FeaturePipeline`** | Transforms raw OHLCV candles into scale-invariant relative features. | Vectorized Pandas/NumPy calculator (log returns, volume ratios, Parkinson volatility). |
| **`TODBaselineEngine`** | Maintains per-stock rolling historical distributions bucketed by time-of-day slot. | Circular buffers / rolling windows of trailing $K$ days for each 5-minute slot (e.g. 09:35). |
| **`StatisticalDetector`** | Computes normalized deviations (Z-scores, EWMA) per feature. | Pure NumPy vectorized computation against TOD baseline distributions. |
| **`IsolationForestDetector`** | Unsupervised multivariate outlier scoring. | Scikit-learn `IsolationForest` scoring scale-invariant feature vectors. |
| **`SignalFusionEngine`** | Blends statistical signals, ML score, and market context into a 0–100 risk score. | Configurable weighted combination with non-linear saturation curves. |
| **`ExplanationEngine`** | Generates human-readable, evidence-based natural language summaries. | Template-driven quantitative compiler citing exact deviations and market context. |
| **`AlertEngine`** | Manages alert lifecycle, severity categorization, deduplication, and cooldowns. | In-memory state machine tracking active/cooling alert states per ticker. |
| **`SurveillanceAPI`** | Exposes system state and controls via REST and WebSocket contracts. | FastAPI routes with Pydantic request/response schemas. |
| **`DashboardUI`** | Surveillance workstation for analyst exploration and demo presentation. | Streamlit multi-page app with Plotly WebGL financial charts. |

## Recommended Project Structure

```
marketwatch/
├── src/
│   └── marketwatch/
│       ├── __init__.py
│       ├── domain/                  # Pure domain models & contracts
│       │   ├── __init__.py
│       │   ├── models.py            # Candle, FeatureSet, AnomalySignal, RiskScore, Alert
│       │   └── interfaces.py        # IMarketDataProvider, IReplayEngine, IDetector
│       ├── data/                    # Data ingestion & caching
│       │   ├── __init__.py
│       │   ├── provider.py          # Abstract MarketDataProvider & ParquetProvider
│       │   ├── prefetch.py          # Script/service to download 5m data via free sources
│       │   └── universe.py          # Universe & benchmark configuration loader
│       ├── engine/                  # Core processing engines
│       │   ├── __init__.py
│       │   ├── replay.py            # Deterministic Replay Engine & clock
│       │   ├── features.py          # Vectorized scale-invariant feature engineering
│       │   ├── baselines.py         # Time-of-Day (TOD) slot-bucketed baseline engine
│       │   └── injector.py          # Anomaly Injection middleware
│       ├── ml/                      # Machine learning & statistical detection
│       │   ├── __init__.py
│       │   ├── statistical.py       # Z-score & EWMA detector
│       │   ├── isolation_forest.py  # Model trainer, persister, and scorer
│       │   └── fusion.py            # Signal fusion & 0-100 risk scoring
│       ├── surveillance/            # Decision support & alerting
│       │   ├── __init__.py
│       │   ├── explainability.py    # Natural language evidence generator
│       │   └── alerts.py            # Alert engine, lifecycle, cooldowns
│       └── api/                     # REST/WebSocket endpoints
│           ├── __init__.py
│           ├── app.py               # FastAPI application factory
│           └── routes/              # Modular endpoint routers
│               ├── health.py
│               ├── replay.py
│               ├── stocks.py
│               └── alerts.py
├── dashboard/                       # Streamlit analyst UI
│   ├── app.py                       # Main Streamlit workstation entrypoint
│   ├── components/
│   │   ├── charts.py                # Plotly candlestick, volume, & anomaly charts
│   │   ├── alert_table.py           # Reactive alert feed and severity badges
│   │   ├── controller.py            # Surveillance Controller injection panel
│   │   └── inspector.py             # Single-stock deep dive & explanation view
│   └── state.py                     # Streamlit session state manager
├── configs/                         # Declarative configuration files
│   ├── universe_us100.json          # S&P 100 / NASDAQ 100 tickers + SPY/Sector ETFs
│   ├── universe_nifty100.json       # NIFTY 100 tickers + NIFTY 50/Sector benchmarks
│   └── settings.yaml                # Model weights, thresholds, replay parameters
├── data/                            # Local Parquet store (gitignored datasets)
│   ├── raw/
│   └── curated/
├── tests/                           # Comprehensive test suite
│   ├── unit/                        # Features, baselines, detectors, fusion tests
│   ├── integration/                 # End-to-end replay & injection round-trip
│   └── fixtures/                    # Mock 5-minute candle datasets
├── pyproject.toml                   # Project dependencies and build config
└── README.md
```

## Architectural Patterns

### Pattern 1: Abstract Data Provider (Decoupled Ingestion)

**What:** Encapsulate market data loading behind an abstract protocol (`MarketDataProvider`) returning immutable `Candle` entities.  
**When to use:** Everywhere. The rest of the system must never know whether candles came from a local Parquet file, a CSV mock, or a live WebSocket stream.  
**Trade-offs:** Adds a lightweight abstraction layer, but guarantees $0 cost offline replay today and seamless live streaming tomorrow.

```python
from typing import Protocol, Iterator
from marketwatch.domain.models import Candle

class MarketDataProvider(Protocol):
    def get_symbols(self) -> list[str]: ...
    def stream_candles(self, start_time: str, end_time: str) -> Iterator[dict[str, Candle]]: ...
```

### Pattern 2: Intercepting Anomaly Injector Middleware

**What:** Anomaly injection mutates raw `Candle` objects at the replay stream level *before* feature computation.  
**When to use:** When the presenter clicks "Inject Flash Volume Spike" in the Surveillance Controller.  
**Trade-offs:** Requires the replay engine to support an injection queue, but ensures the anomaly is genuinely detected by ML and statistical algorithms rather than bypassing the system.

```python
class AnomalyInjector:
    def intercept(self, symbol: str, candle: Candle) -> Candle:
        if symbol in self._pending_injections:
            injection = self._pending_injections.pop(symbol)
            return injection.apply(candle) # e.g. candle.volume *= 8.0, tagged as is_simulated=True
        return candle
```

### Pattern 3: Hybrid Quantitative Explainability

**What:** Avoid opaque black-box neural networks or high-latency TreeSHAP on every candle. Use scikit-learn's `IsolationForest` for multivariate anomaly scoring, and derive the explanation directly from the normalized feature deviations and detector outputs.  
**When to use:** For every generated alert.  
**Trade-offs:** Sub-millisecond execution, zero LLM API cost, zero hallucination, 100% auditable evidence.

## Data Flow: Candle to Alert

```
1. ReplayEngine emits 5-minute candle batch for 100 stocks at timestamp T.
2. AnomalyInjector checks for active user injections; mutates candle if active.
3. FeaturePipeline calculates scale-invariant metrics (returns, volume ratios, Parkinson volatility).
4. TODBaselineEngine retrieves historical distribution for bar slot (e.g. Slot 12 = 10:30 AM).
5. StatisticalDetector computes z-scores for volume, price, volatility.
6. IsolationForestDetector scores feature vector against unsupervised boundary.
7. SignalFusionEngine computes weighted 0–100 Risk Score.
8. If Risk Score >= Alert Threshold:
   a. ExplanationEngine compiles evidence summary citing top deviations.
   b. AlertEngine checks cooldown/deduplication; emits Alert to API and Dashboard.
```

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| **100 Stocks (MVP)** | In-memory Pandas/NumPy execution; local Parquet storage; single workstation process; Streamlit + FastAPI. Sub-second execution per 5m step across all 100 stocks. |
| **1,000 Stocks (v2)** | Threaded parallel symbol batches using Python `multiprocessing` or `ThreadPoolExecutor`; DuckDB/SQLite for historical feature caching. |
| **10,000+ Stocks (Institutional)** | Distributed streaming (Redpanda/Kafka); Apache Flink for real-time windowing; ClickHouse for time-series storage. |

---
*Architecture research for: MarketWatch AI*  
*Researched: 2026-09-15*  

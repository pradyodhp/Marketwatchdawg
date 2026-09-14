# Stack Research

**Domain:** Financial Market Surveillance & Explainable Anomaly Detection  
**Researched:** 2026-09-15  
**Confidence:** HIGH  

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Python** | 3.10+ | Core Runtime | Universal standard for quantitative finance, ML, data engineering, and rapid API/dashboard prototyping. |
| **pandas** | >=2.0.0 | Tabular & Time-Series Processing | Vectorized rolling windows, time-of-day grouping, resample, and fast columnar transformations. |
| **numpy** | >=1.24.0 | High-Performance Numerical Math | Vectorized z-score calculations, EWMA implementations, and array-level signal fusion at microsecond latency. |
| **scikit-learn** | >=1.3.0 | Unsupervised Anomaly Detection | Battle-tested `IsolationForest`, `RobustScaler`, and evaluation metrics. Predictable memory footprint and sub-millisecond inference. |
| **FastAPI** | >=0.110.0 | REST & WebSocket Surveillance API | Async ASGI framework with native Pydantic v2 data validation, OpenAPI docs generation, and sub-millisecond route dispatch. |
| **Pydantic** | >=2.6.0 | Domain Model Contracts | Strict type validation and JSON serialization for candles, features, detector signals, risk scores, and alerts. |
| **Streamlit** | >=1.35.0 | Interactive Surveillance Dashboard | Rapid reactive web UI for live alert streaming, time-series chart inspection, and interactive surveillance controls. |
| **Plotly** | >=5.20.0 | Financial Candlestick & Multi-Track Charts | Interactive WebGL-accelerated financial charts (candlesticks, volume bars, volatility bands, anomaly scatter overlays). |
| **pyarrow** | >=15.0.0 | Parquet Storage & In-Memory IPC | High-throughput columnar read/write for 100-stock 5-minute candle datasets with zero network latency. |
| **pytest** | >=8.0.0 | Automated Testing Framework | Comprehensive unit, statistical, temporal leakage, and integration testing with parameterization and fixtures. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **yfinance** | >=0.2.40 | Free Historical 5m Data Ingestion | Used during the pre-fetch curation pipeline to download 60 days of 5-minute candles for ~100 stocks and benchmarks. |
| **rich** / **structlog** | >=13.0.0 | Structured Console Observability | Formatted, colored surveillance logging for replay progress, detector triggers, and errors. |
| **httpx** | >=0.27.0 | Async HTTP Client | Used in integration tests to exercise FastAPI endpoints and in Streamlit to query the backend API. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| **venv** | Isolated Python environment | Keeps all project dependencies contained within the repository root without polluting global packages. |
| **ruff** | Fast Python linter and formatter | Enforces clean, idiomatic Python code matching PEP8 standards at instant speed. |

## Installation

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

# Core & ML dependencies
pip install pandas numpy scikit-learn pyarrow

# Backend & Dashboard
pip install fastapi uvicorn pydantic streamlit plotly httpx

# Ingestion & Testing
pip install yfinance pytest pytest-asyncio
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| **Parquet + In-Memory Stream** | Kafka / Redpanda / RabbitMQ | Use message brokers only when scaling to 10,000+ real-time tick streams across a distributed cluster. For 100 stocks on 5m replay, in-memory generators are 100x simpler, faster, and zero-failure. |
| **Rule-Based Evidence Explainability** | SHAP / TreeSHAP per Candle | Use TreeSHAP if doing offline batch analysis where 50ms latency per row is acceptable. For real-time 5m replay in Streamlit, rule-based quantitative attribution executes in <0.1ms with zero UI stutter. |
| **Template-Driven Quantitative Attribution** | Paid LLM API (OpenAI/Anthropic) | Use LLMs only if free local inference is available and non-deterministic text is tolerable. For surveillance compliance, deterministic templated sentences (*"Volume 8.2x baseline, price deviation 3.1σ"*) are hallucination-free and $0. |
| **Streamlit + Plotly** | Next.js + React + TradingView Lightweight Charts | Use Next.js for multi-tenant institutional web portals. Streamlit allows building full-featured Python-native surveillance controls in days. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **Paid Market Data APIs** (Bloomberg, Refinitiv, Polygon Starter) | Violates strict $0 budget constraint. | Free curated Parquet datasets seeded via free APIs / open datasets. |
| **Direct Live API calls during Demo** | Free APIs (Twelve Data, Alpha Vantage) have severe rate limits (5 calls/min); venue Wi-Fi drops can crash the pitch. | Offline-first Parquet Replay Engine with abstract `MarketDataProvider`. |
| **Global Moving Averages across Stocks** | Large-cap vs small-cap volume/volatility scale differences cause rampant false positives or total silence. | Stock-specific rolling baselines with Time-of-Day (TOD) diurnal adjustments. |
| **Deep Neural Networks (LSTMs/Transformers)** | Overkill for tabular 5-minute candle features; black-box opacity; prone to severe temporal leakage and overfitting. | Isolation Forest + Multi-metric Statistical Z-Scores / EWMA. |
| **Spark / Distributed Clusters** | Massive resource overhead; unnecessary for 100 stocks on local workstation. | Vectorized NumPy/Pandas operations. |

## Stack Patterns by Variant

**If US Equities (S&P 100 / NASDAQ 100):**
- Benchmark ticker: `SPY` (Broad Market), `QQQ` (Tech benchmark)
- Sector benchmarks: `XLK`, `XLF`, `XLE`, `XLV`, `XLY`, `XLI`, `XLC`
- Trading Hours: 09:30 – 16:00 EST (78 5-minute bars per day)

**If Indian Equities (NIFTY 100):**
- Benchmark ticker: `^NSEI` (Nifty 50)
- Sector benchmarks: `^NSEBANK` (Banking), `^CNXIT` (IT), `^CNXAUTO` (Automobile)
- Trading Hours: 09:15 – 15:30 IST (75 5-minute bars per day)

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| `pydantic>=2.6` | `fastapi>=0.110` | Uses modern Pydantic v2 `BaseModel.model_dump()` and `model_validate()`. |
| `pandas>=2.0` | `pyarrow>=15.0` | Enables PyArrow-backed fast Parquet I/O and zero-copy slicing. |
| `scikit-learn>=1.3` | `numpy>=1.24` | Stable `IsolationForest` scoring and array indexing. |

## Sources

- Scikit-learn Official Documentation (`IsolationForest`, `RobustScaler`)
- FINRA / SEC Market Surveillance Behavioral Anomaly Detection Papers
- PyArrow & Pandas 2.0 Benchmarks for Financial Time-Series
- FastAPI & Pydantic v2 Migration Reference

---
*Stack research for: MarketWatch AI*  
*Researched: 2026-09-15*  

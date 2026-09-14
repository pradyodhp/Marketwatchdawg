<!-- GSD:project-start source:PROJECT.md -->
## Project

**MarketWatch AI — Explainable Real-Time Market Surveillance**

MarketWatch AI is an explainable market surveillance and behavioral anomaly detection platform designed for compliance teams and quantitative surveillance analysts. Operating on continuous 5-minute equity candles across the NIFTY 100 universe, it monitors trading behavior, detects statistically significant and multivariate abnormal activity relative to historical time-of-day (TOD) baselines, assigns a transparent 0–100 risk score, and generates human-readable evidence-based explanations for every alert.

The system is strictly an analyst decision-support tool for detecting statistical anomalies. It does NOT make legal, fraud, or intent determinations, and explicitly disclaims that an alert establishes market manipulation, misconduct, or fraud.

**Core Value:** Empower market surveillance analysts with immediate, explainable, and statistically grounded intelligence on what is abnormal about a stock right now, how abnormal it is, and why it was flagged — without black-box opacity or unsubstantiated claims of manipulation.

### Constraints

- **Budget**: $0 — Only free open-source software and legitimately free data access.
- **Universe**: NIFTY 100 (100 liquid Indian equities + Nifty 50 + sector benchmarks).
- **Intraday Resolution**: 5-minute candles (75 bars/day, 60 days of historical depth).
- **Temporal Leakage**: Strict prohibition of lookahead bias. At time $t$, baseline and detector calculations only consume data available at or prior to $t$.
- **Environment**: Local-first Python 3.10+ execution on Windows/Linux/macOS.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

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
# Create virtual environment
# Activate virtual environment
# Windows:
# Linux/macOS:
# Core & ML dependencies
# Backend & Dashboard
# Ingestion & Testing
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
- Benchmark ticker: `SPY` (Broad Market), `QQQ` (Tech benchmark)
- Sector benchmarks: `XLK`, `XLF`, `XLE`, `XLV`, `XLY`, `XLI`, `XLC`
- Trading Hours: 09:30 – 16:00 EST (78 5-minute bars per day)
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
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->

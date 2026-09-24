"""Thin FastAPI boundary around the headless MarketWatch surveillance core."""

from __future__ import annotations

import io
import logging
from datetime import date
from pathlib import Path
from typing import Any, Literal

import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from marketwatch.alert_engine import AlertEngine
from marketwatch.config.settings import load_settings
from marketwatch.controller import InjectionConfig, SurveillanceController
from marketwatch.ingestion.parquet_store import (
    read_quality_metadata,
    write_quality_metadata,
    write_symbol_parquet,
)
from marketwatch.ingestion.validator import validate_ohlcv
from marketwatch.models.metadata import DataQualityMetadata
from marketwatch.notifications import WebhookNotifier
from marketwatch.providers.parquet_provider import ParquetDataProvider
from marketwatch.replay.engine import ReplayEngine
from marketwatch.risk import RiskScorer

logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    """Deterministic service health response."""

    status: Literal["ok"] = "ok"
    service: str = "marketwatch"
    headless: bool = True


class QualityResponse(BaseModel):
    """Serialized curated dataset quality metadata."""

    model_config = ConfigDict(extra="forbid")

    source_type: str
    universe_id: str
    loaded_symbols_count: int
    total_symbols_count: int
    coverage_percentage: float
    start_timestamp: str
    end_timestamp: str
    total_bars_per_symbol: int
    missing_bars_summary: dict[str, int]
    is_offline_confirmed: bool

    @classmethod
    def from_metadata(cls, metadata: DataQualityMetadata) -> QualityResponse:
        return cls(
            source_type=metadata.source_type,
            universe_id=metadata.universe_id,
            loaded_symbols_count=metadata.loaded_symbols_count,
            total_symbols_count=metadata.total_symbols_count,
            coverage_percentage=metadata.coverage_percentage,
            start_timestamp=metadata.start_timestamp.isoformat(),
            end_timestamp=metadata.end_timestamp.isoformat(),
            total_bars_per_symbol=metadata.total_bars_per_symbol,
            missing_bars_summary=dict(metadata.missing_bars_summary),
            is_offline_confirmed=metadata.is_offline_confirmed,
        )


class StocksResponse(BaseModel):
    """Available symbols from the configured provider."""

    symbols: list[str]
    count: int


class ReplayRequest(BaseModel):
    """Deterministic replay control request."""

    model_config = ConfigDict(extra="forbid")

    action: Literal["step", "reset", "play"] = "step"
    speed: float = Field(default=1.0, gt=0.0)
    injection: InjectionConfig | None = None


class ReplayResponse(BaseModel):
    """Replay state plus the latest surveillance output."""

    state: str
    position: int
    total_batches: int
    progress_pct: float
    current_timestamp: str | None
    alert_id: str | None = None
    risk_score: float | None = None
    severity: str | None = None
    is_simulated: bool = False
    result: dict[str, Any] | None = None


class AlertResponse(BaseModel):
    """Stable JSON representation of a lifecycle-managed alert."""

    alert_id: str
    symbol: str
    timestamp: str
    slot_index: int
    risk_score: float
    severity: str
    state: str
    explanation: dict[str, Any] | None
    is_simulated: bool
    simulation_metadata: dict[str, Any]
    history: list[dict[str, Any]]


class CandleResponse(BaseModel):
    """One 5-minute OHLCV candle for chart rendering."""

    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class CandlesResponse(BaseModel):
    """Historical candle series for one symbol."""

    symbol: str
    count: int
    candles: list[CandleResponse]


class IngestResponse(BaseModel):
    """Result of uploading one symbol's OHLCV data."""

    symbol: str
    rows_received: int
    rows_loaded: int
    rows_dropped: int
    invalid_reasons: dict[str, int]
    date_range: tuple[str, str]


def _serialize_alert(alert: Any) -> AlertResponse:
    return AlertResponse(
        alert_id=alert.alert_id,
        symbol=alert.symbol,
        timestamp=alert.timestamp.isoformat(),
        slot_index=alert.slot_index,
        risk_score=alert.risk_score,
        severity=alert.severity.value,
        state=alert.state.value,
        explanation=alert.explanation.model_dump(mode="json") if alert.explanation else None,
        is_simulated=alert.is_simulated,
        simulation_metadata=dict(alert.simulation_metadata),
        history=[event.model_dump(mode="json") for event in alert.history],
    )


class MarketWatchAPI:
    """Own injected headless dependencies and deterministic replay state."""

    def __init__(
        self,
        *,
        provider: Any | None = None,
        replay: ReplayEngine | None = None,
        controller: SurveillanceController | None = None,
        settings: Any | None = None,
    ) -> None:
        self.settings = settings or load_settings()
        self.curated_dir = Path(self.settings.curated_dir)
        self.provider = provider or ParquetDataProvider(self.curated_dir)
        self.replay = replay
        if controller is not None:
            self.controller = controller
        else:
            risk = self.settings.risk_scoring
            cooldown_minutes = (
                self.settings.cooldown.window_bars * self.settings.market.bar_interval_minutes
            )
            notifier = None
            if self.settings.notifications.webhook_url:
                notifier = WebhookNotifier(
                    self.settings.notifications.webhook_url,
                    min_severity=self.settings.notifications.min_severity,
                )
            self.controller = SurveillanceController(
                risk_scorer=RiskScorer(
                    detector_weights=risk.weights,
                    severity_thresholds={
                        "medium": risk.thresholds.medium,
                        "high": risk.thresholds.high,
                        "critical": risk.thresholds.critical,
                    },
                ),
                alert_engine=AlertEngine(cooldown_minutes=cooldown_minutes),
                notifier=notifier,
            )
        self.last_result: Any | None = None

    def reload_data(self) -> None:
        """Reload curated data from disk and reset replay/controller state.

        Called after an ingest so newly uploaded symbols become visible
        without restarting the service.
        """
        self.provider = ParquetDataProvider(self.curated_dir)
        self.replay = None
        self.controller.reset()
        self.last_result = None

    def ensure_replay(self, symbols: list[str] | None = None) -> ReplayEngine:
        if self.replay is None:
            try:
                self.replay = ReplayEngine.from_provider(self.provider, symbols=symbols)
            except (FileNotFoundError, ValueError) as exc:
                raise HTTPException(status_code=503, detail=f"replay unavailable: {exc}") from exc
        return self.replay


def create_app(service: MarketWatchAPI | None = None) -> FastAPI:
    """Create the API application with optionally injected test dependencies."""
    runtime = service or MarketWatchAPI()
    app = FastAPI(
        title="MarketWatch AI Surveillance API",
        version="0.1.0",
        description="Headless deterministic surveillance service for analyst decision support.",
    )
    app.state.marketwatch = runtime

    @app.get("/health", response_model=HealthResponse, tags=["system"])
    def health() -> HealthResponse:
        return HealthResponse()

    @app.get("/quality", response_model=QualityResponse, tags=["system"])
    def quality() -> QualityResponse:
        return QualityResponse.from_metadata(runtime.provider.get_quality_metadata())

    @app.get("/stocks", response_model=StocksResponse, tags=["universe"])
    def stocks() -> StocksResponse:
        symbols = sorted(runtime.provider.get_symbols())
        return StocksResponse(symbols=symbols, count=len(symbols))

    @app.post("/replay", response_model=ReplayResponse, tags=["replay"])
    def replay(request: ReplayRequest) -> ReplayResponse:
        engine = runtime.ensure_replay()
        if request.action == "reset":
            engine.reset()
            runtime.controller.reset()
            runtime.last_result = None
        elif request.action == "step":
            batch = engine.step_forward()
            if batch is not None:
                runtime.last_result = runtime.controller.process_batch(
                    batch,
                    injection=request.injection,
                )
        else:
            engine.speed = request.speed
            for batch in engine.play():
                runtime.last_result = runtime.controller.process_batch(
                    batch,
                    injection=request.injection,
                )
        summary = engine.get_replay_summary()
        result = runtime.last_result
        alert = result.alert if result is not None else None
        return ReplayResponse(
            **summary,
            alert_id=alert.alert_id if alert else None,
            risk_score=alert.risk_score if alert else None,
            severity=alert.severity.value if alert else None,
            is_simulated=alert.is_simulated if alert else False,
            result=result.model_dump(mode="json") if result else None,
        )

    @app.get("/candles", response_model=CandlesResponse, tags=["universe"])
    def candles(
        symbol: str,
        start: str | None = None,
        end: str | None = None,
        limit: int = 1500,
    ) -> CandlesResponse:
        if symbol not in runtime.provider.get_symbols():
            raise HTTPException(status_code=404, detail=f"unknown symbol: {symbol}")
        try:
            start_date = date.fromisoformat(start) if start else None
            end_date = date.fromisoformat(end) if end else None
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"invalid date: {exc}") from exc
        limit = max(1, min(limit, 20000))
        rows = []
        for candle in runtime.provider.get_candles(symbol, start=start_date, end=end_date):
            rows.append(
                CandleResponse(
                    timestamp=candle.timestamp.isoformat(),
                    open=candle.open,
                    high=candle.high,
                    low=candle.low,
                    close=candle.close,
                    volume=candle.volume,
                )
            )
            if len(rows) >= limit:
                break
        return CandlesResponse(symbol=symbol, count=len(rows), candles=rows)

    @app.post("/ingest", response_model=IngestResponse, status_code=201, tags=["ingestion"])
    async def ingest(request: Request, symbol: str) -> IngestResponse:
        """Upload one symbol's OHLCV data (CSV or Parquet) as the request body.

        CSV needs a datetime column plus Open/High/Low/Close/Volume (any case).
        5-minute bars in NSE trading hours (09:15-15:30 IST) are required;
        rows failing validation are dropped and reported.
        """
        body = await request.body()
        if not body:
            raise HTTPException(status_code=400, detail="empty upload body")
        content_type = request.headers.get("content-type", "")
        try:
            if "parquet" in content_type or body[:4] == b"PAR1":
                df = pd.read_parquet(io.BytesIO(body))
            else:
                df = pd.read_csv(io.BytesIO(body))
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"could not parse upload: {exc}") from exc

        # Normalize columns to title case OHLCV with a Datetime index.
        rename = {}
        datetime_col = None
        for col in df.columns:
            lowered = str(col).strip().lower()
            if lowered in {"datetime", "timestamp", "date", "time"}:
                datetime_col = col
            elif lowered in {"open", "high", "low", "close", "volume"}:
                rename[col] = lowered.capitalize()
        if datetime_col is None and not isinstance(df.index, pd.DatetimeIndex):
            raise HTTPException(
                status_code=400,
                detail="no datetime column found (expected Datetime/Timestamp column)",
            )
        df = df.rename(columns=rename)
        required = {"Open", "High", "Low", "Close", "Volume"}
        missing = required - set(df.columns)
        if missing:
            raise HTTPException(status_code=400, detail=f"missing columns: {sorted(missing)}")
        if datetime_col is not None:
            df[datetime_col] = pd.to_datetime(df[datetime_col], utc=True)
            df = df.set_index(datetime_col)
        df.index = pd.DatetimeIndex(df.index)
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        df.index.name = "Datetime"

        clean, result = validate_ohlcv(symbol, df)
        if clean.empty:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "no valid rows after validation",
                    "invalid_reasons": result.invalid_reasons,
                },
            )
        write_symbol_parquet(symbol, clean, runtime.curated_dir)

        meta = read_quality_metadata(runtime.curated_dir) or {}
        loaded = sorted(set(meta.get("loaded_symbols", [])) | {symbol})
        requested = sorted(set(meta.get("requested_symbols", [])) | {symbol})
        starts = [result.date_range[0]] + ([meta["date_range_start"]] if meta.get("date_range_start") else [])
        ends = [result.date_range[1]] + ([meta["date_range_end"]] if meta.get("date_range_end") else [])
        write_quality_metadata(
            {
                **meta,
                "universe_id": meta.get("universe_id", "custom"),
                "loaded_symbols": loaded,
                "requested_symbols": requested,
                "missing_symbols": [item for item in requested if item not in loaded],
                "coverage_pct": 100.0 * len(loaded) / max(len(requested), 1),
                "date_range_start": min(starts),
                "date_range_end": max(ends),
                "total_rows": int(meta.get("total_rows", 0)) + result.valid_rows,
            },
            runtime.curated_dir,
        )
        runtime.reload_data()
        logger.info("[%s] ingested %d rows via upload", symbol, result.valid_rows)
        return IngestResponse(
            symbol=symbol,
            rows_received=result.total_rows,
            rows_loaded=result.valid_rows,
            rows_dropped=result.dropped_rows,
            invalid_reasons=result.invalid_reasons,
            date_range=result.date_range,
        )

    @app.get("/alerts", response_model=list[AlertResponse], tags=["alerts"])
    def alerts(
        symbol: str | None = Query(default=None),
        state: str | None = Query(default=None),
    ) -> list[AlertResponse]:
        alert_engine = runtime.controller.alert_engine
        if state is not None and state not in {"NEW", "ACKNOWLEDGED", "RESOLVED"}:
            raise HTTPException(status_code=400, detail="invalid alert state")
        return [
            _serialize_alert(alert)
            for alert in alert_engine.all()
            if (symbol is None or alert.symbol == symbol)
            and (state is None or alert.state.value == state)
        ]

    return app


app = create_app()

__all__ = [
    "AlertResponse",
    "CandlesResponse",
    "HealthResponse",
    "IngestResponse",
    "MarketWatchAPI",
    "QualityResponse",
    "ReplayRequest",
    "ReplayResponse",
    "StocksResponse",
    "app",
    "create_app",
]

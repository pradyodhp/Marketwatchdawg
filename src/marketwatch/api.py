"""Thin FastAPI boundary around the headless MarketWatch surveillance core."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from marketwatch.alert_engine import AlertEngine
from marketwatch.controller import InjectionConfig, SurveillanceController
from marketwatch.models.metadata import DataQualityMetadata
from marketwatch.providers.parquet_provider import ParquetDataProvider
from marketwatch.replay.engine import ReplayEngine


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
    ) -> None:
        self.provider = provider or ParquetDataProvider()
        self.replay = replay
        self.controller = controller or SurveillanceController(
            alert_engine=AlertEngine(cooldown_minutes=0)
        )
        self.last_result: Any | None = None

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
    "HealthResponse",
    "MarketWatchAPI",
    "QualityResponse",
    "ReplayRequest",
    "ReplayResponse",
    "StocksResponse",
    "app",
    "create_app",
]

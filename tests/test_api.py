"""Phase 11 FastAPI boundary tests."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from marketwatch.api import MarketWatchAPI, create_app
from marketwatch.models.candle import Candle, CandleBatch
from marketwatch.models.metadata import DataQualityMetadata
from marketwatch.providers.parquet_provider import ParquetDataProvider
from marketwatch.replay.engine import ReplayEngine

IST = ZoneInfo("Asia/Kolkata")
START = datetime(2026, 9, 17, 9, 15, tzinfo=IST)


class FakeProvider:
    def __init__(self, batches: list[CandleBatch]) -> None:
        self.batches = batches

    def get_quality_metadata(self) -> DataQualityMetadata:
        return DataQualityMetadata(
            universe_id="test",
            loaded_symbols_count=1,
            total_symbols_count=1,
            coverage_percentage=100.0,
            start_timestamp=START,
            end_timestamp=self.batches[-1].timestamp,
            total_bars_per_symbol=len(self.batches),
            missing_bars_summary={},
        )

    def get_symbols(self) -> list[str]:
        return ["A.NS"]

    def stream_batches(self, **_: object):
        yield from self.batches


def _batches() -> list[CandleBatch]:
    batches = []
    for index, volume in enumerate((100.0, 110.0, 90.0, 100.0, 100.0)):
        timestamp = START + timedelta(days=index)
        candle = Candle(
            symbol="A.NS",
            timestamp=timestamp,
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.0,
            volume=volume,
        )
        batches.append(CandleBatch(timestamp=timestamp, slot_index=0, candles={"A.NS": candle}))
    return batches


def _client() -> TestClient:
    batches = _batches()
    service = MarketWatchAPI(provider=FakeProvider(batches), replay=ReplayEngine(batches))
    return TestClient(create_app(service))


def test_health_quality_stocks_and_openapi():
    client = _client()

    assert client.get("/health").json() == {
        "status": "ok",
        "service": "marketwatch",
        "headless": True,
    }
    assert client.get("/quality").json()["is_offline_confirmed"] is True
    assert client.get("/stocks").json() == {"symbols": ["A.NS"], "count": 1}
    assert client.get("/openapi.json").status_code == 200
    assert client.get("/docs").status_code == 200


def test_replay_steps_core_and_exposes_alerts_with_injection():
    client = _client()
    injection = {
        "target_symbol": "A.NS",
        "target_timestamp": (START + timedelta(days=4)).isoformat(),
        "magnitude": 8.0,
        "enabled": True,
    }

    for _ in range(4):
        response = client.post("/replay", json={"action": "step", "injection": injection})
        assert response.status_code == 200
    response = client.post("/replay", json={"action": "step", "injection": injection})

    assert response.status_code == 200
    body = response.json()
    assert body["is_simulated"] is True
    assert body["severity"] == "CRITICAL"
    alerts = client.get("/alerts?symbol=A.NS").json()
    simulated = [alert for alert in alerts if alert["is_simulated"]]
    assert simulated
    assert simulated[-1]["simulation_metadata"]["magnitude"] == 8.0


def test_replay_rejects_invalid_requests_and_unknown_alert_state():
    client = _client()

    assert client.post("/replay", json={"action": "invalid"}).status_code == 422
    assert client.get("/alerts?state=UNKNOWN").status_code == 400


def test_reset_is_deterministic_and_missing_provider_data_is_not_fabricated():
    client = _client()
    assert client.post("/replay", json={"action": "step"}).status_code == 200
    reset = client.post("/replay", json={"action": "reset"})
    assert reset.status_code == 200
    assert reset.json()["position"] == -1
    assert client.get("/alerts").json() == []

    empty = MarketWatchAPI(provider=ParquetDataProvider(curated_dir="missing-curated"))
    empty_client = TestClient(create_app(empty))
    assert empty_client.get("/stocks").json()["symbols"] == []

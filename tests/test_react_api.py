"""Tests for the endpoints backing the React front end."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from marketwatch.api import MarketWatchAPI, create_app
from marketwatch.models.candle import Candle, CandleBatch
from marketwatch.replay.engine import ReplayEngine

IST = ZoneInfo("Asia/Kolkata")
START = datetime(2026, 9, 17, 9, 15, tzinfo=IST)


class FakeProvider:
    def __init__(self, batches):
        self.batches = batches

    def get_quality_metadata(self):
        from marketwatch.models.metadata import DataQualityMetadata

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

    def get_symbols(self):
        return ["A.NS"]

    def stream_batches(self, **_):
        yield from self.batches


def _batches(n=40):
    batches = []
    for index in range(n):
        ts = START + timedelta(minutes=5 * index)
        price = 100.0 + (index % 7) * 0.4
        candle = Candle(
            symbol="A.NS",
            timestamp=ts,
            open=price,
            high=price + 1.0,
            low=price - 1.0,
            close=price + 0.2,
            volume=100.0 + (index % 5) * 25.0,
        )
        batches.append(CandleBatch(timestamp=ts, slot_index=index % 75, candles={"A.NS": candle}))
    return batches


@pytest.fixture()
def client(tmp_path):
    batches = _batches()
    service = MarketWatchAPI(
        provider=FakeProvider(batches),
        replay=ReplayEngine(batches),
        config_path=tmp_path / "settings.yaml",
    )
    return TestClient(create_app(service))


def test_settings_roundtrip_persists(client):
    resp = client.get("/settings")
    assert resp.status_code == 200
    payload = resp.json()
    assert "detectors" in payload
    payload["detectors"]["zscore_threshold"] = 2.5
    resp = client.put("/settings", json=payload)
    assert resp.status_code == 200
    assert client.get("/settings").json()["detectors"]["zscore_threshold"] == 2.5


def test_universe_endpoint(client):
    resp = client.get("/universe")
    assert resp.status_code == 200
    body = resp.json()
    assert "entries" in body and body["entries"]


def test_detect_and_scores(client):
    resp = client.post("/detect")
    assert resp.status_code == 200
    summary = resp.json()
    assert summary.get("bars") or summary.get("batches")
    resp = client.get("/scores", params={"symbol": "A.NS", "limit": 10})
    assert resp.status_code == 200
    body = resp.json()
    rows = body["symbols"]["A.NS"]
    assert rows
    row = rows[0]
    for key in ("t", "c", "risk", "z_ret", "ewma_dev", "if_score"):
        assert key in row


def test_alert_lifecycle_patch(client):
    client.post("/detect")
    alerts = client.get("/alerts").json()
    if not alerts:  # no alerts on this synthetic series: nothing to patch
        pytest.skip("no alerts generated for the synthetic series")
    alert_id = alerts[0]["alert_id"]
    resp = client.patch(f"/alerts/{alert_id}", json={"action": "acknowledge", "note": "looking"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["state"] == "ACKNOWLEDGED"
    resp = client.patch(f"/alerts/{alert_id}", json={"action": "escalate"})
    assert resp.status_code == 200
    assert resp.json()["state"] == "ESCALATED"
    history = client.get("/alerts").json()[0]["history"]
    assert any(h.get("note") == "looking" for h in history)
    assert client.patch("/alerts/nope", json={"action": "resolve"}).status_code == 404

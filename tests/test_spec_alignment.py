"""Tests for spec-alignment work: order-imbalance proxy, Isolation Forest
pipeline wiring, mixed-symbol alert handling, data upload, candle API,
alert delivery, and settings-driven configuration."""

from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from marketwatch.api import MarketWatchAPI, create_app
from marketwatch.controller import SurveillanceController
from marketwatch.features import FeaturePipeline
from marketwatch.models.candle import Candle, CandleBatch
from marketwatch.notifications import WebhookNotifier
from marketwatch.risk import RiskScorer

IST = ZoneInfo("Asia/Kolkata")
START = datetime(2026, 9, 17, 9, 15, tzinfo=IST)


def _candle(symbol: str, ts: datetime, price: float = 100.0, volume: float = 100.0,
            open_: float | None = None, high: float | None = None, low: float | None = None) -> Candle:
    return Candle(
        symbol=symbol,
        timestamp=ts,
        open=open_ if open_ is not None else price,
        high=high if high is not None else price + 1.0,
        low=low if low is not None else price - 1.0,
        close=price,
        volume=volume,
    )


def _batch(index: int, symbols: dict[str, Candle]) -> CandleBatch:
    ts = START + timedelta(minutes=5 * index)
    return CandleBatch(timestamp=ts, slot_index=index % 75, candles=symbols)


# ── Order-imbalance proxy ────────────────────────────────────────────────────

def test_buy_sell_pressure_proxy_bounds_and_meaning():
    pipeline = FeaturePipeline()
    ts = START
    # Close at the high: maximum buying pressure.
    up = pipeline.compute_feature_from_candle(
        _candle("A.NS", ts, price=101.0, open_=100.0, high=101.0, low=99.0), None)
    # Close at the low: maximum selling pressure.
    down = pipeline.compute_feature_from_candle(
        _candle("A.NS", ts, price=99.0, open_=100.0, high=101.0, low=99.0), None)
    # Flat bar: no range, no pressure.
    flat = pipeline.compute_feature_from_candle(
        _candle("A.NS", ts, price=100.0, open_=100.0, high=100.0, low=100.0), None)

    assert up.buy_sell_pressure == pytest.approx(0.5)
    assert down.buy_sell_pressure == pytest.approx(-0.5)
    assert flat.buy_sell_pressure == 0.0
    assert -1.0 <= up.buy_sell_pressure <= 1.0
    assert "buy_sell_pressure" in up.raw_features


# ── Isolation Forest wired into the controller ───────────────────────────────

def test_controller_runs_isolation_forest_after_warmup():
    controller = SurveillanceController()
    last = None
    for index in range(14):
        volume = 100.0 + (index % 3) * 10
        last = controller.process_batch(
            _batch(index, {"A.NS": _candle("A.NS", START + timedelta(minutes=5 * index), volume=volume)})
        )
    detectors = {signal.detector_name for signal in last.signals}
    assert "IsolationForestDetector" in detectors
    ml_signals = [s for s in last.signals if s.detector_name == "IsolationForestDetector"]
    assert any(s.is_valid for s in ml_signals)
    assert last.assessment is not None
    assert "IsolationForestDetector" in last.assessment.active_detectors


# ── Mixed-symbol batches no longer drop alerts ───────────────────────────────

def test_mixed_symbol_batch_scores_each_symbol_independently():
    controller = SurveillanceController()
    result = None
    for index in range(14):
        ts = START + timedelta(minutes=5 * index)
        if index == 13:
            # Both symbols spike simultaneously in the final batch.
            candles = {
                "A.NS": _candle("A.NS", ts, volume=5000.0, price=110.0),
                "B.NS": _candle("B.NS", ts, volume=8000.0, price=95.0),
            }
        else:
            candles = {
                "A.NS": _candle("A.NS", ts, volume=100.0 + (index % 3) * 10),
                "B.NS": _candle("B.NS", ts, volume=200.0 + (index % 2) * 15),
            }
        result = controller.process_batch(_batch(index, candles))

    scored_symbols = {assessment.symbol for assessment in result.assessments}
    assert scored_symbols == {"A.NS", "B.NS"}
    assert len(result.assessments) == 2


# ── Alert delivery ───────────────────────────────────────────────────────────

def test_webhook_notifier_respects_min_severity_and_delivers_once():
    delivered = []
    notifier = WebhookNotifier(
        "https://example.invalid/hook",
        min_severity="HIGH",
        poster=lambda url, payload, timeout: delivered.append(payload),
    )
    assert notifier.should_notify("CRITICAL")
    assert notifier.should_notify("HIGH")
    assert not notifier.should_notify("MEDIUM")

    controller = SurveillanceController(notifier=notifier)
    for index in range(14):
        ts = START + timedelta(minutes=5 * index)
        volume = 9000.0 if index == 13 else 100.0 + (index % 3) * 10
        controller.process_batch(
            _batch(index, {"A.NS": _candle("A.NS", ts, volume=volume)})
        )
    # The volume spike produced at least one HIGH/CRITICAL alert, each
    # delivered exactly once, and no MEDIUM/LOW alert was delivered.
    assert delivered, "expected at least one delivered high-severity alert"
    assert len(delivered) == len({payload["alert_id"] for payload in delivered})
    for payload in delivered:
        assert payload["symbol"] == "A.NS"
        assert payload["severity"] in ("HIGH", "CRITICAL")
        assert 0.0 <= payload["risk_score"] <= 100.0


def test_webhook_delivery_failure_does_not_break_pipeline():
    def failing_poster(url, payload, timeout):
        raise RuntimeError("network down")

    notifier = WebhookNotifier("https://example.invalid/hook", poster=failing_poster)
    controller = SurveillanceController(notifier=notifier)
    result = controller.process_batch(
        _batch(0, {"A.NS": _candle("A.NS", START)})
    )
    assert result.batch is not None  # pipeline survived the delivery failure


# ── Ingest + candles API ─────────────────────────────────────────────────────

def _csv_bytes(symbol: str = "UPLOAD.NS", rows: int = 12) -> bytes:
    ts = [START + timedelta(minutes=5 * i) for i in range(rows)]
    df = pd.DataFrame(
        {
            "Datetime": [t.isoformat() for t in ts],
            "Open": [100.0 + i for i in range(rows)],
            "High": [101.0 + i for i in range(rows)],
            "Low": [99.0 + i for i in range(rows)],
            "Close": [100.5 + i for i in range(rows)],
            "Volume": [1000.0 + 50 * i for i in range(rows)],
        }
    )
    return df.to_csv(index=False).encode()


def test_ingest_csv_then_stocks_and_candles(tmp_path: Path):
    service = MarketWatchAPI(settings=_test_settings(tmp_path))
    client = TestClient(create_app(service))

    response = client.post(
        "/ingest",
        params={"symbol": "UPLOAD.NS"},
        content=_csv_bytes(),
        headers={"content-type": "text/csv"},
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["rows_loaded"] == 12
    assert payload["rows_dropped"] == 0

    stocks = client.get("/stocks")
    assert "UPLOAD.NS" in stocks.json()["symbols"]

    candles = client.get("/candles", params={"symbol": "UPLOAD.NS"})
    assert candles.status_code == 200
    body = candles.json()
    assert body["count"] == 12
    assert {"timestamp", "open", "high", "low", "close", "volume"} <= set(body["candles"][0])


def test_ingest_rejects_garbage_and_candles_404(tmp_path: Path):
    service = MarketWatchAPI(settings=_test_settings(tmp_path))
    client = TestClient(create_app(service))

    bad = client.post("/ingest", params={"symbol": "X.NS"}, content=b"not a csv at all \x00\x01")
    assert bad.status_code in (400, 422)

    missing = client.get("/candles", params={"symbol": "NOPE.NS"})
    assert missing.status_code == 404


def _test_settings(tmp_path: Path):
    from marketwatch.config.settings import Settings

    return Settings(
        data_dir=str(tmp_path / "data"),
        curated_dir=str(tmp_path / "data" / "curated"),
        metadata_file=str(tmp_path / "data" / "curated" / "quality_metadata.json"),
    )


# ── Settings-driven wiring ───────────────────────────────────────────────────

def test_api_applies_settings_cooldown_and_weights(tmp_path: Path):
    service = MarketWatchAPI(settings=_test_settings(tmp_path))
    # Default YAML: 6 bars x 5 minutes = 30 minute cooldown.
    assert service.controller.alert_engine.cooldown == timedelta(minutes=30)
    assert isinstance(service.controller.risk_scorer, RiskScorer)
    assert service.controller.risk_scorer.detector_weights["IsolationForestDetector"] == 0.40

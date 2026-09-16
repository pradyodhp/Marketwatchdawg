"""Phase 5 validation: z-score and EWMA anomaly detectors."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from marketwatch.detectors import (
    EWMADetector,
    ZScoreDetector,
    detect_ewma_anomalies,
    detect_z_score_anomalies,
)
from marketwatch.features import FeaturePipeline
from marketwatch.models.features import FeatureSet
from marketwatch.models.signals import AnomalySeverity, AnomalySignal

IST = ZoneInfo("Asia/Kolkata")


def _feature(symbol: str, ts: datetime, slot: int, **kwargs: float) -> FeatureSet:
    data = {
        "log_return": kwargs.get("log_return", 0.0),
        "volume_ratio": kwargs.get("volume_ratio", 1.0),
        "parkinson_volatility": kwargs.get("parkinson_volatility", 0.0),
        "market_excess_return": kwargs.get("market_excess_return", 0.0),
        "sector_excess_return": kwargs.get("sector_excess_return", 0.0),
    }
    return FeatureSet(
        symbol=symbol,
        timestamp=ts,
        slot_index=slot,
        log_return=data["log_return"],
        volume_ratio=data["volume_ratio"],
        parkinson_volatility=data["parkinson_volatility"],
        market_excess_return=data["market_excess_return"],
        sector_excess_return=data["sector_excess_return"],
        raw_features=data,
    )


def test_zscore_detector_mathematically_correct():
    base_ts = datetime(2026, 9, 15, 9, 15, tzinfo=IST)
    history = [
        _feature("A.NS", base_ts + timedelta(days=i, minutes=5), 5, log_return=float(v))
        for i, v in enumerate([-1.0, 0.0, 1.0])
    ]
    current = _feature("A.NS", base_ts + timedelta(days=3, minutes=5), 5, log_return=3.0)
    signals = ZScoreDetector(threshold=2.5, min_observations=3).detect(history + [current])
    current_signal = next(signal for signal in signals if signal.timestamp == current.timestamp and signal.feature_name == "log_return")

    assert current_signal.is_valid is True
    assert current_signal.z_score == pytest.approx(3.0, rel=1e-6)
    assert current_signal.anomaly is True
    assert current_signal.direction == pytest.approx(1.0)
    assert current_signal.severity in {AnomalySeverity.HIGH, AnomalySeverity.CRITICAL}


def test_zscore_negative_deviation_and_threshold_boundary():
    base_ts = datetime(2026, 9, 15, 9, 15, tzinfo=IST)
    history = [
        _feature("A.NS", base_ts + timedelta(days=i, minutes=5), 5, log_return=float(v))
        for i, v in enumerate([-1.0, 0.0, 1.0])
    ]
    current = _feature("A.NS", base_ts + timedelta(days=3, minutes=5), 5, log_return=-3.0)
    signals = ZScoreDetector(threshold=3.0, min_observations=3).detect(history + [current])
    current_signal = next(signal for signal in signals if signal.timestamp == current.timestamp)

    assert current_signal.z_score == pytest.approx(-3.0, rel=1e-6)
    assert current_signal.anomaly is True
    assert current_signal.direction == pytest.approx(-1.0)


def test_zscore_zero_std_becomes_safe_zero_statistic():
    base_ts = datetime(2026, 9, 15, 9, 15, tzinfo=IST)
    history = [_feature("A.NS", base_ts + timedelta(days=i, minutes=5), 5, log_return=0.2) for i in range(3)]
    current = _feature("A.NS", base_ts + timedelta(days=3, minutes=5), 5, log_return=0.9)
    signals = ZScoreDetector(threshold=3.0, min_observations=3).detect(history + [current])
    current_signal = next(signal for signal in signals if signal.timestamp == current.timestamp)

    assert current_signal.z_score == pytest.approx(0.0)
    assert current_signal.anomaly is False
    assert current_signal.is_valid is True


def test_zscore_insufficient_history_is_invalid_and_non_anomalous():
    base_ts = datetime(2026, 9, 15, 9, 15, tzinfo=IST)
    history = [_feature("A.NS", base_ts, 5, log_return=0.1)]
    current = _feature("A.NS", base_ts + timedelta(minutes=5), 5, log_return=10.0)
    signals = ZScoreDetector(threshold=2.5, min_observations=3).detect(history + [current])
    current_signal = next(signal for signal in signals if signal.timestamp == current.timestamp)

    assert current_signal.is_valid is False
    assert current_signal.reason == "insufficient_history"
    assert current_signal.anomaly is False


def test_ewma_initializes_and_walks_with_prior_state():
    base_ts = datetime(2026, 9, 15, 9, 15, tzinfo=IST)
    history = [
        _feature("A.NS", base_ts + timedelta(minutes=5 * i), i, log_return=float(v))
        for i, v in enumerate([0.0, 1.0, 2.0])
    ]
    detector = EWMADetector(alpha=0.5, threshold=1.5, min_periods=2)
    signals = detector.detect(history)

    assert any(signal.reason == "warmup_initialization" for signal in signals)
    assert any(signal.is_valid is True and signal.feature_name == "log_return" for signal in signals)


def test_ewma_detects_large_change_without_future_lookahead():
    base_ts = datetime(2026, 9, 15, 9, 15, tzinfo=IST)
    history = [
        _feature("A.NS", base_ts + timedelta(minutes=5 * i), 5, log_return=float(v))
        for i, v in enumerate([0.0, 0.1, 0.2, 0.3])
    ]
    current = _feature("A.NS", base_ts + timedelta(days=3, minutes=5), 5, log_return=5.0)
    signals = EWMADetector(alpha=0.5, threshold=1.0, min_periods=2).detect(history + [current])
    current_signal = next(signal for signal in signals if signal.timestamp == current.timestamp and signal.feature_name == "log_return")

    assert current_signal.is_valid is True
    assert current_signal.anomaly is True
    assert current_signal.direction == pytest.approx(1.0)


def test_detector_output_contract_is_complete():
    base_ts = datetime(2026, 9, 15, 9, 15, tzinfo=IST)
    history = [_feature("A.NS", base_ts, 0, log_return=0.0), _feature("A.NS", base_ts + timedelta(minutes=5), 1, log_return=2.0)]
    current = _feature("A.NS", base_ts + timedelta(minutes=10), 2, log_return=4.0)
    signal = next(
        signal
        for signal in ZScoreDetector(threshold=2.0, min_observations=2).detect(history + [current])
        if signal.timestamp == current.timestamp and signal.feature_name == "log_return"
    )

    assert isinstance(signal, AnomalySignal)
    assert signal.detector_name == "ZScoreDetector"
    assert signal.anomaly in {True, False}
    assert signal.direction in {-1.0, 0.0, 1.0}
    assert signal.metadata["detector_type"] == "z_score"
    assert signal.baseline_mean == signal.baseline_value


def test_phase5_integration_with_feature_pipeline_and_slot_alignment():
    from marketwatch.models.candle import Candle

    start = datetime(2026, 9, 15, 9, 15, tzinfo=IST)
    pipeline = FeaturePipeline()
    previous = None
    features = []
    for i in range(4):
        candle = Candle(
            symbol="RELIANCE.NS",
            timestamp=start + timedelta(minutes=5 * i),
            open=100.0 + i,
            high=101.0 + i,
            low=99.0 + i,
            close=100.5 + i,
            volume=1000.0 + i * 100,
        )
        feature = pipeline.compute_feature_from_candle(candle, previous)
        features.append(feature)
        previous = candle

    signals = detect_z_score_anomalies(features, feature_names=["volume_ratio"], threshold=1.5, min_observations=2)
    assert signals
    assert {signal.slot_index for signal in signals} <= {0, 1, 2, 3}
    assert all(signal.timestamp.tzinfo is not None for signal in signals)


def test_no_lookahead_leakage_in_detector_baselines():
    base_ts = datetime(2026, 9, 15, 9, 15, tzinfo=IST)
    history = [
        _feature("A.NS", base_ts + timedelta(minutes=5 * i), i, log_return=float(i))
        for i in range(4)
    ]
    current = _feature("A.NS", base_ts + timedelta(minutes=20), 4, log_return=10.0)
    signal = next(
        signal
        for signal in ZScoreDetector(threshold=3.0, min_observations=2).detect(history + [current])
        if signal.timestamp == current.timestamp
    )

    assert signal.metadata["baseline_count"] <= 4
    assert signal.metadata["baseline_count"] < 5


def test_multiple_symbols_and_feature_names_stay_deterministic():
    base_ts = datetime(2026, 9, 15, 9, 15, tzinfo=IST)
    history = [
        _feature("A.NS", base_ts, 0, log_return=0.0, volume_ratio=1.0),
        _feature("B.NS", base_ts, 0, log_return=0.0, volume_ratio=1.0),
        _feature("A.NS", base_ts + timedelta(minutes=5), 1, log_return=1.0, volume_ratio=3.0),
        _feature("B.NS", base_ts + timedelta(minutes=5), 1, log_return=2.0, volume_ratio=2.0),
    ]
    signals_a = detect_z_score_anomalies(history, symbol="A.NS", threshold=1.0, min_observations=1)
    signals_b = detect_z_score_anomalies(history, symbol="A.NS", threshold=1.0, min_observations=1)

    assert [signal.model_dump(mode="json") for signal in signals_a] == [signal.model_dump(mode="json") for signal in signals_b]
    assert {signal.symbol for signal in signals_a} == {"A.NS"}
    assert any(signal.feature_name in {"log_return", "volume_ratio"} for signal in signals_a)


def test_ewma_function_wrapper_returns_structured_signals():
    base_ts = datetime(2026, 9, 15, 9, 15, tzinfo=IST)
    history = [
        _feature("A.NS", base_ts + timedelta(minutes=5 * i), i, log_return=float(i))
        for i in range(3)
    ]
    signals = detect_ewma_anomalies(history, feature_names=["log_return"], alpha=0.5, threshold=1.0, min_periods=2)

    assert signals
    assert all(isinstance(signal, AnomalySignal) for signal in signals)
    assert all(signal.feature_name == "log_return" for signal in signals)

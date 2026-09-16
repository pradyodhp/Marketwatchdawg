"""Phase 6 validation: multivariate model and temporal validation."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pytest

from marketwatch.isolation_forest import (
    FeatureMatrixBuilder,
    IsolationForestDetector,
    chronological_split,
)
from marketwatch.models.features import FeatureSet
from marketwatch.models.signals import AnomalySignal

IST = ZoneInfo("Asia/Kolkata")


def _feature(index: int, *, symbol: str = "A.NS", shock: bool = False) -> FeatureSet:
    timestamp = datetime(2026, 9, 15, 9, 15, tzinfo=IST) + timedelta(days=index)
    value = 8.0 if shock else (float(index) - 5.5) * 0.05
    return FeatureSet(
        symbol=symbol,
        timestamp=timestamp,
        slot_index=0,
        log_return=value,
        volume_ratio=1.0 + value,
        parkinson_volatility=0.01 + abs(value),
        market_excess_return=value * 0.2,
        sector_excess_return=value * 0.1,
        raw_features={},
    )


def test_feature_matrix_has_explicit_order_and_metadata_separation():
    features = [_feature(2), _feature(0), _feature(1)]
    matrix = FeatureMatrixBuilder(["volume_ratio", "log_return"]).build(features)

    assert matrix.feature_names == ("volume_ratio", "log_return")
    assert [item.timestamp for item in matrix.features] == sorted(item.timestamp for item in features)
    assert matrix.values.shape == (3, 2)
    assert matrix.values[0, 0] == pytest.approx(0.725)


def test_invalid_matrix_rows_are_dropped_without_fabrication():
    invalid = FeatureSet.model_construct(
        symbol="A.NS",
        timestamp=datetime(2026, 9, 15, 9, 15, tzinfo=IST),
        slot_index=0,
        log_return=float("nan"),
        volume_ratio=1.0,
        parkinson_volatility=0.1,
        market_excess_return=0.0,
        sector_excess_return=0.0,
        raw_features={},
    )
    matrix = FeatureMatrixBuilder().build([_feature(0), invalid])

    assert len(matrix.features) == 1
    assert matrix.dropped_count == 1
    assert np.isfinite(matrix.values).all()


def test_invalid_evaluation_rows_emit_invalid_signals():
    invalid = FeatureSet.model_construct(
        symbol="A.NS",
        timestamp=datetime(2026, 9, 30, 9, 15, tzinfo=IST),
        slot_index=0,
        log_return=float("inf"),
        volume_ratio=1.0,
        parkinson_volatility=0.1,
        market_excess_return=0.0,
        sector_excess_return=0.0,
        raw_features={},
    )
    detector = IsolationForestDetector(min_training_samples=3, random_state=1)
    signals = detector.fit_score([_feature(index) for index in range(5)], [invalid])

    assert len(signals) == 1
    assert signals[0].is_valid is False
    assert signals[0].reason == "invalid_feature_row"


def test_isolation_forest_detects_multivariate_shock_deterministically():
    training = [_feature(index) for index in range(12)]
    evaluation = [_feature(12, shock=True)]
    detector_a = IsolationForestDetector(n_estimators=50, contamination=0.1, random_state=7)
    detector_b = IsolationForestDetector(n_estimators=50, contamination=0.1, random_state=7)

    signal_a = detector_a.fit_score(training, evaluation)[0]
    signal_b = detector_b.fit_score(training, evaluation)[0]

    assert isinstance(signal_a, AnomalySignal)
    assert signal_a.is_valid is True
    assert signal_a.anomaly is True
    assert signal_a.feature_name == "__multivariate__"
    assert signal_a.direction == 0.0
    assert signal_a.model_dump(mode="json") == signal_b.model_dump(mode="json")


def test_insufficient_and_constant_training_are_explicitly_invalid():
    evaluation = [_feature(4)]
    insufficient = IsolationForestDetector(min_training_samples=5)
    constant = IsolationForestDetector(min_training_samples=3)
    constant_training = [_feature(index) for index in range(3)]
    for item in constant_training:
        for field_name, value in (
            ("log_return", 1.0),
            ("volume_ratio", 2.0),
            ("parkinson_volatility", 1.0),
            ("market_excess_return", 1.0),
            ("sector_excess_return", 1.0),
        ):
            object.__setattr__(item, field_name, value)

    insufficient_signal = insufficient.fit_score([_feature(0), _feature(1)], evaluation)[0]
    constant_signal = constant.fit_score(constant_training, evaluation)[0]

    assert insufficient_signal.is_valid is False
    assert insufficient_signal.reason == "insufficient_training_data"
    assert constant_signal.is_valid is False
    assert constant_signal.reason == "constant_features"


def test_chronological_split_excludes_boundary_from_training():
    features = [_feature(index) for index in range(5)]
    boundary = features[3].timestamp
    split = chronological_split(features, train_end=boundary)

    assert len(split.train) == 3
    assert len(split.evaluation) == 2
    assert all(item.timestamp < boundary for item in split.train)
    assert all(item.timestamp >= boundary for item in split.evaluation)


def test_current_and_future_observations_cannot_change_earlier_prediction():
    training = [_feature(index) for index in range(12)]
    first_evaluation = [_feature(12, shock=True)]
    future = [_feature(13, shock=True), _feature(14, shock=True)]

    first = IsolationForestDetector(n_estimators=40, contamination="auto", random_state=11)
    with_future = IsolationForestDetector(n_estimators=40, contamination="auto", random_state=11)
    first_signal = first.fit_score(training, first_evaluation)[0]
    future_signals = with_future.fit_score(training, first_evaluation + future)

    assert first_signal.model_dump(mode="json") == future_signals[0].model_dump(mode="json")
    assert first_signal.metadata["train_end"] == training[-1].timestamp.isoformat()
    assert first_signal.timestamp not in [item.timestamp for item in training]


def test_walk_forward_is_chronological_and_inspectable():
    features = [_feature(index, symbol="A.NS" if index % 2 == 0 else "B.NS") for index in range(14)]
    detector = IsolationForestDetector(n_estimators=20, min_training_samples=8, random_state=3)
    results = detector.walk_forward(features)

    assert len(results) == 6
    assert all(result.train_end < result.evaluation_start for result in results)
    assert all(result.signals[0].timestamp == result.evaluation_start for result in results)
    assert [result.evaluation_start for result in results] == sorted(result.evaluation_start for result in results)


def test_missing_symbols_are_not_created():
    detector = IsolationForestDetector(min_training_samples=3, random_state=1)
    signals = detector.fit_score([_feature(index, symbol="A.NS") for index in range(5)], [_feature(5, symbol="A.NS")])

    assert {signal.symbol for signal in signals} == {"A.NS"}
    assert "MISSING.NS" not in {signal.symbol for signal in signals}

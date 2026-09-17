"""Phase 7 validation: transparent risk scoring and signal fusion."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from marketwatch.models.signals import AnomalySeverity, AnomalySignal
from marketwatch.risk import RiskAssessment, RiskScorer, RiskSeverity

IST = ZoneInfo("Asia/Kolkata")
TS = datetime(2026, 9, 15, 9, 15, tzinfo=IST)


def _signal(
    detector: str,
    statistic: float,
    threshold: float,
    *,
    feature: str = "log_return",
    valid: bool = True,
    reason: str | None = None,
    anomaly: bool = True,
) -> AnomalySignal:
    return AnomalySignal(
        detector_name=detector,
        symbol="A.NS",
        timestamp=TS,
        slot_index=0,
        feature_name=feature,
        value=statistic,
        baseline_value=0.0,
        baseline_mean=0.0,
        baseline_std=1.0,
        statistic=statistic,
        z_score=statistic,
        threshold=threshold,
        severity=AnomalySeverity.HIGH if anomaly else AnomalySeverity.LOW,
        anomaly=anomaly,
        direction=1.0,
        is_valid=valid,
        reason=reason,
    )


def test_score_is_bounded_and_maps_severity_boundaries():
    scorer = RiskScorer(agreement_bonus=0.0)
    low = scorer.score([_signal("ZScoreDetector", 0.2, 3.0)])
    medium = scorer.score([_signal("ZScoreDetector", 1.5, 3.0)])
    high = scorer.score([_signal("ZScoreDetector", 2.1, 3.0)])
    critical = scorer.score([_signal("ZScoreDetector", 3.0, 3.0)])

    assert low.risk_score == pytest.approx(6.666667)
    assert low.severity is RiskSeverity.LOW
    assert medium.severity is RiskSeverity.MEDIUM
    assert high.severity is RiskSeverity.HIGH
    assert critical.risk_score == pytest.approx(100.0)
    assert critical.severity is RiskSeverity.CRITICAL
    assert all(0.0 <= item.risk_score <= 100.0 for item in (low, medium, high, critical))


def test_weighted_fusion_and_agreement_bonus_are_explicit():
    signals = [
        _signal("ZScoreDetector", 3.0, 3.0),
        _signal("EWMADetector", 1.25, 2.5, feature="volume_ratio"),
        _signal("IsolationForestDetector", 0.25, 0.0, feature="__multivariate__"),
    ]
    result = RiskScorer(agreement_bonus=0.10).score(signals)

    assert result.detector_agreement == 3
    assert result.active_detectors == (
        "EWMADetector",
        "IsolationForestDetector",
        "ZScoreDetector",
    )
    assert result.metadata["base_score"] == pytest.approx(67.5)
    assert result.metadata["agreement_bonus"] == pytest.approx(10.0)
    assert result.risk_score == pytest.approx(77.5)
    assert sum(item.weighted_contribution for item in result.contributions) == pytest.approx(0.675)


def test_multiple_features_from_one_detector_do_not_double_count():
    scorer = RiskScorer(agreement_bonus=0.0)
    result = scorer.score(
        [
            _signal("ZScoreDetector", 3.0, 3.0, feature="log_return"),
            _signal("ZScoreDetector", 2.0, 3.0, feature="volume_ratio"),
        ]
    )

    assert result.risk_score == pytest.approx(100.0)
    assert len(result.contributions) == 1
    assert result.contributions[0].feature_name == "log_return"


def test_missing_and_invalid_detectors_are_reported_without_fabrication():
    result = RiskScorer().score(
        [
            _signal("ZScoreDetector", 3.0, 3.0),
            _signal("EWMADetector", 0.0, 2.5, valid=False, reason="insufficient_history", anomaly=False),
        ]
    )

    assert result.valid is True
    assert result.active_detectors == ("ZScoreDetector",)
    assert "EWMADetector" in result.missing_detectors
    assert "IsolationForestDetector" in result.missing_detectors
    assert result.risk_score == pytest.approx(100.0)


def test_no_valid_evidence_is_explicitly_invalid():
    result = RiskScorer().score(
        [_signal("ZScoreDetector", 0.0, 3.0, valid=False, reason="insufficient_history", anomaly=False)]
    )

    assert isinstance(result, RiskAssessment)
    assert result.valid is False
    assert result.risk_score == 0.0
    assert result.severity is RiskSeverity.LOW
    assert result.reason == "insufficient_history"


def test_extreme_values_are_bounded_and_metadata_preserved():
    signal = _signal("ZScoreDetector", 10_000.0, 0.1)
    signal = signal.model_copy(update={"metadata": {"baseline_count": 12, "detector_type": "z_score"}})
    result = RiskScorer().score([signal])

    assert result.risk_score == 100.0
    assert result.contributions[0].metadata["baseline_count"] == 12


def test_repeated_scoring_and_grouped_scoring_are_deterministic():
    signals = [
        _signal("ZScoreDetector", 2.0, 3.0),
        _signal("IsolationForestDetector", 0.2, 0.0, feature="__multivariate__"),
    ]
    scorer = RiskScorer()
    first = scorer.score(signals)
    second = scorer.score(signals)
    grouped = scorer.score_many(list(reversed(signals)))[0]

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.model_dump(mode="json") == grouped.model_dump(mode="json")


def test_current_timestamp_is_scored_without_future_signal_influence():
    current = _signal("ZScoreDetector", 2.0, 3.0)
    future = _signal("ZScoreDetector", 3.0, 3.0).model_copy(
        update={"timestamp": datetime(2026, 9, 15, 9, 20, tzinfo=IST), "slot_index": 1}
    )

    current_result = RiskScorer().score([current])
    future_result = RiskScorer().score([current, future], timestamp=TS)

    assert current_result.model_dump(mode="json") == future_result.model_dump(mode="json")


def test_mismatched_unfiltered_signal_groups_are_rejected():
    future = _signal("ZScoreDetector", 2.0, 3.0).model_copy(
        update={"timestamp": datetime(2026, 9, 15, 9, 20, tzinfo=IST), "slot_index": 1}
    )
    with pytest.raises(ValueError, match="same symbol and timestamp"):
        RiskScorer().score([_signal("ZScoreDetector", 2.0, 3.0), future])


def test_custom_weights_and_thresholds_are_configurable():
    scorer = RiskScorer(
        detector_weights={"ZScoreDetector": 1.0},
        severity_thresholds={"medium": 40.0, "high": 60.0, "critical": 90.0},
        agreement_bonus=0.0,
    )
    result = scorer.score([_signal("ZScoreDetector", 2.0, 3.0)])

    assert result.weights == {"ZScoreDetector": 1.0}
    assert result.severity is RiskSeverity.HIGH

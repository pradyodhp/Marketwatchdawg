"""Phase 8 validation: deterministic surveillance explanations."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from marketwatch.explainability import (
    EXPLANATION_DISCLAIMER,
    ExplainabilityEngine,
    ExplanationFactorType,
)
from marketwatch.models.features import FeatureSet
from marketwatch.models.signals import AnomalySeverity, AnomalySignal
from marketwatch.risk import RiskScorer, RiskSeverity

IST = ZoneInfo("Asia/Kolkata")
TS = datetime(2026, 9, 15, 9, 15, tzinfo=IST)


def _signal(
    detector: str,
    statistic: float,
    threshold: float,
    *,
    feature: str = "volume_ratio",
    valid: bool = True,
    reason: str | None = None,
) -> AnomalySignal:
    return AnomalySignal(
        detector_name=detector,
        symbol="A.NS",
        timestamp=TS,
        slot_index=0,
        feature_name=feature,
        value=statistic,
        baseline_value=1.0,
        baseline_mean=1.0,
        baseline_std=0.2,
        statistic=statistic,
        z_score=statistic,
        threshold=threshold,
        severity=AnomalySeverity.HIGH if valid else AnomalySeverity.LOW,
        anomaly=valid,
        direction=1.0,
        is_valid=valid,
        reason=reason,
        metadata={"source": detector},
    )


def _feature() -> FeatureSet:
    return FeatureSet(
        symbol="A.NS",
        timestamp=TS,
        slot_index=0,
        log_return=0.012,
        volume_ratio=4.5,
        parkinson_volatility=0.031,
        market_excess_return=0.008,
        sector_excess_return=0.006,
        raw_features={},
    )


def test_explanation_contract_contains_score_and_disclaimer():
    signals = [
        _signal("ZScoreDetector", 3.0, 3.0),
        _signal("EWMADetector", 2.5, 2.5, feature="log_return"),
        _signal("IsolationForestDetector", 0.25, 0.0, feature="__multivariate__"),
    ]
    assessment = RiskScorer().score(signals)
    explanation = ExplainabilityEngine().explain(assessment, signals=signals, feature=_feature())

    assert explanation.risk_score == assessment.risk_score
    assert explanation.severity is RiskSeverity.CRITICAL
    assert EXPLANATION_DISCLAIMER in explanation.disclaimer
    assert explanation.valid is True
    assert explanation.contributing_detectors == (
        "EWMADetector",
        "IsolationForestDetector",
        "ZScoreDetector",
    )


def test_detector_and_feature_factors_are_explicit_and_ordered():
    signals = [
        _signal("ZScoreDetector", 3.0, 3.0),
        _signal("IsolationForestDetector", 0.25, 0.0, feature="__multivariate__"),
    ]
    assessment = RiskScorer().score(signals)
    explanation = ExplainabilityEngine().explain(assessment, signals=signals, feature=_feature())

    keys = [(factor.factor_type.value, factor.key) for factor in explanation.factors]
    assert keys == sorted(keys)
    assert {factor.detector_name for factor in explanation.factors if factor.factor_type is ExplanationFactorType.DETECTOR} == {
        "IsolationForestDetector",
        "ZScoreDetector",
    }
    assert {factor.feature_name for factor in explanation.factors if factor.factor_type is ExplanationFactorType.FEATURE} >= {
        "volume_ratio",
        "log_return",
        "parkinson_volatility",
    }
    assert any("Isolation Forest identified" in factor.detail for factor in explanation.factors)


def test_agreement_bonus_and_score_composition_are_explained():
    signals = [
        _signal("ZScoreDetector", 3.0, 3.0),
        _signal("EWMADetector", 2.5, 2.5, feature="log_return"),
    ]
    assessment = RiskScorer().score(signals)
    explanation = ExplainabilityEngine().explain(assessment, signals=signals)

    agreement = next(
        factor for factor in explanation.factors
        if factor.factor_type is ExplanationFactorType.AGREEMENT
    )
    assert assessment.metadata["agreement_bonus"] == 10.0
    assert str(assessment.metadata["agreement_bonus"]) in agreement.detail
    assert explanation.metadata["base_score"] == assessment.metadata["base_score"]
    assert explanation.metadata["agreement_bonus"] == assessment.metadata["agreement_bonus"]


def test_missing_and_insufficient_evidence_is_not_fabricated():
    signals = [
        _signal("ZScoreDetector", 0.0, 3.0, valid=False, reason="insufficient_history"),
    ]
    assessment = RiskScorer().score(signals)
    explanation = ExplainabilityEngine().explain(assessment, signals=signals)

    assert explanation.valid is False
    assert explanation.risk_score == 0.0
    assert explanation.reason == "insufficient_history"
    assert any(
        factor.factor_type is ExplanationFactorType.DATA_QUALITY
        and factor.valid is False
        for factor in explanation.factors
    )
    assert "could not be fully assessed" in explanation.summary


def test_future_signals_and_mismatched_features_are_ignored():
    current = _signal("ZScoreDetector", 2.0, 3.0)
    future = current.model_copy(update={"timestamp": datetime(2026, 9, 15, 9, 20, tzinfo=IST), "slot_index": 1})
    assessment = RiskScorer().score([current])
    engine = ExplainabilityEngine()

    first = engine.explain(assessment, signals=[current], feature=_feature())
    with_future = engine.explain(assessment, signals=[current, future], feature=_feature())

    assert first.model_dump(mode="json") == with_future.model_dump(mode="json")


def test_repeated_explanations_are_identical_and_neutral():
    signals = [_signal("ZScoreDetector", 10000.0, 0.1)]
    assessment = RiskScorer().score(signals)
    engine = ExplainabilityEngine()

    first = engine.explain(assessment, signals=signals, feature=_feature())
    second = engine.explain(assessment, signals=signals, feature=_feature())
    serialized = first.model_dump_json()

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert "manipulation" not in first.summary.lower()
    assert "fraud" not in first.summary.lower()
    assert "intent" not in first.summary.lower()
    assert serialized == second.model_dump_json()

"""Phase 9 alert creation, deduplication, and lifecycle tests."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from marketwatch.alert_engine import AlertEngine, AlertState
from marketwatch.explainability import ExplainabilityEngine
from marketwatch.models.signals import AnomalySeverity, AnomalySignal
from marketwatch.risk import RiskScorer

IST = ZoneInfo("Asia/Kolkata")
TS = datetime(2026, 9, 17, 9, 15, tzinfo=IST)


def _signal(valid: bool = True) -> AnomalySignal:
    return AnomalySignal(
        detector_name="ZScoreDetector",
        symbol="A.NS",
        timestamp=TS,
        slot_index=0,
        feature_name="volume_ratio",
        value=4.0,
        baseline_value=1.0,
        baseline_mean=1.0,
        baseline_std=0.2,
        statistic=4.0,
        z_score=4.0,
        threshold=3.0,
        severity=AnomalySeverity.HIGH if valid else AnomalySeverity.LOW,
        anomaly=valid,
        direction=1.0,
        is_valid=valid,
        reason=None if valid else "insufficient_history",
        metadata={"model": "zscore"},
    )


def _assessment():
    return RiskScorer().score([_signal()])


def _alert(engine: AlertEngine):
    assessment = _assessment()
    explanation = ExplainabilityEngine().explain(assessment)
    return engine.process(assessment, explanation=explanation)


def test_alert_creation_propagates_phase_7_and_phase_8_evidence():
    engine = AlertEngine()
    assessment = _assessment()
    explanation = ExplainabilityEngine().explain(assessment)
    alert = engine.process(assessment, explanation=explanation)

    assert alert.alert_id.startswith("alert-")
    assert alert.risk_score == assessment.risk_score
    assert alert.severity.value == assessment.severity.value
    assert alert.state is AlertState.NEW
    assert alert.explanation == explanation
    assert alert.detector_metadata == ({"model": "zscore"},)
    assert alert.history[-1].to_state is AlertState.NEW


def test_identity_and_repeated_processing_are_deterministic():
    first = _alert(AlertEngine())
    engine = AlertEngine()
    second = engine.process(_assessment())
    duplicate = engine.process(_assessment())

    assert first.alert_id == second.alert_id
    assert duplicate is second
    assert len(engine.all()) == 1


def test_valid_lifecycle_transitions_preserve_evidence():
    engine = AlertEngine()
    original = _alert(engine)
    acknowledged = engine.transition(original.alert_id, AlertState.ACKNOWLEDGED)
    resolved = engine.transition(original.alert_id, AlertState.RESOLVED)

    assert acknowledged.state is AlertState.ACKNOWLEDGED
    assert resolved.state is AlertState.RESOLVED
    assert resolved.assessment == original.assessment
    assert resolved.explanation == original.explanation
    assert tuple(event.to_state for event in resolved.history) == (
        AlertState.NEW,
        AlertState.ACKNOWLEDGED,
        AlertState.RESOLVED,
    )


def test_invalid_transitions_and_unknown_alerts_are_rejected():
    engine = AlertEngine()
    alert = _alert(engine)

    with pytest.raises(ValueError, match="invalid alert transition"):
        engine.transition(alert.alert_id, AlertState.RESOLVED)
    engine.transition(alert.alert_id, AlertState.ACKNOWLEDGED)
    with pytest.raises(ValueError, match="invalid alert transition"):
        engine.transition(alert.alert_id, AlertState.NEW)
    engine.transition(alert.alert_id, AlertState.RESOLVED)
    with pytest.raises(ValueError, match="invalid alert transition"):
        engine.transition(alert.alert_id, AlertState.ACKNOWLEDGED)
    with pytest.raises(KeyError):
        engine.transition("alert-missing", AlertState.ACKNOWLEDGED)


def test_invalid_upstream_evidence_and_mismatched_explanation_are_rejected():
    engine = AlertEngine()
    with pytest.raises(ValueError, match="valid RiskAssessment"):
        engine.process(RiskScorer().score([_signal(valid=False)]))

    explanation = ExplainabilityEngine().explain(_assessment())
    mismatched = explanation.model_copy(update={"symbol": "B.NS"})
    with pytest.raises(ValueError, match="match the assessment"):
        engine.process(_assessment(), explanation=mismatched)


def test_transition_timestamp_is_explicit_and_alerts_are_chronological():
    engine = AlertEngine()
    alert = _alert(engine)
    later = datetime(2026, 9, 17, 9, 20, tzinfo=IST)
    updated = engine.transition(alert.alert_id, AlertState.ACKNOWLEDGED, timestamp=later)

    assert updated.history[-1].timestamp == later
    assert engine.all() == (updated,)


def test_configurable_cooldown_suppresses_repeated_symbol_events_until_resolution():
    engine = AlertEngine(cooldown_minutes=10)
    first = _alert(engine)
    later_assessment = _assessment().model_copy(
        update={"timestamp": datetime(2026, 9, 17, 9, 20, tzinfo=IST)}
    )

    suppressed = engine.process(later_assessment)
    assert suppressed is first
    assert len(engine.active()) == 1

    engine.transition(first.alert_id, AlertState.ACKNOWLEDGED)
    engine.transition(first.alert_id, AlertState.RESOLVED)
    created = engine.process(later_assessment)
    assert created.alert_id != first.alert_id
    assert len(engine.active()) == 1

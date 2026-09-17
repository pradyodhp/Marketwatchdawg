"""Phase 10 deterministic injection and genuine pipeline tests."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from marketwatch.controller import (
    InjectionConfig,
    InjectionType,
    SurveillanceController,
)
from marketwatch.models.candle import Candle, CandleBatch

IST = ZoneInfo("Asia/Kolkata")
START = datetime(2026, 9, 10, 9, 15, tzinfo=IST)


def _batch(index: int, volume: float = 100.0) -> CandleBatch:
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
    return CandleBatch(timestamp=timestamp, slot_index=0, candles={"A.NS": candle})


def _config(index: int = 4, *, enabled: bool = True) -> InjectionConfig:
    return InjectionConfig(
        target_symbol="A.NS",
        target_timestamp=START + timedelta(days=index),
        injection_type=InjectionType.VOLUME_SURGE,
        magnitude=8.0,
        enabled=enabled,
    )


def test_disabled_injection_preserves_source_and_missing_target_is_explicit():
    source = _batch(0)
    disabled = SurveillanceController.inject(source, _config(0, enabled=False))
    missing = SurveillanceController.inject(
        source,
        _config(0).model_copy(update={"target_symbol": "MISSING.NS"}),
    )

    assert disabled.batch == source
    assert disabled.applied is False
    assert disabled.reason == "injection_disabled"
    assert missing.batch == source
    assert missing.applied is False
    assert missing.reason == "target_symbol_missing"


def test_injection_is_deterministic_and_preserves_unaffected_candle_fields():
    source = _batch(0)
    first = SurveillanceController.inject(source, _config(0))
    second = SurveillanceController.inject(source, _config(0))

    assert source["A.NS"].volume == 100.0
    assert first.batch["A.NS"].volume == 800.0
    assert first.batch["A.NS"].open == source["A.NS"].open
    assert first.batch["A.NS"].high == source["A.NS"].high
    assert first.batch["A.NS"].low == source["A.NS"].low
    assert first.batch["A.NS"].close == source["A.NS"].close
    assert first.batch == second.batch
    assert first.is_simulated is True
    assert first.metadata["magnitude"] == 8.0


def test_invalid_configuration_and_duplicate_injection_are_rejected():
    with pytest.raises(ValueError):
        InjectionConfig(
            target_symbol="A.NS",
            target_timestamp=START,
            magnitude=0.0,
        )

    controller = SurveillanceController()
    controller.process_batch(_batch(0), injection=_config(0))
    with pytest.raises(ValueError, match="only one injection"):
        controller.process_batch(_batch(1), injection=_config(1))


def test_8x_volume_flows_through_features_detectors_risk_explanation_and_alert():
    batches = [_batch(0, 100.0), _batch(1, 110.0), _batch(2, 90.0), _batch(3, 100.0), _batch(4, 100.0)]
    controller = SurveillanceController()
    results = controller.replay(batches, injection=_config(4))
    result = results[-1]

    assert result.injection.applied is True
    assert result.batch["A.NS"].volume == 800.0
    assert result.features["A.NS"].volume_ratio == 8.0
    assert any(signal.anomaly for signal in result.signals)
    assert result.assessment is not None
    assert result.explanation is not None
    assert result.alert is not None
    assert result.alert.is_simulated is True
    assert result.alert.simulation_metadata["injection_type"] == "volume_surge"
    assert result.alert.risk_score == result.assessment.risk_score
    assert result.alert.severity.value == result.assessment.severity.value
    assert result.assessment.severity.value == "CRITICAL"


def test_repeated_controller_runs_produce_identical_outputs():
    batches = [_batch(0, 100.0), _batch(1, 110.0), _batch(2, 90.0), _batch(3, 100.0), _batch(4, 100.0)]
    first = SurveillanceController().replay(batches, injection=_config(4))
    second = SurveillanceController().replay(batches, injection=_config(4))

    assert [item.model_dump(mode="json") for item in first] == [
        item.model_dump(mode="json") for item in second
    ]

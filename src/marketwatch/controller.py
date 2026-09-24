"""Deterministic surveillance controller and raw-candle anomaly injection."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from marketwatch.alert_engine import AlertEngine, SurveillanceAlert
from marketwatch.detectors import EWMADetector, ZScoreDetector
from marketwatch.explainability import ExplainabilityEngine, SurveillanceExplanation
from marketwatch.features import FeaturePipeline
from marketwatch.isolation_forest import IsolationForestDetector
from marketwatch.models.candle import Candle, CandleBatch
from marketwatch.models.features import FeatureSet
from marketwatch.models.signals import AnomalySignal
from marketwatch.notifications import WebhookNotifier
from marketwatch.risk import RiskAssessment, RiskScorer

logger = logging.getLogger(__name__)


class InjectionType(str, Enum):
    """Supported deterministic raw-observation transformations."""

    VOLUME_SURGE = "volume_surge"


class InjectionConfig(BaseModel):
    """Minimal immutable configuration for one replay injection."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    target_symbol: str
    target_timestamp: datetime
    injection_type: InjectionType = InjectionType.VOLUME_SURGE
    magnitude: float = Field(default=8.0, gt=0.0)
    enabled: bool = True

    @field_validator("target_timestamp")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        return value


class InjectionResult(BaseModel):
    """Result of applying an injection to one candle batch."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    batch: CandleBatch
    applied: bool
    is_simulated: bool = False
    reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ControllerResult(BaseModel):
    """All downstream outputs for one evaluated current batch."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    batch: CandleBatch
    features: dict[str, FeatureSet]
    signals: tuple[AnomalySignal, ...]
    assessment: RiskAssessment | None = None
    explanation: SurveillanceExplanation | None = None
    alert: SurveillanceAlert | None = None
    assessments: tuple[RiskAssessment, ...] = ()
    alerts: tuple[SurveillanceAlert, ...] = ()
    injection: InjectionResult


class SurveillanceController:
    """Run raw candles through the existing deterministic surveillance stages."""

    def __init__(
        self,
        *,
        feature_pipeline: FeaturePipeline | None = None,
        zscore_detector: ZScoreDetector | None = None,
        ewma_detector: EWMADetector | None = None,
        risk_scorer: RiskScorer | None = None,
        isolation_forest_detector: IsolationForestDetector | None = None,
        explainability_engine: ExplainabilityEngine | None = None,
        alert_engine: AlertEngine | None = None,
        notifier: WebhookNotifier | None = None,
    ) -> None:
        self.feature_pipeline = feature_pipeline or FeaturePipeline()
        self.zscore_detector = zscore_detector or ZScoreDetector()
        self.ewma_detector = ewma_detector or EWMADetector()
        self.isolation_forest_detector = isolation_forest_detector or IsolationForestDetector()
        self.risk_scorer = risk_scorer or RiskScorer()
        self.explainability_engine = explainability_engine or ExplainabilityEngine()
        self.alert_engine = alert_engine or AlertEngine(cooldown_minutes=0)
        self.notifier = notifier
        self._feature_history: list[FeatureSet] = []
        self._previous_candles: dict[str, Candle] = {}
        self._injection_applied = False
        self._notified_alert_ids: set[str] = set()

    @staticmethod
    def inject(batch: CandleBatch, config: InjectionConfig | None) -> InjectionResult:
        """Apply one configured raw-candle transformation without mutating source data."""
        if config is None or not config.enabled:
            return InjectionResult(batch=batch, applied=False, reason="injection_disabled")
        if batch.timestamp != config.target_timestamp:
            return InjectionResult(batch=batch, applied=False, reason="target_not_reached")
        candle = batch.candles.get(config.target_symbol)
        if candle is None:
            return InjectionResult(batch=batch, applied=False, reason="target_symbol_missing")
        if config.injection_type is not InjectionType.VOLUME_SURGE:
            raise ValueError(f"unsupported injection type: {config.injection_type}")
        injected = candle.model_copy(update={"volume": candle.volume * config.magnitude})
        candles = dict(batch.candles)
        candles[config.target_symbol] = injected
        return InjectionResult(
            batch=batch.model_copy(update={"candles": candles}),
            applied=True,
            is_simulated=True,
            metadata={
                "target_symbol": config.target_symbol,
                "target_timestamp": config.target_timestamp.isoformat(),
                "injection_type": config.injection_type.value,
                "magnitude": config.magnitude,
            },
        )

    def process_batch(
        self,
        batch: CandleBatch,
        *,
        injection: InjectionConfig | None = None,
    ) -> ControllerResult:
        """Process one chronological batch through the genuine surveillance pipeline."""
        if (
            self._injection_applied
            and injection is not None
            and batch.timestamp == injection.target_timestamp
        ):
            raise ValueError("controller accepts only one injection per replay")
        injection_result = self.inject(batch, injection)
        if injection_result.applied:
            self._injection_applied = True
        current_batch = injection_result.batch
        features = self.feature_pipeline.process_batch(
            current_batch,
            previous_by_symbol=self._previous_candles,
        )
        self._previous_candles.update(current_batch.candles)
        # Isolation Forest is walk-forward: it may only train on history from
        # before the current batch, then scores the current batch.
        prior_history = list(self._feature_history)
        current_features = tuple(features.values())
        self._feature_history.extend(current_features)

        stat_signals = tuple(
            signal
            for detector in (self.zscore_detector, self.ewma_detector)
            for signal in detector.detect(self._feature_history)
            if any(
                signal.symbol == feature.symbol and signal.timestamp == feature.timestamp
                for feature in current_features
            )
        )
        ml_signals: tuple[AnomalySignal, ...] = ()
        if current_features:
            try:
                ml_signals = tuple(
                    self.isolation_forest_detector.fit_score(prior_history, list(current_features))
                )
            except (ValueError, RuntimeError) as exc:
                logger.warning("isolation forest scoring skipped for this batch: %s", exc)
                ml_signals = tuple(
                    self.isolation_forest_detector._invalid_signal(feature, "scoring_error")
                    for feature in current_features
                )
        signals = stat_signals + ml_signals

        # Score every symbol independently: one mixed-symbol scoring call used
        # to raise (and be silently swallowed), dropping all alerts for the batch.
        current_signals = [
            signal for signal in signals if signal.timestamp == current_batch.timestamp
        ]
        signals_by_symbol: dict[str, list[AnomalySignal]] = {}
        for signal in current_signals:
            signals_by_symbol.setdefault(signal.symbol, []).append(signal)

        assessments: list[RiskAssessment] = []
        for symbol_name in sorted(signals_by_symbol):
            try:
                assessments.append(
                    self.risk_scorer.score(
                        signals_by_symbol[symbol_name],
                        symbol=symbol_name,
                        timestamp=current_batch.timestamp,
                    )
                )
            except ValueError as exc:
                logger.warning(
                    "risk scoring failed for %s at %s: %s",
                    symbol_name, current_batch.timestamp.isoformat(), exc,
                )

        alerts: list[SurveillanceAlert] = []
        explanations: dict[str, SurveillanceExplanation] = {}
        for assessment in assessments:
            if not assessment.valid:
                continue
            feature = features.get(assessment.symbol)
            explanation = self.explainability_engine.explain(
                assessment,
                signals=current_signals,
                feature=feature,
            )
            alert = self.alert_engine.process(
                assessment,
                explanation=explanation,
                is_simulated=injection_result.is_simulated,
                simulation_metadata=injection_result.metadata,
            )
            explanations[assessment.symbol] = explanation
            alerts.append(alert)
            if (
                self.notifier is not None
                and alert.alert_id not in self._notified_alert_ids
                and self.notifier.notify(alert)
            ):
                self._notified_alert_ids.add(alert.alert_id)

        # Backward-compatible headline fields: highest-risk assessment/alert.
        assessment: RiskAssessment | None = None
        explanation: SurveillanceExplanation | None = None
        alert: SurveillanceAlert | None = None
        if assessments:
            assessment = max(
                (item for item in assessments if item.valid),
                key=lambda item: item.risk_score,
                default=None,
            )
            if assessment is None:
                assessment = assessments[0]
            else:
                explanation = explanations.get(assessment.symbol)
                alert = next(
                    (item for item in alerts if item.symbol == assessment.symbol),
                    alerts[0] if alerts else None,
                )
        return ControllerResult(
            batch=current_batch,
            features=features,
            signals=signals,
            assessment=assessment,
            explanation=explanation,
            alert=alert,
            assessments=tuple(assessments),
            alerts=tuple(alerts),
            injection=injection_result,
        )

    def replay(
        self,
        batches: Sequence[CandleBatch],
        *,
        injection: InjectionConfig | None = None,
    ) -> list[ControllerResult]:
        """Process batches in chronological order without future-data access."""
        ordered = sorted(batches, key=lambda item: (item.timestamp, item.slot_index))
        return [self.process_batch(batch, injection=injection) for batch in ordered]

    def reset(self) -> None:
        """Reset controller state and its in-memory alert registry."""
        self._feature_history.clear()
        self._previous_candles.clear()
        self._injection_applied = False
        self._notified_alert_ids.clear()
        self.alert_engine.clear()


__all__ = [
    "ControllerResult",
    "InjectionConfig",
    "InjectionResult",
    "InjectionType",
    "SurveillanceController",
]

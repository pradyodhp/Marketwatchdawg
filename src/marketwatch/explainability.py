"""Deterministic regulatory-oriented surveillance explanations."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from marketwatch.models.features import FeatureSet
from marketwatch.models.signals import AnomalySignal
from marketwatch.risk import RiskAssessment, RiskSeverity

EXPLANATION_DISCLAIMER = "Unusual activity does not establish manipulation, fraud, misconduct, or intent."


class _DeepFrozenDict(dict[str, Any]):
    """JSON-compatible dictionary that recursively rejects mutation."""

    def __init__(self, value: Mapping[str, Any] | None = None) -> None:
        dict.__init__(self, {key: _deep_freeze(item) for key, item in (value or {}).items()})

    @staticmethod
    def _immutable(*args: Any, **kwargs: Any) -> None:
        raise TypeError("immutable explanation metadata cannot be mutated")

    __delitem__ = __setitem__ = _immutable
    clear = pop = popitem = setdefault = update = _immutable

    def __ior__(self, value: Mapping[str, Any]):
        self._immutable(value)
        return self


def _deep_freeze(value: Any) -> Any:
    """Recursively convert JSON-like containers to immutable equivalents."""
    if isinstance(value, Mapping):
        return _DeepFrozenDict(value)
    if isinstance(value, list):
        return tuple(_deep_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_deep_freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(_deep_freeze(item) for item in value)
    return value


class ExplanationFactorType(str, Enum):
    """Stable categories for evidence displayed by future consumers."""

    DETECTOR = "detector"
    FEATURE = "feature"
    AGREEMENT = "agreement"
    DATA_QUALITY = "data_quality"


class ExplanationFactor(BaseModel):
    """One deterministic, structured piece of observable explanation evidence."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    factor_type: ExplanationFactorType
    key: str
    label: str
    detail: str
    detector_name: str | None = None
    feature_name: str | None = None
    value: float | None = None
    threshold: float | None = None
    normalized_evidence: float | None = Field(default=None, ge=0.0, le=1.0)
    weighted_contribution: float | None = Field(default=None, ge=0.0, le=1.0)
    valid: bool
    reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata", mode="after")
    @classmethod
    def freeze_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _deep_freeze(value)

    @model_validator(mode="after")
    def validate_finite_values(self) -> ExplanationFactor:
        for name in ("value", "threshold", "normalized_evidence", "weighted_contribution"):
            value = getattr(self, name)
            if value is not None and not math.isfinite(value):
                raise ValueError(f"Explanation factor field '{name}' must be finite")
        return self


class SurveillanceExplanation(BaseModel):
    """Structured explanation contract for a single Phase 7 assessment."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    timestamp: datetime
    slot_index: int = Field(ge=0, le=74)
    risk_score: float = Field(ge=0.0, le=100.0)
    severity: RiskSeverity
    summary: str
    factors: tuple[ExplanationFactor, ...] = ()
    contributing_detectors: tuple[str, ...] = ()
    contributing_features: tuple[str, ...] = ()
    valid: bool
    reason: str | None = None
    disclaimer: str = EXPLANATION_DISCLAIMER
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata", mode="after")
    @classmethod
    def freeze_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _deep_freeze(value)

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        return value

    @model_validator(mode="after")
    def validate_score(self) -> SurveillanceExplanation:
        if not math.isfinite(self.risk_score):
            raise ValueError("risk_score must be finite")
        if EXPLANATION_DISCLAIMER not in self.disclaimer:
            raise ValueError("disclaimer must include the required neutral disclaimer")
        return self


FEATURE_LABELS = {
    "log_return": "Price return",
    "volume_ratio": "Volume ratio",
    "parkinson_volatility": "Parkinson volatility",
    "market_excess_return": "Market excess return",
    "sector_excess_return": "Sector excess return",
    "buy_sell_pressure": "Buying/selling pressure (order-imbalance proxy)",
    "__multivariate__": "Multivariate feature combination",
}


class ExplainabilityEngine:
    """Compile neutral explanations from supplied Phase 5-7 outputs only."""

    def explain(
        self,
        assessment: RiskAssessment,
        *,
        signals: Sequence[AnomalySignal] = (),
        feature: FeatureSet | None = None,
    ) -> SurveillanceExplanation:
        """Build an explanation without recomputing or consulting future data."""
        matching_signals = tuple(
            sorted(
                (
                    signal
                    for signal in signals
                    if signal.symbol == assessment.symbol and signal.timestamp == assessment.timestamp
                ),
                key=lambda signal: (signal.detector_name, signal.feature_name),
            )
        )
        factors: list[ExplanationFactor] = []
        for contribution in assessment.contributions:
            factors.append(self._detector_factor(contribution))

        if feature is not None and (
            feature.symbol != assessment.symbol or feature.timestamp != assessment.timestamp
        ):
            feature = None
        signal_features = {
            signal.feature_name
            for signal in matching_signals
            if signal.feature_name != "__multivariate__"
        }
        contribution_features = {
            contribution.feature_name
            for contribution in assessment.contributions
            if contribution.feature_name != "__multivariate__"
        }
        feature_names = set(FEATURE_LABELS) - {"__multivariate__"}
        for feature_name in sorted(feature_names | signal_features | contribution_features):
            if feature is None:
                continue
            value = getattr(feature, feature_name, None)
            if value is None:
                value = feature.raw_features.get(feature_name)
            if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                continue
            factors.append(
                ExplanationFactor(
                    factor_type=ExplanationFactorType.FEATURE,
                    key=f"feature:{feature_name}",
                    label=FEATURE_LABELS.get(feature_name, feature_name),
                    detail=self._feature_detail(feature_name, float(value)),
                    feature_name=feature_name,
                    value=float(value),
                    valid=True,
                    metadata={"slot_index": feature.slot_index},
                )
            )

        if assessment.detector_agreement >= 2:
            bonus = float(assessment.metadata.get("agreement_bonus", 0.0))
            factors.append(
                ExplanationFactor(
                    factor_type=ExplanationFactorType.AGREEMENT,
                    key="agreement_bonus",
                    label="Detector agreement",
                    detail=(
                        f"{assessment.detector_agreement} independent detectors contributed "
                        f"to the assessment; the configured agreement contribution is {bonus:.2f} points."
                    ),
                    value=float(assessment.detector_agreement),
                    threshold=bonus,
                    valid=True,
                    metadata={"agreement_bonus_points": bonus},
                )
            )

        if assessment.missing_detectors:
            factors.append(
                ExplanationFactor(
                    factor_type=ExplanationFactorType.DATA_QUALITY,
                    key="missing_detectors",
                    label="Missing detector evidence",
                    detail=(
                        "No valid evidence was supplied for: "
                        + ", ".join(assessment.missing_detectors)
                        + "."
                    ),
                    valid=False,
                    reason="missing_detector_evidence",
                    metadata={"detectors": assessment.missing_detectors},
                )
            )
        if not assessment.valid:
            factors.append(
                ExplanationFactor(
                    factor_type=ExplanationFactorType.DATA_QUALITY,
                    key="assessment_invalid",
                    label="Insufficient valid evidence",
                    detail="The assessment does not contain sufficient valid detector evidence for a supported explanation.",
                    valid=False,
                    reason=assessment.reason or "insufficient_valid_evidence",
                )
            )

        factors.sort(key=lambda factor: (factor.factor_type.value, factor.key))
        contributing_detectors = tuple(sorted(assessment.active_detectors))
        contributing_features = tuple(
            sorted(
                {
                    factor.feature_name
                    for factor in factors
                    if factor.factor_type is ExplanationFactorType.FEATURE and factor.feature_name is not None
                }
                | {
                    contribution.feature_name
                    for contribution in assessment.contributions
                    if contribution.feature_name != "__multivariate__"
                }
            )
        )
        summary = self._summary(assessment, contributing_detectors, contributing_features)
        return SurveillanceExplanation(
            symbol=assessment.symbol,
            timestamp=assessment.timestamp,
            slot_index=assessment.slot_index,
            risk_score=assessment.risk_score,
            severity=assessment.severity,
            summary=summary,
            factors=tuple(factors),
            contributing_detectors=contributing_detectors,
            contributing_features=contributing_features,
            valid=assessment.valid,
            reason=assessment.reason,
            metadata={
                "base_score": assessment.metadata.get("base_score", 0.0),
                "agreement_bonus": assessment.metadata.get("agreement_bonus", 0.0),
                "weights": dict(assessment.weights),
                "source_signal_count": len(matching_signals),
            },
        )

    def _detector_factor(self, contribution: Any) -> ExplanationFactor:
        label = contribution.detector_name.replace("Detector", "")
        if contribution.detector_name == "IsolationForestDetector":
            detail = "Isolation Forest identified the multivariate feature combination as unusual."
        else:
            detail = (
                f"{label} evidence was {contribution.normalized_evidence:.2f} after normalization; "
                f"weighted contribution was {contribution.weighted_contribution * 100:.2f} points."
            )
        return ExplanationFactor(
            factor_type=ExplanationFactorType.DETECTOR,
            key=f"detector:{contribution.detector_name}",
            label=f"{label} contribution",
            detail=detail,
            detector_name=contribution.detector_name,
            feature_name=contribution.feature_name,
            value=contribution.raw_statistic,
            normalized_evidence=contribution.normalized_evidence,
            weighted_contribution=contribution.weighted_contribution,
            valid=contribution.valid,
            reason=contribution.reason,
            metadata=dict(contribution.metadata),
        )

    def _feature_detail(self, feature_name: str, value: float) -> str:
        label = FEATURE_LABELS.get(feature_name, feature_name)
        if feature_name == "volume_ratio":
            return f"{label} was {value:.2f}x the preceding observed volume."
        return f"{label} was {value:.6f} for the observed candle."

    def _summary(
        self,
        assessment: RiskAssessment,
        detectors: tuple[str, ...],
        features: tuple[str, ...],
    ) -> str:
        if not assessment.valid:
            return (
                f"Activity for {assessment.symbol} at {assessment.timestamp.isoformat()} "
                "could not be fully assessed because valid detector evidence was insufficient."
            )
        detector_text = ", ".join(detector.replace("Detector", "") for detector in detectors)
        feature_text = ", ".join(FEATURE_LABELS.get(name, name) for name in features)
        evidence = f" Detected feature evidence: {feature_text}." if feature_text else ""
        return (
            f"{assessment.symbol} received a {assessment.risk_score:.2f}/100 "
            f"{assessment.severity.value} unusual-activity assessment from {detector_text}."
            f"{evidence} This describes statistical deviation from configured baselines and models."
        )


def explain_assessment(
    assessment: RiskAssessment,
    *,
    signals: Sequence[AnomalySignal] = (),
    feature: FeatureSet | None = None,
) -> SurveillanceExplanation:
    """Convenience wrapper for deterministic explanation generation."""
    return ExplainabilityEngine().explain(assessment, signals=signals, feature=feature)


__all__ = [
    "EXPLANATION_DISCLAIMER",
    "ExplainabilityEngine",
    "ExplanationFactor",
    "ExplanationFactorType",
    "SurveillanceExplanation",
    "explain_assessment",
]

"""Transparent deterministic risk scoring and detector signal fusion."""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import datetime
from enum import Enum
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from marketwatch.models.signals import AnomalySignal

IST = ZoneInfo("Asia/Kolkata")
DEFAULT_DETECTOR_WEIGHTS = {
    "ZScoreDetector": 0.35,
    "EWMADetector": 0.25,
    "IsolationForestDetector": 0.40,
}
DEFAULT_SEVERITY_THRESHOLDS = {
    "medium": 50.0,
    "high": 70.0,
    "critical": 85.0,
}


class RiskSeverity(str, Enum):
    """Engineering severity tier for a bounded surveillance risk score."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskContribution(BaseModel):
    """Selected detector evidence contributing to a risk assessment."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    detector_name: str
    feature_name: str
    raw_statistic: float
    normalized_evidence: float = Field(ge=0.0, le=1.0)
    detector_weight: float = Field(ge=0.0, le=1.0)
    weighted_contribution: float = Field(ge=0.0, le=1.0)
    anomaly: bool
    valid: bool
    reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_finite_values(self) -> RiskContribution:
        for name in ("raw_statistic", "normalized_evidence", "detector_weight", "weighted_contribution"):
            if not math.isfinite(getattr(self, name)):
                raise ValueError(f"Risk contribution field '{name}' must be finite")
        return self


class RiskAssessment(BaseModel):
    """Structured Phase 7 result consumed by future explainability layers."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    timestamp: datetime
    slot_index: int = Field(ge=0, le=74)
    risk_score: float = Field(ge=0.0, le=100.0)
    severity: RiskSeverity
    contributions: tuple[RiskContribution, ...] = ()
    active_detectors: tuple[str, ...] = ()
    missing_detectors: tuple[str, ...] = ()
    detector_agreement: int = Field(ge=0)
    valid: bool
    reason: str | None = None
    weights: dict[str, float] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=IST)
        return value.astimezone(IST)

    @model_validator(mode="after")
    def validate_finite_score(self) -> RiskAssessment:
        if not math.isfinite(self.risk_score):
            raise ValueError("risk_score must be finite")
        return self


def _finite(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


class RiskScorer:
    """Fuse Phase 5 and Phase 6 evidence using explicit bounded mathematics.

    Statistical evidence is ``clamp(abs(statistic) / threshold, 0, 1)``.
    Isolation Forest evidence is ``clamp((statistic - threshold) / score_scale, 0, 1)``.
    Only the strongest valid signal from each detector contributes, preventing
    multiple features from the same detector from being counted repeatedly.
    Available detector weights are renormalized when a detector is missing or invalid.
    A configurable agreement bonus is added when at least two detectors contribute.
    """

    def __init__(
        self,
        *,
        detector_weights: dict[str, float] | None = None,
        severity_thresholds: dict[str, float] | None = None,
        isolation_score_scale: float = 0.5,
        agreement_bonus: float = 0.10,
    ) -> None:
        self.detector_weights = dict(detector_weights or DEFAULT_DETECTOR_WEIGHTS)
        if not self.detector_weights or any(weight < 0 for weight in self.detector_weights.values()):
            raise ValueError("detector_weights must contain non-negative values")
        if sum(self.detector_weights.values()) <= 0:
            raise ValueError("detector_weights must have a positive total")
        self.severity_thresholds = dict(severity_thresholds or DEFAULT_SEVERITY_THRESHOLDS)
        self._validate_severity_thresholds()
        if isolation_score_scale <= 0:
            raise ValueError("isolation_score_scale must be positive")
        if not 0.0 <= agreement_bonus <= 1.0:
            raise ValueError("agreement_bonus must be in [0, 1]")
        self.isolation_score_scale = float(isolation_score_scale)
        self.agreement_bonus = float(agreement_bonus)

    def score(
        self,
        signals: Sequence[AnomalySignal],
        *,
        symbol: str | None = None,
        timestamp: datetime | None = None,
    ) -> RiskAssessment:
        """Fuse signals for one symbol and timestamp without using future observations."""
        selected = [
            signal
            for signal in signals
            if (symbol is None or signal.symbol == symbol)
            and (timestamp is None or signal.timestamp == timestamp)
        ]
        if not selected:
            raise ValueError("at least one signal is required to establish score metadata")
        selected.sort(key=lambda signal: (signal.detector_name, signal.feature_name, signal.timestamp))
        current_symbol = symbol or selected[0].symbol
        current_timestamp = timestamp or selected[0].timestamp
        mismatched = [
            signal
            for signal in selected
            if signal.symbol != current_symbol or signal.timestamp != current_timestamp
        ]
        if mismatched:
            raise ValueError("all signals must belong to the same symbol and timestamp")

        by_detector: dict[str, list[AnomalySignal]] = {}
        invalid_reasons: list[str] = []
        for signal in selected:
            if signal.detector_name not in self.detector_weights:
                continue
            if not signal.is_valid:
                invalid_reasons.append(signal.reason or f"{signal.detector_name}:invalid")
                continue
            if any(
                _finite(getattr(signal, field_name)) is None
                for field_name in ("statistic", "threshold", "value")
            ):
                invalid_reasons.append(f"{signal.detector_name}:non_finite")
                continue
            by_detector.setdefault(signal.detector_name, []).append(signal)

        chosen: list[tuple[AnomalySignal, float]] = []
        for detector_signals in by_detector.values():
            strongest = max(
                detector_signals,
                key=lambda signal: (
                    self._normalize_signal(signal),
                    signal.feature_name,
                ),
            )
            chosen.append((strongest, self._normalize_signal(strongest)))
        chosen.sort(key=lambda item: (item[0].detector_name, item[0].feature_name))

        active_detectors = tuple(signal.detector_name for signal, _ in chosen)
        missing_detectors = tuple(
            name for name in self.detector_weights if name not in active_detectors
        )
        active_weight_total = sum(self.detector_weights[name] for name in active_detectors)
        contributions: list[RiskContribution] = []
        base_score = 0.0
        if active_weight_total > 0:
            for signal, evidence in chosen:
                weight = self.detector_weights[signal.detector_name] / active_weight_total
                weighted = evidence * weight
                base_score += weighted
                contributions.append(
                    RiskContribution(
                        detector_name=signal.detector_name,
                        feature_name=signal.feature_name,
                        raw_statistic=float(signal.statistic),
                        normalized_evidence=evidence,
                        detector_weight=weight,
                        weighted_contribution=weighted,
                        anomaly=signal.anomaly,
                        valid=signal.is_valid,
                        reason=signal.reason,
                        metadata=dict(signal.metadata),
                    )
                )

        agreement_count = len(active_detectors)
        agreement = self.agreement_bonus if agreement_count >= 2 else 0.0
        normalized_score = _clamp(base_score + agreement)
        risk_score = round(normalized_score * 100.0, 6)
        valid = bool(contributions)
        reason = None if valid else (
            ";".join(sorted(set(invalid_reasons))) or "insufficient_valid_evidence"
        )
        return RiskAssessment(
            symbol=current_symbol,
            timestamp=current_timestamp,
            slot_index=selected[0].slot_index,
            risk_score=risk_score,
            severity=self._severity(risk_score),
            contributions=tuple(contributions),
            active_detectors=active_detectors,
            missing_detectors=missing_detectors,
            detector_agreement=agreement_count,
            valid=valid,
            reason=reason,
            weights=dict(self.detector_weights),
            metadata={
                "base_score": round(base_score * 100.0, 6),
                "agreement_bonus": round(agreement * 100.0, 6),
                "agreement_bonus_fraction": self.agreement_bonus,
                "isolation_score_scale": self.isolation_score_scale,
                "severity_thresholds": dict(self.severity_thresholds),
            },
        )

    def score_many(self, signals: Sequence[AnomalySignal]) -> list[RiskAssessment]:
        """Score grouped signal sets in stable symbol/timestamp order."""
        groups: dict[tuple[str, datetime], list[AnomalySignal]] = {}
        for signal in signals:
            groups.setdefault((signal.symbol, signal.timestamp), []).append(signal)
        return [
            self.score(group, symbol=symbol, timestamp=timestamp)
            for (symbol, timestamp), group in sorted(groups.items())
        ]

    def _normalize_signal(self, signal: AnomalySignal) -> float:
        statistic = float(signal.statistic)
        threshold = float(signal.threshold)
        if signal.detector_name == "IsolationForestDetector":
            return _clamp((statistic - threshold) / self.isolation_score_scale)
        scale = max(abs(threshold), 1e-9)
        return _clamp(abs(statistic) / scale)

    def _severity(self, score: float) -> RiskSeverity:
        if score >= self.severity_thresholds["critical"]:
            return RiskSeverity.CRITICAL
        if score >= self.severity_thresholds["high"]:
            return RiskSeverity.HIGH
        if score >= self.severity_thresholds["medium"]:
            return RiskSeverity.MEDIUM
        return RiskSeverity.LOW

    def _validate_severity_thresholds(self) -> None:
        required = {"medium", "high", "critical"}
        if set(self.severity_thresholds) != required:
            raise ValueError("severity_thresholds must define medium, high, and critical")
        values = [self.severity_thresholds[name] for name in ("medium", "high", "critical")]
        if values != sorted(values) or values[0] < 0 or values[-1] > 100:
            raise ValueError("severity thresholds must be ordered and within [0, 100]")


__all__ = [
    "DEFAULT_DETECTOR_WEIGHTS",
    "DEFAULT_SEVERITY_THRESHOLDS",
    "RiskAssessment",
    "RiskContribution",
    "RiskScorer",
    "RiskSeverity",
]

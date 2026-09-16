"""Statistical anomaly detectors for MarketWatch AI."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from marketwatch.features import TODBaselineEngine
from marketwatch.models.features import FeatureSet
from marketwatch.models.signals import AnomalySeverity, AnomalySignal


def _safe_float(value: float | None, default: float = 0.0) -> float:
    """Coerce and sanitize float values while preserving deterministic defaults."""
    try:
        result = float(value)
    except (TypeError, ValueError):
        return float(default)
    if not math.isfinite(result):
        return float(default)
    return result


def _severity_from_statistic(statistic: float, *, threshold: float) -> AnomalySeverity:
    """Map absolute deviation magnitude to a deterministic severity tier."""
    magnitude = abs(statistic)
    if magnitude >= max(threshold * 2.5, 5.0):
        return AnomalySeverity.CRITICAL
    if magnitude >= max(threshold * 1.1, 2.0):
        return AnomalySeverity.HIGH
    if magnitude >= threshold:
        return AnomalySeverity.MEDIUM
    return AnomalySeverity.LOW


@dataclass(frozen=True)
class DetectorState:
    """Persistent EWMA state for one symbol/feature pair."""

    mean: float
    variance: float
    count: int


class ZScoreDetector:
    """Compute rolling z-score deviations against per-symbol, per-slot historical baselines."""

    def __init__(
        self,
        *,
        feature_names: Sequence[str] | None = None,
        threshold: float = 3.0,
        min_observations: int = 3,
    ) -> None:
        self.feature_names = tuple(feature_names) if feature_names is not None else (
            "log_return",
            "volume_ratio",
            "parkinson_volatility",
            "market_excess_return",
            "sector_excess_return",
        )
        self.threshold = float(threshold)
        self.min_observations = max(1, int(min_observations))
        self.baseline_engine = TODBaselineEngine(min_observations=self.min_observations)

    def detect(
        self,
        feature_history: Sequence[FeatureSet],
        *,
        symbol: str | None = None,
    ) -> list[AnomalySignal]:
        """Return z-score anomalies for the provided historical feature stream."""
        if not feature_history:
            return []

        ordered = sorted(feature_history, key=lambda f: (f.timestamp, f.symbol, f.slot_index))
        grouped: dict[str, list[FeatureSet]] = defaultdict(list)
        for feature in ordered:
            if symbol is not None and feature.symbol != symbol:
                continue
            grouped[feature.symbol].append(feature)

        signals: list[AnomalySignal] = []
        for symbol_name, features in grouped.items():
            for feature in features:
                for feature_name in self.feature_names:
                    current_value = _safe_float(getattr(feature, feature_name, None), default=0.0)
                    baseline = self.baseline_engine.baseline_for_feature(feature, features, feature_name)
                    if not baseline.valid or baseline.count < self.min_observations:
                        signals.append(
                            AnomalySignal(
                                detector_name="ZScoreDetector",
                                symbol=symbol_name,
                                timestamp=feature.timestamp,
                                slot_index=feature.slot_index,
                                feature_name=feature_name,
                                value=current_value,
                                baseline_value=baseline.mean,
                                baseline_mean=baseline.mean,
                                baseline_std=baseline.std,
                                statistic=0.0,
                                z_score=0.0,
                                threshold=self.threshold,
                                severity=AnomalySeverity.LOW,
                                anomaly=False,
                                direction=0.0,
                                is_valid=False,
                                reason="insufficient_history",
                                metadata={
                                    "baseline_count": baseline.count,
                                    "baseline_slot_index": baseline.slot_index,
                                    "detector_type": "z_score",
                                },
                            )
                        )
                        continue

                    std = baseline.std
                    if std <= 1e-8:
                        deviation = current_value - baseline.mean
                        statistic = 0.0
                        z_score = 0.0
                    else:
                        deviation = current_value - baseline.mean
                        statistic = deviation / std
                        z_score = statistic

                    anomaly = abs(z_score) >= self.threshold
                    direction = math.copysign(1.0, z_score) if z_score != 0 else 0.0
                    severity = _severity_from_statistic(z_score, threshold=self.threshold)
                    signals.append(
                        AnomalySignal(
                            detector_name="ZScoreDetector",
                            symbol=symbol_name,
                            timestamp=feature.timestamp,
                            slot_index=feature.slot_index,
                            feature_name=feature_name,
                            value=current_value,
                            baseline_value=baseline.mean,
                            baseline_mean=baseline.mean,
                            baseline_std=baseline.std,
                            statistic=z_score,
                            z_score=z_score,
                            threshold=self.threshold,
                            severity=severity if anomaly else AnomalySeverity.LOW,
                            anomaly=anomaly,
                            direction=direction,
                            is_valid=True,
                            reason=None,
                            metadata={
                                "baseline_count": baseline.count,
                                "baseline_slot_index": baseline.slot_index,
                                "deviation": deviation,
                                "detector_type": "z_score",
                            },
                        )
                    )

        return signals


class EWMADetector:
    """Compute exponentially weighted moving statistics using only prior observations."""

    def __init__(
        self,
        *,
        feature_names: Sequence[str] | None = None,
        alpha: float = 0.3,
        threshold: float = 2.5,
        min_periods: int = 2,
    ) -> None:
        self.feature_names = tuple(feature_names) if feature_names is not None else (
            "log_return",
            "volume_ratio",
            "parkinson_volatility",
            "market_excess_return",
            "sector_excess_return",
        )
        self.alpha = max(0.0, min(1.0, float(alpha)))
        self.threshold = float(threshold)
        self.min_periods = max(1, int(min_periods))

    def detect(
        self,
        feature_history: Sequence[FeatureSet],
        *,
        symbol: str | None = None,
    ) -> list[AnomalySignal]:
        """Return EWMA-based anomaly signals in chronological order."""
        if not feature_history:
            return []

        ordered = sorted(feature_history, key=lambda f: (f.timestamp, f.symbol, f.slot_index))
        states: dict[tuple[str, str], DetectorState] = {}
        signals: list[AnomalySignal] = []

        for feature in ordered:
            if symbol is not None and feature.symbol != symbol:
                continue
            for feature_name in self.feature_names:
                current_value = _safe_float(getattr(feature, feature_name, None), default=0.0)
                key = (feature.symbol, feature_name)
                prior = states.get(key)

                if prior is None:
                    current_mean = current_value
                    variance = 0.0
                    count = 1
                    deviation = 0.0
                    statistic = 0.0
                    anomaly = False
                    severity = AnomalySeverity.LOW
                    is_valid = False
                    reason = "warmup_initialization"
                    baseline_value = current_value
                    baseline_std = 0.0
                else:
                    previous_mean = prior.mean
                    previous_variance = prior.variance
                    current_mean = self.alpha * current_value + (1.0 - self.alpha) * previous_mean
                    variance = self.alpha * (current_value - previous_mean) ** 2 + (1.0 - self.alpha) * previous_variance
                    deviation = current_value - previous_mean
                    baseline_std = math.sqrt(max(variance, 0.0))
                    baseline_value = previous_mean
                    statistic = deviation / baseline_std if baseline_std > 1e-8 else 0.0
                    count = prior.count + 1
                    is_valid = count >= self.min_periods
                    anomaly = is_valid and abs(statistic) >= self.threshold
                    severity = _severity_from_statistic(statistic, threshold=self.threshold) if anomaly else AnomalySeverity.LOW
                    reason = None if is_valid else "insufficient_history"

                signals.append(
                    AnomalySignal(
                        detector_name="EWMADetector",
                        symbol=feature.symbol,
                        timestamp=feature.timestamp,
                        slot_index=feature.slot_index,
                        feature_name=feature_name,
                        value=current_value,
                        baseline_value=baseline_value,
                        baseline_mean=current_mean if prior is not None else current_value,
                        baseline_std=baseline_std,
                        statistic=statistic,
                        z_score=statistic,
                        threshold=self.threshold,
                        severity=severity,
                        anomaly=anomaly,
                        direction=math.copysign(1.0, statistic) if statistic != 0 else 0.0,
                        is_valid=is_valid,
                        reason=reason,
                        metadata={
                            "alpha": self.alpha,
                            "ewma_mean": current_mean,
                            "ewma_variance": variance,
                            "detector_type": "ewma",
                            "count": count,
                        },
                    )
                )

                states[key] = DetectorState(mean=current_mean, variance=variance, count=count)

        return signals


def detect_z_score_anomalies(
    feature_history: Sequence[FeatureSet],
    *,
    symbol: str | None = None,
    feature_names: Sequence[str] | None = None,
    threshold: float = 3.0,
    min_observations: int = 3,
) -> list[AnomalySignal]:
    """Convenience wrapper to score a feature history with z-score anomalies."""
    detector = ZScoreDetector(
        feature_names=feature_names,
        threshold=threshold,
        min_observations=min_observations,
    )
    return detector.detect(feature_history, symbol=symbol)


def detect_ewma_anomalies(
    feature_history: Sequence[FeatureSet],
    *,
    symbol: str | None = None,
    feature_names: Sequence[str] | None = None,
    alpha: float = 0.3,
    threshold: float = 2.5,
    min_periods: int = 2,
) -> list[AnomalySignal]:
    """Convenience wrapper to score a feature history with EWMA anomalies."""
    detector = EWMADetector(
        feature_names=feature_names,
        alpha=alpha,
        threshold=threshold,
        min_periods=min_periods,
    )
    return detector.detect(feature_history, symbol=symbol)


__all__ = [
    "EWMADetector",
    "ZScoreDetector",
    "detect_ewma_anomalies",
    "detect_z_score_anomalies",
]

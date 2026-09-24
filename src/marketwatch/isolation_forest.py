"""Deterministic multivariate Isolation Forest detection and validation."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from marketwatch.models.features import FeatureSet
from marketwatch.models.signals import AnomalySeverity, AnomalySignal

DEFAULT_FEATURE_NAMES = (
    "log_return",
    "volume_ratio",
    "parkinson_volatility",
    "market_excess_return",
    "sector_excess_return",
    "buy_sell_pressure",
)


def _finite(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


@dataclass(frozen=True)
class FeatureMatrix:
    """Chronologically ordered model matrix with metadata kept separately."""

    values: np.ndarray
    features: tuple[FeatureSet, ...]
    feature_names: tuple[str, ...]
    dropped_count: int = 0


@dataclass(frozen=True)
class TemporalSplit:
    """Explicit chronological train/evaluation boundary."""

    train: tuple[FeatureSet, ...]
    evaluation: tuple[FeatureSet, ...]
    train_end: datetime | None
    evaluation_start: datetime | None


@dataclass(frozen=True)
class WalkForwardResult:
    """Signals and inspectable boundaries for one walk-forward window."""

    train_start: datetime | None
    train_end: datetime | None
    evaluation_start: datetime | None
    evaluation_end: datetime | None
    signals: tuple[AnomalySignal, ...]


class FeatureMatrixBuilder:
    """Build deterministic finite matrices from the Phase 4 FeatureSet contract."""

    def __init__(self, feature_names: Sequence[str] | None = None) -> None:
        self.feature_names = tuple(feature_names or DEFAULT_FEATURE_NAMES)
        if not self.feature_names or len(set(self.feature_names)) != len(self.feature_names):
            raise ValueError("feature_names must be non-empty and unique")

    def build(self, features: Sequence[FeatureSet]) -> FeatureMatrix:
        ordered = tuple(sorted(features, key=lambda item: (item.timestamp, item.symbol, item.slot_index)))
        valid_features: list[FeatureSet] = []
        rows: list[list[float]] = []
        for feature in ordered:
            row = [_finite(getattr(feature, name, None)) for name in self.feature_names]
            if all(value is not None for value in row):
                valid_features.append(feature)
                rows.append([float(value) for value in row if value is not None])
        values = np.asarray(rows, dtype=float)
        if not rows:
            values = np.empty((0, len(self.feature_names)), dtype=float)
        return FeatureMatrix(
            values=values,
            features=tuple(valid_features),
            feature_names=self.feature_names,
            dropped_count=len(ordered) - len(valid_features),
        )


def chronological_split(
    features: Sequence[FeatureSet],
    *,
    train_end: datetime,
) -> TemporalSplit:
    """Split strictly before and at/after ``train_end`` without overlap."""
    ordered = tuple(sorted(features, key=lambda item: (item.timestamp, item.symbol, item.slot_index)))
    train = tuple(feature for feature in ordered if feature.timestamp < train_end)
    evaluation = tuple(feature for feature in ordered if feature.timestamp >= train_end)
    return TemporalSplit(
        train=train,
        evaluation=evaluation,
        train_end=train[-1].timestamp if train else None,
        evaluation_start=evaluation[0].timestamp if evaluation else None,
    )


class IsolationForestDetector:
    """Fit Isolation Forest on historical features and score later observations."""

    def __init__(
        self,
        *,
        feature_names: Sequence[str] | None = None,
        n_estimators: int = 100,
        contamination: float | str = "auto",
        random_state: int = 42,
        min_training_samples: int = 8,
    ) -> None:
        if isinstance(contamination, float) and not 0.0 < contamination <= 0.5:
            raise ValueError("contamination must be in (0, 0.5]")
        if n_estimators < 1:
            raise ValueError("n_estimators must be positive")
        self.matrix_builder = FeatureMatrixBuilder(feature_names)
        self.n_estimators = int(n_estimators)
        self.contamination = contamination
        self.random_state = int(random_state)
        self.min_training_samples = max(2, int(min_training_samples))
        self._model: IsolationForest | None = None
        self._scaler: StandardScaler | None = None
        self._feature_names: tuple[str, ...] = self.matrix_builder.feature_names
        self._threshold: float | None = None
        self._train_features: tuple[FeatureSet, ...] = ()
        self._reason: str | None = None

    @property
    def feature_names(self) -> tuple[str, ...]:
        return self._feature_names

    @property
    def threshold(self) -> float | None:
        return self._threshold

    @property
    def fitted(self) -> bool:
        return self._model is not None and self._scaler is not None

    def fit(self, training_features: Sequence[FeatureSet]) -> bool:
        """Fit scaler and model using only the supplied historical features."""
        matrix = self.matrix_builder.build(training_features)
        self._model = None
        self._scaler = None
        self._threshold = None
        self._train_features = matrix.features
        self._reason = None
        if len(matrix.features) < self.min_training_samples:
            self._reason = "insufficient_training_data"
            return False
        if np.any(np.ptp(matrix.values, axis=0) > 1e-12):
            varying = np.ptp(matrix.values, axis=0) > 1e-12
        else:
            varying = np.zeros(matrix.values.shape[1], dtype=bool)
        if not np.any(varying):
            self._reason = "constant_features"
            return False

        scaler = StandardScaler()
        scaled = scaler.fit_transform(matrix.values)
        model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=self.random_state,
            n_jobs=1,
        )
        model.fit(scaled)
        self._scaler = scaler
        self._model = model
        # sklearn's decision_function already subtracts offset_; zero is the
        # deterministic prediction boundary for the exposed anomaly score.
        self._threshold = 0.0
        self._feature_names = matrix.feature_names
        return True

    def score(self, evaluation_features: Sequence[FeatureSet]) -> list[AnomalySignal]:
        """Score only observations after the model was fitted."""
        matrix = self.matrix_builder.build(evaluation_features)
        ordered_evaluation = tuple(
            sorted(evaluation_features, key=lambda item: (item.timestamp, item.symbol, item.slot_index))
        )
        valid_ids = {id(feature) for feature in matrix.features}
        if not self.fitted:
            return [
                self._invalid_signal(
                    feature,
                    self._reason or "not_fitted"
                    if id(feature) in valid_ids
                    else "invalid_feature_row",
                )
                for feature in ordered_evaluation
            ]
        if not matrix.features:
            return [self._invalid_signal(feature, "invalid_feature_row") for feature in ordered_evaluation]
        assert self._model is not None
        assert self._scaler is not None
        raw_decisions = self._model.decision_function(self._scaler.transform(matrix.values))
        scores = -np.asarray(raw_decisions, dtype=float)
        threshold = float(self._threshold if self._threshold is not None else 0.0)
        signals: list[AnomalySignal] = []
        train_start = self._train_features[0].timestamp if self._train_features else None
        train_end = self._train_features[-1].timestamp if self._train_features else None
        for feature, score in zip(matrix.features, scores):
            anomaly = bool(score >= threshold)
            signals.append(
                AnomalySignal(
                    detector_name="IsolationForestDetector",
                    symbol=feature.symbol,
                    timestamp=feature.timestamp,
                    slot_index=feature.slot_index,
                    feature_name="__multivariate__",
                    value=float(score),
                    baseline_value=threshold,
                    baseline_mean=threshold,
                    baseline_std=1.0,
                    statistic=float(score),
                    z_score=0.0,
                    threshold=threshold,
                    severity=AnomalySeverity.HIGH if anomaly else AnomalySeverity.LOW,
                    anomaly=anomaly,
                    direction=0.0,
                    is_valid=True,
                    reason=None,
                    metadata={
                        "detector_type": "isolation_forest",
                        "raw_decision": float(-score),
                        "model_offset": float(self._model.offset_),
                        "anomaly_score": float(score),
                        "train_start": train_start.isoformat() if train_start else None,
                        "train_end": train_end.isoformat() if train_end else None,
                        "feature_names": self._feature_names,
                        "random_state": self.random_state,
                    },
                )
            )
        scored_by_id = {
            id(feature): signal for feature, signal in zip(matrix.features, signals)
        }
        return [
            scored_by_id.get(id(feature), self._invalid_signal(feature, "invalid_feature_row"))
            for feature in ordered_evaluation
        ]

    def fit_score(
        self,
        training_features: Sequence[FeatureSet],
        evaluation_features: Sequence[FeatureSet],
    ) -> list[AnomalySignal]:
        """Fit on historical data and score a separate later evaluation window."""
        self.fit(training_features)
        return self.score(evaluation_features)

    def walk_forward(
        self,
        features: Sequence[FeatureSet],
        *,
        min_training_samples: int | None = None,
    ) -> list[WalkForwardResult]:
        """Run expanding-window one-observation-ahead evaluation."""
        ordered = tuple(sorted(features, key=lambda item: (item.timestamp, item.symbol, item.slot_index)))
        minimum = max(self.min_training_samples, min_training_samples or self.min_training_samples)
        results: list[WalkForwardResult] = []
        for index in range(minimum, len(ordered)):
            training = ordered[:index]
            evaluation = (ordered[index],)
            signals = tuple(self.fit_score(training, evaluation))
            results.append(
                WalkForwardResult(
                    train_start=training[0].timestamp,
                    train_end=training[-1].timestamp,
                    evaluation_start=evaluation[0].timestamp,
                    evaluation_end=evaluation[-1].timestamp,
                    signals=signals,
                )
            )
        return results

    def _invalid_signal(self, feature: FeatureSet, reason: str) -> AnomalySignal:
        return AnomalySignal(
            detector_name="IsolationForestDetector",
            symbol=feature.symbol,
            timestamp=feature.timestamp,
            slot_index=feature.slot_index,
            feature_name="__multivariate__",
            value=0.0,
            baseline_value=0.0,
            baseline_mean=0.0,
            baseline_std=1.0,
            statistic=0.0,
            z_score=0.0,
            threshold=0.0,
            severity=AnomalySeverity.LOW,
            anomaly=False,
            direction=0.0,
            is_valid=False,
            reason=reason,
            metadata={"detector_type": "isolation_forest"},
        )


__all__ = [
    "DEFAULT_FEATURE_NAMES",
    "FeatureMatrix",
    "FeatureMatrixBuilder",
    "IsolationForestDetector",
    "TemporalSplit",
    "WalkForwardResult",
    "chronological_split",
]

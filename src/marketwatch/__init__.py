"""MarketWatch AI — Explainable Real-Time Market Surveillance."""

from marketwatch.detectors import (
    EWMADetector,
    ZScoreDetector,
    detect_ewma_anomalies,
    detect_z_score_anomalies,
)
from marketwatch.features import BaselineStats, FeaturePipeline, TODBaselineEngine
from marketwatch.models.signals import AnomalySeverity, AnomalySignal

__version__ = "0.1.0"

__all__ = [
    "AnomalySeverity",
    "AnomalySignal",
    "BaselineStats",
    "EWMADetector",
    "FeaturePipeline",
    "TODBaselineEngine",
    "ZScoreDetector",
    "__version__",
    "detect_ewma_anomalies",
    "detect_z_score_anomalies",
]

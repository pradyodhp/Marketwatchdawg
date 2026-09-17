"""MarketWatch AI — Explainable Real-Time Market Surveillance."""

from marketwatch.detectors import (
    EWMADetector,
    ZScoreDetector,
    detect_ewma_anomalies,
    detect_z_score_anomalies,
)
from marketwatch.features import BaselineStats, FeaturePipeline, TODBaselineEngine
from marketwatch.isolation_forest import (
    FeatureMatrix,
    FeatureMatrixBuilder,
    IsolationForestDetector,
    TemporalSplit,
    WalkForwardResult,
    chronological_split,
)
from marketwatch.models.signals import AnomalySeverity, AnomalySignal
from marketwatch.risk import RiskAssessment, RiskContribution, RiskScorer, RiskSeverity

__version__ = "0.1.0"

__all__ = [
    "AnomalySeverity",
    "AnomalySignal",
    "BaselineStats",
    "EWMADetector",
    "FeatureMatrix",
    "FeatureMatrixBuilder",
    "FeaturePipeline",
    "IsolationForestDetector",
    "RiskAssessment",
    "RiskContribution",
    "RiskScorer",
    "RiskSeverity",
    "TODBaselineEngine",
    "TemporalSplit",
    "WalkForwardResult",
    "ZScoreDetector",
    "__version__",
    "chronological_split",
    "detect_ewma_anomalies",
    "detect_z_score_anomalies",
]

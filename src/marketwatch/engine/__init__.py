"""Engine package for MarketWatch AI."""

from marketwatch.alert_engine import (
    AlertEngine,
    AlertEvent,
    AlertState,
    SurveillanceAlert,
)
from marketwatch.detectors import (
    EWMADetector,
    ZScoreDetector,
    detect_ewma_anomalies,
    detect_z_score_anomalies,
)
from marketwatch.explainability import (
    EXPLANATION_DISCLAIMER,
    ExplainabilityEngine,
    ExplanationFactor,
    ExplanationFactorType,
    SurveillanceExplanation,
    explain_assessment,
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
from marketwatch.risk import RiskAssessment, RiskContribution, RiskScorer, RiskSeverity

__all__ = [
    "EXPLANATION_DISCLAIMER",
    "AlertEngine",
    "AlertEvent",
    "AlertState",
    "BaselineStats",
    "EWMADetector",
    "ExplainabilityEngine",
    "ExplanationFactor",
    "ExplanationFactorType",
    "FeatureMatrix",
    "FeatureMatrixBuilder",
    "FeaturePipeline",
    "IsolationForestDetector",
    "RiskAssessment",
    "RiskContribution",
    "RiskScorer",
    "RiskSeverity",
    "SurveillanceAlert",
    "SurveillanceExplanation",
    "TODBaselineEngine",
    "TemporalSplit",
    "WalkForwardResult",
    "ZScoreDetector",
    "chronological_split",
    "detect_ewma_anomalies",
    "detect_z_score_anomalies",
    "explain_assessment",
]

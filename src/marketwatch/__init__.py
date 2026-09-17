"""MarketWatch AI — Explainable Real-Time Market Surveillance."""

from marketwatch.alert_engine import (
    AlertEngine,
    AlertEvent,
    AlertState,
    SurveillanceAlert,
)
from marketwatch.controller import (
    ControllerResult,
    InjectionConfig,
    InjectionResult,
    InjectionType,
    SurveillanceController,
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
from marketwatch.models.signals import AnomalySeverity, AnomalySignal
from marketwatch.risk import RiskAssessment, RiskContribution, RiskScorer, RiskSeverity

__version__ = "0.1.0"

__all__ = [
    "EXPLANATION_DISCLAIMER",
    "AlertEngine",
    "AlertEvent",
    "AlertState",
    "AnomalySeverity",
    "AnomalySignal",
    "BaselineStats",
    "ControllerResult",
    "EWMADetector",
    "ExplainabilityEngine",
    "ExplanationFactor",
    "ExplanationFactorType",
    "FeatureMatrix",
    "FeatureMatrixBuilder",
    "FeaturePipeline",
    "InjectionConfig",
    "InjectionResult",
    "InjectionType",
    "IsolationForestDetector",
    "RiskAssessment",
    "RiskContribution",
    "RiskScorer",
    "RiskSeverity",
    "SurveillanceAlert",
    "SurveillanceController",
    "SurveillanceExplanation",
    "TODBaselineEngine",
    "TemporalSplit",
    "WalkForwardResult",
    "ZScoreDetector",
    "__version__",
    "chronological_split",
    "detect_ewma_anomalies",
    "detect_z_score_anomalies",
    "explain_assessment",
]

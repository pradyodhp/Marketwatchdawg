"""Compatibility layer for detector imports."""

from marketwatch.detectors import (
    EWMADetector,
    ZScoreDetector,
    detect_ewma_anomalies,
    detect_z_score_anomalies,
)

__all__ = [
    "EWMADetector",
    "ZScoreDetector",
    "detect_ewma_anomalies",
    "detect_z_score_anomalies",
]

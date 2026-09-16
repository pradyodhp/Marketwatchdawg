"""Domain models for MarketWatch AI."""

from marketwatch.models.alerts import DEFAULT_DISCLAIMER, Alert, AlertSeverity
from marketwatch.models.candle import Candle, CandleBatch, compute_slot_index
from marketwatch.models.features import FeatureSet
from marketwatch.models.metadata import DataQualityMetadata
from marketwatch.models.signals import AnomalySeverity, AnomalySignal

__all__ = [
    "DEFAULT_DISCLAIMER",
    "Alert",
    "AlertSeverity",
    "AnomalySeverity",
    "AnomalySignal",
    "Candle",
    "CandleBatch",
    "DataQualityMetadata",
    "FeatureSet",
    "compute_slot_index",
]

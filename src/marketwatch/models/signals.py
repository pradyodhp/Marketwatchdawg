"""Domain models for structured anomaly detector outputs."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from zoneinfo import ZoneInfo
from pydantic import BaseModel, ConfigDict, Field, field_validator

IST = ZoneInfo("Asia/Kolkata")


class AnomalySeverity(str, Enum):
    """Severity classification for an individual detector trigger."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AnomalySignal(BaseModel):
    """Structured deviation signal emitted by a statistical or ML detector."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    detector_name: str
    symbol: str
    timestamp: datetime
    slot_index: int = Field(ge=0, le=74)
    feature_name: str
    value: float
    baseline_mean: float
    baseline_std: float
    z_score: float
    severity: AnomalySeverity
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=IST)
        return v.astimezone(IST)

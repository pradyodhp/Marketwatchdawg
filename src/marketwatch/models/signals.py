"""Domain models for structured anomaly detector outputs."""

from __future__ import annotations

import math
from datetime import datetime
from enum import Enum
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
    baseline_value: float = 0.0
    baseline_mean: float = 0.0
    baseline_std: float = 1.0
    statistic: float = 0.0
    z_score: float = 0.0
    threshold: float = 0.0
    severity: AnomalySeverity = AnomalySeverity.LOW
    anomaly: bool = False
    direction: float = 0.0
    is_valid: bool = True
    reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=IST)
        return v.astimezone(IST)

    @model_validator(mode="after")
    def validate_numeric_finiteness(self) -> AnomalySignal:
        """Ensure signal fields remain finite and deterministic."""
        for field_name in [
            "value",
            "baseline_value",
            "baseline_mean",
            "baseline_std",
            "statistic",
            "z_score",
            "threshold",
            "direction",
        ]:
            if not math.isfinite(getattr(self, field_name)):
                raise ValueError(f"Signal field '{field_name}' must be finite")
        return self

"""Domain models for surveillance alerts and lifecycle entities."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from zoneinfo import ZoneInfo
from pydantic import BaseModel, ConfigDict, Field, field_validator

IST = ZoneInfo("Asia/Kolkata")
DEFAULT_DISCLAIMER = (
    "NOTICE: This alert reflects statistically significant behavioral deviation from historical "
    "baselines for analyst review. It does NOT establish market manipulation, fraud, or intentional misconduct."
)


class AlertSeverity(str, Enum):
    """Severity tier for a finalized surveillance alert."""

    LOW = "LOW"          # 0 - 49
    MEDIUM = "MEDIUM"    # 50 - 69
    HIGH = "HIGH"        # 70 - 84
    CRITICAL = "CRITICAL"# 85 - 100


class Alert(BaseModel):
    """Finalized explainable surveillance alert produced by signal fusion."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    alert_id: str
    symbol: str
    timestamp: datetime
    slot_index: int = Field(ge=0, le=74)
    risk_score: float = Field(ge=0.0, le=100.0)
    severity: AlertSeverity
    contributing_features: list[dict[str, Any]] = Field(default_factory=list)
    explanation: str
    disclaimer: str = DEFAULT_DISCLAIMER
    is_simulated: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=IST)
        return v.astimezone(IST)

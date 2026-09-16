"""Domain models for scale-invariant engineered features."""

from __future__ import annotations

import math
from datetime import datetime
from zoneinfo import ZoneInfo
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

IST = ZoneInfo("Asia/Kolkata")


class FeatureSet(BaseModel):
    """Engineered relative scale-invariant features for a single stock at timestamp t.

    All features are scale-invariant to allow cross-sectional evaluation and
    model generalization across large-cap and mid-cap stocks without scale distortion.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    timestamp: datetime
    slot_index: int = Field(ge=0, le=74)
    log_return: float
    volume_ratio: float = Field(ge=0.0)
    parkinson_volatility: float = Field(ge=0.0)
    market_excess_return: float
    sector_excess_return: float
    raw_features: dict[str, float] = Field(default_factory=dict)

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp(cls, v: datetime) -> datetime:
        """Ensure timestamp is normalized to Asia/Kolkata."""
        if v.tzinfo is None:
            return v.replace(tzinfo=IST)
        return v.astimezone(IST)

    @model_validator(mode="after")
    def validate_finite_floats(self) -> FeatureSet:
        """Ensure no NaN or Infinite values leak into feature representations."""
        for name, val in [
            ("log_return", self.log_return),
            ("volume_ratio", self.volume_ratio),
            ("parkinson_volatility", self.parkinson_volatility),
            ("market_excess_return", self.market_excess_return),
            ("sector_excess_return", self.sector_excess_return),
        ]:
            if not math.isfinite(val):
                raise ValueError(f"Feature '{name}' must be finite, got {val}")
        return self

"""Domain models for dataset quality and runtime coverage verification."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator

IST = ZoneInfo("Asia/Kolkata")


class DataQualityMetadata(BaseModel):
    """Audit metadata proving offline dataset integrity and coverage."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_type: str = "offline_parquet"
    universe_id: str
    loaded_symbols_count: int = Field(ge=0)
    total_symbols_count: int = Field(ge=0)
    coverage_percentage: float = Field(ge=0.0, le=100.0)
    start_timestamp: datetime
    end_timestamp: datetime
    total_bars_per_symbol: int = Field(ge=0)
    missing_bars_summary: dict[str, int] = Field(default_factory=dict)
    is_offline_confirmed: bool = True

    @field_validator("start_timestamp", "end_timestamp")
    @classmethod
    def normalize_timestamps(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=IST)
        return v.astimezone(IST)

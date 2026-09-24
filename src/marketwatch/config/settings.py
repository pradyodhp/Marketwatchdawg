"""Application runtime settings and configuration loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MarketSettings(BaseModel):
    """Market timing and resolution settings."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    timezone: str = "Asia/Kolkata"
    slots_per_day: int = 75
    bar_interval_minutes: int = 5


class RiskThresholds(BaseModel):
    """Thresholds for risk score severity classification."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    low: float = 0.0
    medium: float = 50.0
    high: float = 70.0
    critical: float = 85.0


class RiskScoringSettings(BaseModel):
    """Risk scoring engine configuration.

    ``weights`` maps detector name to fusion weight; unknown detectors are
    ignored by the scorer and missing detectors are renormalized out.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    weights: dict[str, float] = Field(
        default_factory=lambda: {
            "ZScoreDetector": 0.35,
            "EWMADetector": 0.25,
            "IsolationForestDetector": 0.40,
        }
    )
    thresholds: RiskThresholds = Field(default_factory=RiskThresholds)


class NotificationSettings(BaseModel):
    """Outbound alert delivery configuration.

    webhook_url can also be set via MARKETWATCH_NOTIFICATIONS__WEBHOOK_URL.
    Empty URL disables delivery.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    webhook_url: str = ""
    min_severity: str = "HIGH"


class CooldownSettings(BaseModel):
    """Alert cooldown parameters."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    window_bars: int = 6  # 30 minutes for 5m bars


class ReplaySettings(BaseModel):
    """Replay streaming defaults."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    default_speed: float = 1.0
    auto_play: bool = False


class LoggingSettings(BaseModel):
    """Logging settings."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    level: str = "INFO"


class Settings(BaseSettings):
    """Global application settings with environment variable override support."""

    model_config = SettingsConfigDict(
        env_prefix="MARKETWATCH_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    data_dir: str = "data"
    curated_dir: str = "data/curated"
    metadata_file: str = "data/curated/quality_metadata.json"
    universe_config_path: str = "configs/universe_nifty100.json"
    market: MarketSettings = Field(default_factory=MarketSettings)
    risk_scoring: RiskScoringSettings = Field(default_factory=RiskScoringSettings)
    cooldown: CooldownSettings = Field(default_factory=CooldownSettings)
    notifications: NotificationSettings = Field(default_factory=NotificationSettings)
    replay: ReplaySettings = Field(default_factory=ReplaySettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)


def load_settings(config_path: str | Path | None = None) -> Settings:
    """Load settings from YAML file with environment variable overrides."""
    import os

    if config_path is None:
        config_path = Path("configs/settings.yaml")
    else:
        config_path = Path(config_path)

    raw_data: dict[str, Any] = {}
    if config_path.is_file():
        with open(config_path, "r", encoding="utf-8") as f:
            raw_data = yaml.safe_load(f) or {}

    # Merge MARKETWATCH_ environment variable overrides over YAML values
    prefix = "MARKETWATCH_"
    delimiter = "__"
    for k, v in os.environ.items():
        if k.startswith(prefix):
            parts = k[len(prefix):].lower().split(delimiter)
            target = raw_data
            for part in parts[:-1]:
                if part not in target or not isinstance(target[part], dict):
                    target[part] = {}
                target = target[part]

            leaf = parts[-1]
            try:
                if "." in v:
                    val: Any = float(v)
                else:
                    val = int(v)
            except ValueError:
                if v.lower() == "true":
                    val = True
                elif v.lower() == "false":
                    val = False
                else:
                    val = v
            target[leaf] = val

    return Settings.model_validate(raw_data)

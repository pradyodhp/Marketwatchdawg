"""Full-history detection runs feeding the /scores and /detect API endpoints.

The replay endpoints stream batches through the controller interactively.
This module instead runs the same controller once over the whole curated
history, records per-bar detector evidence and risk for every symbol, and
caches the result keyed by data + settings so repeated reads are instant.
Alerts produced during the run live in the controller's alert engine, so
GET /alerts stays consistent with the bar-level scores.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from marketwatch.replay.engine import ReplayEngine

Z = "ZScoreDetector"
EWMA = "EWMADetector"
IFOREST = "IsolationForestDetector"


def _data_signature(curated_dir: Path) -> str:
    """Fingerprint the curated parquet inputs so cache invalidates on new data."""
    entries: list[str] = []
    if curated_dir.exists():
        for path in sorted(curated_dir.glob("*.parquet")):
            stat = path.stat()
            entries.append(f"{path.name}:{stat.st_size}:{stat.st_mtime_ns}")
        meta = curated_dir / "quality_metadata.json"
        if meta.exists():
            entries.append(f"meta:{meta.stat().st_mtime_ns}")
    return hashlib.sha256("|".join(entries).encode()).hexdigest()[:16]


def _settings_digest(settings: Any) -> str:
    payload = {
        "weights": settings.risk_scoring.weights,
        "thresholds": settings.risk_scoring.thresholds.model_dump(),
        "cooldown_bars": settings.cooldown.window_bars,
        "detectors": settings.detectors.model_dump(),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]


class DetectionCache:
    """One cached detection pass: per-symbol bar records + run metadata."""

    def __init__(self) -> None:
        self.key: str | None = None
        self.bars: dict[str, list[dict[str, Any]]] = {}
        self.elapsed_ms: int = 0
        self.batches: int = 0

    def matches(self, key: str) -> bool:
        return self.key == key

    def store(self, key: str, bars: dict[str, list[dict[str, Any]]], elapsed_ms: int, batches: int) -> None:
        self.key = key
        self.bars = bars
        self.elapsed_ms = elapsed_ms
        self.batches = batches

    def clear(self) -> None:
        self.key = None
        self.bars = {}


def cache_key(runtime: Any) -> str:
    return f"{_data_signature(runtime.curated_dir)}:{_settings_digest(runtime.settings)}"


def run_detection(runtime: Any) -> DetectionCache:
    """Run the full surveillance pipeline once and cache per-bar evidence.

    Uses the runtime's own controller (after a reset), so the alerts this run
    produces are exactly what GET /alerts returns.
    """
    import time

    key = cache_key(runtime)
    cache = runtime.detection_cache
    if cache.matches(key):
        return cache

    controller = runtime.controller
    controller.reset()
    engine = ReplayEngine.from_provider(runtime.provider)

    bars: dict[str, list[dict[str, Any]]] = {}
    start = time.perf_counter()
    batches = 0
    while True:
        batch = engine.step_forward()
        if batch is None:
            break
        batches += 1
        result = controller.process_batch(batch)

        z_by_feature: dict[tuple[str, str], Any] = {}
        ewma_by_feature: dict[tuple[str, str], Any] = {}
        if_by_symbol: dict[str, Any] = {}
        for signal in result.signals:
            if signal.detector_name == Z:
                z_by_feature[(signal.symbol, signal.feature_name)] = signal
            elif signal.detector_name == EWMA:
                ewma_by_feature[(signal.symbol, signal.feature_name)] = signal
            elif signal.detector_name == IFOREST:
                if_by_symbol[signal.symbol] = signal
        assessments = {item.symbol: item for item in result.assessments}

        for symbol, feature in result.features.items():
            candle = batch.candles[symbol]
            assessment = assessments.get(symbol)
            contrib: dict[str, float] = {"z": 0.0, "ewma": 0.0, "iforest": 0.0}
            if assessment is not None:
                for item in assessment.contributions:
                    label = {Z: "z", EWMA: "ewma", IFOREST: "iforest"}.get(item.detector_name)
                    if label:
                        contrib[label] = round(item.weighted_contribution * 100.0, 3)
            z_ret = z_by_feature.get((symbol, "log_return"))
            z_vol = z_by_feature.get((symbol, "volume_ratio"))
            z_pressure = z_by_feature.get((symbol, "buy_sell_pressure"))
            ewma_ret = ewma_by_feature.get((symbol, "log_return"))
            if_signal = if_by_symbol.get(symbol)
            records = bars.setdefault(symbol, [])
            records.append(
                {
                    "t": candle.timestamp.isoformat(),
                    "slot": candle.slot_index,
                    "o": candle.open,
                    "h": candle.high,
                    "l": candle.low,
                    "c": candle.close,
                    "v": candle.volume,
                    "log_return": feature.log_return,
                    "volume_ratio": feature.volume_ratio,
                    "park": round(math.sqrt(feature.parkinson_volatility) * 100.0, 6),
                    "pressure": feature.buy_sell_pressure,
                    "z_ret": z_ret.z_score if z_ret and z_ret.is_valid else 0.0,
                    "z_vol": z_vol.z_score if z_vol and z_vol.is_valid else 0.0,
                    "z_pressure": z_pressure.z_score if z_pressure and z_pressure.is_valid else 0.0,
                    "ewma_dev": ewma_ret.statistic if ewma_ret and ewma_ret.is_valid else 0.0,
                    "if_score": if_signal.statistic if if_signal and if_signal.is_valid else 0.0,
                    "risk": assessment.risk_score if assessment is not None else 0.0,
                    "severity": assessment.severity.value if assessment is not None else "LOW",
                    "valid": assessment.valid if assessment is not None else False,
                    "contrib": contrib,
                    "agreement": (
                        round(float(assessment.metadata.get("agreement_bonus", 0.0)), 3)
                        if assessment is not None
                        else 0.0
                    ),
                }
            )

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    cache.store(key, bars, elapsed_ms, batches)
    return cache


__all__ = ["DetectionCache", "cache_key", "run_detection"]

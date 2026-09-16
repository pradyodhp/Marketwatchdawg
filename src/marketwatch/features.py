"""Feature engineering and TOD baseline utilities for MarketWatch AI.

This module intentionally stays independent from the dashboard and API layers.
It consumes existing Candle/CandleBatch domain models and produces deterministic,
scale-invariant feature sets plus leakage-safe time-of-day baselines.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

import numpy as np

from marketwatch.models.candle import Candle, CandleBatch
from marketwatch.models.features import FeatureSet


def _safe_float(value: float | None, default: float = 0.0) -> float:
    """Convert values to float while guarding against NaN/Inf noise."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return float(default)
    if not math.isfinite(f):
        return float(default)
    return f


def _safe_ratio(numerator: float, denominator: float, default: float = 1.0) -> float:
    """Return numerator / denominator with deterministic fallback on invalid division."""
    numerator = _safe_float(numerator)
    denominator = _safe_float(denominator)
    if denominator <= 0:
        return float(default)
    return numerator / denominator


def _safe_log_ratio(current_value: float, previous_value: float, default: float = 0.0) -> float:
    """Compute log-ratio but guard against invalid or non-positive inputs."""
    current_value = _safe_float(current_value)
    previous_value = _safe_float(previous_value)
    if current_value <= 0 or previous_value <= 0:
        return float(default)
    return math.log(current_value / previous_value)


@dataclass(frozen=True)
class BaselineStats:
    """Robust baseline summary used for a symbol/slot/feature combination."""

    symbol: str
    slot_index: int
    feature_name: str
    count: int
    mean: float
    std: float
    median: float
    valid: bool


class FeaturePipeline:
    """Compute deterministic, scale-invariant feature sets from OHLCV candles.

    The pipeline is intentionally lightweight and downstream-detector-friendly.
    It emits the feature fields required by the Phase 5 statistical detector and
    the Phase 6 multivariate model without introducing future-data leakage.
    """

    def __init__(self, market_symbol: str | None = None, sector_symbol: str | None = None) -> None:
        self.market_symbol = market_symbol
        self.sector_symbol = sector_symbol

    def compute_feature_from_candle(
        self,
        candle: Candle,
        previous_candle: Candle | None = None,
        market_candle: Candle | None = None,
        sector_candle: Candle | None = None,
        market_previous_candle: Candle | None = None,
        sector_previous_candle: Candle | None = None,
    ) -> FeatureSet:
        """Compute the feature set for one candle, relative to prior observed candles."""
        previous_close = _safe_float(previous_candle.close if previous_candle is not None else None)
        current_close = _safe_float(candle.close)
        current_volume = _safe_float(candle.volume)
        previous_volume = _safe_float(previous_candle.volume if previous_candle is not None else None)

        log_return = _safe_log_ratio(current_close, previous_close) if previous_close > 0 else 0.0

        if previous_volume > 0:
            volume_ratio = current_volume / previous_volume
        else:
            volume_ratio = 1.0 if current_volume > 0 else 0.0

        if candle.high > 0 and candle.low > 0:
            parkinson_volatility = (math.log(candle.high / candle.low) ** 2) / (4.0 * math.log(2.0))
        else:
            parkinson_volatility = 0.0

        market_return = 0.0
        if market_candle is not None and market_previous_candle is not None:
            market_previous_close = _safe_float(market_previous_candle.close)
            market_current_close = _safe_float(market_candle.close)
            market_return = _safe_log_ratio(market_current_close, market_previous_close)

        sector_return = 0.0
        if sector_candle is not None and sector_previous_candle is not None:
            sector_previous_close = _safe_float(sector_previous_candle.close)
            sector_current_close = _safe_float(sector_candle.close)
            sector_return = _safe_log_ratio(sector_current_close, sector_previous_close)

        market_excess_return = log_return - market_return
        sector_excess_return = log_return - sector_return

        raw_features = {
            "log_return": _safe_float(log_return),
            "volume_ratio": _safe_float(volume_ratio),
            "parkinson_volatility": _safe_float(parkinson_volatility),
            "market_excess_return": _safe_float(market_excess_return),
            "sector_excess_return": _safe_float(sector_excess_return),
        }

        return FeatureSet(
            symbol=candle.symbol,
            timestamp=candle.timestamp,
            slot_index=candle.slot_index,
            log_return=raw_features["log_return"],
            volume_ratio=raw_features["volume_ratio"],
            parkinson_volatility=raw_features["parkinson_volatility"],
            market_excess_return=raw_features["market_excess_return"],
            sector_excess_return=raw_features["sector_excess_return"],
            raw_features=raw_features,
        )

    def process_batch(
        self,
        batch: CandleBatch,
        previous_by_symbol: dict[str, Candle] | None = None,
    ) -> dict[str, FeatureSet]:
        """Compute all feature sets for the symbols present in a CandleBatch.

        previous_by_symbol is a dictionary of last observed candles for each symbol
        and must contain only historical data, never the current batch.
        """
        previous = dict(previous_by_symbol or {})
        results: dict[str, FeatureSet] = {}

        market_previous = previous.get(self.market_symbol) if self.market_symbol else None
        sector_previous = previous.get(self.sector_symbol) if self.sector_symbol else None

        for symbol, candle in batch.candles.items():
            prev_candle = previous.get(symbol)
            market_candle = batch.candles.get(self.market_symbol) if self.market_symbol else None
            sector_candle = batch.candles.get(self.sector_symbol) if self.sector_symbol else None

            feature_set = self.compute_feature_from_candle(
                candle=candle,
                previous_candle=prev_candle,
                market_candle=market_candle,
                sector_candle=sector_candle,
                market_previous_candle=market_previous,
                sector_previous_candle=sector_previous,
            )
            results[symbol] = feature_set
            previous[symbol] = candle

        if self.market_symbol and self.market_symbol in batch.candles:
            previous[self.market_symbol] = batch.candles[self.market_symbol]
        if self.sector_symbol and self.sector_symbol in batch.candles:
            previous[self.sector_symbol] = batch.candles[self.sector_symbol]

        return results

    def process_batches(self, batches: Sequence[CandleBatch]) -> list[dict[str, FeatureSet]]:
        """Process a chronological series of CandleBatch objects into feature outputs."""
        previous_by_symbol: dict[str, Candle] = {}
        outputs: list[dict[str, FeatureSet]] = []
        for batch in batches:
            outputs.append(self.process_batch(batch, previous_by_symbol=previous_by_symbol))
            for symbol, candle in batch.candles.items():
                previous_by_symbol[symbol] = candle
        return outputs

    @staticmethod
    def compute_symbol_features(
        candle: Candle,
        previous_candle: Candle | None,
        market_candle: Candle | None = None,
        sector_candle: Candle | None = None,
        market_previous_candle: Candle | None = None,
        sector_previous_candle: Candle | None = None,
    ) -> FeatureSet:
        """Static convenience wrapper for one-symbol feature generation."""
        pipeline = FeaturePipeline(
            market_symbol=market_candle.symbol if market_candle is not None else None,
            sector_symbol=sector_candle.symbol if sector_candle is not None else None,
        )
        return pipeline.compute_feature_from_candle(
            candle=candle,
            previous_candle=previous_candle,
            market_candle=market_candle,
            sector_candle=sector_candle,
            market_previous_candle=market_previous_candle,
            sector_previous_candle=sector_previous_candle,
        )


class TODBaselineEngine:
    """Compute 75-slot time-of-day baselines using only prior historical observations."""

    def __init__(self, min_observations: int = 3, contamination_sigma: float = 6.0) -> None:
        self.min_observations = max(1, min_observations)
        self.contamination_sigma = contamination_sigma

    def _summarize(self, symbol: str, feature_name: str, slot_index: int, values: Sequence[float]) -> BaselineStats:
        values_arr = np.asarray([_safe_float(v) for v in values], dtype=float)
        if values_arr.size == 0:
            return BaselineStats(
                symbol=symbol,
                slot_index=slot_index,
                feature_name=feature_name,
                count=0,
                mean=0.0,
                std=1.0,
                median=0.0,
                valid=False,
            )

        median = float(np.median(values_arr))
        mad = float(np.median(np.abs(values_arr - median)))
        robust_std = 1.4826 * mad if mad > 0 else float(np.std(values_arr, ddof=1)) if values_arr.size > 1 else 1.0
        robust_std = max(float(robust_std), 1e-8)

        if values_arr.size > 1:
            filtered = values_arr[np.abs(values_arr - median) <= self.contamination_sigma * robust_std]
        else:
            filtered = values_arr

        if filtered.size == 0:
            filtered = values_arr

        mean = float(np.mean(filtered))
        std = float(np.std(filtered, ddof=1)) if filtered.size > 1 else 1.0
        std = max(std, 1e-8)

        return BaselineStats(
            symbol=symbol,
            slot_index=slot_index,
            feature_name=feature_name,
            count=int(filtered.size),
            mean=mean,
            std=std,
            median=median,
            valid=filtered.size >= self.min_observations,
        )

    def build_symbol_baselines(
        self,
        symbol: str,
        feature_history: Sequence[FeatureSet],
        feature_name: str,
        reference_time: datetime | None = None,
    ) -> dict[int, BaselineStats]:
        """Build a 75-slot baseline map over historical FeatureSet values.

        reference_time excludes the current observation and any future data from
        the baseline calculation for the same symbol.
        """
        buckets: dict[int, list[float]] = {slot: [] for slot in range(75)}
        for feature in feature_history:
            if feature.symbol != symbol:
                continue
            if reference_time is not None and feature.timestamp >= reference_time:
                continue
            value = getattr(feature, feature_name, None)
            if value is None:
                continue
            buckets[feature.slot_index].append(float(value))

        return {
            slot: self._summarize(symbol, feature_name, slot, values)
            for slot, values in buckets.items()
        }

    def baseline_for_feature(
        self,
        feature: FeatureSet,
        feature_history: Sequence[FeatureSet],
        feature_name: str,
    ) -> BaselineStats:
        """Return the baseline stats for a single feature set, excluding itself."""
        return self.build_symbol_baselines(
            symbol=feature.symbol,
            feature_history=feature_history,
            feature_name=feature_name,
            reference_time=feature.timestamp,
        ).get(feature.slot_index, self._summarize(feature.symbol, feature_name, feature.slot_index, []))

    def build_history_baselines(
        self,
        feature_history: Sequence[FeatureSet],
        feature_name: str,
    ) -> dict[str, dict[int, BaselineStats]]:
        """Build all per-symbol, per-slot baselines from prior features."""
        by_symbol: dict[str, list[FeatureSet]] = {}
        for feature in feature_history:
            by_symbol.setdefault(feature.symbol, []).append(feature)

        result: dict[str, dict[int, BaselineStats]] = {}
        for symbol, values in by_symbol.items():
            result[symbol] = self.build_symbol_baselines(symbol, values, feature_name)
        return result


def build_feature_history(
    batches: Sequence[CandleBatch],
    market_symbol: str | None = None,
    sector_symbol: str | None = None,
) -> list[dict[str, FeatureSet]]:
    """Convenience function to process a sequence of CandleBatch objects into feature batches."""
    pipeline = FeaturePipeline(market_symbol=market_symbol, sector_symbol=sector_symbol)
    return pipeline.process_batches(batches)


def build_tod_baselines(
    feature_history: Sequence[FeatureSet],
    feature_name: str,
    symbol: str | None = None,
) -> dict[str, dict[int, BaselineStats]]:
    """Build per-symbol, per-slot baseline summaries for a named feature."""
    engine = TODBaselineEngine()
    if symbol is not None:
        return {symbol: engine.build_symbol_baselines(symbol, feature_history, feature_name)}
    return engine.build_history_baselines(feature_history, feature_name)


__all__ = [
    "BaselineStats",
    "FeaturePipeline",
    "TODBaselineEngine",
    "build_feature_history",
    "build_tod_baselines",
]

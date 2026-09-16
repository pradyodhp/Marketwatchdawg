"""Phase 4 validation: feature engineering and TOD baselines."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from marketwatch.features import (
    FeaturePipeline,
    TODBaselineEngine,
    build_feature_history,
)
from marketwatch.models.candle import Candle, CandleBatch

IST = ZoneInfo("Asia/Kolkata")


def make_candle(symbol: str, timestamp: datetime, open_: float, close: float, high: float, low: float, volume: float) -> Candle:
    adjusted_high = max(high, open_, close) + 1.0
    adjusted_low = min(low, open_, close) - 1.0
    return Candle(
        symbol=symbol,
        timestamp=timestamp,
        open=open_,
        high=adjusted_high,
        low=adjusted_low,
        close=close,
        volume=volume,
    )


def test_feature_pipeline_known_values():
    day = datetime(2026, 9, 15, 9, 15, tzinfo=IST)
    prev = make_candle("RELIANCE.NS", day, 100.0, 101.0, 102.0, 99.5, 1000.0)
    curr = make_candle("RELIANCE.NS", day + timedelta(minutes=5), 101.0, 104.0, 105.0, 100.5, 1500.0)

    feature = FeaturePipeline().compute_feature_from_candle(curr, prev)

    assert feature.symbol == "RELIANCE.NS"
    assert feature.slot_index == 1
    assert feature.log_return == pytest.approx(0.029270, rel=1e-4)
    assert feature.volume_ratio == pytest.approx(1.5, rel=1e-6)
    assert feature.parkinson_volatility > 0.0
    assert "log_return" in feature.raw_features
    assert feature.raw_features["market_excess_return"] == pytest.approx(feature.log_return)


def test_feature_pipeline_tracks_slot_and_timestamp_alignment():
    start = datetime(2026, 9, 15, 9, 15, tzinfo=IST)
    candles = [
        make_candle("A.NS", start + timedelta(minutes=5 * i), 100.0, 100.0 + i, 101.0 + i, 99.0 + i, 2000.0 + i * 250)
        for i in range(5)
    ]

    previous = None
    pipeline = FeaturePipeline()
    features = []
    for candle in candles:
        features.append(pipeline.compute_feature_from_candle(candle, previous))
        previous = candle

    assert [f.slot_index for f in features] == [0, 1, 2, 3, 4]
    assert [f.timestamp for f in features] == [c.timestamp for c in candles]


def test_tod_baselines_cover_all_75_slots_for_symbol():
    start = datetime(2026, 9, 15, 9, 15, tzinfo=IST)
    features = []
    for slot in range(75):
        ts = start + timedelta(minutes=5 * slot)
        prev_ts = start + timedelta(minutes=5 * max(slot - 1, 0))
        prev_candle = make_candle("A.NS", prev_ts, 100.0, 100.0 + max(slot - 1, 0), 101.0 + max(slot - 1, 0), 99.0 + max(slot - 1, 0), 1000.0 + max(slot - 1, 0) * 10)
        candle = make_candle("A.NS", ts, 100.0, 100.0 + slot, 101.0 + slot, 99.0 + slot, 1000.0 + slot * 10)
        features.append(FeaturePipeline().compute_feature_from_candle(candle, prev_candle if slot > 0 else None))

    baselines = TODBaselineEngine(min_observations=1).build_symbol_baselines("A.NS", features, "volume_ratio")
    assert set(baselines) == set(range(75))
    assert all(stats.valid is True for stats in baselines.values())


def test_repeated_computation_is_deterministic():
    start = datetime(2026, 9, 15, 9, 15, tzinfo=IST)
    pipeline = FeaturePipeline()
    candles = [
        make_candle("A.NS", start + timedelta(minutes=5 * i), 100.0 + i, 101.0 + i, 102.0 + i, 99.0 + i, 1000.0 + i * 50)
        for i in range(8)
    ]

    previous = None
    run_a = []
    run_b = []
    for candle in candles:
        run_a.append(pipeline.compute_feature_from_candle(candle, previous))
        previous = candle

    previous = None
    for candle in candles:
        run_b.append(pipeline.compute_feature_from_candle(candle, previous))
        previous = candle

    assert [f.model_dump(mode="json") for f in run_a] == [f.model_dump(mode="json") for f in run_b]


def test_volume_ratio_and_rolling_window_behavior():
    start = datetime(2026, 9, 15, 9, 15, tzinfo=IST)
    prev = make_candle("A.NS", start, 100.0, 100.0, 101.0, 99.0, 1000.0)
    curr = make_candle("A.NS", start + timedelta(minutes=5), 100.0, 101.0, 102.0, 100.0, 2000.0)
    feature = FeaturePipeline().compute_feature_from_candle(curr, prev)

    assert feature.volume_ratio == pytest.approx(2.0)
    assert feature.raw_features["volume_ratio"] == pytest.approx(2.0)


def test_missing_history_is_handled_without_fabrication():
    candle = make_candle("A.NS", datetime(2026, 9, 15, 9, 15, tzinfo=IST), 100.0, 101.0, 102.0, 99.0, 1000.0)
    feature = FeaturePipeline().compute_feature_from_candle(candle, None)

    assert feature.log_return == 0.0
    assert feature.volume_ratio == 1.0
    assert feature.market_excess_return == 0.0
    assert feature.sector_excess_return == 0.0


def test_insufficient_history_defaults_to_valid_false():
    engine = TODBaselineEngine(min_observations=3)
    start = datetime(2026, 9, 15, 9, 15, tzinfo=IST)
    features = [
        FeaturePipeline().compute_feature_from_candle(
            make_candle("A.NS", start, 100.0, 100.0, 101.0, 99.0, 1000.0),
            None,
        )
    ]
    baselines = engine.build_symbol_baselines("A.NS", features, "log_return")
    assert baselines[0].count == 1
    assert baselines[0].valid is False


def test_no_lookahead_leakage_excludes_current_observation():
    engine = TODBaselineEngine(min_observations=1)
    start = datetime(2026, 9, 15, 9, 15, tzinfo=IST)
    history = []
    prev = None
    for i in range(5):
        candle = make_candle("A.NS", start + timedelta(minutes=5 * i), 100.0 + i, 101.0 + i, 102.0 + i, 99.0 + i, 1000.0 + 100 * i)
        feature = FeaturePipeline().compute_feature_from_candle(candle, prev)
        history.append(feature)
        prev = candle

    current_ts = start + timedelta(minutes=30)
    current = FeaturePipeline().compute_feature_from_candle(
        make_candle("A.NS", current_ts, 105.0, 106.0, 107.0, 104.0, 1500.0),
        prev,
    )
    baseline = engine.baseline_for_feature(current, history, "log_return")
    assert baseline.count == 0
    assert baseline.valid is False


def test_missing_symbols_remain_absent():
    batch = CandleBatch(
        timestamp=datetime(2026, 9, 15, 9, 15, tzinfo=IST),
        slot_index=0,
        candles={
            "A.NS": make_candle("A.NS", datetime(2026, 9, 15, 9, 15, tzinfo=IST), 100.0, 101.0, 102.0, 99.0, 1000.0),
            "B.NS": make_candle("B.NS", datetime(2026, 9, 15, 9, 15, tzinfo=IST), 90.0, 91.0, 92.0, 89.0, 800.0),
        },
    )
    features = FeaturePipeline().process_batch(batch)
    assert set(features) == {"A.NS", "B.NS"}
    assert "MISSING.NS" not in features


def test_provider_integration_with_replay_abstraction(tmp_path):
    from marketwatch.ingestion.parquet_store import (
        write_quality_metadata,
        write_symbol_parquet,
    )
    from marketwatch.providers.parquet_provider import ParquetDataProvider

    path = tmp_path
    ts0 = datetime(2026, 9, 15, 9, 15, tzinfo=IST)
    ts1 = datetime(2026, 9, 15, 9, 20, tzinfo=IST)
    df = pd.DataFrame(
        [
            {"Open": 100.0, "High": 101.0, "Low": 99.0, "Close": 101.0, "Volume": 1000.0},
            {"Open": 101.0, "High": 104.0, "Low": 100.0, "Close": 103.0, "Volume": 1500.0},
        ],
        index=pd.DatetimeIndex([ts0, ts1], tz="Asia/Kolkata", name="Datetime"),
    )
    write_symbol_parquet("A.NS", df, curated_dir=path)
    write_quality_metadata({"loaded_symbols": ["A.NS"], "requested_symbols": ["A.NS"], "coverage_pct": 100.0}, curated_dir=path)

    provider = ParquetDataProvider(curated_dir=path)
    batches = list(provider.stream_batches(["A.NS"]))
    feature_batches = build_feature_history(batches)

    assert len(feature_batches) == 2
    assert set(feature_batches[0]) == {"A.NS"}
    assert feature_batches[0]["A.NS"].slot_index == 0
    assert feature_batches[1]["A.NS"].slot_index == 1


def test_downstream_detector_compatibility():
    feature = FeaturePipeline().compute_feature_from_candle(
        make_candle("A.NS", datetime(2026, 9, 15, 9, 15, tzinfo=IST), 100.0, 101.0, 101.5, 99.5, 1200.0),
        None,
    )

    assert set(feature.raw_features) == {"log_return", "volume_ratio", "parkinson_volatility", "market_excess_return", "sector_excess_return"}
    assert feature.raw_features["volume_ratio"] >= 0.0
    assert feature.parkinson_volatility >= 0.0

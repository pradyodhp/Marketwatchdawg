"""Comprehensive tests for Phase 3: Deterministic Replay Engine.

All tests are fully offline using synthetic CandleBatch fixtures.
"""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from marketwatch.models.candle import Candle, CandleBatch
from marketwatch.replay.clock import ReplayClock
from marketwatch.replay.engine import PlaybackState, ReplayEngine

IST = ZoneInfo("Asia/Kolkata")

# ── Fixtures ──────────────────────────────────────────────────────────────────

def _ts(year: int, month: int, day: int, hour: int, minute: int) -> datetime:
    return datetime(year, month, day, hour, minute, 0, tzinfo=IST)


def _candle(symbol: str, ts: datetime, price: float = 100.0) -> Candle:
    return Candle(
        symbol=symbol,
        timestamp=ts,
        open=price,
        high=price + 2.0,
        low=price - 1.0,
        close=price + 1.0,
        volume=10000.0,
    )


def _batch(ts: datetime, symbols: list[str], slot: int, price: float = 100.0) -> CandleBatch:
    candles = {s: _candle(s, ts, price) for s in symbols}
    return CandleBatch(timestamp=ts, slot_index=slot, candles=candles)


# Day 1: 3 bars at 09:15, 09:20, 09:25
D1_T0 = _ts(2024, 1, 15, 9, 15)
D1_T1 = _ts(2024, 1, 15, 9, 20)
D1_T2 = _ts(2024, 1, 15, 9, 25)

# Day 2: 2 bars at 09:15, 09:20
D2_T0 = _ts(2024, 1, 16, 9, 15)
D2_T1 = _ts(2024, 1, 16, 9, 20)

SYMBOLS = ["A.NS", "B.NS", "C.NS"]


def _make_batches() -> list[CandleBatch]:
    """5 batches across 2 trading days."""
    return [
        _batch(D1_T0, SYMBOLS, 0, 100.0),
        _batch(D1_T1, SYMBOLS, 1, 101.0),
        _batch(D1_T2, ["A.NS", "B.NS"], 2, 102.0),  # C.NS missing (sparse)
        _batch(D2_T0, SYMBOLS, 0, 103.0),
        _batch(D2_T1, ["A.NS"], 1, 104.0),  # only A.NS (very sparse)
    ]


# ── ReplayClock Tests ─────────────────────────────────────────────────────────

class TestReplayClock:
    def test_initial_state(self):
        clock = ReplayClock([D1_T0, D1_T1, D1_T2])
        assert clock.position == -1
        assert clock.is_at_start
        assert clock.current_timestamp is None
        assert clock.total_steps == 3
        assert clock.progress_pct == 0.0

    def test_advance_sequence(self):
        clock = ReplayClock([D1_T0, D1_T1, D1_T2])
        ts = clock.advance()
        assert ts == D1_T0
        assert clock.position == 0
        assert clock.current_timestamp == D1_T0
        ts = clock.advance()
        assert ts == D1_T1
        assert clock.position == 1

    def test_exhaustion(self):
        clock = ReplayClock([D1_T0, D1_T1])
        clock.advance()
        clock.advance()
        assert clock.is_exhausted
        assert clock.advance() is None
        assert clock.remaining_steps == 0

    def test_progress_pct(self):
        clock = ReplayClock([D1_T0, D1_T1, D1_T2, D2_T0])
        clock.advance()  # pos=0
        assert abs(clock.progress_pct - 25.0) < 0.1
        clock.advance()  # pos=1
        assert abs(clock.progress_pct - 50.0) < 0.1
        clock.advance()  # pos=2
        assert abs(clock.progress_pct - 75.0) < 0.1
        clock.advance()  # pos=3
        assert abs(clock.progress_pct - 100.0) < 0.1

    def test_reset(self):
        clock = ReplayClock([D1_T0, D1_T1])
        clock.advance()
        clock.advance()
        clock.reset()
        assert clock.position == -1
        assert clock.is_at_start

    def test_trading_date(self):
        clock = ReplayClock([D1_T0, D2_T0])
        clock.advance()
        assert clock.current_trading_date == date(2024, 1, 15)
        clock.advance()
        assert clock.current_trading_date == date(2024, 1, 16)

    def test_empty_timestamps_raises(self):
        with pytest.raises(ValueError, match="at least one"):
            ReplayClock([])

    def test_unsorted_timestamps_raises(self):
        with pytest.raises(ValueError, match="not sorted"):
            ReplayClock([D1_T1, D1_T0])

    def test_first_last_timestamp(self):
        clock = ReplayClock([D1_T0, D1_T1, D1_T2])
        assert clock.first_timestamp == D1_T0
        assert clock.last_timestamp == D1_T2


# ── ReplayEngine Tests ────────────────────────────────────────────────────────

class TestReplayEngine:
    def test_construction(self):
        batches = _make_batches()
        engine = ReplayEngine(batches)
        assert engine.total_batches == 5
        assert engine.state == PlaybackState.STOPPED
        assert engine.current_batch is None

    def test_empty_batches_raises(self):
        with pytest.raises(ValueError, match="at least one"):
            ReplayEngine([])

    def test_unsorted_batches_raises(self):
        batches = _make_batches()
        with pytest.raises(ValueError, match="chronological"):
            ReplayEngine([batches[1], batches[0]])

    def test_step_forward_basic(self):
        engine = ReplayEngine(_make_batches())
        b1 = engine.step_forward()
        assert b1 is not None
        assert b1.timestamp == D1_T0
        assert engine.state == PlaybackState.PLAYING

        b2 = engine.step_forward()
        assert b2 is not None
        assert b2.timestamp == D1_T1

    def test_step_forward_exhaustion(self):
        batches = _make_batches()
        engine = ReplayEngine(batches)
        for _ in range(5):
            engine.step_forward()
        assert engine.is_complete
        assert engine.step_forward() is None
        assert engine.state == PlaybackState.STOPPED

    def test_chronological_order(self):
        engine = ReplayEngine(_make_batches())
        timestamps = []
        while not engine.is_complete:
            batch = engine.step_forward()
            if batch:
                timestamps.append(batch.timestamp)
        assert timestamps == sorted(timestamps)
        assert len(timestamps) == 5

    def test_5_minute_progression(self):
        engine = ReplayEngine(_make_batches())
        b0 = engine.step_forward()
        b1 = engine.step_forward()
        assert b0 is not None and b1 is not None
        delta = (b1.timestamp - b0.timestamp).total_seconds()
        assert delta == 300.0  # 5 minutes

    def test_slot_index_progression(self):
        engine = ReplayEngine(_make_batches())
        slots = []
        while not engine.is_complete:
            batch = engine.step_forward()
            if batch:
                slots.append(batch.slot_index)
        # Day 1: 0, 1, 2 then Day 2: 0, 1
        assert slots == [0, 1, 2, 0, 1]

    def test_sparse_batch_preserves_missing(self):
        """Tickers missing at some timestamps must be absent, not fabricated."""
        engine = ReplayEngine(_make_batches())
        engine.step_forward()  # D1_T0 — all 3
        engine.step_forward()  # D1_T1 — all 3
        b3 = engine.step_forward()  # D1_T2 — A, B only
        assert b3 is not None
        assert "A.NS" in b3
        assert "B.NS" in b3
        assert "C.NS" not in b3  # sparse — NOT fabricated

    def test_very_sparse_batch(self):
        engine = ReplayEngine(_make_batches())
        for _ in range(5):
            b = engine.step_forward()
        # Last batch — only A.NS
        assert b is not None
        assert "A.NS" in b
        assert "B.NS" not in b
        assert "C.NS" not in b
        assert len(b) == 1

    def test_trading_session_boundaries(self):
        """Each trading day starts at slot 0 (09:15 IST)."""
        engine = ReplayEngine(_make_batches())
        engine.step_forward()  # D1 slot 0
        assert engine.clock.current_trading_date == date(2024, 1, 15)
        engine.step_forward()  # D1 slot 1
        engine.step_forward()  # D1 slot 2
        engine.step_forward()  # D2 slot 0
        assert engine.clock.current_trading_date == date(2024, 1, 16)
        assert engine.current_batch.slot_index == 0

    def test_play_yields_all(self):
        engine = ReplayEngine(_make_batches())
        results = list(engine.play(speed=float("inf")))
        assert len(results) == 5
        assert all(isinstance(b, CandleBatch) for b in results)

    def test_play_chronological(self):
        engine = ReplayEngine(_make_batches())
        results = list(engine.play(speed=float("inf")))
        timestamps = [b.timestamp for b in results]
        assert timestamps == sorted(timestamps)

    def test_pause_stops_play(self):
        engine = ReplayEngine(_make_batches())
        collected = []
        for batch in engine.play(speed=float("inf")):
            collected.append(batch)
            if len(collected) == 2:
                engine.pause()
        assert len(collected) == 2
        assert engine.state == PlaybackState.PAUSED

    def test_resume_after_pause(self):
        engine = ReplayEngine(_make_batches())
        # Step to position 2
        engine.step_forward()
        engine.step_forward()
        engine.pause()
        # Resume and collect remaining
        remaining = list(engine.resume())
        assert len(remaining) == 3  # 3 remaining batches

    def test_reset_replays_identically(self):
        """Determinism: reset and replay yields identical sequence."""
        engine = ReplayEngine(_make_batches())
        run1 = list(engine.play(speed=float("inf")))
        engine.reset()
        run2 = list(engine.play(speed=float("inf")))
        assert len(run1) == len(run2)
        for b1, b2 in zip(run1, run2):
            assert b1.timestamp == b2.timestamp
            assert b1.slot_index == b2.slot_index
            assert set(b1.candles.keys()) == set(b2.candles.keys())

    def test_deterministic_across_instances(self):
        """Two engines from the same batches produce identical sequences."""
        batches = _make_batches()
        e1 = ReplayEngine(list(batches))
        e2 = ReplayEngine(list(batches))
        r1 = list(e1.play(speed=float("inf")))
        r2 = list(e2.play(speed=float("inf")))
        for b1, b2 in zip(r1, r2):
            assert b1.timestamp == b2.timestamp
            assert b1.slot_index == b2.slot_index

    def test_zero_lookahead_history(self):
        """History only contains past batches — never future data."""
        engine = ReplayEngine(_make_batches())
        engine.step_forward()  # pos=0
        engine.step_forward()  # pos=1
        assert len(engine.history) == 2
        # History timestamps must all be <= current
        current_ts = engine.clock.current_timestamp
        for b in engine.history:
            assert b.timestamp <= current_ts

    def test_get_batches_up_to_current(self):
        engine = ReplayEngine(_make_batches())
        engine.step_forward()
        engine.step_forward()
        engine.step_forward()
        up_to = engine.get_batches_up_to_current()
        assert len(up_to) == 3
        # Must NOT include future batches
        assert all(b.timestamp <= engine.clock.current_timestamp for b in up_to)

    def test_get_history_for_symbol(self):
        engine = ReplayEngine(_make_batches())
        for _ in range(5):
            engine.step_forward()
        a_history = engine.get_history_for_symbol("A.NS")
        assert len(a_history) == 5  # A.NS present in all batches
        c_history = engine.get_history_for_symbol("C.NS")
        assert len(c_history) == 3  # C.NS in D1_T0, D1_T1, D2_T0

    def test_speed_setter(self):
        engine = ReplayEngine(_make_batches())
        engine.speed = 2.0
        assert engine.speed == 2.0
        with pytest.raises(ValueError, match="positive"):
            engine.speed = 0
        with pytest.raises(ValueError, match="positive"):
            engine.speed = -1.0

    def test_replay_summary(self):
        engine = ReplayEngine(_make_batches())
        engine.step_forward()
        summary = engine.get_replay_summary()
        assert summary["state"] == "playing"
        assert summary["position"] == 0
        assert summary["total_batches"] == 5
        assert summary["remaining_steps"] == 4
        assert summary["history_length"] == 1
        assert summary["current_timestamp"] is not None

    def test_is_complete(self):
        engine = ReplayEngine(_make_batches())
        assert not engine.is_complete
        for _ in range(5):
            engine.step_forward()
        assert engine.is_complete

    def test_candle_batch_types(self):
        """All yielded objects are CandleBatch with typed Candle values."""
        engine = ReplayEngine(_make_batches())
        for batch in engine.play(speed=float("inf")):
            assert isinstance(batch, CandleBatch)
            for sym, candle in batch.candles.items():
                assert isinstance(candle, Candle)
                assert isinstance(sym, str)

    def test_75_slot_boundary(self):
        """Slot index 74 (15:25 IST) is the maximum valid slot."""
        ts_last = _ts(2024, 1, 15, 15, 25)
        batch = _batch(ts_last, ["A.NS"], 74)
        engine = ReplayEngine([batch])
        b = engine.step_forward()
        assert b is not None
        assert b.slot_index == 74


# ── Integration with Phase 2 ParquetDataProvider ─────────────────────────────

class TestReplayWithParquetProvider:
    def _make_provider(self, tmp_path):
        """Create a mini ParquetDataProvider with synthetic data."""
        import pandas as pd
        from marketwatch.ingestion.parquet_store import (
            write_symbol_parquet,
            write_quality_metadata,
        )
        from marketwatch.providers.parquet_provider import ParquetDataProvider

        # Create 3 bars for 2 symbols
        for sym in ["TEST1.NS", "TEST2.NS"]:
            rows = {
                "Open": [100.0, 101.0, 102.0],
                "High": [102.0, 103.0, 104.0],
                "Low": [99.0, 100.0, 101.0],
                "Close": [101.0, 102.0, 103.0],
                "Volume": [10000.0, 20000.0, 30000.0],
            }
            idx = pd.DatetimeIndex(
                [D1_T0, D1_T1, D1_T2], name="Datetime", tz="Asia/Kolkata"
            )
            df = pd.DataFrame(rows, index=idx)
            write_symbol_parquet(sym, df, curated_dir=tmp_path)

        write_quality_metadata({
            "loaded_symbols": ["TEST1.NS", "TEST2.NS"],
            "requested_symbols": ["TEST1.NS", "TEST2.NS"],
            "missing_symbols": [],
            "coverage_pct": 100.0,
            "date_range_start": D1_T0.isoformat(),
            "date_range_end": D1_T2.isoformat(),
        }, curated_dir=tmp_path)

        return ParquetDataProvider(curated_dir=tmp_path)

    def test_from_provider(self, tmp_path):
        provider = self._make_provider(tmp_path)
        engine = ReplayEngine.from_provider(provider)
        assert engine.total_batches == 3
        batches = list(engine.play(speed=float("inf")))
        assert len(batches) == 3
        # Both symbols at each timestamp
        for b in batches:
            assert "TEST1.NS" in b
            assert "TEST2.NS" in b

    def test_from_provider_deterministic(self, tmp_path):
        provider = self._make_provider(tmp_path)
        e1 = ReplayEngine.from_provider(provider)
        run1 = list(e1.play(speed=float("inf")))
        e2 = ReplayEngine.from_provider(provider)
        run2 = list(e2.play(speed=float("inf")))
        for b1, b2 in zip(run1, run2):
            assert b1.timestamp == b2.timestamp
            assert set(b1.candles.keys()) == set(b2.candles.keys())

    def test_from_provider_with_date_filter(self, tmp_path):
        provider = self._make_provider(tmp_path)
        engine = ReplayEngine.from_provider(
            provider, start=date(2024, 1, 15), end=date(2024, 1, 15)
        )
        batches = list(engine.play(speed=float("inf")))
        assert len(batches) == 3  # all 3 are on Jan 15

    def test_from_provider_candle_values_preserved(self, tmp_path):
        provider = self._make_provider(tmp_path)
        engine = ReplayEngine.from_provider(provider)
        b = engine.step_forward()
        assert b is not None
        c = b["TEST1.NS"]
        assert c.open == 100.0
        assert c.high == 102.0
        assert c.low == 99.0
        assert c.close == 101.0
        assert c.volume == 10000.0

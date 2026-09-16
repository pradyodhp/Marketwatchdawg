"""Pytest configuration and shared fixtures for MarketWatch AI."""

from datetime import datetime
from zoneinfo import ZoneInfo
import pytest
from marketwatch.models.candle import Candle, CandleBatch

IST = ZoneInfo("Asia/Kolkata")


@pytest.fixture
def sample_ist_datetime() -> datetime:
    """09:15:00 IST on 2026-09-15 (Slot 0)."""
    return datetime(2026, 9, 15, 9, 15, 0, tzinfo=IST)


@pytest.fixture
def sample_midday_datetime() -> datetime:
    """12:00:00 IST on 2026-09-15 (Slot 33)."""
    return datetime(2026, 9, 15, 12, 0, 0, tzinfo=IST)


@pytest.fixture
def sample_close_datetime() -> datetime:
    """15:25:00 IST on 2026-09-15 (Slot 74)."""
    return datetime(2026, 9, 15, 15, 25, 0, tzinfo=IST)


@pytest.fixture
def valid_candle_dict(sample_ist_datetime) -> dict:
    """Dictionary representing valid Reliance 5m candle."""
    return {
        "symbol": "RELIANCE.NS",
        "timestamp": sample_ist_datetime,
        "open": 2500.0,
        "high": 2515.0,
        "low": 2495.0,
        "close": 2510.0,
        "volume": 25000.0,
    }


@pytest.fixture
def sample_candle(valid_candle_dict) -> Candle:
    """Sample Candle instance."""
    return Candle.model_validate(valid_candle_dict)


@pytest.fixture
def sample_candle_batch(sample_candle, sample_ist_datetime) -> CandleBatch:
    """Sample CandleBatch with single constituent."""
    return CandleBatch(
        timestamp=sample_ist_datetime,
        slot_index=0,
        candles={"RELIANCE.NS": sample_candle},
    )

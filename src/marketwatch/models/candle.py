"""Domain models for 5-minute equity candles and cross-sectional batches."""

from __future__ import annotations

import math
from collections.abc import Iterator
from datetime import date, datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

IST = ZoneInfo("Asia/Kolkata")
MARKET_OPEN_MINUTES = 9 * 60 + 15  # 09:15 IST = 555 minutes
TOTAL_DAILY_SLOTS = 75             # 75 5-minute slots (09:15 to 15:30)


def compute_slot_index(dt: datetime) -> int:
    """Compute 5-minute intraday slot index (0..74) for NSE market hours.

    Args:
        dt: A timezone-aware datetime.

    Returns:
        Integer slot index between 0 and 74 inclusive.

    Raises:
        ValueError: If dt is outside regular trading hours (09:15 - 15:30 IST).
    """
    dt_ist = dt.astimezone(IST)
    minutes_from_midnight = dt_ist.hour * 60 + dt_ist.minute
    minutes_from_open = minutes_from_midnight - MARKET_OPEN_MINUTES

    # Each slot is [open_min, open_min + 5)
    # Slot 0: 09:15 - 09:20
    # Slot 74: 15:25 - 15:30
    slot = minutes_from_open // 5
    if slot < 0 or slot >= TOTAL_DAILY_SLOTS:
        raise ValueError(
            f"Timestamp {dt_ist.isoformat()} ({dt_ist.strftime('%H:%M:%S')} IST) "
            f"is outside NSE trading hours (09:15 - 15:30 IST, slot {slot})"
        )
    return slot


class Candle(BaseModel):
    """Immutable single-ticker 5-minute OHLCV candle.

    Enforces financial price and volume invariants, IST timezone normalization,
    and diurnal slot calculation.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp(cls, v: datetime) -> datetime:
        """Ensure timestamp is timezone-aware and normalized to Asia/Kolkata."""
        if v.tzinfo is None:
            # Assume local IST if naive
            return v.replace(tzinfo=IST)
        return v.astimezone(IST)

    @model_validator(mode="after")
    def validate_financial_invariants(self) -> Candle:
        """Enforce OHLC relationships, finite non-negative values, and valid prices."""
        # 1. Finite float checks (prevent NaN / Inf leakage)
        for field_name, value in [
            ("open", self.open),
            ("high", self.high),
            ("low", self.low),
            ("close", self.close),
            ("volume", self.volume),
        ]:
            if not math.isfinite(value):
                raise ValueError(f"Candle field '{field_name}' must be finite, got {value}")

        # 2. Strict positive price check
        if self.open <= 0 or self.high <= 0 or self.low <= 0 or self.close <= 0:
            raise ValueError(
                f"Candle prices must be strictly positive: "
                f"open={self.open}, high={self.high}, low={self.low}, close={self.close}"
            )

        # 3. Non-negative volume
        if self.volume < 0:
            raise ValueError(f"Candle volume cannot be negative: volume={self.volume}")

        # 4. Standard OHLC geometric bounds
        if self.high < self.low:
            raise ValueError(f"High ({self.high}) cannot be less than low ({self.low})")

        if self.high < self.open or self.high < self.close:
            raise ValueError(
                f"High ({self.high}) must be >= max(open, close) (open={self.open}, close={self.close})"
            )

        if self.low > self.open or self.low > self.close:
            raise ValueError(
                f"Low ({self.low}) must be <= min(open, close) (open={self.open}, close={self.close})"
            )

        # 5. Validate trading hours eagerly — raises ValueError if out of 09:15-15:30 IST
        compute_slot_index(self.timestamp)

        return self

    @property
    def slot_index(self) -> int:
        """Computed 5-minute diurnal slot index (0..74)."""
        return compute_slot_index(self.timestamp)

    @property
    def trading_date(self) -> date:
        """Trading calendar date in IST."""
        return self.timestamp.astimezone(IST).date()


class CandleBatch(BaseModel):
    """Synchronized cross-sectional batch of 5-minute candles across tickers at timestamp t.

    Uses a sparse dictionary mapping symbol -> Candle, omitting tickers that
    did not trade or were halted so downstream engines never receive fabricated data.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    timestamp: datetime
    slot_index: int
    candles: dict[str, Candle]

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp(cls, v: datetime) -> datetime:
        """Ensure timestamp is normalized to Asia/Kolkata."""
        if v.tzinfo is None:
            return v.replace(tzinfo=IST)
        return v.astimezone(IST)

    @property
    def active_symbols(self) -> list[str]:
        """List of active symbols present in this candle batch."""
        return sorted(self.candles.keys())

    def __getitem__(self, symbol: str) -> Candle:
        return self.candles[symbol]

    def __contains__(self, symbol: str) -> bool:
        return symbol in self.candles

    def __len__(self) -> int:
        return len(self.candles)

    def __iter__(self) -> Iterator[str]:
        return iter(self.candles)

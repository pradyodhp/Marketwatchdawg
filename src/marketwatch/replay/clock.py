"""Replay clock controller — tracks temporal position within the replay sequence.

The ReplayClock is a thin cursor over a sorted list of timestamps that
the engine will step through.  It enforces strict forward-only traversal
and provides temporal boundary information.
"""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


class ReplayClock:
    """Forward-only temporal cursor for deterministic replay.

    The clock steps through a sorted list of timestamps, exposing the
    current position without allowing backward movement or random access
    to future timestamps.

    Attributes:
        timestamps: Immutable sorted list of all replay timestamps.
        position: Current index into the timestamp list (-1 = before start).
    """

    def __init__(self, timestamps: list[datetime]) -> None:
        """Initialize with a sorted list of IST-aware timestamps.

        Args:
            timestamps: Sorted chronological 5-minute bar timestamps.

        Raises:
            ValueError: If timestamps are empty or not sorted.
        """
        if not timestamps:
            raise ValueError("ReplayClock requires at least one timestamp")
        # Verify sorted order
        for i in range(1, len(timestamps)):
            if timestamps[i] <= timestamps[i - 1]:
                raise ValueError(
                    f"Timestamps not sorted at index {i}: "
                    f"{timestamps[i-1]} >= {timestamps[i]}"
                )
        self._timestamps = list(timestamps)
        self._position: int = -1  # before first timestamp

    @property
    def timestamps(self) -> list[datetime]:
        """Return the full list of replay timestamps (read-only copy)."""
        return list(self._timestamps)

    @property
    def position(self) -> int:
        """Current index in the timestamp sequence (-1 = before start)."""
        return self._position

    @property
    def total_steps(self) -> int:
        """Total number of timestamps in the replay sequence."""
        return len(self._timestamps)

    @property
    def current_timestamp(self) -> datetime | None:
        """Current timestamp, or None if before start or past end."""
        if 0 <= self._position < len(self._timestamps):
            return self._timestamps[self._position]
        return None

    @property
    def is_at_start(self) -> bool:
        """True if the clock has not yet advanced."""
        return self._position < 0

    @property
    def is_at_end(self) -> bool:
        """True if the clock has reached the final timestamp."""
        return self._position >= len(self._timestamps) - 1

    @property
    def is_exhausted(self) -> bool:
        """True if there are no more steps to advance."""
        return self._position >= len(self._timestamps) - 1

    @property
    def remaining_steps(self) -> int:
        """Number of steps remaining after the current position."""
        return max(0, len(self._timestamps) - 1 - self._position)

    @property
    def progress_pct(self) -> float:
        """Replay progress as percentage (0.0 to 100.0)."""
        if self._position < 0:
            return 0.0
        return min(100.0, (self._position + 1) / len(self._timestamps) * 100)

    @property
    def first_timestamp(self) -> datetime:
        return self._timestamps[0]

    @property
    def last_timestamp(self) -> datetime:
        return self._timestamps[-1]

    @property
    def current_trading_date(self) -> date | None:
        """Trading date (IST) of the current timestamp."""
        ts = self.current_timestamp
        return ts.astimezone(IST).date() if ts else None

    def advance(self) -> datetime | None:
        """Advance the clock by one step.  Returns the new timestamp or None if exhausted."""
        if self._position >= len(self._timestamps) - 1:
            return None
        self._position += 1
        return self._timestamps[self._position]

    def reset(self) -> None:
        """Reset clock to before-start position for re-replay."""
        self._position = -1

    def __repr__(self) -> str:
        ts = self.current_timestamp
        ts_str = ts.isoformat() if ts else "NOT_STARTED"
        return (
            f"ReplayClock(position={self._position}/{self.total_steps}, "
            f"ts={ts_str}, progress={self.progress_pct:.1f}%)"
        )

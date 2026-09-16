"""Deterministic Replay Engine — synchronized 5-minute candle replay.

The ReplayEngine loads all candle batches from a MarketDataProvider at
initialization, sorts them chronologically, and exposes a deterministic
step-through interface with play/pause/resume/step-forward controls and
variable speed throttling.

Guarantees:
  - Deterministic: same provider + same config = identical replay every time.
  - Zero lookahead: at step t, only data from timestamps <= t is accessible.
  - Sparse batches: tickers missing at any timestamp are simply absent.
  - Headless: no dependency on UI, API, or network.
"""
from __future__ import annotations

import enum
import logging
import time
from collections.abc import Iterator
from datetime import date

from marketwatch.models.candle import CandleBatch
from marketwatch.replay.clock import ReplayClock

logger = logging.getLogger(__name__)


class PlaybackState(enum.Enum):
    """Replay engine lifecycle states."""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"


class ReplayEngine:
    """Stateful, deterministic 5-minute candle replay engine.

    Usage:
        provider = ParquetDataProvider(...)
        engine = ReplayEngine.from_provider(provider)

        # Step-by-step
        batch = engine.step_forward()

        # Continuous play with throttle
        for batch in engine.play(speed=2.0):
            process(batch)

        # Pause / Resume
        engine.pause()
        engine.resume()
    """

    def __init__(self, batches: list[CandleBatch]) -> None:
        """Initialize with a pre-sorted list of CandleBatch objects.

        Args:
            batches: Chronologically sorted list of CandleBatch objects.

        Raises:
            ValueError: If batches is empty.
        """
        if not batches:
            raise ValueError("ReplayEngine requires at least one CandleBatch")

        # Verify chronological order
        for i in range(1, len(batches)):
            if batches[i].timestamp <= batches[i - 1].timestamp:
                raise ValueError(
                    f"Batches not in chronological order at index {i}: "
                    f"{batches[i-1].timestamp} >= {batches[i].timestamp}"
                )

        self._batches = list(batches)
        self._clock = ReplayClock([b.timestamp for b in self._batches])
        self._state = PlaybackState.STOPPED
        self._speed: float = 1.0
        self._history: list[CandleBatch] = []  # past batches (anti-leakage buffer)

    @classmethod
    def from_provider(
        cls,
        provider: object,
        symbols: list[str] | None = None,
        start: date | None = None,
        end: date | None = None,
    ) -> ReplayEngine:
        """Create a ReplayEngine from a data provider.

        Args:
            provider: Object with stream_batches() method (MarketDataProvider).
            symbols: Optional subset of symbols.  None = all available.
            start: Optional inclusive start date.
            end: Optional inclusive end date.

        Returns:
            Initialized ReplayEngine with all batches pre-loaded.
        """
        if symbols is not None:
            batches = list(provider.stream_batches(symbols=symbols, start=start, end=end))
        else:
            batches = list(provider.stream_batches(start=start, end=end))

        if not batches:
            raise ValueError("Provider yielded zero batches for the given parameters")

        # Ensure chronological sort (defensive — provider should already sort)
        batches.sort(key=lambda b: b.timestamp)

        return cls(batches)

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def state(self) -> PlaybackState:
        """Current playback state."""
        return self._state

    @property
    def clock(self) -> ReplayClock:
        """Access the replay clock for position/progress info."""
        return self._clock

    @property
    def speed(self) -> float:
        """Current replay speed multiplier (1.0 = real-time, higher = faster)."""
        return self._speed

    @speed.setter
    def speed(self, value: float) -> None:
        if value <= 0:
            raise ValueError(f"Speed must be positive, got {value}")
        self._speed = value

    @property
    def current_batch(self) -> CandleBatch | None:
        """Current CandleBatch, or None if not yet started."""
        pos = self._clock.position
        if 0 <= pos < len(self._batches):
            return self._batches[pos]
        return None

    @property
    def total_batches(self) -> int:
        """Total number of batches in the replay sequence."""
        return len(self._batches)

    @property
    def history(self) -> list[CandleBatch]:
        """All batches that have been replayed so far (anti-leakage: past only).

        This list never contains future data.
        """
        return list(self._history)

    @property
    def is_complete(self) -> bool:
        """True if the replay has reached the end of the sequence."""
        return self._clock.is_exhausted

    # ── Playback controls ─────────────────────────────────────────────────────

    def step_forward(self) -> CandleBatch | None:
        """Advance the replay by exactly one 5-minute bar.

        Returns:
            The next CandleBatch, or None if replay is exhausted.
        """
        ts = self._clock.advance()
        if ts is None:
            self._state = PlaybackState.STOPPED
            return None

        batch = self._batches[self._clock.position]
        self._history.append(batch)
        self._state = PlaybackState.PLAYING
        return batch

    def play(self, speed: float | None = None) -> Iterator[CandleBatch]:
        """Continuous replay generator yielding batches with throttle delay.

        Args:
            speed: Replay speed multiplier.  None = use current speed.
                   Higher = faster.  At speed=1.0, each step waits 5 minutes
                   of simulated time (scaled).

        Yields:
            CandleBatch objects in chronological order.
        """
        if speed is not None:
            self.speed = speed

        self._state = PlaybackState.PLAYING

        while not self._clock.is_exhausted:
            if self._state == PlaybackState.PAUSED:
                break

            batch = self.step_forward()
            if batch is None:
                break

            yield batch

            # Throttle: simulate passage of time between bars
            # At speed=1.0, wait 0.0s (no real-time delay for offline replay)
            # The delay is purely for presentation — scaled by 1/speed
            if self._speed < float("inf") and not self._clock.is_exhausted:
                delay = max(0.0, 0.01 / self._speed)  # minimal delay for responsiveness
                if delay > 0:
                    time.sleep(delay)

        if self._clock.is_exhausted:
            self._state = PlaybackState.STOPPED

    def pause(self) -> None:
        """Pause replay.  Resume with resume() or step_forward()."""
        if self._state == PlaybackState.PLAYING:
            self._state = PlaybackState.PAUSED
            logger.info("Replay paused at position %d", self._clock.position)

    def resume(self) -> Iterator[CandleBatch]:
        """Resume replay from paused state.  Returns iterator of remaining batches."""
        if self._state != PlaybackState.PAUSED:
            logger.warning("Cannot resume — state is %s", self._state.value)
            return
        self._state = PlaybackState.PLAYING
        yield from self.play()

    def reset(self) -> None:
        """Reset replay to the beginning for a fresh deterministic run."""
        self._clock.reset()
        self._history.clear()
        self._state = PlaybackState.STOPPED
        logger.info("Replay engine reset to beginning")

    # ── Temporal anti-leakage ─────────────────────────────────────────────────

    def get_history_for_symbol(self, symbol: str) -> list[CandleBatch]:
        """Return past batches containing a specific symbol (no future data)."""
        return [b for b in self._history if symbol in b]

    def get_batches_up_to_current(self) -> list[CandleBatch]:
        """Return all batches from start up to and including current position.

        This is the only safe way to access data — guaranteed zero lookahead.
        """
        pos = self._clock.position
        if pos < 0:
            return []
        return list(self._batches[:pos + 1])

    # ── Info ──────────────────────────────────────────────────────────────────

    def get_replay_summary(self) -> dict:
        """Return a summary dict of the current replay state."""
        return {
            "state": self._state.value,
            "position": self._clock.position,
            "total_batches": self.total_batches,
            "progress_pct": self._clock.progress_pct,
            "speed": self._speed,
            "current_timestamp": (
                self._clock.current_timestamp.isoformat()
                if self._clock.current_timestamp
                else None
            ),
            "first_timestamp": self._clock.first_timestamp.isoformat(),
            "last_timestamp": self._clock.last_timestamp.isoformat(),
            "remaining_steps": self._clock.remaining_steps,
            "history_length": len(self._history),
        }

    def __repr__(self) -> str:
        return (
            f"ReplayEngine(state={self._state.value}, "
            f"batches={self.total_batches}, {self._clock})"
        )

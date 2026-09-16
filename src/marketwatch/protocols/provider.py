"""Abstract market data provider protocol contracts."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from typing import Protocol, runtime_checkable

from marketwatch.models.candle import Candle, CandleBatch
from marketwatch.models.metadata import DataQualityMetadata


@runtime_checkable
class MarketDataProvider(Protocol):
    """Abstract interface decoupling market data feeds from downstream surveillance engines.

    Enforces synchronous generator streaming for zero-copy in-memory replay and
    audit metadata inspection.
    """

    def get_symbols(self) -> list[str]:
        """Return list of all symbols available in the provider's dataset."""
        ...

    def get_date_range(self) -> tuple[datetime, datetime]:
        """Return the start and end timestamp of available data."""
        ...

    def get_quality_metadata(self) -> DataQualityMetadata:
        """Return dataset quality, coverage, and offline-source confirmation."""
        ...

    def get_candles(self, symbol: str) -> Iterator[Candle]:
        """Yield sequential candles for an individual ticker."""
        ...

    def stream_batches(self) -> Iterator[CandleBatch]:
        """Yield synchronized cross-sectional 5-minute candle batches across all tickers."""
        ...


def is_market_data_provider(obj: object) -> bool:
    """Check if an object complies with the MarketDataProvider protocol."""
    return isinstance(obj, MarketDataProvider)

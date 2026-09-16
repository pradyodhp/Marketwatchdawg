"""Protocol interfaces for MarketWatch AI."""

from marketwatch.protocols.provider import MarketDataProvider, is_market_data_provider

__all__ = [
    "MarketDataProvider",
    "is_market_data_provider",
]

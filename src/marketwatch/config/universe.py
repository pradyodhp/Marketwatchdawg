"""Declarative Universe configuration models and loaders."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EquityConfig(BaseModel):
    """Configuration for an individual equity constituent."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    base_symbol: str
    name: str
    sector: str
    industry: str
    benchmark_symbol: str
    lot_size: int = Field(default=1, ge=1)


class BenchmarkConfig(BaseModel):
    """Configuration for a benchmark index."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    name: str
    provider_symbol: str | None = None


class MarketHoursConfig(BaseModel):
    """Market trading hours and intraday slot configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    open: str = "09:15"
    close: str = "15:30"
    timezone: str = "Asia/Kolkata"
    slots_per_day: int = 75
    bar_interval_minutes: int = 5


class BenchmarksMap(BaseModel):
    """Broad-market and sector benchmark configuration mappings."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    broad: BenchmarkConfig
    sectors: dict[str, BenchmarkConfig] = Field(default_factory=dict)


class UniverseConfig(BaseModel):
    """Declarative specification of the surveillance trading universe."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    universe_id: str
    market: str = "NSE"
    market_hours: MarketHoursConfig
    benchmarks: BenchmarksMap
    equities: list[EquityConfig]

    @model_validator(mode="after")
    def validate_universe_integrity(self) -> UniverseConfig:
        """Enforce constituent uniqueness, size, and valid benchmark links."""
        # 1. Check unique symbols
        symbols = [e.symbol for e in self.equities]
        if len(symbols) != len(set(symbols)):
            duplicates = [s for s in symbols if symbols.count(s) > 1]
            raise ValueError(f"Duplicate equity symbols found in universe: {set(duplicates)}")

        # 2. Check unique base symbols
        base_symbols = [e.base_symbol for e in self.equities]
        if len(base_symbols) != len(set(base_symbols)):
            duplicates = [s for s in base_symbols if base_symbols.count(s) > 1]
            raise ValueError(f"Duplicate base symbols found in universe: {set(duplicates)}")

        # 3. Check slots per day invariant (NSE 09:15-15:30 is exactly 75 5m bars)
        if self.market_hours.slots_per_day != 75:
            raise ValueError(
                f"slots_per_day must be 75 for NSE 5-minute bars, got {self.market_hours.slots_per_day}"
            )

        # 4. Check all benchmark references exist
        valid_benchmark_symbols = {self.benchmarks.broad.symbol} | {
            b.symbol for b in self.benchmarks.sectors.values()
        }
        for e in self.equities:
            if e.benchmark_symbol not in valid_benchmark_symbols:
                raise ValueError(
                    f"Equity {e.symbol} references unknown benchmark '{e.benchmark_symbol}'. "
                    f"Must be one of {valid_benchmark_symbols}"
                )

        return self

    def get_equity(self, symbol: str) -> EquityConfig:
        """Lookup an equity by canonical symbol."""
        for e in self.equities:
            if e.symbol == symbol:
                return e
        raise KeyError(f"Symbol '{symbol}' not found in universe '{self.universe_id}'")

    @property
    def equity_count(self) -> int:
        """Number of equity constituents in this universe."""
        return len(self.equities)

    @property
    def benchmark(self) -> str:
        """Broad market benchmark symbol (e.g. '^NSEI')."""
        return self.benchmarks.broad.symbol

    def get_symbols(self) -> list[str]:
        """Return sorted list of all equity symbols in the universe."""
        return sorted([e.symbol for e in self.equities])

    def get_sector_benchmark(self, sector: str) -> str:
        """Return benchmark symbol for sector, falling back to broad market."""
        if sector in self.benchmarks.sectors:
            return self.benchmarks.sectors[sector].symbol
        return self.benchmarks.broad.symbol


def load_universe_config(path: str | Path | None = None) -> UniverseConfig:
    """Load and validate universe configuration from JSON file."""
    if path is None:
        path = Path("configs/universe_nifty100.json")
    else:
        path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(f"Universe configuration file not found at: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return UniverseConfig.model_validate(data)

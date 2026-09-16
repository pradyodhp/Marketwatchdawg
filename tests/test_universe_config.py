"""Unit tests for NIFTY 100 universe configuration and settings loader."""

import pytest
from pydantic import ValidationError
from marketwatch.config.settings import load_settings
from marketwatch.config.universe import (
    UniverseConfig,
    load_universe_config,
)


class TestUniverseConfiguration:
    """Verification of configs/universe_nifty100.json and UniverseConfig loader."""

    def test_universe_file_integrity(self):
        universe = load_universe_config("configs/universe_nifty100.json")
        assert universe.universe_id == "nifty100"
        assert universe.market == "NSE"

        # Invariant 1: Exactly 100 equities
        assert len(universe.equities) == 100, f"Expected 100 constituents, got {len(universe.equities)}"

        # Invariant 2: All symbols end with .NS and are unique
        symbols = [e.symbol for e in universe.equities]
        assert len(symbols) == len(set(symbols)), "Duplicate symbols in universe"
        for s in symbols:
            assert s.endswith(".NS"), f"Symbol '{s}' does not end with '.NS'"

        # Invariant 3: Base symbols are unique
        base_symbols = [e.base_symbol for e in universe.equities]
        assert len(base_symbols) == len(set(base_symbols)), "Duplicate base symbols in universe"

        # Invariant 4: Broad benchmark is ^NSEI
        assert universe.benchmarks.broad.symbol == "^NSEI"

        # Invariant 5: All sector benchmarks exist and are referenced validly
        assert len(universe.benchmarks.sectors) >= 9
        for e in universe.equities:
            valid_targets = {universe.benchmarks.broad.symbol} | {
                b.symbol for b in universe.benchmarks.sectors.values()
            }
            assert e.benchmark_symbol in valid_targets

    def test_lookup_methods(self):
        universe = load_universe_config("configs/universe_nifty100.json")
        reliance = universe.get_equity("RELIANCE.NS")
        assert reliance.base_symbol == "RELIANCE"
        assert reliance.sector == "ENERGY"

        # Non-existent symbol lookup
        with pytest.raises(KeyError):
            universe.get_equity("UNKNOWN.NS")

        # Sector benchmark lookup
        assert universe.get_sector_benchmark("BANK") == "^NSEBANK"
        # Fallback to broad market for unknown sector
        assert universe.get_sector_benchmark("UNLISTED_SECTOR") == "^NSEI"

    def test_invalid_universe_rejections(self):
        valid = load_universe_config("configs/universe_nifty100.json")
        data = valid.model_dump()

        # 1. Reject duplicate symbol
        data_dup = dict(data)
        data_dup["equities"] = list(data["equities"]) + [data["equities"][0]]
        with pytest.raises(ValidationError, match="Duplicate equity symbols"):
            UniverseConfig.model_validate(data_dup)

        # 2. Reject invalid benchmark reference
        data_bad_bench = dict(data)
        bad_equity = dict(data["equities"][0], benchmark_symbol="INVALID_BENCHMARK")
        data_bad_bench["equities"] = [bad_equity] + data["equities"][1:]
        with pytest.raises(ValidationError, match="references unknown benchmark"):
            UniverseConfig.model_validate(data_bad_bench)


class TestSettingsLoader:
    """Verification of configs/settings.yaml and Settings loader."""

    def test_settings_load_yaml(self):
        settings = load_settings("configs/settings.yaml")
        assert settings.data_dir == "data"
        assert settings.curated_dir == "data/curated"
        assert settings.market.slots_per_day == 75
        assert settings.market.timezone == "Asia/Kolkata"
        assert settings.risk_scoring.thresholds.critical == 85.0
        assert settings.risk_scoring.weights.stat_weight == 0.40
        assert settings.cooldown.window_bars == 6

    def test_settings_env_override(self, monkeypatch):
        monkeypatch.setenv("MARKETWATCH_LOGGING__LEVEL", "DEBUG")
        monkeypatch.setenv("MARKETWATCH_RISK_SCORING__THRESHOLDS__CRITICAL", "90.0")

        settings = load_settings("configs/settings.yaml")
        assert settings.logging.level == "DEBUG"
        assert settings.risk_scoring.thresholds.critical == 90.0

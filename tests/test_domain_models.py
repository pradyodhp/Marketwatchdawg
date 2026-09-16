"""Unit tests for Pydantic v2 domain models and protocols."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from marketwatch.models.alerts import DEFAULT_DISCLAIMER, Alert, AlertSeverity
from marketwatch.models.candle import Candle, CandleBatch, compute_slot_index
from marketwatch.models.features import FeatureSet
from marketwatch.models.metadata import DataQualityMetadata
from marketwatch.models.signals import AnomalySeverity, AnomalySignal
from marketwatch.protocols.provider import MarketDataProvider, is_market_data_provider

IST = ZoneInfo("Asia/Kolkata")


class TestCandleModel:
    """Tests for Candle model validation and slot calculation."""

    def test_valid_candle_creation(self, valid_candle_dict):
        candle = Candle.model_validate(valid_candle_dict)
        assert candle.symbol == "RELIANCE.NS"
        assert candle.open == 2500.0
        assert candle.high == 2515.0
        assert candle.low == 2495.0
        assert candle.close == 2510.0
        assert candle.volume == 25000.0
        assert candle.slot_index == 0
        assert candle.trading_date.year == 2026

    def test_slot_index_calculations(self):
        # 09:15:00 -> Slot 0
        dt_open = datetime(2026, 9, 15, 9, 15, tzinfo=IST)
        assert compute_slot_index(dt_open) == 0

        # 09:20:00 -> Slot 1
        dt_second = datetime(2026, 9, 15, 9, 20, tzinfo=IST)
        assert compute_slot_index(dt_second) == 1

        # 12:00:00 -> Slot 33 ((12*60 - 9*60 - 15) // 5 = 165 // 5 = 33)
        dt_mid = datetime(2026, 9, 15, 12, 0, tzinfo=IST)
        assert compute_slot_index(dt_mid) == 33

        # 15:25:00 -> Slot 74 ((15*60 + 25 - 555) // 5 = 370 // 5 = 74)
        dt_last = datetime(2026, 9, 15, 15, 25, tzinfo=IST)
        assert compute_slot_index(dt_last) == 74

    def test_out_of_market_hours_raises(self):
        # 09:10 (pre-market)
        dt_pre = datetime(2026, 9, 15, 9, 10, tzinfo=IST)
        with pytest.raises(ValueError, match="outside NSE trading hours"):
            compute_slot_index(dt_pre)

        # 15:30 (market closed)
        dt_post = datetime(2026, 9, 15, 15, 30, tzinfo=IST)
        with pytest.raises(ValueError, match="outside NSE trading hours"):
            compute_slot_index(dt_post)

    def test_candle_immutability(self, sample_candle):
        with pytest.raises(ValidationError):
            sample_candle.close = 2600.0  # type: ignore

    def test_candle_extra_fields_forbidden(self, valid_candle_dict):
        bad_dict = dict(valid_candle_dict, arbitrary_field=123)
        with pytest.raises(ValidationError, match="extra_forbidden"):
            Candle.model_validate(bad_dict)

    def test_candle_ohlc_invariants(self, valid_candle_dict):
        # High < Low
        with pytest.raises(ValidationError, match="cannot be less than low"):
            Candle.model_validate(dict(valid_candle_dict, high=2400.0, low=2500.0))

        # High < Open
        with pytest.raises(ValidationError, match="High .* must be >= max"):
            Candle.model_validate(dict(valid_candle_dict, open=2520.0, high=2515.0))

        # Low > Close
        with pytest.raises(ValidationError, match="Low .* must be <= min"):
            Candle.model_validate(dict(valid_candle_dict, low=2515.0, close=2510.0))

        # Negative Volume
        with pytest.raises(ValidationError, match="volume cannot be negative"):
            Candle.model_validate(dict(valid_candle_dict, volume=-1.0))

        # Non-positive price
        with pytest.raises(ValidationError, match="prices must be strictly positive"):
            Candle.model_validate(dict(valid_candle_dict, open=0.0))


class TestCandleBatch:
    """Tests for cross-sectional CandleBatch sparse map."""

    def test_batch_sparse_dict(self, sample_candle, sample_ist_datetime):
        batch = CandleBatch(
            timestamp=sample_ist_datetime,
            slot_index=0,
            candles={"RELIANCE.NS": sample_candle},
        )
        assert len(batch) == 1
        assert "RELIANCE.NS" in batch
        assert "TCS.NS" not in batch
        assert batch.active_symbols == ["RELIANCE.NS"]
        assert batch["RELIANCE.NS"].open == sample_candle.open

    def test_batch_immutability(self, sample_candle_batch):
        with pytest.raises(ValidationError):
            sample_candle_batch.slot_index = 5  # type: ignore


class TestFeatureSet:
    """Tests for scale-invariant FeatureSet."""

    def test_feature_set_creation(self, sample_ist_datetime):
        features = FeatureSet(
            symbol="RELIANCE.NS",
            timestamp=sample_ist_datetime,
            slot_index=0,
            log_return=0.0045,
            volume_ratio=2.1,
            parkinson_volatility=0.012,
            market_excess_return=0.002,
            sector_excess_return=0.001,
        )
        assert features.volume_ratio == 2.1
        data = features.model_dump(mode="json")
        assert data["symbol"] == "RELIANCE.NS"
        assert "timestamp" in data

    def test_nan_features_rejected(self, sample_ist_datetime):
        with pytest.raises(ValidationError, match="must be finite"):
            FeatureSet(
                symbol="RELIANCE.NS",
                timestamp=sample_ist_datetime,
                slot_index=0,
                log_return=float("nan"),
                volume_ratio=1.0,
                parkinson_volatility=0.01,
                market_excess_return=0.0,
                sector_excess_return=0.0,
            )


class TestSignalsAndAlerts:
    """Tests for AnomalySignal and Alert models."""

    def test_anomaly_signal(self, sample_ist_datetime):
        signal = AnomalySignal(
            detector_name="zscore_volume",
            symbol="RELIANCE.NS",
            timestamp=sample_ist_datetime,
            slot_index=0,
            feature_name="volume_ratio",
            value=8.2,
            baseline_mean=1.0,
            baseline_std=1.2,
            z_score=6.0,
            severity=AnomalySeverity.CRITICAL,
        )
        assert signal.severity == AnomalySeverity.CRITICAL
        assert signal.z_score == 6.0

    def test_alert_creation_and_disclaimer(self, sample_ist_datetime):
        alert = Alert(
            alert_id="ALT-20260915-001",
            symbol="RELIANCE.NS",
            timestamp=sample_ist_datetime,
            slot_index=0,
            risk_score=88.5,
            severity=AlertSeverity.CRITICAL,
            explanation="Volume is 8.2x baseline, price shock 3.1σ.",
        )
        assert alert.risk_score == 88.5
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.disclaimer == DEFAULT_DISCLAIMER
        assert alert.is_simulated is False

    def test_alert_risk_score_bounds(self, sample_ist_datetime):
        with pytest.raises(ValidationError):
            Alert(
                alert_id="ALT-002",
                symbol="RELIANCE.NS",
                timestamp=sample_ist_datetime,
                slot_index=0,
                risk_score=105.0,  # Invalid: >100
                severity=AlertSeverity.CRITICAL,
                explanation="Test",
            )


class TestDataQualityMetadata:
    """Tests for DataQualityMetadata."""

    def test_metadata_creation(self, sample_ist_datetime, sample_close_datetime):
        meta = DataQualityMetadata(
            universe_id="nifty100",
            loaded_symbols_count=100,
            total_symbols_count=100,
            coverage_percentage=100.0,
            start_timestamp=sample_ist_datetime,
            end_timestamp=sample_close_datetime,
            total_bars_per_symbol=4500,
            is_offline_confirmed=True,
        )
        assert meta.source_type == "offline_parquet"
        assert meta.coverage_percentage == 100.0


class TestMarketDataProviderProtocol:
    """Tests for MarketDataProvider protocol contract."""

    def test_protocol_conformance(self):
        class MockProvider:
            def get_symbols(self) -> list[str]:
                return ["RELIANCE.NS"]

            def get_date_range(self) -> tuple[datetime, datetime]:
                now = datetime.now(tz=IST)
                return (now, now)

            def get_quality_metadata(self) -> DataQualityMetadata:
                now = datetime.now(tz=IST)
                return DataQualityMetadata(
                    universe_id="mock",
                    loaded_symbols_count=1,
                    total_symbols_count=1,
                    coverage_percentage=100.0,
                    start_timestamp=now,
                    end_timestamp=now,
                    total_bars_per_symbol=1,
                )

            def get_candles(self, symbol: str):
                yield from ()

            def stream_batches(self):
                yield from ()

        provider = MockProvider()
        assert isinstance(provider, MarketDataProvider)
        assert is_market_data_provider(provider) is True

    def test_non_conforming_object(self):
        class IncompleteProvider:
            def get_symbols(self):
                return []

        assert is_market_data_provider(IncompleteProvider()) is False

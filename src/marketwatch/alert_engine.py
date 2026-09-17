"""Deterministic alert creation and lifecycle management."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator

from marketwatch.explainability import SurveillanceExplanation
from marketwatch.models.alerts import AlertSeverity
from marketwatch.risk import RiskAssessment

IST = ZoneInfo("Asia/Kolkata")


class AlertState(str, Enum):
    """Allowed states in the analyst alert lifecycle."""

    NEW = "NEW"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class AlertEvent(BaseModel):
    """Immutable audit record for one lifecycle transition."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    timestamp: datetime
    from_state: AlertState | None = None
    to_state: AlertState

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=IST)
        return value.astimezone(IST)


class SurveillanceAlert(BaseModel):
    """Auditable alert carrying the original Phase 7-8 evidence."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    alert_id: str
    symbol: str
    timestamp: datetime
    slot_index: int = Field(ge=0, le=74)
    risk_score: float = Field(ge=0.0, le=100.0)
    severity: AlertSeverity
    state: AlertState = AlertState.NEW
    assessment: RiskAssessment
    explanation: SurveillanceExplanation | None = None
    detector_metadata: tuple[dict[str, Any], ...] = ()
    data_quality_reason: str | None = None
    is_simulated: bool = False
    history: tuple[AlertEvent, ...] = ()

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=IST)
        return value.astimezone(IST)


_TRANSITIONS = {
    AlertState.NEW: AlertState.ACKNOWLEDGED,
    AlertState.ACKNOWLEDGED: AlertState.RESOLVED,
}


def _alert_id(assessment: RiskAssessment) -> str:
    payload = {
        "symbol": assessment.symbol,
        "timestamp": assessment.timestamp.isoformat(),
        "slot_index": assessment.slot_index,
        "risk_score": assessment.risk_score,
        "severity": assessment.severity.value,
        "contributions": [item.model_dump(mode="json") for item in assessment.contributions],
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:24]
    return f"alert-{digest}"


class AlertEngine:
    """Create, deduplicate, and transition alerts without external persistence."""

    def __init__(self, *, cooldown_minutes: int = 5) -> None:
        if cooldown_minutes < 0:
            raise ValueError("cooldown_minutes must be non-negative")
        self.cooldown = timedelta(minutes=cooldown_minutes)
        self._alerts: dict[str, SurveillanceAlert] = {}

    def process(
        self,
        assessment: RiskAssessment,
        *,
        explanation: SurveillanceExplanation | None = None,
    ) -> SurveillanceAlert:
        """Create an alert or return the existing alert for the same event."""
        if not assessment.valid or not assessment.contributions:
            raise ValueError("a valid RiskAssessment with detector evidence is required")
        if explanation is not None and (
            explanation.symbol != assessment.symbol
            or explanation.timestamp != assessment.timestamp
        ):
            raise ValueError("explanation must match the assessment symbol and timestamp")
        alert_id = _alert_id(assessment)
        existing = self._alerts.get(alert_id)
        if existing is not None:
            return existing
        if self.cooldown:
            recent = [
                alert
                for alert in self._alerts.values()
                if alert.symbol == assessment.symbol
                and alert.state is not AlertState.RESOLVED
                and timedelta(0) <= assessment.timestamp - alert.timestamp <= self.cooldown
            ]
            if recent:
                return min(recent, key=lambda alert: (alert.timestamp, alert.alert_id))
        alert = SurveillanceAlert(
            alert_id=alert_id,
            symbol=assessment.symbol,
            timestamp=assessment.timestamp,
            slot_index=assessment.slot_index,
            risk_score=assessment.risk_score,
            severity=AlertSeverity(assessment.severity.value),
            assessment=assessment,
            explanation=explanation,
            detector_metadata=tuple(
                contribution.metadata for contribution in assessment.contributions
            ),
            data_quality_reason=assessment.reason,
            history=(
                AlertEvent(
                    timestamp=assessment.timestamp,
                    to_state=AlertState.NEW,
                ),
            ),
        )
        self._alerts[alert_id] = alert
        return alert

    def transition(
        self,
        alert_id: str,
        target: AlertState,
        *,
        timestamp: datetime | None = None,
    ) -> SurveillanceAlert:
        """Apply one valid lifecycle transition using a deterministic timestamp."""
        alert = self._alerts.get(alert_id)
        if alert is None:
            raise KeyError(f"unknown alert: {alert_id}")
        expected = _TRANSITIONS.get(alert.state)
        if expected is not target:
            raise ValueError(f"invalid alert transition: {alert.state.value} -> {target.value}")
        event_time = timestamp or alert.timestamp
        updated = alert.model_copy(
            update={
                "state": target,
                "history": alert.history
                + (
                    AlertEvent(
                        timestamp=event_time,
                        from_state=alert.state,
                        to_state=target,
                    ),
                ),
            }
        )
        self._alerts[alert_id] = updated
        return updated

    def get(self, alert_id: str) -> SurveillanceAlert | None:
        """Return an alert by deterministic identity."""
        return self._alerts.get(alert_id)

    def all(self) -> tuple[SurveillanceAlert, ...]:
        """Return alerts in stable chronological and identity order."""
        return tuple(sorted(self._alerts.values(), key=lambda item: (item.timestamp, item.alert_id)))

    def active(self) -> tuple[SurveillanceAlert, ...]:
        """Return unresolved alerts in stable order."""
        return tuple(alert for alert in self.all() if alert.state is not AlertState.RESOLVED)


__all__ = ["AlertEngine", "AlertEvent", "AlertState", "SurveillanceAlert"]

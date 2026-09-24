"""Outbound alert delivery for high-risk surveillance alerts.

The dashboard shows alerts in-app; this module delivers them to the analyst
when they are not watching - e.g. a webhook into Slack, Teams, Telegram,
or any automation tool that accepts an HTTPS POST of JSON.

Delivery is best-effort and never blocks the surveillance pipeline: failures
are logged, not raised.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from marketwatch.models.alerts import AlertSeverity

logger = logging.getLogger(__name__)

_SEVERITY_ORDER = {
    AlertSeverity.LOW.value: 0,
    AlertSeverity.MEDIUM.value: 1,
    AlertSeverity.HIGH.value: 2,
    AlertSeverity.CRITICAL.value: 3,
}


class WebhookNotifier:
    """POST a JSON summary of each newly created high-severity alert to a webhook.

    Args:
        webhook_url: HTTPS endpoint that accepts a JSON POST.
        min_severity: Minimum alert severity to deliver ("HIGH" or "CRITICAL"
            are the sensible choices for sudden-move alerting).
        poster: Injectable callable ``poster(url, payload, timeout)`` used for
            delivery. Defaults to an httpx POST. Tests inject a stub.
        timeout_seconds: Delivery timeout.
    """

    def __init__(
        self,
        webhook_url: str,
        *,
        min_severity: str = "HIGH",
        poster: Callable[[str, dict[str, Any], float], None] | None = None,
        timeout_seconds: float = 5.0,
    ) -> None:
        if not webhook_url:
            raise ValueError("webhook_url must be non-empty")
        min_severity = min_severity.upper()
        if min_severity not in _SEVERITY_ORDER:
            raise ValueError(f"unknown min_severity: {min_severity}")
        self.webhook_url = webhook_url
        self.min_severity = min_severity
        self.timeout_seconds = float(timeout_seconds)
        self._poster = poster or self._httpx_post

    def should_notify(self, severity: str) -> bool:
        """Return True when the severity meets the configured minimum."""
        return _SEVERITY_ORDER.get(severity.upper(), -1) >= _SEVERITY_ORDER[self.min_severity]

    def notify(self, alert: Any) -> bool:
        """Deliver one alert. Returns True on successful delivery.

        ``alert`` is a SurveillanceAlert (duck-typed to avoid a hard import cycle).
        """
        severity = alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity)
        if not self.should_notify(severity):
            return False
        explanation_summary = None
        if getattr(alert, "explanation", None) is not None:
            explanation_summary = getattr(alert.explanation, "summary", None)
        payload = {
            "text": (
                f"MarketWatch AI alert: {alert.symbol} risk {alert.risk_score:.1f}/100 "
                f"({severity}) at {alert.timestamp.isoformat()}"
            ),
            "alert_id": alert.alert_id,
            "symbol": alert.symbol,
            "timestamp": alert.timestamp.isoformat(),
            "risk_score": alert.risk_score,
            "severity": severity,
            "explanation": explanation_summary,
            "is_simulated": bool(getattr(alert, "is_simulated", False)),
        }
        try:
            self._poster(self.webhook_url, payload, self.timeout_seconds)
        except Exception as exc:  # noqa: BLE001 - delivery must never break the pipeline
            logger.warning("alert webhook delivery failed for %s: %s", alert.alert_id, exc)
            return False
        logger.info("alert %s delivered to webhook (%s)", alert.alert_id, severity)
        return True

    @staticmethod
    def _httpx_post(url: str, payload: dict[str, Any], timeout: float) -> None:
        import httpx

        response = httpx.post(url, json=payload, timeout=timeout)
        response.raise_for_status()


__all__ = ["WebhookNotifier"]

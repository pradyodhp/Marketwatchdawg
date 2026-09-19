from __future__ import annotations

import httpx

from frontend.api_client import APIClient
from frontend.state import PAGES


def test_api_client_uses_configured_base_url(monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return httpx.Response(200, request=httpx.Request("GET", url), json={"status": "ok"})

    monkeypatch.setattr(httpx, "get", fake_get)
    assert APIClient("http://example.test/").health() == {"status": "ok"}
    assert calls[0][0] == "http://example.test/health"


def test_api_client_sends_replay_injection(monkeypatch):
    payload = {"action": "step", "injection": {"enabled": True}}
    seen = {}

    def fake_post(url, **kwargs):
        seen.update(url=url, **kwargs)
        return httpx.Response(200, request=httpx.Request("POST", url), json={"is_simulated": True})

    monkeypatch.setattr(httpx, "post", fake_post)
    assert APIClient("http://example.test").replay(injection=payload["injection"])["is_simulated"]
    assert seen["json"] == payload


def test_alert_filters_omit_empty_values(monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append(kwargs.get("params"))
        return httpx.Response(
            200,
            request=httpx.Request("GET", url),
            json=[],
        )

    monkeypatch.setattr(httpx, "get", fake_get)
    client = APIClient("http://example.test")
    client.alerts()
    client.alerts(symbol="RELIANCE")
    client.alerts(state="CRITICAL")
    client.alerts(symbol="RELIANCE", state="NEW")
    assert calls == [
        None,
        {"symbol": "RELIANCE"},
        {"state": "CRITICAL"},
        {"symbol": "RELIANCE", "state": "NEW"},
    ]


def test_navigation_pages_are_explicit_and_stable():
    assert PAGES == (
        "Surveillance Overview",
        "Security Investigation",
        "Alert Investigation",
        "Replay / Simulation",
    )

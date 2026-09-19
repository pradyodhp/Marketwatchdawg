"""Small HTTP client for the Phase 11 MarketWatch API."""

from __future__ import annotations

import os
from typing import Any

import httpx


class APIClient:
    """Fetch backend-owned surveillance data without local analytical logic."""

    def __init__(self, base_url: str | None = None, timeout: float = 5.0) -> None:
        self.base_url = (base_url or os.getenv("MARKETWATCH_API_URL", "http://127.0.0.1:8000")).rstrip("/")
        self.timeout = timeout

    def _get(self, path: str, **params: Any) -> Any:
        response = httpx.get(f"{self.base_url}{path}", params=params or None, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def health(self) -> dict[str, Any]:
        return self._get("/health")

    def quality(self) -> dict[str, Any]:
        return self._get("/quality")

    def stocks(self) -> dict[str, Any]:
        return self._get("/stocks")

    def alerts(self, symbol: str | None = None, state: str | None = None) -> list[dict[str, Any]]:
        params = {
            key: value
            for key, value in {"symbol": symbol, "state": state}.items()
            if value is not None and value.strip()
        }
        return self._get("/alerts", **params)

    def replay(self, action: str = "step", injection: dict[str, Any] | None = None) -> dict[str, Any]:
        response = httpx.post(
            f"{self.base_url}/replay",
            json={"action": action, "injection": injection},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

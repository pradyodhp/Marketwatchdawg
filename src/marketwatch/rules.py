"""User-defined trigger rules and metric-based guidance events.

Rules are cheap, explainable thresholds (price, % change, volume spike,
fused risk, Z-score, buy/sell pressure) evaluated on every new bar -
including bars arriving from the live poller.  When a rule fires it produces
a GuidanceEvent: a plain-English, metric-grounded suggestion.  Guidance is
decision support for a surveillance analyst; it is not financial advice and
no trade is ever placed.
"""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

import yaml

IST = ZoneInfo("Asia/Kolkata")

METRICS = (
    "price_above",
    "price_below",
    "pct_change_up",
    "pct_change_down",
    "volume_spike",
    "risk_above",
    "zscore_above",
    "pressure_above",
    "pressure_below",
)

DISCLAIMER = (
    "Statistical signal, not financial advice. MarketWatch AI places no trades; "
    "always confirm against your own research and risk plan."
)


@dataclass
class TriggerRule:
    """One user-defined trigger: `symbol` (or "*") `metric` crosses `threshold`."""

    id: str
    symbol: str
    metric: str
    threshold: float
    note: str = ""
    enabled: bool = True
    created_at: str = ""

    @staticmethod
    def create(symbol: str, metric: str, threshold: float, note: str = "") -> "TriggerRule":
        if metric not in METRICS:
            raise ValueError(f"unknown metric {metric!r}; expected one of {', '.join(METRICS)}")
        return TriggerRule(
            id=f"rule-{uuid.uuid4().hex[:12]}",
            symbol=symbol.strip().upper() or "*",
            metric=metric,
            threshold=float(threshold),
            note=note.strip(),
            created_at=datetime.now(IST).isoformat(),
        )


@dataclass
class GuidanceEvent:
    """A fired rule with the metric evidence behind it."""

    id: str
    rule_id: str
    symbol: str
    timestamp: str
    metric: str
    threshold: float
    observed: float
    close: float
    pct_change: float
    volume_ratio: float | None
    risk: float | None
    zscore: float | None
    pressure: float | None
    title: str
    suggestion: str
    note: str = ""
    disclaimer: str = DISCLAIMER


def _fmt_pct(value: float) -> str:
    return f"{value:+.2f}%"


def evaluate_rule(
    rule: TriggerRule,
    symbol: str,
    *,
    timestamp: datetime,
    close: float,
    prev_close: float | None,
    volume: float | None,
    avg_volume: float | None,
    risk: float | None = None,
    zscore: float | None = None,
    pressure: float | None = None,
) -> GuidanceEvent | None:
    """Evaluate one rule against one bar; returns a GuidanceEvent when it fires."""
    if not rule.enabled:
        return None
    if rule.symbol not in ("*", symbol, symbol.upper(), symbol.split(".")[0]):
        return None

    pct = ((close - prev_close) / prev_close * 100.0) if prev_close else 0.0
    vol_ratio = (volume / avg_volume) if (volume is not None and avg_volume) else None

    metric = rule.metric
    thr = rule.threshold
    observed: float | None = None
    if metric == "price_above" and close > thr:
        observed = close
    elif metric == "price_below" and close < thr:
        observed = close
    elif metric == "pct_change_up" and pct >= thr:
        observed = pct
    elif metric == "pct_change_down" and pct <= -thr:
        observed = pct
    elif metric == "volume_spike" and vol_ratio is not None and vol_ratio >= thr:
        observed = vol_ratio
    elif metric == "risk_above" and risk is not None and risk >= thr:
        observed = risk
    elif metric == "zscore_above" and zscore is not None and abs(zscore) >= thr:
        observed = zscore
    elif metric == "pressure_above" and pressure is not None and pressure >= thr:
        observed = pressure
    elif metric == "pressure_below" and pressure is not None and pressure <= -thr:
        observed = pressure
    if observed is None:
        return None

    base = symbol.split(".")[0]
    titles = {
        "price_above": lambda: f"{base} crossed above Rs {thr:,.2f}",
        "price_below": lambda: f"{base} fell below Rs {thr:,.2f}",
        "pct_change_up": lambda: f"{base} up {_fmt_pct(pct)} in one bar",
        "pct_change_down": lambda: f"{base} down {_fmt_pct(pct)} in one bar",
        "volume_spike": lambda: f"{base} volume {vol_ratio:.1f}x its recent average",
        "risk_above": lambda: f"{base} fused risk hit {observed:.0f}/100",
        "zscore_above": lambda: f"{base} moved {abs(observed):.1f} sigma from its baseline",
        "pressure_above": lambda: f"{base} buy-side pressure at {observed:+.2f}",
        "pressure_below": lambda: f"{base} sell-side pressure at {observed:+.2f}",
    }
    parts = [f"Last Rs {close:,.2f} ({_fmt_pct(pct)} this bar)"]
    if vol_ratio is not None:
        parts.append(f"volume {vol_ratio:.1f}x average")
    if risk is not None:
        parts.append(f"fused risk {risk:.0f}/100")
    if zscore is not None and abs(zscore) >= 1.0:
        parts.append(f"Z-score {zscore:+.1f} sigma")
    if pressure is not None and abs(pressure) >= 0.3:
        side = "buy" if pressure > 0 else "sell"
        parts.append(f"{side}-side pressure {pressure:+.2f}")
    evidence = "; ".join(parts)
    suggestion = (
        f"{evidence}. This rule fired because {metric.replace('_', ' ')} crossed "
        f"{thr:g}. Worth a look against your plan for {base} - check whether the move "
        f"holds over the next bars and how the detectors evolve."
    )
    return GuidanceEvent(
        id=f"guide-{uuid.uuid4().hex[:12]}",
        rule_id=rule.id,
        symbol=symbol,
        timestamp=timestamp.isoformat(),
        metric=metric,
        threshold=thr,
        observed=float(observed),
        close=float(close),
        pct_change=float(pct),
        volume_ratio=float(vol_ratio) if vol_ratio is not None else None,
        risk=float(risk) if risk is not None else None,
        zscore=float(zscore) if zscore is not None else None,
        pressure=float(pressure) if pressure is not None else None,
        title=titles[metric](),
        suggestion=suggestion,
        note=rule.note,
    )


def load_rules(path: Path) -> list[TriggerRule]:
    if not path.is_file():
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    return [TriggerRule(**item) for item in raw]


def save_rules(path: Path, rules: Iterable[TriggerRule]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [asdict(rule) for rule in rules]
    path.write_text(
        "# MarketWatch AI trigger rules (managed; edit here or via the API/UI)\n"
        + yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )


def append_guidance(path: Path, events: Iterable[GuidanceEvent]) -> None:
    events = list(events)
    if not events:
        return
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(asdict(event)) + "\n")


def load_guidance(path: Path, *, limit: int = 200) -> list[GuidanceEvent]:
    import json

    if not path.is_file():
        return []
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [GuidanceEvent(**row) for row in rows[-limit:]][::-1]

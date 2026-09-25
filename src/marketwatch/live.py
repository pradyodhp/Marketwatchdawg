"""Live polling: free Yahoo Finance data -> ingest -> detect -> rules -> guidance.

Free data reality: Yahoo (via yfinance) is the only no-key source that covers
NSE 5-minute bars reliably.  It is officially delayed (usually up to ~15
minutes; observed ~1-2 minutes in testing).  True real-time NSE feeds are
paid (NSE Data & Analytics, broker APIs such as Zerodha Kite / Upstox).  This
module is honest about that delay in its status payload.
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

import pandas as pd

from marketwatch.ingestion.parquet_store import read_symbol_parquet, write_symbol_parquet
from marketwatch.models.candle import Candle, CandleBatch
from marketwatch.rules import (
    GuidanceEvent,
    TriggerRule,
    append_guidance,
    evaluate_rule,
    load_guidance,
    load_rules,
    save_rules,
)

IST = ZoneInfo("Asia/Kolkata")
logger = logging.getLogger("marketwatch.live")

DATA_SOURCE = "Yahoo Finance via yfinance (free, no API key)"
DATA_DELAY_NOTE = (
    "Free Yahoo data is officially delayed - usually up to ~15 minutes for NSE "
    "(observed ~1-2 minutes in testing). True real-time NSE data is paid only."
)

try:
    import yfinance as yf

    _YF_AVAILABLE = True
except ImportError:  # pragma: no cover - environment dependent
    _YF_AVAILABLE = False


def _yahoo_symbol(symbol: str) -> str:
    if symbol.startswith("^") or "." in symbol:
        return symbol
    return f"{symbol}.NS"


def fetch_latest_bars(symbol: str) -> pd.DataFrame | None:
    """Fetch today's 5-minute bars for one symbol from Yahoo."""
    if not _YF_AVAILABLE:
        return None
    df = yf.Ticker(_yahoo_symbol(symbol)).history(period="1d", interval="5m", auto_adjust=True)
    if df is None or df.empty:
        return None
    df = df[[c for c in ("Open", "High", "Low", "Close", "Volume") if c in df.columns]].dropna()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df.index = df.index.tz_convert("Asia/Kolkata")
    return df


class LivePoller:
    """Polls Yahoo on an interval, appends new bars, streams them through the
    controller and evaluates the user's trigger rules on each new bar."""

    def __init__(
        self,
        runtime: Any,
        *,
        curated_dir: Path,
        rules_path: Path,
        guidance_path: Path,
        fetch: Callable[[str], pd.DataFrame | None] = fetch_latest_bars,
        interval_sec: int = 300,
    ) -> None:
        self.runtime = runtime
        self.curated_dir = Path(curated_dir)
        self.rules_path = Path(rules_path)
        self.guidance_path = Path(guidance_path)
        self.fetch = fetch
        self.interval_sec = int(interval_sec)
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._last_poll: str | None = None
        self._last_summary: dict[str, Any] = {}
        self._errors: list[str] = []

    # ── rules CRUD ──────────────────────────────────────────────────────────
    def rules(self) -> list[TriggerRule]:
        return load_rules(self.rules_path)

    def add_rule(self, symbol: str, metric: str, threshold: float, note: str = "") -> TriggerRule:
        rule = TriggerRule.create(symbol, metric, threshold, note)
        rules = self.rules()
        rules.append(rule)
        save_rules(self.rules_path, rules)
        return rule

    def delete_rule(self, rule_id: str) -> bool:
        rules = self.rules()
        kept = [r for r in rules if r.id != rule_id]
        if len(kept) == len(rules):
            return False
        save_rules(self.rules_path, kept)
        return True

    def guidance(self, limit: int = 200) -> list[GuidanceEvent]:
        return load_guidance(self.guidance_path, limit=limit)

    # ── polling ─────────────────────────────────────────────────────────────
    def poll_once(self, symbols: list[str] | None = None) -> dict[str, Any]:
        """One poll cycle: fetch -> append parquet -> controller -> rules."""
        runtime = self.runtime
        symbols = symbols or list(runtime.provider.get_symbols())
        rules = self.rules()
        new_batches: dict[datetime, dict[str, Candle]] = {}
        per_symbol: dict[str, Any] = {}
        guidance_events: list[GuidanceEvent] = []

        for symbol in symbols:
            df_new = self.fetch(symbol)
            if df_new is None or df_new.empty:
                per_symbol[symbol] = {"fetched": 0, "appended": 0}
                continue
            df_new = df_new.rename(columns=str.lower)
            existing = read_symbol_parquet(symbol, self.curated_dir)
            if existing is not None and not existing.empty:
                fresh = df_new[df_new.index > existing.index.max()]
                combined = pd.concat([existing, df_new]).groupby(level=0).last().sort_index()
            else:
                fresh = df_new
                combined = df_new
            appended = 0
            if not fresh.empty:
                write_symbol_parquet(symbol, combined, self.curated_dir)
                if hasattr(runtime.provider, "_loaded_dfs"):
                    runtime.provider._loaded_dfs.pop(symbol, None)  # drop cached df
                appended = len(fresh)
                prev_close = float(existing["close"].iloc[-1]) if existing is not None and not existing.empty else None
                hist = combined["volume"].tail(21)
                avg_volume = float(hist.iloc[:-1].mean()) if len(hist) > 1 else None
                for ts, row in fresh.iterrows():
                    candle = Candle(
                        symbol=symbol,
                        timestamp=ts.to_pydatetime(),
                        open=float(row["open"]), high=float(row["high"]),
                        low=float(row["low"]), close=float(row["close"]),
                        volume=float(row["volume"]),
                    )
                    new_batches.setdefault(candle.timestamp, {})[symbol] = candle
                    prev_close = float(row["close"])
            per_symbol[symbol] = {"fetched": len(df_new), "appended": appended}

        # Stream new bars chronologically through the real pipeline.
        alerts = 0
        assessments_by_key: dict[tuple[str, datetime], float] = {}
        signals_by_key: dict[tuple[str, datetime], list[Any]] = {}
        features_by_key: dict[tuple[str, datetime], Any] = {}
        for ts in sorted(new_batches):
            batch = CandleBatch(timestamp=ts, slot_index=0, candles=new_batches[ts])
            result = runtime.controller.process_batch(batch)
            alerts += len(result.alerts)
            for assessment in result.assessments:
                assessments_by_key[(assessment.symbol, assessment.timestamp)] = assessment.risk_score
            for signal in result.signals:
                signals_by_key.setdefault((signal.symbol, signal.timestamp), []).append(signal)
            features_by_key.update({(f.symbol, f.timestamp): f for f in result.features.values()})

        # Evaluate user rules on every new bar.
        for ts, candles in sorted(new_batches.items()):
            for symbol, candle in candles.items():
                existing = read_symbol_parquet(symbol, self.curated_dir)
                idx = existing.index.get_loc(candle.timestamp) if existing is not None and candle.timestamp in existing.index else None
                prev_close = float(existing["close"].iloc[idx - 1]) if existing is not None and idx else None
                hist = existing["volume"].iloc[max(0, (idx or 1) - 21):(idx or 1)] if existing is not None else []
                avg_volume = float(hist.iloc[:-1].mean()) if len(hist) > 1 else None
                feature = features_by_key.get((symbol, ts))
                risk = assessments_by_key.get((symbol, ts))
                zs = [s for s in signals_by_key.get((symbol, ts), []) if s.detector_name.startswith("ZScore")]
                for rule in rules:
                    event = evaluate_rule(
                        rule, symbol,
                        timestamp=ts,
                        close=candle.close,
                        prev_close=prev_close,
                        volume=candle.volume,
                        avg_volume=avg_volume,
                        risk=risk,
                        zscore=max((s.z_score for s in zs), key=abs, default=None),
                        pressure=feature.buy_sell_pressure if feature else None,
                    )
                    if event is not None:
                        guidance_events.append(event)
        append_guidance(self.guidance_path, guidance_events)

        summary = {
            "polled_at": datetime.now(IST).isoformat(),
            "symbols": per_symbol,
            "new_bars": sum(len(v) for v in new_batches.values()),
            "new_alerts": alerts,
            "guidance_fired": len(guidance_events),
        }
        with self._lock:
            self._last_poll = summary["polled_at"]
            self._last_summary = summary
        return summary

    # ── background loop ─────────────────────────────────────────────────────
    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.poll_once()
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception("live poll failed")
                with self._lock:
                    self._errors.append(str(exc))
                    self._errors = self._errors[-20:]
            self._stop.wait(self.interval_sec)

    def start(self, interval_sec: int | None = None) -> dict[str, Any]:
        if interval_sec:
            self.interval_sec = int(interval_sec)
        if self._thread and self._thread.is_alive():
            return self.status()
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="marketwatch-live")
        self._thread.start()
        return self.status()

    def stop(self) -> dict[str, Any]:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
        return self.status()

    def status(self) -> dict[str, Any]:
        running = bool(self._thread and self._thread.is_alive())
        with self._lock:
            return {
                "running": running,
                "interval_sec": self.interval_sec,
                "source": DATA_SOURCE,
                "delay_note": DATA_DELAY_NOTE,
                "available": _YF_AVAILABLE,
                "last_poll": self._last_poll,
                "last_summary": self._last_summary,
                "errors": list(self._errors),
            }

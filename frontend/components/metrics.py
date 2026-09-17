"""KPI and empty-state components."""

from __future__ import annotations

import streamlit as st


def render_metrics(symbol_count: int | None, alert_count: int | None, quality: dict | None) -> None:
    cols = st.columns(4)
    cols[0].metric("MONITORED SECURITIES", symbol_count if symbol_count is not None else "--")
    cols[1].metric("ACTIVE ALERTS", alert_count if alert_count is not None else "--")
    cols[2].metric("COVERAGE", f"{quality['coverage_percentage']:.1f}%" if quality else "--")
    cols[3].metric("SOURCE", quality["source_type"].upper() if quality else "--")


def empty_state(message: str) -> None:
    st.warning(message)

"""Streamlit session-state helpers."""

from __future__ import annotations

import streamlit as st

PAGES = (
    "Surveillance Overview",
    "Security Investigation",
    "Alert Investigation",
    "Replay / Simulation",
)


def initialize() -> None:
    st.session_state.setdefault("page", PAGES[0])
    st.session_state.setdefault("selected_symbol", None)
    st.session_state.setdefault("selected_alert", None)


def navigate(page: str, *, symbol: str | None = None, alert_id: str | None = None) -> None:
    st.session_state["page"] = page
    if symbol is not None:
        st.session_state["selected_symbol"] = symbol
    if alert_id is not None:
        st.session_state["selected_alert"] = alert_id

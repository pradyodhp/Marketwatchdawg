"""Surveillance overview screen."""

from __future__ import annotations

import streamlit as st

from frontend.components.alerts import render_alert_feed
from frontend.components.charts import render_score_chart
from frontend.components.metrics import empty_state, render_metrics
from frontend.state import navigate


def render(client, quality, stocks, alerts) -> None:
    render_metrics(
        stocks.get("count") if stocks else None,
        len(alerts) if alerts is not None else None,
        quality,
    )
    st.subheader("Monitored securities")
    symbols = stocks.get("symbols", []) if stocks else []
    if not symbols:
        empty_state("NO MONITORED SECURITIES")
    else:
        selected = st.selectbox("Security", symbols)
        if st.button("OPEN SECURITY INVESTIGATION"):
            navigate("Security Investigation", symbol=selected)
            st.rerun()
    st.subheader("Active alert feed")
    render_alert_feed(alerts or [])
    render_score_chart(alerts or [])

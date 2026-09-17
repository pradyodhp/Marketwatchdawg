"""Security investigation screen."""

from __future__ import annotations

import streamlit as st

from frontend.components.charts import render_price_chart
from frontend.components.metrics import empty_state


def render(client, symbol: str | None) -> None:
    if not symbol:
        empty_state("Select a security from the overview.")
        return
    st.header(f"Security Investigation: {symbol}")
    st.caption("All analytical values are backend-owned. No local detector is run.")
    render_price_chart()
    st.info("Detector, baseline, market-context, and sector-context series are unavailable in the current API contract.")

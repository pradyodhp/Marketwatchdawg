"""Surveillance overview screen."""

from __future__ import annotations

import httpx
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
    with st.expander("Add your own market data (CSV or Parquet)"):
        st.caption(
            "Upload 5-minute OHLCV bars for one symbol. The backend validates the rows, "
            "adds the symbol to the monitored universe, and replays it through the same "
            "detectors and risk scoring. Rows outside NSE hours (09:15-15:30 IST) are dropped."
        )
        upload_symbol = st.text_input("Symbol", placeholder="e.g. RELIANCE.NS")
        upload_file = st.file_uploader("OHLCV file", type=["csv", "parquet"])
        if st.button("UPLOAD DATA"):
            if not upload_symbol.strip() or upload_file is None:
                st.error("Enter a symbol and choose a file first.")
            else:
                try:
                    outcome = client.ingest(
                        upload_symbol.strip(),
                        upload_file.getvalue(),
                        is_parquet=upload_file.name.lower().endswith(".parquet"),
                    )
                except (httpx.HTTPError, OSError, ValueError) as exc:
                    st.error(f"Upload failed: {exc}")
                else:
                    st.success(
                        f"Loaded {outcome['rows_loaded']} rows for {outcome['symbol']} "
                        f"({outcome['rows_dropped']} dropped). Refresh to see it in the universe."
                    )

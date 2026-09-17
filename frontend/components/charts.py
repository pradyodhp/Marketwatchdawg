"""Plotly views using only backend-provided values."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st


def render_score_chart(alerts: list[dict]) -> None:
    if not alerts:
        st.info("NO ALERT EVIDENCE AVAILABLE")
        return
    figure = go.Figure(
        go.Bar(
            x=[item["symbol"] for item in alerts],
            y=[item["risk_score"] for item in alerts],
            marker_color=[
                {"LOW": "#64748b", "MEDIUM": "#eab308", "HIGH": "#f97316", "CRITICAL": "#ef4444"}.get(
                    item["severity"], "#64748b"
                )
                for item in alerts
            ],
        )
    )
    figure.update_layout(template="plotly_dark", height=300, title="Backend Risk Scores")
    st.plotly_chart(figure, use_container_width=True)


def render_price_chart() -> None:
    st.info("PRICE/OHLCV SERIES UNAVAILABLE: the current API does not expose historical candle data.")

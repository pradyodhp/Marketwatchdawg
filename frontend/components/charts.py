"""Plotly views using only backend-provided values."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots


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


def render_price_chart(series: dict | None) -> None:
    """Render a candlestick + volume chart from backend /candles data."""
    candles = (series or {}).get("candles") or []
    if not candles:
        st.info("NO CANDLE DATA AVAILABLE FOR THIS SECURITY")
        return
    timestamps = [item["timestamp"] for item in candles]
    figure = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.7, 0.3],
        vertical_spacing=0.03,
    )
    figure.add_trace(
        go.Candlestick(
            x=timestamps,
            open=[item["open"] for item in candles],
            high=[item["high"] for item in candles],
            low=[item["low"] for item in candles],
            close=[item["close"] for item in candles],
            name="OHLC",
        ),
        row=1,
        col=1,
    )
    figure.add_trace(
        go.Bar(x=timestamps, y=[item["volume"] for item in candles], name="Volume"),
        row=2,
        col=1,
    )
    figure.update_layout(
        template="plotly_dark",
        height=480,
        title="Price and volume",
        xaxis_rangeslider_visible=False,
        showlegend=False,
    )
    st.plotly_chart(figure, use_container_width=True)

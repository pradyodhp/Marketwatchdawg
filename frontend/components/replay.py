"""Replay and simulation controls."""

from __future__ import annotations

from datetime import datetime

import httpx
import streamlit as st

from frontend.api_client import APIClient


def render_replay_controls(client: APIClient, symbols: list[str]) -> None:
    st.subheader("Replay / Simulation")
    symbol = st.selectbox("Target symbol", symbols) if symbols else None
    timestamp = st.text_input("Target timestamp (ISO 8601)", placeholder="Backend replay timestamp")
    enabled = st.checkbox("Enable simulated volume surge", value=False)
    magnitude = st.number_input("Volume multiplier", min_value=0.01, value=8.0, step=0.5)
    if st.button("STEP REPLAY"):
        injection = None
        if enabled:
            try:
                datetime.fromisoformat(timestamp)
            except ValueError:
                st.error("Enter a valid ISO 8601 timestamp before enabling injection.")
                return
            injection = {
                "target_symbol": symbol,
                "target_timestamp": timestamp,
                "injection_type": "volume_surge",
                "magnitude": magnitude,
                "enabled": True,
            }
        try:
            result = client.replay(injection=injection)
        except (httpx.HTTPError, OSError, ValueError) as exc:
            st.error(f"Replay unavailable: {exc}")
            return
        if result.get("is_simulated"):
            st.warning("SIMULATED / INJECTED event processed through the backend pipeline.")
        st.json(result)

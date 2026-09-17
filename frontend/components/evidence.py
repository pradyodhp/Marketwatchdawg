"""Backend evidence and explanation rendering."""

from __future__ import annotations

import streamlit as st


def render_explanation(alert: dict) -> None:
    explanation = alert.get("explanation")
    if not explanation:
        st.warning("EXPLANATION UNAVAILABLE")
        return
    st.subheader("Why was this alert generated?")
    st.write(explanation.get("summary", "Summary unavailable"))
    st.caption(explanation.get("disclaimer", "Disclaimer unavailable"))
    for factor in explanation.get("factors", []):
        st.markdown(f"**{factor.get('label', 'Evidence')}** — {factor.get('detail', 'Detail unavailable')}")

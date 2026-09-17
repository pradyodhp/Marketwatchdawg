"""Dashboard header and connection status."""

from __future__ import annotations

import streamlit as st


def render_header(connected: bool, *, quality_available: bool) -> None:
    st.title("MARKETWATCH AI")
    st.caption("Explainable real-time market surveillance | analyst decision support")
    status = "ONLINE" if connected else "DISCONNECTED"
    data = "DATA AVAILABLE" if quality_available else "DATA UNAVAILABLE"
    st.info(f"Backend: {status}  |  Curated data: {data}")

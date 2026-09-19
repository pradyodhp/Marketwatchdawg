"""MarketWatch AI Streamlit analyst workstation."""

from __future__ import annotations

from pathlib import Path

import httpx
import streamlit as st

from frontend.api_client import APIClient
from frontend.components.header import render_header
from frontend.pages import alert, overview, replay, security
from frontend.state import PAGES, initialize

st.set_page_config(page_title="MarketWatch AI", page_icon="◎", layout="wide")
initialize()
theme_path = Path(__file__).parent / "styles" / "theme.css"
st.markdown(f"<style>{theme_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

client = APIClient()


def load_endpoint(name: str, loader, default):
    try:
        return loader(), None
    except (httpx.HTTPError, OSError, ValueError) as exc:
        return default, f"{name} unavailable: {exc}"


health, health_error = load_endpoint("Health", client.health, {})
connected = health.get("status") == "ok"
if health_error:
    st.error(f"Backend disconnected: {health_error}")

quality, quality_error = load_endpoint("Quality metadata", client.quality, None)
stocks, stocks_error = load_endpoint("Monitored securities", client.stocks, None)
alerts, alerts_error = load_endpoint("Alerts", client.alerts, None)
for endpoint_error in (quality_error, stocks_error, alerts_error):
    if endpoint_error:
        st.warning(endpoint_error)

if connected:
    st.success("Backend health check passed.")

render_header(connected, quality_available=quality is not None)
st.sidebar.title("NAVIGATION")
st.session_state["page"] = st.sidebar.radio("Screen", PAGES, index=PAGES.index(st.session_state["page"]))

if st.session_state["page"] == PAGES[0]:
    overview.render(client, quality, stocks or {}, alerts)
elif st.session_state["page"] == PAGES[1]:
    security.render(client, st.session_state.get("selected_symbol"))
elif st.session_state["page"] == PAGES[2]:
    alert.render(client, st.session_state.get("selected_alert"))
else:
    replay.render(client, (stocks or {}).get("symbols", []))

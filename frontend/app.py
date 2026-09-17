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
try:
    health = client.health()
    quality = client.quality()
    stocks = client.stocks()
    alerts = client.alerts()
    connected = health.get("status") == "ok"
except (httpx.HTTPError, OSError, ValueError) as exc:
    connected = False
    quality = None
    stocks = None
    alerts = None
    st.error(f"Backend disconnected: {exc}")

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

"""Alert investigation screen."""

from __future__ import annotations

import streamlit as st

from frontend.components.evidence import render_explanation
from frontend.components.metrics import empty_state


def render(client, alert_id: str | None) -> None:
    alerts = client.alerts()
    alert = next((item for item in alerts if item["alert_id"] == alert_id), None)
    if alert is None:
        empty_state("ALERT DATA UNAVAILABLE")
        return
    st.header(f"Alert Investigation: {alert['alert_id']}")
    st.metric("Risk score", f"{alert['risk_score']:.2f}/100")
    st.write(f"**{alert['symbol']}** | {alert['timestamp']} | **{alert['severity']}** | State: {alert['state']}")
    if alert["is_simulated"]:
        st.warning("SIMULATED / INJECTED")
    render_explanation(alert)
    st.subheader("Lifecycle history")
    st.json(alert["history"])
    st.info("Lifecycle transition controls are unavailable: the current API exposes no transition endpoint.")

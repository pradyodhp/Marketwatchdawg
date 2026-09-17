"""Alert feed components."""

from __future__ import annotations

import streamlit as st

from frontend.state import navigate


def render_alert_feed(alerts: list[dict]) -> None:
    if not alerts:
        st.info("NO ACTIVE ALERTS")
        return
    for alert in alerts:
        label = f"{alert['severity']} | {alert['symbol']} | {alert['risk_score']:.2f}/100"
        if st.button(label, key=f"alert-{alert['alert_id']}"):
            navigate("Alert Investigation", alert_id=alert["alert_id"])
            st.rerun()

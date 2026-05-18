"""
drift_timeline.py — reusable Streamlit component for a drift score timeline.
Accepts a list of (event_label, drift_score) pairs and renders a line chart.
"""
import pandas as pd
import streamlit as st
import altair as alt


def render_drift_timeline(events: list[tuple[str, float]]):
    """
    Render a drift score timeline.

    Parameters
    ----------
    events : list of (label, score) tuples, e.g. [("Event 1", 0.0), ("Event 2", 1.0)]
    """
    if not events:
        st.info("No events to display.")
        return

    df = pd.DataFrame(events, columns=["event", "drift_score"])

    threshold_line = alt.Chart(
        pd.DataFrame([{"threshold": 0.5}])
    ).mark_rule(color="red", strokeDash=[4, 4]).encode(
        y="threshold:Q"
    )

    line = (
        alt.Chart(df)
        .mark_line(point=True)
        .encode(
            x=alt.X("event:O", title="Event"),
            y=alt.Y("drift_score:Q", scale=alt.Scale(domain=[0, 1]), title="Drift Score"),
            color=alt.condition(
                alt.datum.drift_score >= 0.5,
                alt.value("red"),
                alt.value("green"),
            ),
            tooltip=["event", "drift_score"],
        )
    )

    st.altair_chart(line + threshold_line, use_container_width=True)

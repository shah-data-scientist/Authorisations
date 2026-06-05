"""
02_user_access_review.py — Fleet risk table + individual employee audit.
"""
import os

import httpx
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from role_recommender.dashboard.cluster_utils import (
    load_fleet_analytics,
    get_user_weights,
    score_user_all_systems,
)

_API_URL = os.environ.get("API_URL", "http://localhost:8000")
_FONT = dict(size=14, color="#1a1a1a")

st.title("User Access Review")
st.caption(
    "Fleet-wide risk overview sorted by Balanced Risk Score."
    " Filter, select an employee, then drill into their access profile."
)

st.info(
    "**Two distinct scores are used on this page — do not confuse them:**\n\n"
    "- **Drift Score** — a continuous score (0–1) per system:"
    " *< 0.3 = Normal* (fits the employee's role profile),"
    " *0.3–0.7 = Minor Drift* (partial overlap with a related cluster),"
    " *≥ 0.7 = High Drift* (outside the employee's role profile entirely)."
    " This answers: *'Is this specific system access appropriate?'*\n\n"
    "- **Balanced Risk Score** — an overall score *given to the employee*,"
    " summarising their entire access portfolio."
    " Formula: `(n_high × 1.0 + n_minor × 0.5 + n_normal × 0.0)`"
    " divided by total systems. Ranges from 0 (all access normal) to 1"
    " (all access highly anomalous)."
    " This answers:"
    " *'How risky is this employee's overall access profile?'*\n\n"
    "**Risk Categories** are tertile-based so High / Medium / Low each"
    " contain approximately one-third of employees.\n\n"
)

# ── Load fleet analytics ─────────────────────────────────────────────────────
with st.spinner("Loading fleet analytics…"):
    analytics_df = load_fleet_analytics()

# ── Filter controls ──────────────────────────────────────────────────────────
all_employee_ids = sorted(analytics_df["employee_id"].tolist())

col_f1, col_f2 = st.columns([1, 2])
with col_f1:
    risk_filter = st.selectbox(
        "Filter by Risk Category",
        options=["All", "High", "Medium", "Low"],
        index=0,
    )
with col_f2:
    emp_filter = st.selectbox(
        "Filter by Employee ID",
        options=["All"] + all_employee_ids,
        index=0,
        format_func=lambda x: "All employees" if x == "All" else str(x),
    )

filtered = analytics_df.copy()
if risk_filter != "All":
    filtered = filtered[filtered["risk_category"] == risk_filter]
if emp_filter != "All":
    filtered = filtered[filtered["employee_id"] == emp_filter]

filtered = filtered.sort_values(
    "balanced_risk_score", ascending=False
).reset_index(drop=True)

# ── Fleet table ──────────────────────────────────────────────────────────────
st.subheader(f"Employee Risk Table — {len(filtered):,} employees")

display_cols = {
    "employee_id": "Employee ID",
    "dominant_cluster": "Cluster",
    "risk_category": "Risk Category",
    "balanced_risk_score": "Balanced Risk Score",
    "n_systems": "# Systems",
    "n_high": "# High Drift",
    "anomaly_rate": "Anomaly Rate",
}
table_df = (
    filtered[list(display_cols)]
    .rename(columns=display_cols)
    .reset_index(drop=True)
)
table_df["Balanced Risk Score"] = table_df["Balanced Risk Score"].map(
    "{:.3f}".format
)
table_df["Anomaly Rate"] = table_df["Anomaly Rate"].map("{:.1%}".format)

st.dataframe(
    table_df,
    use_container_width=True,
    hide_index=True,
    height=300,
)

# ── Employee selector for drilldown ─────────────────────────────────────────
st.divider()
st.subheader("Individual Employee Drilldown")

valid_ids = filtered["employee_id"].tolist()
if not valid_ids:
    st.warning("No employees match the current filters.")
    st.stop()

default_id = st.session_state.get("selected_user_id", valid_ids[0])
if default_id not in valid_ids:
    default_id = valid_ids[0]

user_id = st.selectbox(
    "Select Employee ID for detailed review",
    options=valid_ids,
    index=valid_ids.index(default_id),
    format_func=lambda x: str(x),
)
st.session_state["selected_user_id"] = user_id

# Clear cached review data whenever the selected employee changes so stale
# data from a previous employee is never shown under the new one.
if st.session_state.get("_review_uid") != user_id:
    for k in ("_review_weights", "_review_scores", "_review_emp_row"):
        st.session_state.pop(k, None)
    st.session_state["_review_uid"] = user_id

# ── Run button — computes and caches; does NOT render ────────────────────────
if st.button("Run Access Review", type="primary"):
    with st.spinner("Analysing access profile…"):
        weights_df = get_user_weights(int(user_id))
        scores_df = score_user_all_systems(int(user_id))
    emp_row = analytics_df[analytics_df["employee_id"] == user_id].iloc[0]
    st.session_state["_review_weights"] = weights_df
    st.session_state["_review_scores"] = scores_df
    st.session_state["_review_emp_row"] = emp_row

# ── Results — rendered from session state on every rerun ─────────────────────
if "_review_weights" not in st.session_state:
    st.stop()

weights_df = st.session_state["_review_weights"]
scores_df = st.session_state["_review_scores"]
emp_row = st.session_state["_review_emp_row"]

dominant = weights_df.loc[weights_df["weight"].idxmax(), "cluster"]
n_anomalous = emp_row["n_high"] + emp_row["n_minor"]
anomaly_rate = emp_row["anomaly_rate"]
brs = emp_row["balanced_risk_score"]
risk_cat = emp_row["risk_category"]

m1, m2, m3, m4 = st.columns(4)
m1.metric("Dominant Cluster", dominant)
m2.metric("Balanced Risk Score", f"{brs:.3f}")
m3.metric("Risk Category", risk_cat)
m4.metric("Anomalous Systems", f"{n_anomalous} ({anomaly_rate:.0%})")

st.divider()

# ── Cluster weights + anomaly gauge ──────────────────────────────────────────
col1, col2 = st.columns([1, 1.4])

with col1:
    st.subheader("Cluster Membership Weights")
    fig_w = px.bar(
        weights_df, x="weight", y="cluster", orientation="h",
        color="weight",
        color_continuous_scale="Blues",
        labels={"weight": "Membership Weight", "cluster": "Cluster"},
        text=weights_df["weight"].round(2),
    )
    fig_w.update_traces(textposition="outside", textfont=_FONT)
    fig_w.update_layout(
        coloraxis_showscale=False,
        yaxis={"categoryorder": "category ascending", "tickfont": _FONT},
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            showgrid=True, gridcolor="#eee", range=[0, 1.1],
            title_font=_FONT,
        ),
        height=420,
        margin=dict(l=10, r=10, t=10, b=10),
        font=_FONT,
    )
    st.plotly_chart(fig_w, use_container_width=True)

with col2:
    st.subheader("Access Anomaly Rate")
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=anomaly_rate * 100,
        number={"suffix": "%", "font": {"size": 36}},
        title={
            "text": "Systems Outside Expected Pattern",
            "font": {"size": 14},
        },
        gauge={
            "axis": {"range": [0, 100], "ticksuffix": "%"},
            "bar": {"color": "#2c3e50"},
            "steps": [
                {"range": [0, 15], "color": "#d5f5e3"},
                {"range": [15, 35], "color": "#fdebd0"},
                {"range": [35, 100], "color": "#fadbd8"},
            ],
            "threshold": {
                "line": {"color": "red", "width": 3},
                "thickness": 0.75,
                "value": 30,
            },
        },
    ))
    fig_gauge.update_layout(
        height=260, margin=dict(t=60, b=0, l=30, r=30),
        font=_FONT,
    )
    st.plotly_chart(fig_gauge, use_container_width=True)

    if anomaly_rate < 0.15:
        st.success("Access profile looks healthy. No immediate action needed.")
    elif anomaly_rate < 0.35:
        st.warning(
            "Some accesses warrant a review."
            " Check the highlighted systems below."
        )
    else:
        st.error(
            "High proportion of anomalous access."
            " Recommend escalation for full access review."
        )

st.divider()

# ── Drift breakdown ───────────────────────────────────────────────────────────
st.subheader("System Drift Breakdown")

drift_counts = (
    scores_df["drift_category"]
    .value_counts()
    .rename_axis("Category")
    .reset_index(name="Count")
)
cat_colors = {
    "Normal": "#27ae60",
    "Minor Drift": "#f39c12",
    "High Drift": "#e74c3c",
}

col_pie, _ = st.columns([1, 1])
with col_pie:
    fig_pie = px.pie(
        drift_counts, names="Category", values="Count",
        title="Proportion by Drift Category",
        color="Category",
        color_discrete_map=cat_colors,
        hole=0.4,
    )
    fig_pie.update_traces(textinfo="percent+label", textfont=_FONT)
    fig_pie.update_layout(font=_FONT)
    st.plotly_chart(fig_pie, use_container_width=True)

# ── Full system table ─────────────────────────────────────────────────────────
with st.expander("Full System Access Table", expanded=False):
    display_df = scores_df.rename(columns={"drift_category": "status"})
    st.dataframe(
        display_df[["system_id", "drift_score", "status", "explanation"]],
        use_container_width=True,
        hide_index=True,
    )

# ── Revoke access ─────────────────────────────────────────────────────────────
st.divider()
st.subheader("Revoke Access")
st.caption(
    "Select a system to log an access revocation event in the audit"
    " trail. This does not modify the underlying dataset — it records"
    " the revocation decision for compliance purposes."
)

revoke_systems = scores_df["system_id"].tolist()
col_rev1, col_rev2 = st.columns([1, 2])
with col_rev1:
    revoke_system = st.selectbox(
        "System to Revoke",
        options=revoke_systems,
        key="revoke_system_select",
    )
with col_rev2:
    revoke_reason = st.text_input(
        "Reason (optional)",
        placeholder="e.g. Role change, no longer required",
        key="revoke_reason_input",
    )

if st.button("Revoke Access", type="secondary", key="revoke_btn"):
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.post(
                f"{_API_URL}/simulations/revoke",
                json={
                    "employee_id": int(user_id),
                    "system_id": int(revoke_system),
                    "reason": revoke_reason or None,
                },
            )
        if resp.status_code == 201:
            st.success(
                f"Revocation of system {revoke_system} for employee"
                f" {user_id} logged in audit trail."
            )
        else:
            st.error(f"API error {resp.status_code}: {resp.text}")
    except Exception as exc:
        st.error(f"Could not reach API: {exc}")

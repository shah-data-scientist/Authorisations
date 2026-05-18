"""
02_user_access_review.py — Fleet risk table + individual employee audit.
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from role_recommender.dashboard.cluster_utils import (
    load_fleet_analytics,
    get_user_weights, get_user_systems,
    score_user_all_systems,
)

_FONT = dict(size=14, color="#1a1a1a")

st.title("User Access Review")
st.caption(
    "Fleet-wide risk overview sorted by Balanced Risk Score."
    " Filter, select an employee, then drill into their access profile."
)

st.info(
    "**Two distinct scores are used on this page — do not confuse them:**\n\n"
    "- **Drift Score** — a per-system evaluation for this employee."
    " Each system they have access to receives a drift score:"
    " *0.0 = normal* (system is typical for their cluster),"
    " *0.3 = minor drift* (system used by a related cluster),"
    " *1.0 = high drift* (system not typical for any of their clusters)."
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

# Apply filters
filtered = analytics_df.copy()
if risk_filter != "All":
    filtered = filtered[filtered["risk_category"] == risk_filter]
if emp_filter != "All":
    filtered = filtered[filtered["employee_id"] == emp_filter]

# Sort: highest risk first
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

# Honour cross-page session state (set by User Access Simulation)
default_id = st.session_state.get("selected_user_id", valid_ids[0])
if default_id not in valid_ids:
    default_id = valid_ids[0]

user_id = st.selectbox(
    "Select Employee ID for detailed review",
    options=valid_ids,
    index=valid_ids.index(default_id),
    format_func=lambda x: str(x),
)
# Sync session state so the Simulation page pre-selects the same employee
st.session_state["selected_user_id"] = user_id

if st.button("Run Access Review", type="primary"):
    with st.spinner("Analysing access profile…"):
        weights_df = get_user_weights(int(user_id))
        systems = get_user_systems(int(user_id))
        scores_df = score_user_all_systems(int(user_id))

    # Pull pre-computed summary row for this employee
    emp_row = analytics_df[analytics_df["employee_id"] == user_id].iloc[0]

    dominant = weights_df.loc[weights_df["weight"].idxmax(), "cluster"]
    n_systems = emp_row["n_systems"]
    n_anomalous = emp_row["n_high"] + emp_row["n_minor"]
    anomaly_rate = emp_row["anomaly_rate"]
    brs = emp_row["balanced_risk_score"]
    risk_cat = emp_row["risk_category"]

    # Top metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Dominant Cluster", dominant)
    m2.metric("Balanced Risk Score", f"{brs:.3f}")
    m3.metric("Risk Category", risk_cat)
    m4.metric(
        "Anomalous Systems",
        f"{n_anomalous} ({anomaly_rate:.0%})",
    )

    st.divider()

    # ── Cluster weights + anomaly gauge ──────────────────────────────────
    col1, col2 = st.columns([1, 1.4])

    with col1:
        st.subheader("Cluster Membership Weights")
        fig_w = px.bar(
            weights_df, x="weight", y="cluster", orientation="h",
            color="weight",
            color_continuous_scale="Blues",
            labels={
                "weight": "Membership Weight", "cluster": "Cluster"
            },
            text=weights_df["weight"].round(2),
        )
        fig_w.update_traces(textposition="outside", textfont=_FONT)
        fig_w.update_layout(
            coloraxis_showscale=False,
            yaxis={"categoryorder": "category ascending",
                   "tickfont": _FONT},
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
            st.success(
                "Access profile looks healthy. No immediate action needed."
            )
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

    # ── Drift breakdown ───────────────────────────────────────────────────
    st.subheader("System Drift Breakdown")

    drift_counts = (
        scores_df["drift_score"]
        .map({0.0: "Normal", 0.3: "Minor Drift", 1.0: "High Drift"})
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
        fig_pie.update_traces(
            textinfo="percent+label",
            textfont=_FONT,
        )
        fig_pie.update_layout(font=_FONT)
        st.plotly_chart(fig_pie, use_container_width=True)

    # ── Full system table ─────────────────────────────────────────────────
    with st.expander("Full System Access Table", expanded=False):
        display_df = scores_df.copy()
        display_df["status"] = display_df["drift_score"].map(
            {
                0.0: "Normal",
                0.3: "Minor Drift",
                1.0: "High Drift",
            }
        )
        st.dataframe(
            display_df[
                ["system_id", "drift_score", "status", "explanation"]
            ],
            use_container_width=True,
            hide_index=True,
        )

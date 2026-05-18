"""
01_access_intelligence.py — Fleet overview + system risk analysis.
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from role_recommender.dashboard.cluster_utils import (
    CLUSTER_LABELS, STRENGTH_ORDER, STRENGTH_COLORS, RISK_COLORS,
    compute_fleet_stats, compute_systems_per_cluster,
    get_system_cluster_strengths, get_system_employees,
    score_single, load_matrix, load_fleet_analytics,
)

_FONT = dict(size=14, color="#1a1a1a")

st.title("Access Intelligence")
st.caption(
    "Fleet-level overview of how employees are clustered by their access"
    " patterns, and a system-centric risk analysis tool."
)

st.info(
    "**Key concepts used throughout this platform:**\n\n"
    "- **Drift Score** — an evaluation of a *specific system access* for a"
    " *specific employee*. It measures how unusual it is for that employee"
    " to access that particular system, based on what employees in their"
    " cluster typically access. Values: 0.0 (normal), 0.3 (minor drift),"
    " 1.0 (high drift).\n\n"
    "- **Balanced Risk Score** — an overall risk score *given to a user*,"
    " summarising their entire access profile. Formula:"
    " `(n_high × 1.0 + n_minor × 0.5 + n_normal × 0.0) / total_systems`."
    " Ranges 0–1. The higher the score, the more their overall access"
    " deviates from what is expected for employees in their cluster(s)."
)

# ── Section A: Fleet Overview ───────────────────────────────────────────────
st.header("Fleet Overview")

with st.spinner("Loading fleet statistics…"):
    fleet_df = compute_fleet_stats()
    sys_df = compute_systems_per_cluster()
    analytics_df = load_fleet_analytics()

# Timestamp banner
computed_at = pd.to_datetime(
    analytics_df["computed_at"].iloc[0]
).strftime("%Y-%m-%d %H:%M")
st.caption(f"Fleet analytics computed: **{computed_at}**")

# ── Chart 1 — employees per cluster (half width, chart 2 takes full width) ──
col1, _ = st.columns(2)
with col1:
    emp_count = (
        fleet_df.groupby("dominant_cluster")
        .size()
        .reindex(CLUSTER_LABELS, fill_value=0)
        .reset_index(name="Employees")
        .rename(columns={"dominant_cluster": "Cluster"})
    )
    fig1 = px.bar(
        emp_count, x="Cluster", y="Employees",
        title="Employees per Access Cluster",
        color="Employees",
        color_continuous_scale="Blues",
        text="Employees",
    )
    fig1.update_traces(
        textposition="outside", textfont=_FONT, cliponaxis=False
    )
    fig1.update_layout(
        coloraxis_showscale=False,
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(showgrid=True, gridcolor="#eee", title_font=_FONT),
        xaxis=dict(title_font=_FONT, tickfont=_FONT),
        font=_FONT,
        margin=dict(t=60, b=40, l=40, r=20),
    )
    st.plotly_chart(fig1, use_container_width=True)

# ── Chart 2 — cluster membership strength (full width) ──────────────────────
strength_df = (
    fleet_df.groupby(["dominant_cluster", "strength"])
    .size()
    .reset_index(name="count")
)
full_idx = pd.MultiIndex.from_product(
    [CLUSTER_LABELS, STRENGTH_ORDER],
    names=["dominant_cluster", "strength"],
)
strength_df = (
    strength_df.set_index(["dominant_cluster", "strength"])
    .reindex(full_idx, fill_value=0)
    .reset_index()
)
fig2 = px.bar(
    strength_df,
    x="dominant_cluster", y="count", color="strength",
    title="Cluster Membership Strength",
    labels={
        "dominant_cluster": "Cluster",
        "count": "Employees",
        "strength": "Membership",
    },
    category_orders={
        "dominant_cluster": CLUSTER_LABELS,
        "strength": STRENGTH_ORDER,
    },
    color_discrete_map=STRENGTH_COLORS,
    text="count",
)
fig2.update_traces(
    textposition="outside", textfont=_FONT, cliponaxis=False
)
fig2.update_layout(
    plot_bgcolor="rgba(0,0,0,0)",
    yaxis=dict(showgrid=True, gridcolor="#eee", title_font=_FONT),
    xaxis=dict(title_font=_FONT, tickfont=_FONT),
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
    font=_FONT,
    margin=dict(t=80, b=40, l=40, r=20),
)
st.plotly_chart(fig2, use_container_width=True)

st.caption(
    "**Strong** — employee's dominant cluster weight > 70%  |  "
    "**Partial** — 30–70%  |  "
    "**Weak** — < 30% (employee sits between multiple clusters)"
)

# ── Chart 3 — characteristic systems per cluster ────────────────────────────
fig3 = px.bar(
    sys_df, x="n_systems", y="cluster", orientation="h",
    title="Characteristic Systems per Access Cluster",
    color="n_systems",
    color_continuous_scale="YlOrRd",
    labels={"n_systems": "Characteristic Systems", "cluster": "Cluster"},
    text="n_systems",
)
fig3.update_traces(
    textposition="outside", textfont=_FONT, cliponaxis=False
)
fig3.update_layout(
    yaxis={"categoryorder": "category ascending", "tickfont": _FONT},
    coloraxis_showscale=False,
    height=520,
    plot_bgcolor="rgba(0,0,0,0)",
    xaxis=dict(showgrid=True, gridcolor="#eee", title_font=_FONT),
    font=_FONT,
    margin=dict(t=60, b=40, l=60, r=80),
)
st.plotly_chart(fig3, use_container_width=True)
st.caption(
    "A system is 'characteristic' for a cluster if its NMF association"
    " strength exceeds that cluster's average across all systems."
)

# ── Charts 4 & 5 — anomaly distribution & risk category breakdown ───────────
st.divider()
st.subheader("Fleet Risk Distribution")

col4, col5 = st.columns(2)

with col4:
    fig4 = px.histogram(
        analytics_df,
        x="anomaly_rate",
        nbins=20,
        title="Anomaly Rate Distribution Across Employees",
        labels={
            "anomaly_rate": "Anomaly Rate (% systems with drift > 0)",
            "count": "Employees",
        },
        color_discrete_sequence=["#3498db"],
    )
    fig4.update_traces(
        texttemplate="%{y}",
        textposition="outside",
        cliponaxis=False,
        textfont=_FONT,
    )
    fig4.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        bargap=0.05,
        yaxis=dict(
            showgrid=True, gridcolor="#eee",
            title="Employees", title_font=_FONT,
        ),
        xaxis=dict(title_font=_FONT, tickformat=".0%"),
        font=_FONT,
        margin=dict(t=60, b=40, l=40, r=20),
    )
    st.plotly_chart(fig4, use_container_width=True)
    st.caption(
        "Distribution of the proportion of each employee's systems"
        " that have a drift score above zero."
    )

with col5:
    cat_order = ["Low", "Medium", "High"]
    cat_counts = (
        analytics_df["risk_category"]
        .value_counts()
        .reindex(cat_order, fill_value=0)
        .reset_index()
        .rename(columns={
            "risk_category": "Risk Category", "count": "Employees"
        })
    )
    fig5 = px.bar(
        cat_counts,
        x="Risk Category", y="Employees",
        title="Employees by Balanced Risk Score Category",
        color="Risk Category",
        color_discrete_map=RISK_COLORS,
        text="Employees",
        category_orders={"Risk Category": cat_order},
    )
    fig5.update_traces(
        textposition="outside", textfont=_FONT, cliponaxis=False
    )
    fig5.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(showgrid=True, gridcolor="#eee", title_font=_FONT),
        xaxis=dict(title_font=_FONT, tickfont=_FONT),
        showlegend=False,
        font=_FONT,
        margin=dict(t=60, b=40, l=40, r=20),
    )
    st.plotly_chart(fig5, use_container_width=True)
    st.caption(
        "Risk categories are tertile-based: each band contains"
        " approximately one-third of employees."
    )

# ── Section B: System Risk Analysis ─────────────────────────────────────────
st.divider()
st.header("System Risk Analysis")
st.markdown(
    "Select a system to see which clusters are most associated with it"
    " and how many current employees have anomalous access to it."
)

matrix = load_matrix()
all_systems = sorted(matrix.columns.tolist())
selected = st.selectbox(
    "Select System ID", options=all_systems,
    help="Type to search by system ID.",
)

if selected is not None:
    col_a, col_b = st.columns([1.2, 1])

    with col_a:
        strengths = get_system_cluster_strengths(selected)
        if not strengths.empty:
            fig_s = px.bar(
                strengths, x="cluster", y="association_strength",
                title=f"Cluster Association — System {selected}",
                color="association_strength",
                color_continuous_scale="Oranges",
                labels={
                    "cluster": "Cluster",
                    "association_strength": "Association Strength",
                },
                text=strengths["association_strength"].round(3),
            )
            fig_s.update_traces(
                textposition="outside", textfont=_FONT, cliponaxis=False
            )
            fig_s.update_layout(
                coloraxis_showscale=False,
                plot_bgcolor="rgba(0,0,0,0)",
                height=380,
                yaxis=dict(
                    showgrid=True, gridcolor="#eee", title_font=_FONT
                ),
                xaxis=dict(title_font=_FONT, tickfont=_FONT),
                font=_FONT,
                margin=dict(t=60, b=40, l=40, r=20),
            )
            st.plotly_chart(fig_s, use_container_width=True)
            top_cluster = strengths.loc[
                strengths["association_strength"].idxmax(), "cluster"
            ]
            st.caption(
                f"Cluster **{top_cluster}** has the strongest association"
                f" with System {selected}."
            )

    with col_b:
        employees = get_system_employees(selected)
        st.metric("Employees with Current Access", len(employees))

        if employees:
            with st.spinner("Scoring employee access…"):
                drift_rows = []
                for emp in employees[:60]:
                    r = score_single(int(emp), int(selected))
                    drift_rows.append({
                        "employee_id": emp,
                        "drift_score": r["drift_score"],
                    })
            risk_df = pd.DataFrame(drift_rows)
            n_anomalous = (risk_df["drift_score"] > 0).sum()
            pct = n_anomalous / len(risk_df) * 100

            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=pct,
                number={"suffix": "%", "font": {"size": 28}},
                title={"text": "Employees with Anomalous Access",
                       "font": {"size": 14}},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": "#2c3e50"},
                    "steps": [
                        {"range": [0, 20], "color": "#d5f5e3"},
                        {"range": [20, 50], "color": "#fdebd0"},
                        {"range": [50, 100], "color": "#fadbd8"},
                    ],
                    "threshold": {
                        "line": {"color": "red", "width": 3},
                        "thickness": 0.75, "value": 30,
                    },
                },
            ))
            fig_gauge.update_layout(
                height=300, margin=dict(t=60, b=0, l=20, r=20),
                font=_FONT,
            )
            st.plotly_chart(fig_gauge, use_container_width=True)
        else:
            st.info("No employees currently have access to this system.")

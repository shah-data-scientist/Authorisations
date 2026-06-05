"""
03_user_access_simulation.py — Simulate granting access to a new system.
"""
import os

import httpx
import streamlit as st
import plotly.graph_objects as go

from role_recommender.dashboard.cluster_utils import (
    load_matrix,
    get_user_weights, get_user_nonaccess_systems,
    score_single,
)

_API_URL = os.environ.get("API_URL", "http://localhost:8000")


def _persist_simulation(
    employee_id: int,
    system_id: int,
    drift_score: float,
    risk_label: str,
    explanation: str,
) -> None:
    """POST simulation result to API (non-blocking; silent on failure)."""
    try:
        with httpx.Client(timeout=3.0) as client:
            client.post(
                f"{_API_URL}/simulations/",
                json={
                    "employee_id": employee_id,
                    "system_id": system_id,
                    "drift_score": drift_score,
                    "risk_label": risk_label,
                    "explanation": explanation,
                },
            )
    except Exception:
        pass


def _fetch_history(employee_id: int) -> list[dict]:
    """GET recent simulations for this employee (silent on failure)."""
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(
                f"{_API_URL}/simulations/history",
                params={"employee_id": employee_id},
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return []


st.title("User Access Simulation")
st.caption(
    "Simulate granting an employee access to a system they do not"
    " currently have, and score how anomalous that access would be."
)

st.info(
    "**What this page computes:** A **Drift Score** — the evaluation of a"
    " *specific (employee, system) access pair*. It measures how unusual"
    " it would be for this employee to access the selected system, based"
    " on what employees in their cluster(s) typically access.\n\n"
    "This is different from the **Balanced Risk Score** (found in User"
    " Access Review), which summarises an employee's *overall* access"
    " portfolio. Here, we evaluate one hypothetical access at a time.\n\n"
    "**How to use:**\n"
    "1. Select an employee (pre-filled if you arrived from User Access"
    " Review).\n"
    "2. The system dropdown shows **only systems the employee does not"
    " currently have access to** — these are the ones worth simulating.\n"
    "3. Click Simulate to receive the drift score for that access.\n\n"
    "**Drift Score interpretation (continuous 0–1 scale):**\n"
    "- **< 0.3 — Normal:** Access fits the employee's role profile."
    " Safe to grant.\n"
    "- **0.3–0.7 — Minor Drift:** Partial overlap with a related cluster."
    " Quick review recommended before granting.\n"
    "- **≥ 0.7 — High Drift:** Access falls outside the employee's role"
    " profile entirely. Escalate for review before granting."
)

matrix = load_matrix()
valid_users = sorted(matrix.index.tolist())

# ── Employee selection — honours cross-page session state ────────────────────
default_id = st.session_state.get("selected_user_id", valid_users[0])
if default_id not in valid_users:
    default_id = valid_users[0]

user_id = st.selectbox(
    "Select Employee ID (ROLE_CODE)",
    options=valid_users,
    index=valid_users.index(default_id),
)
# Keep session state in sync so User Access Review sees the same selection
st.session_state["selected_user_id"] = user_id

# Load the employee's cluster weights for context
weights_df = get_user_weights(int(user_id))
dominant = weights_df.loc[weights_df["weight"].idxmax(), "cluster"]
row = matrix.loc[user_id]
n_current = int((row > 0).sum())

col_info1, col_info2 = st.columns(2)
col_info1.metric("Dominant Cluster", dominant)
col_info2.metric("Current System Count", n_current)

# ── System selection ─────────────────────────────────────────────────────────
with st.spinner("Loading available systems…"):
    nonaccess_systems = get_user_nonaccess_systems(int(user_id))

if not nonaccess_systems:
    st.success(
        "This employee already has access to all systems in the dataset."
    )
    st.stop()

st.caption(
    f"**{len(nonaccess_systems):,}** systems available to simulate"
    f" (employee does not currently have access to these)."
)

system_id = st.selectbox(
    "Select System to Simulate Access To",
    options=nonaccess_systems,
    help="Type to search by system ID.",
)

# ── Simulation ───────────────────────────────────────────────────────────────
if st.button("Run Simulation", type="primary"):
    with st.spinner("Scoring access request…"):
        result = score_single(int(user_id), int(system_id))

    score = result["drift_score"]
    risk_label = (
        "Safe" if score < 0.3
        else "Review" if score < 0.7
        else "Escalate"
    )
    _persist_simulation(
        int(user_id), int(system_id),
        score, risk_label, result.get("explanation", ""),
    )

    st.divider()
    st.subheader(
        f"Simulation Result — Employee {user_id} → System {system_id}"
    )

    col_gauge, col_verdict = st.columns([1, 1.2])

    with col_gauge:
        color = (
            "#27ae60" if score < 0.3
            else "#f39c12" if score < 0.7
            else "#e74c3c"
        )
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=score * 100,
            number={
                "suffix": "%",
                "font": {"size": 40},
                "valueformat": ".0f",
            },
            title={"text": "Drift Score", "font": {"size": 16}},
            gauge={
                "axis": {
                    "range": [0, 100],
                    "ticksuffix": "%",
                    "tickvals": [0, 30, 70, 100],
                },
                "bar": {"color": color, "thickness": 0.3},
                "bgcolor": "white",
                "steps": [
                    {"range": [0, 30], "color": "#d5f5e3"},
                    {"range": [30, 70], "color": "#fdebd0"},
                    {"range": [70, 100], "color": "#fadbd8"},
                ],
                "threshold": {
                    "line": {"color": "red", "width": 3},
                    "thickness": 0.75,
                    "value": 50,
                },
            },
        ))
        fig_gauge.update_layout(
            height=280, margin=dict(t=60, b=20, l=20, r=20),
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col_verdict:
        st.markdown("### Recommendation")
        if score < 0.3:
            st.success(
                "**Safe to grant.**\n\n"
                + result["explanation"]
                + "\n\nThis access is consistent with the employee's"
                " cluster. No further review needed."
            )
        elif score < 0.7:
            st.warning(
                "**Review before granting.**\n\n"
                + result["explanation"]
                + "\n\nThis access partially overlaps the employee's"
                " role profile. A quick approval check is recommended."
            )
        else:
            st.error(
                "**Do not grant without review.**\n\n"
                + result["explanation"]
                + "\n\nThis access falls outside the employee's role"
                " profile entirely. Escalate for approval."
            )

        st.markdown("---")
        st.markdown("**Employee's cluster profile**")
        top3 = (
            weights_df[weights_df["weight"] > 0.05]
            .sort_values("weight", ascending=False)
            .head(3)
        )
        for _, r in top3.iterrows():
            st.progress(
                float(r["weight"]),
                text=f"Cluster {r['cluster']} — {r['weight']:.0%}",
            )

    # ── Simulation history ────────────────────────────────────────────────
    st.divider()
    with st.expander("Simulation History (this employee)", expanded=False):
        history = _fetch_history(int(user_id))
        if not history:
            st.caption(
                "No past simulations found — either none recorded yet "
                "or the API is not reachable."
            )
        else:
            import pandas as pd
            hist_df = pd.DataFrame(history)[
                [
                    "requested_at", "system_id", "drift_score",
                    "risk_label", "review_status", "reviewed_by", "notes",
                ]
            ].rename(columns={
                "requested_at": "Timestamp",
                "system_id": "System",
                "drift_score": "Drift",
                "risk_label": "Label",
                "review_status": "Status",
                "reviewed_by": "Reviewed By",
                "notes": "Notes",
            })
            st.dataframe(hist_df, use_container_width=True, hide_index=True)

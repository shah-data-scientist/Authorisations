"""
app.py — Access Management Platform dashboard entry point.
"""
import streamlit as st

st.set_page_config(
    page_title="Access Management Platform",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🔐 Access Management Platform")
st.subheader("Hybrid Role Mining · Access Drift Detection · Risk Review")

st.markdown(
    "Analyse employee access patterns, detect anomalies, and simulate"
    " new access requests — powered by NMF role mining on the"
    " Amazon Employee Access dataset."
)

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 📊 Access Intelligence")
    st.markdown(
        "Fleet-level overview of how employees are grouped into"
        " access clusters, cluster sizes, membership strength,"
        " and system coverage. Includes system-centric risk"
        " analysis and anomaly rate distribution."
    )

with col2:
    st.markdown("### 🔍 User Access Review")
    st.markdown(
        "Fleet-wide risk table sorted by Balanced Risk Score."
        " Filter by risk category (High / Medium / Low) or"
        " employee ID. Select any employee to drill into their"
        " cluster profile and anomalous system accesses."
    )

with col3:
    st.markdown("### 🧪 User Access Simulation")
    st.markdown(
        "Simulate granting an employee access to a system they"
        " do not currently have. Scored against their cluster"
        " profile — Safe to grant, Review recommended,"
        " or Escalate for approval."
    )

st.divider()
st.info("👈 Select a page from the sidebar to begin.")
st.caption(
    "Data: Amazon Employee Access Challenge (Kaggle) · "
    "Model: NMF role mining (15 clusters) + overlap-based drift scoring"
)

"""
role_card.py — reusable Streamlit component for displaying a role summary card.
"""
import streamlit as st


def render_role_card(role_id: int, top_permissions: list, weight: float | None = None):
    """Render a compact card showing a role's key info."""
    with st.container(border=True):
        header = f"Role {role_id}"
        if weight is not None:
            header += f"  —  weight: {weight:.1%}"
        st.markdown(f"**{header}**")
        st.caption(f"{len(top_permissions)} top permissions")
        st.dataframe(
            {"resource_id": top_permissions[:10]},
            use_container_width=True,
            hide_index=True,
        )

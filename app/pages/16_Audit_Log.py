"""Read-only application audit history for Admin and Developer roles."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.auth import get_auth_store, require_page_permission
from app.navigation import timestamp_column
from app.security import Permission
from app.ui import apply_theme, page_header, section_intro


user = require_page_permission(Permission.VIEW_AUDIT)
store = get_auth_store()
apply_theme()
page_header(
    "Audit Log",
    "Review authenticated data changes, imports, deletions, and user-management activity.",
    "ADMINISTRATION",
)

events = store.list_audit(user, limit=5000)
frame = pd.DataFrame(
    [
        {
            "OCCURRED_AT": event.occurred_at,
            "USER": event.actor_email,
            "ACTION": event.action,
            "ENTITY_TYPE": event.entity_type,
            "ENTITY_ID": event.entity_id,
            "DETAILS": event.details,
        }
        for event in events
    ]
)

if frame.empty:
    section_intro("Audit events")
    st.info("No audited actions have been recorded yet.")
else:
    filters = st.container(horizontal=True, vertical_alignment="bottom")
    user_filter = filters.selectbox("User", ["All", *sorted(frame["USER"].dropna().unique())])
    action_filter = filters.selectbox("Action", ["All", *sorted(frame["ACTION"].dropna().unique())])
    entity_filter = filters.selectbox("Entity", ["All", *sorted(frame["ENTITY_TYPE"].dropna().unique())])
    filtered = frame.copy()
    if user_filter != "All":
        filtered = filtered[filtered["USER"] == user_filter]
    if action_filter != "All":
        filtered = filtered[filtered["ACTION"] == action_filter]
    if entity_filter != "All":
        filtered = filtered[filtered["ENTITY_TYPE"] == entity_filter]
    section_intro("Audit events", f"{len(filtered):,} of {len(frame):,} event(s).")
    st.dataframe(
        filtered,
        width="stretch",
        hide_index=True,
        height=600,
        column_config={
            "OCCURRED_AT": timestamp_column("Timestamp"),
            "USER": st.column_config.TextColumn("User"),
            "ACTION": st.column_config.TextColumn("Action"),
            "ENTITY_TYPE": st.column_config.TextColumn("Entity"),
            "ENTITY_ID": st.column_config.TextColumn("Record ID"),
            "DETAILS": st.column_config.TextColumn("Details"),
        },
    )

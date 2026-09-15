"""Prototype EFNS user and role administration."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.auth import get_auth_store, require_page_permission
from app.navigation import timestamp_column
from app.security import Permission, Role
from app.ui import apply_theme, page_header, section_intro, show_data_error


admin = require_page_permission(Permission.MANAGE_USERS)
store = get_auth_store()
apply_theme()
page_header(
    "User Management",
    "Manage EFNS users, application roles, and account activation.",
    "ADMINISTRATION",
)
if store.supports_passwords:
    st.info("Local mode accepts only @nsegg.ca accounts and stores password hashes only.")
else:
    st.info("Snowflake supplies viewer identity. EFNS stores application roles and active status; passwords remain managed by Snowflake.")

issued = st.session_state.get("issued_temporary_credential") if store.supports_passwords else None
if issued:
    with st.container(border=True):
        st.success(f"Temporary password for {issued['email']}")
        st.code(issued["password"], language=None)
        st.warning("Copy this value now. It is shown only in this browser session and must be changed after login.")
        if st.button("Clear temporary password", icon=":material/visibility_off:"):
            st.session_state.pop("issued_temporary_credential", None)
            st.rerun()

users = store.list_users(admin)
user_frame = pd.DataFrame(
    [
        {
            "EMAIL": user.email,
            "DISPLAY_NAME": user.display_name,
            "ROLE": user.role.value,
            "ACTIVE": user.active,
            "TEMPORARY_PASSWORD": user.must_change_password,
            "LAST_LOGIN_AT": user.last_login_at,
            "UPDATED_AT": user.updated_at,
        }
        for user in users
    ]
)
section_intro("Users", f"{len(users):,} prototype account(s). Password hashes are never displayed.")
st.dataframe(
    user_frame,
    width="stretch",
    hide_index=True,
    column_config={
        "EMAIL": st.column_config.TextColumn("Email"),
        "DISPLAY_NAME": st.column_config.TextColumn("Name"),
        "ROLE": st.column_config.TextColumn("Role"),
        "ACTIVE": st.column_config.CheckboxColumn("Active"),
        "TEMPORARY_PASSWORD": st.column_config.CheckboxColumn("Password change required"),
        "LAST_LOGIN_AT": timestamp_column("Last login"),
        "UPDATED_AT": timestamp_column("Updated"),
    },
)

create_tab, maintain_tab = st.tabs(["Add user", "Maintain user"])
with create_tab:
    with st.form("create_prototype_user", clear_on_submit=True):
        email = st.text_input("Internal email address", placeholder="name@nsegg.ca")
        display_name = st.text_input("Display name")
        role_name = st.selectbox("Role", [role.value for role in Role])
        create = st.form_submit_button("Add user", type="primary", icon=":material/person_add:")
    if create:
        try:
            created, temporary_password = store.create_user(admin, email, display_name, Role(role_name))
            if temporary_password:
                st.session_state["issued_temporary_credential"] = {
                    "email": created.email,
                    "password": temporary_password,
                }
            else:
                st.success(f"{created.email} can now use EFNS through Snowflake.")
            st.rerun()
        except Exception as exc:
            show_data_error(exc)

with maintain_tab:
    options = {f"{user.display_name} · {user.email}": user.user_id for user in users}
    selected_label = st.selectbox("User", list(options), key="admin_selected_user")
    selected = next(user for user in users if user.user_id == options[selected_label])
    with st.form("maintain_prototype_user"):
        st.text_input("Email", value=selected.email, disabled=True)
        role_name = st.selectbox(
            "Assigned role",
            [role.value for role in Role],
            index=[role.value for role in Role].index(selected.role.value),
        )
        active = st.checkbox("Active account", value=selected.active)
        save = st.form_submit_button("Save access settings", type="primary", icon=":material/save:")
    if save:
        try:
            store.update_user(admin, selected.user_id, role=Role(role_name), active=active)
            st.success("User access settings updated.")
            st.rerun()
        except Exception as exc:
            show_data_error(exc)

    actions = st.container(horizontal=True, vertical_alignment="center")
    if store.supports_passwords and actions.button("Reset temporary password", icon=":material/password:"):
        try:
            temporary_password = store.reset_temporary_password(admin, selected.user_id)
            st.session_state["issued_temporary_credential"] = {
                "email": selected.email,
                "password": temporary_password,
            }
            st.rerun()
        except Exception as exc:
            show_data_error(exc)
    confirm_delete = actions.checkbox(
        "Confirm deletion", key="admin_confirm_user_delete", disabled=selected.user_id == admin.user_id
    )
    if actions.button(
        "Delete user",
        icon=":material/delete:",
        disabled=selected.user_id == admin.user_id or not confirm_delete,
    ):
        try:
            store.delete_user(admin, selected.user_id)
            st.success("User deleted.")
            st.rerun()
        except Exception as exc:
            show_data_error(exc)

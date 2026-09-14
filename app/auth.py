"""Shared Streamlit login, session, page-guard, and repository setup helpers."""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from app.security import (
    AuthenticationError,
    AuthorizationError,
    Permission,
    AuthStore,
    SQLiteAuthStore,
    User,
    UserValidationError,
    has_permission,
    require_permission as enforce_permission,
)
from app.runtime import RuntimeMode, current_runtime_mode, snowflake_viewer_email
from app.services.authorized_repository import AuthorizedRepository


SESSION_TOKEN_KEY = "efns_auth_session_token"


def _default_database_path() -> str:
    root = Path(__file__).resolve().parents[1]
    return os.getenv("EFNS_AUTH_DB", str(root / ".local" / "efns_auth.db"))


@st.cache_resource
def _cached_auth_store(database_path: str) -> SQLiteAuthStore:
    return SQLiteAuthStore(database_path)


def get_auth_store() -> AuthStore:
    if current_runtime_mode() == RuntimeMode.SNOWFLAKE:
        from app.snowflake_security import SnowflakeAuthStore

        store = st.session_state.get("_snowflake_auth_store")
        if not isinstance(store, SnowflakeAuthStore):
            store = SnowflakeAuthStore()
            st.session_state["_snowflake_auth_store"] = store
        return store
    return _cached_auth_store(_default_database_path())


def current_user() -> User | None:
    if current_runtime_mode() == RuntimeMode.SNOWFLAKE:
        email = snowflake_viewer_email()
        return get_auth_store().resolve_identity(email) if email else None
    token = st.session_state.get(SESSION_TOKEN_KEY)
    user = get_auth_store().resolve_session(token)
    if token and user is None:
        st.session_state.pop(SESSION_TOKEN_KEY, None)
        st.session_state.pop("repo", None)
        st.session_state.pop("_base_repo", None)
    return user


def _logout() -> None:
    if current_runtime_mode() == RuntimeMode.SNOWFLAKE:
        return
    token = st.session_state.pop(SESSION_TOKEN_KEY, None)
    get_auth_store().logout(token)
    st.session_state.pop("repo", None)
    st.session_state.pop("_base_repo", None)
    st.query_params.clear()
    st.rerun()


def render_login() -> None:
    from app.ui import apply_theme, page_header

    apply_theme()
    page_header(
        "Sign in to EFNS",
        "Use an active internal @nsegg.ca prototype account.",
        "SECURE ACCESS",
    )
    with st.container(border=True):
        with st.form("efns_login_form"):
            email = st.text_input("Email address", key="auth_login_email")
            password = st.text_input("Password", type="password", key="auth_login_password")
            submitted = st.form_submit_button(
                "Sign in", type="primary", icon=":material/login:", width="stretch"
            )
        if submitted:
            try:
                _, token = get_auth_store().login(email, password)
                st.session_state[SESSION_TOKEN_KEY] = token
                st.session_state.pop("auth_login_password", None)
                st.rerun()
            except AuthenticationError:
                st.error("Invalid email or password, or the account is inactive.")
    st.caption("Prototype authentication is local to this deployment and will be replaced by an organizational identity provider.")


def render_snowflake_access_denied() -> None:
    from app.ui import apply_theme, page_header

    apply_theme()
    page_header(
        "Access not provisioned",
        "EFNS uses your authenticated Snowflake viewer identity in this environment.",
        "SECURE ACCESS",
    )
    email = snowflake_viewer_email()
    if not email:
        st.error("Snowflake did not provide a viewer email. Ask an administrator to verify the Snowflake user profile.")
    elif not email.endswith("@nsegg.ca"):
        st.error("Only authenticated @nsegg.ca viewers may use EFNS.")
    else:
        st.error("Your EFNS application account is missing or inactive. Ask an EFNS Admin to provision access.")
    st.caption("Password sign-in is disabled inside Streamlit in Snowflake.")


def _render_required_password_change(user: User) -> None:
    from app.ui import apply_theme, page_header

    apply_theme()
    page_header(
        "Change temporary password",
        "Set a new password before opening EFNS application pages.",
        "SECURE ACCESS",
    )
    with st.container(border=True):
        with st.form("efns_change_password_form"):
            password = st.text_input("New password", type="password", key="auth_new_password")
            confirmation = st.text_input("Confirm new password", type="password", key="auth_confirm_password")
            submitted = st.form_submit_button(
                "Change password", type="primary", icon=":material/password:", width="stretch"
            )
        if submitted:
            if password != confirmation:
                st.error("The password confirmation does not match.")
            else:
                try:
                    get_auth_store().change_own_password(user, password)
                    st.session_state.pop("auth_new_password", None)
                    st.session_state.pop("auth_confirm_password", None)
                    st.success("Password changed.")
                    st.rerun()
                except UserValidationError as exc:
                    st.error(str(exc))
        if st.button("Sign out", icon=":material/logout:", key="temporary_password_logout"):
            _logout()


def require_authenticated() -> User:
    try:
        user = current_user()
    except Exception as exc:
        if current_runtime_mode() != RuntimeMode.SNOWFLAKE:
            raise
        from app.ui import apply_theme, page_header

        apply_theme()
        page_header(
            "Authorization unavailable",
            "EFNS could not verify your application access in Snowflake.",
            "SECURE ACCESS",
        )
        st.error("Ask an EFNS administrator to verify the SECURITY and APP schema setup and application-owner grants.")
        st.caption(f"Reference: {type(exc).__name__}")
        st.stop()
    if user is None:
        if current_runtime_mode() == RuntimeMode.SNOWFLAKE:
            render_snowflake_access_denied()
        else:
            render_login()
        st.stop()
    if user.must_change_password and get_auth_store().supports_passwords:
        _render_required_password_change(user)
        st.stop()
    return user


def require_page_permission(permission: Permission) -> User:
    user = require_authenticated()
    try:
        enforce_permission(user, permission)
    except AuthorizationError:
        from app.ui import apply_theme, page_header

        apply_theme()
        page_header(
            "Access denied",
            "Your current role does not allow access to this page.",
            "SECURE ACCESS",
        )
        if st.button("Return to dashboard", icon=":material/home:"):
            st.switch_page(os.getenv("EFNS_ENTRYPOINT", "Home.py"))
        st.stop()
    ensure_authorized_repository(user)
    return user


def require_operational_page() -> User:
    user = require_page_permission(Permission.VIEW_DATA)
    view = str(st.query_params.get("view", "list")).lower()
    if view == "new":
        require_page_permission(Permission.CREATE_DATA)
    elif view == "edit":
        require_page_permission(Permission.UPDATE_DATA)
    return user


def can_current(permission: Permission) -> bool:
    user = current_user()
    return bool(user and has_permission(user, permission))


def ensure_authorized_repository(user: User | None = None):
    from data.repositories import get_repository

    user = user or require_authenticated()
    current = st.session_state.get("repo")
    base = st.session_state.get("_base_repo")
    if base is None:
        base = current.repository if isinstance(current, AuthorizedRepository) else current
        base = base or get_repository()
        st.session_state["_base_repo"] = base
    if not isinstance(current, AuthorizedRepository) or current.actor != user or current.repository is not base:
        current = AuthorizedRepository(base, get_auth_store(), user)
        st.session_state["repo"] = current
    return current


def render_user_sidebar(user: User) -> None:
    st.markdown(f"**{user.display_name}**")
    st.caption(f"{user.email} · {user.role.value}")
    if get_auth_store().supports_passwords:
        if st.button("Sign out", icon=":material/logout:", key="efns_logout", width="stretch"):
            _logout()
    else:
        st.caption("Identity supplied by Snowflake")

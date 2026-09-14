"""User-triggered repository and Snowflake diagnostics."""

from __future__ import annotations

import streamlit as st

from app.auth import require_page_permission
from app.security import Permission

from app.ui import apply_theme, page_header, section_intro, show_data_error
from data.connection import LazySqlExecutor, SnowflakeSettings, streamlit_connection_configured
from data.repositories import get_repository


require_page_permission(Permission.VIEW_DIAGNOSTICS)
apply_theme()
if "repo" not in st.session_state:
    st.session_state.repo = get_repository()
repo = st.session_state.repo
repository_name = getattr(repo, "repository_name", type(repo).__name__.replace("Repository", ""))
is_snowflake = repository_name == "Snowflake"

page_header(
    "System Status",
    "Review the active data mode and run an explicit, credential-safe connection check.",
    "ADMINISTRATION",
)

settings = SnowflakeSettings.from_env()
executor = getattr(repo, "executor", None)
runtime = getattr(executor, "runtime_name", None) or ("Local Streamlit" if not is_snowflake else "Not connected")
if is_snowflake and isinstance(executor, LazySqlExecutor) and not executor.is_resolved:
    runtime = "Auto-detect on first use"

status_columns = st.columns(3)
status_columns[0].metric("Repository", repository_name)
status_columns[1].metric("Runtime", runtime)
if not is_snowflake:
    config_status = "Not required"
elif settings.configured or streamlit_connection_configured():
    config_status = "Ready"
else:
    config_status = "Not configured"
status_columns[2].metric("Snowflake configuration", config_status)

if not is_snowflake:
    st.warning("Mock data is held in the current Streamlit session and resets when the session is replaced.")
else:
    st.info("No connection is opened by this page until Check connection is selected.")

section_intro("Connection diagnostics", "This check runs SELECT CURRENT_VERSION() and does not write data.")
if st.button("Check connection", icon=":material/cable:", type="primary", disabled=not is_snowflake):
    try:
        repo.check_connection()
        st.success(f"Snowflake connection is ready. Runtime: {repo.runtime_name}.")
    except Exception as exc:
        show_data_error(exc)

section_intro("Configuration methods")
st.markdown(
    "Use a named Snowflake connection, SSO/external browser, or key-pair authentication. "
    "Username and password remain an optional local development method. Secrets and full connection errors are never displayed here."
)

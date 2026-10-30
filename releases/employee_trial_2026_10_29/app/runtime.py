"""Runtime detection shared by authentication and repository selection.

The deployed app uses Snowflake's authenticated viewer identity. Local
development remains explicit and defaults to the existing mock/SQLite mode.
"""

from __future__ import annotations

from enum import StrEnum
import os


class RuntimeMode(StrEnum):
    LOCAL = "local"
    SNOWFLAKE = "snowflake"


class RuntimeConfigurationError(RuntimeError):
    """Raised when the requested EFNS runtime mode is invalid."""


def snowflake_viewer_email(streamlit_module=None) -> str | None:
    """Return the Streamlit in Snowflake viewer email without opening SQL."""
    try:
        if streamlit_module is None:
            import streamlit as streamlit_module
        value = getattr(streamlit_module.user, "email", None)
    except Exception:
        return None
    normalized = str(value or "").strip().casefold()
    return normalized or None


def active_warehouse_session_available() -> bool:
    """Detect Streamlit in Snowflake without issuing a SQL statement."""
    try:
        from snowflake.snowpark.context import get_active_session

        return get_active_session() is not None
    except Exception:
        return False


def resolve_runtime_mode(
    configured: str | None = None,
    viewer_email: str | None = None,
    warehouse_session: bool | None = None,
) -> RuntimeMode:
    """Resolve ``local``, ``snowflake``, or automatic runtime selection."""
    selected = str(configured if configured is not None else os.getenv("EFNS_RUNTIME_MODE", "auto")).strip().lower()
    if selected == "auto":
        identity = viewer_email if viewer_email is not None else snowflake_viewer_email()
        active_session = active_warehouse_session_available() if warehouse_session is None else warehouse_session
        return RuntimeMode.SNOWFLAKE if identity and active_session else RuntimeMode.LOCAL
    try:
        return RuntimeMode(selected)
    except ValueError as exc:
        raise RuntimeConfigurationError(
            "EFNS_RUNTIME_MODE must be 'local', 'snowflake', or 'auto'."
        ) from exc


def current_runtime_mode() -> RuntimeMode:
    return resolve_runtime_mode()

"""Shared record navigation and command-bar helpers."""

from __future__ import annotations

from dataclasses import dataclass
import inspect
from pathlib import Path

import pandas as pd
import streamlit as st

from app.auth import can_current
from app.security import Permission


VALID_VIEWS = {"list", "new", "detail", "edit"}
DISPLAY_TIMEZONE = "America/Halifax"
DISPLAY_TIMEZONE_LABEL = "America/Halifax"
_ACTIVE_SCOPE_KEY = "_efns_active_record_scope"
_PAGE_FILES = {
    "Accounts_&_Facilities": "3_Accounts_Facilities_Flocks.py",
    "Facilities": "11_Facilities.py",
    "Facility_Details": "13_Facility_Details.py",
    "Flocks": "5_Flocks.py",
    "Flock_Transactions": "6_Flock_Transactions.py",
    "Quota_Registrations": "7_Quota_Registrations.py",
    "Quota_Transactions": "8_Quota_Transactions.py",
    "Salmonella_Tests": "9_Salmonella_Tests.py",
}


def _caller_scope() -> str:
    frame = inspect.currentframe()
    while frame:
        filename = Path(frame.f_code.co_filename)
        if filename.parent.name == "pages":
            return filename.stem
        frame = frame.f_back
    return "application"


def _view_key(scope: str, name: str) -> str:
    return f"_efns_record_{scope}_{name}"


@dataclass(frozen=True)
class RecordView:
    name: str
    record_id: str | None = None


def read_record_view() -> RecordView:
    """Read page-local record state without constructing browser routes."""
    scope = _caller_scope()
    st.session_state[_ACTIVE_SCOPE_KEY] = scope
    name = str(st.session_state.get(_view_key(scope, "view"), "list")).lower()
    if name not in VALID_VIEWS:
        name = "list"
    record_id = st.session_state.get(_view_key(scope, "id"))
    if name in {"detail", "edit"} and not record_id:
        name = "list"
    return RecordView(name, str(record_id) if record_id else None)


def open_view(name: str, record_id: str | None = None, **parameters) -> None:
    """Navigate inside the registered page using session state only."""
    scope = st.session_state.get(_ACTIVE_SCOPE_KEY) or _caller_scope()
    selected_view = name if name in VALID_VIEWS else "list"
    st.session_state[_view_key(scope, "view")] = selected_view
    if record_id:
        st.session_state[_view_key(scope, "id")] = str(record_id)
    else:
        st.session_state.pop(_view_key(scope, "id"), None)
    parameter_prefix = _view_key(scope, "parameter_")
    for key in [key for key in st.session_state if key.startswith(parameter_prefix)]:
        st.session_state.pop(key, None)
    for key, value in parameters.items():
        if value is not None and value != "":
            st.session_state[f"{parameter_prefix}{key}"] = value
    st.rerun()


def back_to_list() -> None:
    open_view("list")


def view_parameter(name: str, default=None):
    """Return a page-local parameter set by an internal registered-page action."""
    scope = st.session_state.get(_ACTIVE_SCOPE_KEY) or _caller_scope()
    return st.session_state.get(f"{_view_key(scope, 'parameter_')}{name}", default)


def open_module(
    page_slug: str,
    view: str = "list",
    record_id: str | None = None,
    **parameters,
) -> None:
    """Switch registered pages without creating a browser URL or href."""
    filename = _PAGE_FILES.get(page_slug)
    if not filename:
        raise ValueError("Unknown application page.")
    scope = Path(filename).stem
    st.session_state[_view_key(scope, "view")] = view if view in VALID_VIEWS else "list"
    if record_id:
        st.session_state[_view_key(scope, "id")] = str(record_id)
    else:
        st.session_state.pop(_view_key(scope, "id"), None)
    parameter_prefix = _view_key(scope, "parameter_")
    for key in [key for key in st.session_state if key.startswith(parameter_prefix)]:
        st.session_state.pop(key, None)
    for key, value in parameters.items():
        if value is not None and value != "":
            st.session_state[f"{parameter_prefix}{key}"] = value
    st.switch_page(f"pages/{filename}")


def ensure_record_form_state(prefix: str, record_id: str | None) -> None:
    """Discard widget values when a form starts editing a different record."""
    marker = f"{prefix}loaded_record_id"
    identity = str(record_id or "__new__")
    if st.session_state.get(marker) != identity:
        clear_keys = [key for key in st.session_state if key.startswith(prefix)]
        for key in clear_keys:
            st.session_state.pop(key, None)
        st.session_state[marker] = identity


def to_display_timestamp(value):
    """Interpret persisted timestamps as UTC and convert them for EFNS users."""
    converted = pd.to_datetime(value, errors="coerce", utc=True)
    return converted if pd.isna(converted) else converted.tz_convert(DISPLAY_TIMEZONE)


def format_timestamp(value) -> str:
    converted = to_display_timestamp(value)
    if pd.isna(converted):
        return "Not available"
    return f"{converted.strftime('%Y-%m-%d %H:%M %Z')} ({DISPLAY_TIMEZONE_LABEL})"


def timestamp_column(label: str):
    """Use an explicit timezone and label for every timestamp data column."""
    return st.column_config.DatetimeColumn(
        f"{label} ({DISPLAY_TIMEZONE_LABEL})",
        format="YYYY-MM-DD HH:mm",
        timezone=DISPLAY_TIMEZONE,
    )


def timestamp_columns(columns) -> dict:
    """Build explicit Halifax display configuration for timestamp fields."""
    configured = {}
    for column in columns:
        name = str(column)
        if name.endswith(("_AT", "_ON", " At", " On")) or name == "UPLOAD_TIMESTAMP":
            label = name.replace("_", " ").title()
            configured[name] = timestamp_column(label)
    return configured


def selected_row_index(key: str) -> int | None:
    """Return the prior rerun's single selected dataframe row."""
    state = st.session_state.get(key)
    selection = getattr(state, "selection", None)
    rows = getattr(selection, "rows", []) if selection is not None else []
    return int(rows[0]) if rows else None


def list_command_bar(prefix: str, selected: bool = False) -> str | None:
    """Render a Dynamics-like list command bar and return the chosen action."""
    st.caption("Select a record to view its details.")
    action = None
    with st.container(border=True, horizontal=True, vertical_alignment="center"):
        if st.button("New", icon=":material/add:", type="primary", key=f"{prefix}_new", disabled=not can_current(Permission.CREATE_DATA)):
            action = "new"
        if st.button("View", icon=":material/visibility:", key=f"{prefix}_view", disabled=not selected):
            action = "view"
        if st.button("Delete", icon=":material/delete:", disabled=not selected or not can_current(Permission.DELETE_DATA), key=f"{prefix}_delete"):
            action = "delete"
        if st.button("Refresh", icon=":material/refresh:", key=f"{prefix}_refresh"):
            action = "refresh"
    return action


def record_command_bar(prefix: str, view: str, allow_delete: bool = True) -> str | None:
    """Render Back/Edit/Save/Cancel/Delete actions for record pages."""
    action = None
    with st.container(border=True, horizontal=True, vertical_alignment="center"):
        if st.button("Back", icon=":material/arrow_back:", key=f"{prefix}_back"):
            action = "back"
        if view == "detail" and st.button("Edit", icon=":material/edit:", type="primary", key=f"{prefix}_edit", disabled=not can_current(Permission.UPDATE_DATA)):
            action = "edit"
        if view == "detail" and st.button("Refresh", icon=":material/refresh:", key=f"{prefix}_refresh"):
            action = "refresh"
        if view in {"new", "edit"}:
            if st.button("Save", icon=":material/save:", type="primary", key=f"{prefix}_save"):
                action = "save"
            if st.button("Cancel", icon=":material/close:", key=f"{prefix}_cancel"):
                action = "cancel"
        if view in {"detail", "edit"} and allow_delete:
            if st.button("Delete", icon=":material/delete:", key=f"{prefix}_delete", disabled=not can_current(Permission.DELETE_DATA)):
                action = "delete"
    return action

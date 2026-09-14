"""Shared record navigation and command-bar helpers."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote, urlencode, urlsplit, urlunsplit

import pandas as pd
import streamlit as st

from app.auth import can_current
from app.security import Permission


VALID_VIEWS = {"list", "new", "detail", "edit"}
DISPLAY_TIMEZONE = "America/Halifax"
DISPLAY_TIMEZONE_LABEL = "America/Halifax"


def _module_path(current_path: str, page_slug: str) -> str:
    """Preserve Snowflake's /!/ multipage prefix when building record links."""
    encoded = quote(page_slug, safe="_&-")
    if "/!/" in current_path:
        app_root = current_path.split("/!/", 1)[0]
        return f"{app_root}/!/{encoded}"
    return f"/{encoded}"


def _url_query(current_path: str, values: dict[str, str]) -> str:
    """Encode manual Snowflake links with its browser query-key prefix."""
    prefix = "streamlit-" if "/!/" in current_path else ""
    return urlencode({f"{prefix}{key}": value for key, value in values.items()})


def _snowflake_fragment_route(parsed) -> str | None:
    route = str(parsed.fragment or "").split("?", 1)[0].split("#", 1)[0]
    return route if "/!/" in route else None


@dataclass(frozen=True)
class RecordView:
    name: str
    record_id: str | None = None


def read_record_view() -> RecordView:
    """Read a stable list/new/detail/edit state from the current URL."""
    name = str(st.query_params.get("view", "list")).lower()
    if name not in VALID_VIEWS:
        name = "list"
    record_id = st.query_params.get("id")
    if name in {"detail", "edit"} and not record_id:
        name = "list"
    return RecordView(name, str(record_id) if record_id else None)


def open_view(name: str, record_id: str | None = None, **parameters) -> None:
    """Navigate within the current module and preserve the state on refresh."""
    st.query_params.clear()
    st.query_params["view"] = name if name in VALID_VIEWS else "list"
    if record_id:
        st.query_params["id"] = str(record_id)
    for key, value in parameters.items():
        if value is not None and value != "":
            st.query_params[key] = str(value)
    st.rerun()


def back_to_list() -> None:
    open_view("list")


def current_page_url(record_id: str, label: str, view: str = "detail") -> str:
    """Build an absolute link to a record on the current Streamlit page."""
    raw_url = str(getattr(st.context, "url", "") or "")
    parsed = urlsplit(raw_url)
    fragment_route = _snowflake_fragment_route(parsed)
    display_label = str(label or record_id).replace("#", " ")
    if fragment_route:
        query = _url_query(fragment_route, {"view": view, "id": str(record_id)})
        fragment = f"{fragment_route}?{query}#{display_label}"
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, fragment))
    base = raw_url.split("?", 1)[0].split("#", 1)[0]
    if not base or base.lower() == "none":
        base = "http://localhost:8501"
    query = _url_query(urlsplit(base).path, {"view": view, "id": str(record_id)})
    return f"{base}?{query}#{display_label}"


def module_url(page_slug: str, record_id: str, label: str) -> str:
    """Build an absolute record URL for another registered st.navigation page."""
    raw_url = str(getattr(st.context, "url", "") or "http://localhost:8501")
    parsed = urlsplit(raw_url)
    if not parsed.scheme or not parsed.netloc:
        parsed = urlsplit("http://localhost:8501")
    display_label = str(label or record_id).replace("#", " ")
    fragment_route = _snowflake_fragment_route(parsed)
    if fragment_route:
        path = _module_path(fragment_route, page_slug)
        query = _url_query(fragment_route, {"view": "detail", "id": str(record_id)})
        fragment = f"{path}?{query}#{display_label}"
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, fragment))
    path = _module_path(parsed.path, page_slug)
    query = _url_query(parsed.path, {"view": "detail", "id": str(record_id)})
    return urlunsplit((parsed.scheme, parsed.netloc, path, query, display_label))


def module_view_url(page_slug: str, view: str, record_id: str | None = None, **parameters) -> str:
    """Build an absolute list/new/detail/edit URL for another module."""
    raw_url = str(getattr(st.context, "url", "") or "http://localhost:8501")
    parsed = urlsplit(raw_url)
    if not parsed.scheme or not parsed.netloc:
        parsed = urlsplit("http://localhost:8501")
    query = {"view": view if view in VALID_VIEWS else "list"}
    if record_id:
        query["id"] = str(record_id)
    query.update({key: str(value) for key, value in parameters.items() if value is not None and value != ""})
    fragment_route = _snowflake_fragment_route(parsed)
    if fragment_route:
        fragment = f"{_module_path(fragment_route, page_slug)}?{_url_query(fragment_route, query)}"
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, fragment))
    return urlunsplit((parsed.scheme, parsed.netloc, _module_path(parsed.path, page_slug), _url_query(parsed.path, query), ""))


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


def selected_row_index(key: str) -> int | None:
    """Return the prior rerun's single selected dataframe row."""
    state = st.session_state.get(key)
    selection = getattr(state, "selection", None)
    rows = getattr(selection, "rows", []) if selection is not None else []
    return int(rows[0]) if rows else None


def list_command_bar(prefix: str, selected: bool = False) -> str | None:
    """Render a Dynamics-like list command bar and return the chosen action."""
    action = None
    with st.container(border=True, horizontal=True, vertical_alignment="center"):
        if st.button("New", icon=":material/add:", type="primary", key=f"{prefix}_new", disabled=not can_current(Permission.CREATE_DATA)):
            action = "new"
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

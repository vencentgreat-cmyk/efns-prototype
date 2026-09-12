"""Shared record navigation and command-bar helpers."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote, urlencode, urlsplit, urlunsplit

import pandas as pd
import streamlit as st


VALID_VIEWS = {"list", "new", "detail", "edit"}


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
    base = raw_url.split("?", 1)[0].split("#", 1)[0]
    if not base or base.lower() == "none":
        base = "http://localhost:8501"
    query = urlencode({"view": view, "id": str(record_id)})
    display_label = str(label or record_id).replace("#", " ")
    return f"{base}?{query}#{display_label}"


def module_url(page_slug: str, record_id: str, label: str) -> str:
    """Build an absolute record URL for another registered st.navigation page."""
    raw_url = str(getattr(st.context, "url", "") or "http://localhost:8501")
    parsed = urlsplit(raw_url)
    if not parsed.scheme or not parsed.netloc:
        parsed = urlsplit("http://localhost:8501")
    path = f"/{quote(page_slug, safe='_&-')}"
    query = urlencode({"view": "detail", "id": str(record_id)})
    display_label = str(label or record_id).replace("#", " ")
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
    return urlunsplit((parsed.scheme, parsed.netloc, f"/{quote(page_slug, safe='_&-')}", urlencode(query), ""))


def ensure_record_form_state(prefix: str, record_id: str | None) -> None:
    """Discard widget values when a form starts editing a different record."""
    marker = f"{prefix}loaded_record_id"
    identity = str(record_id or "__new__")
    if st.session_state.get(marker) != identity:
        clear_keys = [key for key in st.session_state if key.startswith(prefix)]
        for key in clear_keys:
            st.session_state.pop(key, None)
        st.session_state[marker] = identity


def format_timestamp(value) -> str:
    converted = pd.to_datetime(value, errors="coerce")
    return "Not available" if pd.isna(converted) else converted.strftime("%Y-%m-%d %H:%M")


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
        if st.button("New", icon=":material/add:", type="primary", key=f"{prefix}_new"):
            action = "new"
        if st.button("Delete", icon=":material/delete:", disabled=not selected, key=f"{prefix}_delete"):
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
        if view == "detail" and st.button("Edit", icon=":material/edit:", type="primary", key=f"{prefix}_edit"):
            action = "edit"
        if view == "detail" and st.button("Refresh", icon=":material/refresh:", key=f"{prefix}_refresh"):
            action = "refresh"
        if view in {"new", "edit"}:
            if st.button("Save", icon=":material/save:", type="primary", key=f"{prefix}_save"):
                action = "save"
            if st.button("Cancel", icon=":material/close:", key=f"{prefix}_cancel"):
                action = "cancel"
        if view in {"detail", "edit"} and allow_delete:
            if st.button("Delete", icon=":material/delete:", key=f"{prefix}_delete"):
                action = "delete"
    return action

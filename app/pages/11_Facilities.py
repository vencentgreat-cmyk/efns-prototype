"""Facility list and record workspace."""

from __future__ import annotations

import datetime as dt

import pandas as pd
import streamlit as st

from app.navigation import current_page_url, format_timestamp, list_command_bar, module_url, open_view, read_record_view, record_command_bar, selected_row_index
from app.ui import apply_theme, clear_widget_prefix, page_header, section_intro
from data.constants import FACILITY_STATUSES
from data.repositories import get_repository


apply_theme()
if "repo" not in st.session_state:
    st.session_state.repo = get_repository()
repo = st.session_state.repo
view = read_record_view()
facilities = repo.get_facilities()
accounts = repo.get_accounts()
account_names = {row.ACCOUNT_ID: row.ORGANIZATION_NAME for row in accounts.itertuples()}
account_options = {f"{row.ORGANIZATION_NAME} · {row.REGISTRATION_NUMBER or row.ACCOUNT_ID[:8]}": row.ACCOUNT_ID for row in accounts.itertuples()}
FACILITY_TYPES = ("Pullet", "Layer", "Other")


def option_index(options, value):
    return options.index(value) if value in options else 0


def label_for_id(mapping, value):
    return next((label for label, record_id in mapping.items() if record_id == value), next(iter(mapping), None))


def get_facility(record_id):
    match = facilities[facilities["FACILITY_ID"] == record_id]
    return match.iloc[0].to_dict() if not match.empty else None


if view.name == "list":
    page_header("Active Facilities", "Search and maintain facilities and their physical details.", "FACILITY MANAGEMENT")
    selected_index = selected_row_index("facility_list_grid")
    row_ids = st.session_state.get("facility_list_row_ids", [])
    selected_id = row_ids[selected_index] if selected_index is not None and selected_index < len(row_ids) else None
    action = list_command_bar("facility_list", selected=bool(selected_id))
    if action == "new": open_view("new")
    if action == "refresh": clear_widget_prefix("facility_filter_"); st.rerun()
    if action == "delete" and selected_id: st.session_state.facility_delete_pending = selected_id
    if st.session_state.get("facility_delete_pending"):
        with st.container(border=True):
            st.warning("Delete the selected Facility? Related Details or Flocks will block deletion.")
            with st.container(horizontal=True):
                if st.button("Confirm delete", type="primary", key="facility_confirm_delete"):
                    try:
                        repo.delete_facility(st.session_state.facility_delete_pending)
                        st.session_state.pop("facility_delete_pending", None); st.rerun()
                    except ValueError as exc: st.error(str(exc))
                if st.button("Cancel", key="facility_cancel_delete"):
                    st.session_state.pop("facility_delete_pending", None); st.rerun()
    filters = st.columns([2, 1, 1])
    keyword = filters[0].text_input("Filter by keyword", placeholder="Facility or Account name", key="facility_filter_keyword")
    status = filters[1].selectbox("Status", ["All", *FACILITY_STATUSES], key="facility_filter_status")
    facility_type = filters[2].selectbox("Facility type", ["All", *FACILITY_TYPES], key="facility_filter_type")
    display = facilities.copy()
    display["ACCOUNT_NAME"] = display["ACCOUNT_ID"].map(account_names)
    if keyword:
        display = display[display[["FACILITY_NAME", "ACCOUNT_NAME"]].fillna("").astype(str).apply(lambda col: col.str.contains(keyword, case=False, regex=False)).any(axis=1)]
    if status != "All": display = display[display["STATUS"] == status]
    if facility_type != "All": display = display[display["FACILITY_TYPE"] == facility_type]
    if display.empty:
        st.info("No Facilities match the current filters.")
    else:
        display = display.reset_index(drop=True)
        display["FACILITY_LINK"] = display.apply(lambda row: current_page_url(row["FACILITY_ID"], row["FACILITY_NAME"]), axis=1)
        display["ACCOUNT_LINK"] = display.apply(lambda row: module_url("Accounts_&_Facilities", row["ACCOUNT_ID"], row["ACCOUNT_NAME"]), axis=1)
        st.session_state.facility_list_row_ids = display["FACILITY_ID"].tolist()
        st.dataframe(display[["FACILITY_LINK", "ACCOUNT_LINK", "FACILITY_TYPE", "STATUS", "ACTIVATION_DATE", "CLOSURE_DATE", "CREATED_AT"]], width="stretch", height=540, hide_index=True, on_select="rerun", selection_mode="single-row", key="facility_list_grid", column_config={"FACILITY_LINK": st.column_config.LinkColumn("Facility Name", display_text=r".*#(.*)$"), "ACCOUNT_LINK": st.column_config.LinkColumn("Account", display_text=r".*#(.*)$"), "CREATED_AT": st.column_config.DatetimeColumn("Created On", format="YYYY-MM-DD HH:mm")})
else:
    current = get_facility(view.record_id) if view.record_id else None
    if view.name in {"detail", "edit"} and current is None:
        st.error("The requested Facility could not be found.")
        if st.button("Back to Facilities"): open_view("list")
        st.stop()
    is_form = view.name in {"new", "edit"}
    page_header("New Facility" if view.name == "new" else current["FACILITY_NAME"], "Facility record and related physical details.", "FACILITY RECORD")
    action = record_command_bar("facility_record", view.name)
    if action in {"back", "cancel"}: open_view("detail", view.record_id) if action == "cancel" and view.record_id else open_view("list")
    if action == "edit": clear_widget_prefix("facility_form_"); open_view("edit", view.record_id)
    if action == "delete" and view.record_id:
        try: repo.delete_facility(view.record_id); open_view("list")
        except ValueError as exc: st.error(str(exc))
    if not is_form:
        st.caption(f"Created On: {format_timestamp(current.get('CREATED_AT'))} · Updated On: {format_timestamp(current.get('UPDATED_AT'))}")
        summary, related = st.tabs(["Summary", "Related Records"])
        with summary:
            with st.container(border=True):
                left, right = st.columns(2)
                left.markdown(f"**Facility Name**  \n{current.get('FACILITY_NAME')}")
                left.markdown(f"**Account**  \n{account_names.get(current.get('ACCOUNT_ID'), 'Unknown')}")
                left.markdown(f"**Type**  \n{current.get('FACILITY_TYPE') or '—'}")
                right.markdown(f"**Status**  \n{current.get('STATUS')}")
                right.markdown(f"**Activation Date**  \n{current.get('ACTIVATION_DATE') or '—'}")
                right.markdown(f"**Closure Date**  \n{current.get('CLOSURE_DATE') or '—'}")
        with related:
            for heading, frame, key, label, slug in (
                ("Facility Details", repo.get_facility_details(view.record_id), "FACILITY_ID", "DETAIL_NAME", "Facilities"),
                ("Flocks", repo.get_flocks(facility_id=view.record_id), "FLOCK_ID", "FLOCK_NUMBER", "Flocks"),
                ("Salmonella Tests", repo.get_salmonella_tests(facility_id=view.record_id), "SALMONELLA_TEST_ID", "PERMIT_NUMBER", "Salmonella_Tests"),
            ):
                section_intro(heading)
                if frame.empty: st.info(f"No related {heading}.")
                else:
                    frame = frame.copy(); frame["RECORD_LINK"] = frame.apply(lambda row: module_url(slug, row[key], row.get(label) or row[key]), axis=1)
                    columns = [column for column in frame.columns if column not in {key, "RECORD_LINK", "CREATED_AT", "UPDATED_AT"}][:5]
                    st.dataframe(frame[["RECORD_LINK", *columns]], width="stretch", hide_index=True, column_config={"RECORD_LINK": st.column_config.LinkColumn("Record", display_text=r".*#(.*)$")})
    else:
        current = current or {}
        with st.container(border=True):
            left, right = st.columns(2)
            facility_name = left.text_input("Facility Name *", value=str(current.get("FACILITY_NAME") or ""), key="facility_form_name")
            account_label = left.selectbox("Account *", list(account_options), index=option_index(list(account_options), label_for_id(account_options, current.get("ACCOUNT_ID"))), key="facility_form_account")
            facility_type = left.selectbox("Facility Type", FACILITY_TYPES, index=option_index(list(FACILITY_TYPES), current.get("FACILITY_TYPE")), key="facility_form_type")
            status = left.selectbox("Status", FACILITY_STATUSES, index=option_index(list(FACILITY_STATUSES), current.get("STATUS")), key="facility_form_status")
            activation = right.date_input("Activation Date", value=current.get("ACTIVATION_DATE"), key="facility_form_activation")
            construction = right.date_input("Construction Date", value=current.get("CONSTRUCTION_DATE"), key="facility_form_construction")
            closure = right.date_input("Closure Date", value=current.get("CLOSURE_DATE"), key="facility_form_closure")
            inactive = right.date_input("Inactive Date", value=current.get("INACTIVE_DATE"), key="facility_form_inactive")
        if action == "save":
            if not facility_name.strip(): st.error("Facility Name is required.")
            else:
                record = {"FACILITY_ID": view.record_id, "FACILITY_NAME": facility_name.strip(), "ACCOUNT_ID": account_options[account_label], "FACILITY_TYPE": facility_type, "STATUS": status, "ACTIVATION_DATE": activation, "CONSTRUCTION_DATE": construction, "CLOSURE_DATE": closure, "INACTIVE_DATE": inactive}
                if not view.record_id: record.pop("FACILITY_ID")
                saved_id = repo.upsert_facility(record); clear_widget_prefix("facility_form_"); open_view("detail", saved_id)

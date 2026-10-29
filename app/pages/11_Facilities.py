"""Facility list and record workspace."""

from __future__ import annotations

from app.services.form_safety import open_saved_record, stored_index, capture_form, preserve_form, save_form, stored_options, start_new_form, begin_form, field_changed, delete_confirmation
from data.producer_identity import text as stored_text
from data.business_time import halifax_today

import datetime as dt

import pandas as pd
import uuid
from data.repositories.continuity import changed_attributes
import streamlit as st

from app.auth import require_operational_page
from app.navigation import format_timestamp, list_command_bar, open_module, open_view, read_record_view, record_command_bar, related_records_table, saved_view_selector, selected_row_index, timestamp_column
from app.ui import apply_theme, clear_widget_prefix, optional_form_date, page_header, section_intro, show_data_error
from data.repositories.base import RepositoryError
from data.constants import FACILITY_STATUSES
from data.repositories import get_repository


require_operational_page()
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
    page_header("Facilities", "Search and maintain facilities and their physical details.", "FACILITY MANAGEMENT")
    statuses, _ = saved_view_selector("FACILITY", "Facilities", key="facility_saved_view", selection_keys=("facility_list_grid", "facility_list_row_ids", "facility_delete_pending"))
    selected_index = selected_row_index("facility_list_grid")
    row_ids = st.session_state.get("facility_list_row_ids", [])
    selected_id = row_ids[selected_index] if selected_index is not None and selected_index < len(row_ids) else None
    action = list_command_bar("facility_list", selected=bool(selected_id))
    if action == "view" and selected_id: open_view("detail", selected_id)
    if action == "new": start_new_form('facility_form_'); open_view("new")
    if action == "refresh": clear_widget_prefix("facility_filter_"); st.rerun()
    if action == "delete" and selected_id: st.session_state['facility_form___delete_pending']=selected_id
    filters = st.columns([2, 1])
    keyword = filters[0].text_input("Filter by keyword", placeholder="Facility or Account name", key="facility_filter_keyword")
    facility_type = filters[1].selectbox("Facility type", ["All", *FACILITY_TYPES], key="facility_filter_type")
    display = repo.get_facilities(statuses=statuses).copy()
    display["ACCOUNT_NAME"] = display["ACCOUNT_ID"].map(account_names)
    if keyword:
        display = display[display[["FACILITY_NAME", "ACCOUNT_NAME"]].fillna("").astype(str).apply(lambda col: col.str.contains(keyword, case=False, regex=False)).any(axis=1)]
    if facility_type != "All": display = display[display["FACILITY_TYPE"] == facility_type]
    st.caption(f"{len(display):,} facility record(s) in this view")
    if display.empty:
        st.info("No Facilities match the current filters.")
    else:
        display = display.reset_index(drop=True)
        st.session_state.facility_list_row_ids = display["FACILITY_ID"].tolist()
        st.dataframe(display[["FACILITY_NAME", "ACCOUNT_NAME", "FACILITY_TYPE", "STATUS", "ACTIVATION_DATE", "CLOSURE_DATE", "CREATED_AT"]], width="stretch", height=540, hide_index=True, on_select="rerun", selection_mode="single-row", key="facility_list_grid", column_config={"FACILITY_NAME": "Facility Name", "ACCOUNT_NAME": "Account", "CREATED_AT": timestamp_column("Created On")})
else:
    current = get_facility(view.record_id) if view.record_id else None
    if view.name in {"detail", "edit"} and current is None:
        st.error("The requested Facility could not be found.")
        if st.button("Back to Facilities"): open_view("list")
        st.stop()
    is_form = view.name in {"new", "edit"}
    page_header("New Facility" if view.name == "new" else current["FACILITY_NAME"], "Facility record and related physical details.", "FACILITY RECORD")
    action = record_command_bar("facility_record", view.name)
    if action in {"back", "cancel"}: start_new_form("facility_form_"); open_view("detail", view.record_id) if action == "cancel" and view.record_id else open_view("list")
    if action == "edit": start_new_form("facility_form_"); open_view("edit", view.record_id)
    if action == "delete" and view.record_id: st.session_state['facility_form___delete_pending']=view.record_id
    if not is_form:
        st.caption(f"Created On: {format_timestamp(current.get('CREATED_AT'))} · Updated On: {format_timestamp(current.get('UPDATED_AT'))}")
        summary, related = st.tabs(["Summary", "Related Records"])
        with summary:
            with st.container(border=True):
                left, right = st.columns(2)
                left.markdown(f"**Facility Name**  \n{current.get('FACILITY_NAME')}")
                left.markdown(f"**Account**  \n{account_names.get(current.get('ACCOUNT_ID'), 'Unknown')}")
                if current.get("ACCOUNT_ID") and left.button("View Account", key="facility_parent_account", icon=":material/account_circle:"):
                    open_module("Accounts_&_Facilities", "detail", current["ACCOUNT_ID"])
                left.markdown(f"**Type**  \n{current.get('FACILITY_TYPE') or '—'}")
                right.markdown(f"**Status**  \n{current.get('STATUS')}")
                right.markdown(f"**Activation Date**  \n{current.get('ACTIVATION_DATE') or '—'}")
                right.markdown(f"**Closure Date**  \n{current.get('CLOSURE_DATE') or '—'}")
        with related:
            if st.button("New Facility Detail", icon=":material/add:", type="primary"):
                open_module("Facility_Details", "new", facility_id=view.record_id)
            for heading, frame, key, label, slug in (
                ("Facility Details", repo.get_facility_details(view.record_id), "FACILITY_DETAIL_ID", "DETAIL_NAME", "Facility_Details"),
                ("Flocks", repo.get_flocks(facility_id=view.record_id), "FLOCK_ID", "FLOCK_NUMBER", "Flocks"),
                ("Salmonella Tests", repo.get_salmonella_tests(facility_id=view.record_id), "SALMONELLA_TEST_ID", "PERMIT_NUMBER", "Salmonella_Tests"),
            ):
                related_records_table(heading, frame, id_column=key, label_column=label, page_slug=slug, key=f"facility_related_{slug}")
    else:
        current = current or {}
        begin_form('facility_form_',view.record_id)
        expected_key = f"facility_form_expected_{view.record_id}"
        if view.name == "edit" and view.record_id:
            st.session_state.setdefault(expected_key, current.get("UPDATED_AT"))
        with st.container(border=True):
            left, right = st.columns(2)
            facility_name = left.text_input("Facility Name *", value=str(current.get("FACILITY_NAME") or ""), key="facility_form_name")
            account_label = left.selectbox("Account *", list(account_options), index=option_index(list(account_options), label_for_id(account_options, current.get("ACCOUNT_ID"))), key="facility_form_account")
            facility_type = left.selectbox("Facility Type", stored_options(FACILITY_TYPES,current.get("FACILITY_TYPE"),bool(view.record_id)), index=(stored_index(FACILITY_TYPES,current.get("FACILITY_TYPE")) if view.record_id else option_index(list(FACILITY_TYPES), current.get("FACILITY_TYPE"))), key="facility_form_type")
            status = left.selectbox("Status", stored_options(FACILITY_STATUSES,current.get("STATUS"),bool(view.record_id)), index=(stored_index(FACILITY_STATUSES,current.get("STATUS")) if view.record_id else option_index(list(FACILITY_STATUSES), current.get("STATUS"))), key="facility_form_status")
            activation = right.date_input("Activation Date", value=optional_form_date(current.get("ACTIVATION_DATE")), key="facility_form_activation")
            construction = right.date_input("Construction Date", value=optional_form_date(current.get("CONSTRUCTION_DATE")), key="facility_form_construction")
            closure = right.date_input("Closure Date", value=optional_form_date(current.get("CLOSURE_DATE")), key="facility_form_closure")
            inactive = right.date_input("Inactive Date", value=optional_form_date(current.get("INACTIVE_DATE")), key="facility_form_inactive")
            if view.record_id:
                revision_reason = st.text_input("Reason for correction *",key="facility_form_revision_reason")
                st.session_state.setdefault("facility_form_revision_request",uuid.uuid4().hex)
        capture_form('facility_form_',current,{'FACILITY_NAME': ['facility_form_name'], 'ACCOUNT_ID': ['facility_form_account'], 'FACILITY_TYPE': ['facility_form_type'], 'STATUS': ['facility_form_status'], 'ACTIVATION_DATE': ['facility_form_activation'], 'CONSTRUCTION_DATE': ['facility_form_construction'], 'CLOSURE_DATE': ['facility_form_closure'], 'INACTIVE_DATE': ['facility_form_inactive']})
        if action == "save":
            if not facility_name.strip(): st.error("Facility Name is required.")
            else:
                record = {"FACILITY_ID": view.record_id, "FACILITY_NAME": facility_name.strip(), "ACCOUNT_ID": account_options[account_label], "FACILITY_TYPE": facility_type, "STATUS": status, "ACTIVATION_DATE": activation, "CONSTRUCTION_DATE": construction, "CLOSURE_DATE": closure, "INACTIVE_DATE": inactive}
                if not view.record_id: record.pop("FACILITY_ID")
                else: record["EXPECTED_UPDATED_AT"] = st.session_state.get(expected_key)
                try:
                    if view.record_id:
                        saved_id = save_form(repo,'FACILITY',record,current,'facility_form_',revision_reason)
                    else: saved_id = save_form(repo,'FACILITY',record,current,'facility_form_')
                    open_saved_record(saved_id)
                except Exception as exc: show_data_error(exc)

_pending=st.session_state.get('facility_form___delete_pending')
if _pending and delete_confirmation(repo,'delete_facility',_pending,'facility_form___delete'):
    st.session_state.pop('facility_form___delete_pending',None)
    open_view("list")

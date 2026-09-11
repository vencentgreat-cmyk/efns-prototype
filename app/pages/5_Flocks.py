"""Enterprise-style flock workspace with validated relationships."""

from __future__ import annotations

import datetime as dt

import pandas as pd
import streamlit as st

from app.ui import apply_theme, clear_widget_prefix, page_header, section_intro
from data.constants import EGG_COLOURS, FLOCK_QUOTA_TYPES, FLOCK_STATUSES, UNASSIGNED_LABEL
from data.repositories import get_repository
from data.validation import validate_flock

apply_theme()
if "repo" not in st.session_state:
    st.session_state.repo = get_repository()
repo = st.session_state.repo

def option_index(options, value, default=0):
    return options.index(value) if value in options else default

def label_for_id(mapping, value, default=None):
    return next((label for label, item_id in mapping.items() if item_id == value), default)

page_header("Flocks", "Create and maintain flock records with explicit account, facility, and quota relationships.", "FLOCK MANAGEMENT")
st.info("Quota types and several operational fields are provisional pending Dataverse metadata.")

accounts = repo.get_accounts()
account_labels = {
    f"{row.ORGANIZATION_NAME} · {row.REGISTRATION_NUMBER or row.ACCOUNT_ID[:8]}": row.ACCOUNT_ID
    for row in accounts.itertuples()
}

filter_col, facility_col = st.columns(2)
account_filter_label = filter_col.selectbox("Account filter", ["All", *account_labels], key="flock_page_account_filter")
account_filter = account_labels.get(account_filter_label)
available_facilities = repo.get_facilities(account_id=account_filter) if account_filter else repo.get_facilities()
facility_labels = {row.FACILITY_NAME: row.FACILITY_ID for row in available_facilities.itertuples()}
facility_filter_label = facility_col.selectbox("Facility filter", ["All", *facility_labels], key="flock_page_facility_filter")
facility_filter = facility_labels.get(facility_filter_label)

flocks = repo.get_flocks(account_id=account_filter, facility_id=facility_filter)
if flocks.empty:
    st.info("No flocks match the current filters.")
else:
    display = flocks.merge(accounts[["ACCOUNT_ID", "ORGANIZATION_NAME"]], on="ACCOUNT_ID", how="left")
    display = display.merge(repo.get_facilities()[["FACILITY_ID", "FACILITY_NAME"]], on="FACILITY_ID", how="left")
    display = display.merge(repo.get_quota_registrations()[["QUOTA_ID", "QUOTA_NAME"]], on="QUOTA_ID", how="left")
    display["FACILITY_NAME"] = display["FACILITY_NAME"].fillna(UNASSIGNED_LABEL)
    display["QUOTA_NAME"] = display["QUOTA_NAME"].fillna(UNASSIGNED_LABEL)
    columns = [column for column in (
        "FLOCK_NUMBER", "ORGANIZATION_NAME", "FACILITY_NAME", "PERMIT_NUMBER",
        "QUOTA_NAME", "FLOCK_QUOTA_TYPE", "BIRD_COUNT", "HATCH_DATE",
        "PLACEMENT_DATE", "DISPOSAL_DATE", "STATUS", "UPDATED_AT",
    ) if column in display]
    st.dataframe(display[columns], width="stretch", height=430, hide_index=True)

with st.expander("Create or edit a flock", expanded=False):
    all_flocks = repo.get_flocks()
    edit_options = {f"{row.FLOCK_NUMBER} · {row.PERMIT_NUMBER}": row.FLOCK_ID for row in all_flocks.itertuples()}
    edit_label = st.selectbox("Record", ["Create new", *edit_options], key="flock_edit_record", on_change=clear_widget_prefix, args=("flock_form_", ()))
    current = repo.get_flock(edit_options[edit_label]) if edit_label != "Create new" else {}

    general_tab, detail_tab = st.tabs(["General & relationships", "Flock details"])
    with general_tab:
        left, right = st.columns(2)
        current_account = current.get("ACCOUNT_ID")
        account_names = list(account_labels)
        account_index = next((i for i, label in enumerate(account_names) if account_labels[label] == current_account), 0)
        selected_account_label = left.selectbox("Account *", account_names, index=account_index, key="flock_form_account")
        selected_account_id = account_labels[selected_account_label]
        related_facilities = repo.get_facilities(account_id=selected_account_id)
        related_facility_labels = {row.FACILITY_NAME: row.FACILITY_ID for row in related_facilities.itertuples()}
        facility_names = list(related_facility_labels)
        selected_facility_label = left.selectbox("Facility *", facility_names, index=option_index(facility_names, label_for_id(related_facility_labels, current.get("FACILITY_ID"))), key="flock_form_facility")
        selected_facility_id = related_facility_labels.get(selected_facility_label)
        details = repo.get_facility_details(facility_id=selected_facility_id)
        detail_labels = {row.DETAIL_NAME: row.FACILITY_DETAIL_ID for row in details.itertuples()}
        detail_options = [UNASSIGNED_LABEL, *detail_labels]
        selected_detail_label = left.selectbox("Facility Detail", detail_options, index=option_index(detail_options, label_for_id(detail_labels, current.get("FACILITY_DETAIL_ID"), UNASSIGNED_LABEL)), key="flock_form_detail")
        active_quotas = repo.get_quota_registrations(account_id=selected_account_id, active_only=True)
        quota_labels = {f"{row.QUOTA_NAME} · {row.REGISTRATION_NUMBER}": row.QUOTA_ID for row in active_quotas.itertuples()}
        quota_options = [UNASSIGNED_LABEL, *quota_labels]
        quota_label = left.selectbox("Quota Registration", quota_options, index=option_index(quota_options, label_for_id(quota_labels, current.get("QUOTA_ID"), UNASSIGNED_LABEL)), key="flock_form_quota")
        quota_type = left.selectbox("Flock Quota Type", FLOCK_QUOTA_TYPES, index=option_index(list(FLOCK_QUOTA_TYPES), current.get("FLOCK_QUOTA_TYPE")), key="flock_form_quota_type")
        flock_number = right.text_input("Flock Number *", value=str(current.get("FLOCK_NUMBER") or ""), key="flock_form_number")
        status = right.selectbox("Status", FLOCK_STATUSES, index=option_index(list(FLOCK_STATUSES), current.get("STATUS")), key="flock_form_status")
        create_delivery = right.toggle("Create Delivery Transaction", value=bool(current.get("CREATE_DELIVERY_TRANSACTION", False)), key="flock_form_delivery")
        st.caption(f"Flock ID: {current.get('FLOCK_ID', 'Assigned when saved')} · Created/updated timestamps are managed by the repository.")

    with detail_tab:
        left, right = st.columns(2)
        permit_number = left.text_input("Permit Number *", value=str(current.get("PERMIT_NUMBER") or ""), key="flock_form_permit")
        permit_date = left.date_input("Permit Date", value=current.get("PERMIT_DATE"), key="flock_form_permit_date")
        hatch_date = left.date_input("Hatch Date *", value=current.get("HATCH_DATE") or dt.date.today(), key="flock_form_hatch")
        ordered_date = left.date_input("Date Ordered", value=current.get("DATE_ORDERED"), key="flock_form_ordered")
        placement_date = left.date_input("Placement Date", value=current.get("PLACEMENT_DATE"), key="flock_form_placement")
        bird_count = left.number_input("Bird Count *", min_value=0, value=int(current.get("BIRD_COUNT") or 0), key="flock_form_birds")
        egg_colour = left.selectbox("Flock / Egg Colour", EGG_COLOURS, index=option_index(list(EGG_COLOURS), current.get("EGG_COLOUR")), key="flock_form_colour")
        bird_strain = right.text_input("Bird Strain", value=str(current.get("BIRD_STRAIN") or ""), key="flock_form_strain")
        estimated_disposal = right.date_input("Estimated Disposal Date", value=current.get("EST_DISPOSAL"), key="flock_form_est_disposal")
        disposal_date = right.date_input("Disposal Date", value=current.get("DISPOSAL_DATE"), key="flock_form_disposal")
        birds_disposed = right.number_input("Birds Disposed", min_value=0, value=int(current.get("BIRDS_DISPOSED") or 0), key="flock_form_disposed")
        breeder = right.text_input("Breeder", value=str(current.get("BREEDER") or ""), key="flock_form_breeder")
        hatchery = right.text_input("Hatchery", value=str(current.get("HATCHERY") or ""), key="flock_form_hatchery")
        pullet_grower = right.text_input("Pullet Grower", value=str(current.get("PULLET_GROWER") or ""), key="flock_form_grower")
        disposal_plant = right.text_input("Disposal Plant", value=str(current.get("DISPOSAL_PLANT") or ""), key="flock_form_plant")
        comments = st.text_area("Comments", value=str(current.get("COMMENTS") or ""), key="flock_form_comments")

    if st.button("Save Flock", type="primary", key="flock_form_save"):
        record = {
            "FLOCK_ID": current.get("FLOCK_ID"), "FLOCK_NUMBER": flock_number,
            "ACCOUNT_ID": selected_account_id, "FACILITY_ID": selected_facility_id,
            "FACILITY_DETAIL_ID": detail_labels.get(selected_detail_label),
            "QUOTA_ID": quota_labels.get(quota_label), "FLOCK_QUOTA_TYPE": quota_type,
            "STATUS": status, "CREATE_DELIVERY_TRANSACTION": create_delivery,
            "PERMIT_NUMBER": permit_number, "PERMIT_DATE": permit_date,
            "HATCH_DATE": hatch_date, "DATE_ORDERED": ordered_date,
            "BIRD_COUNT": bird_count, "EGG_COLOUR": egg_colour,
            "BIRD_STRAIN": bird_strain or None, "PLACEMENT_DATE": placement_date,
            "EST_DISPOSAL": estimated_disposal, "DISPOSAL_DATE": disposal_date,
            "BIRDS_DISPOSED": birds_disposed, "BREEDER": breeder or None,
            "HATCHERY": hatchery or None, "PULLET_GROWER": pullet_grower or None,
            "DISPOSAL_PLANT": disposal_plant or None, "COMMENTS": comments or None,
        }
        record = {key: value for key, value in record.items() if value is not None or key not in ("FLOCK_ID",)}
        errors = validate_flock(repo, record)
        if errors:
            for error in errors:
                st.error(error)
        else:
            try:
                flock_id = repo.upsert_flock(record)
                st.success(f"Flock saved: {flock_id}")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

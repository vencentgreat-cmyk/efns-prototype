"""Farm Location (Dynamics Other Address) record workspace."""

from __future__ import annotations

import streamlit as st

from app.auth import require_operational_page
from app.navigation import (
    ensure_record_form_state, format_timestamp, list_command_bar, open_module,
    open_view, read_record_view, record_command_bar, saved_view_selector,
    selected_row_index, timestamp_column, view_parameter,
)
from app.ui import apply_theme, clear_widget_prefix, page_header, show_data_error
from data.constants import FARM_LOCATION_STATUSES
from data.repositories import get_repository
from data.repositories.base import RepositoryError
from data.validation import validate_farm_location


require_operational_page()
apply_theme()
if "repo" not in st.session_state:
    st.session_state.repo = get_repository()
repo = st.session_state.repo
view = read_record_view()
accounts = repo.get_accounts()
account_names = dict(zip(accounts.get("ACCOUNT_ID", []), accounts.get("ORGANIZATION_NAME", [])))
account_options = {
    f"{row.ORGANIZATION_NAME} · {row.REGISTRATION_NUMBER or str(row.ACCOUNT_ID)[:8]}": row.ACCOUNT_ID
    for row in accounts.itertuples()
}


def option_index(options, value):
    return options.index(value) if value in options else 0


def label_for_id(mapping, value):
    return next((label for label, record_id in mapping.items() if record_id == value), next(iter(mapping), None))


if view.name == "list":
    page_header(
        "Farm Locations",
        "Account-owned postal, physical, and operational addresses (Dynamics Other Addresses).",
        "ACCOUNT & FACILITY",
    )
    statuses, _ = saved_view_selector(
        "FARM_LOCATION", "Farm Locations", key="farm_location_saved_view",
        selection_keys=("farm_location_list_grid", "farm_location_list_row_ids", "farm_location_delete_pending"),
    )
    selected_index = selected_row_index("farm_location_list_grid")
    row_ids = st.session_state.get("farm_location_list_row_ids", [])
    selected_id = row_ids[selected_index] if selected_index is not None and selected_index < len(row_ids) else None
    action = list_command_bar("farm_location_list", selected=bool(selected_id))
    if action == "new": open_view("new")
    if action == "view" and selected_id: open_view("detail", selected_id)
    if action == "refresh": st.rerun()
    if action == "delete" and selected_id: st.session_state.farm_location_delete_pending = selected_id
    pending = st.session_state.get("farm_location_delete_pending")
    if pending:
        with st.container(border=True):
            st.warning("Delete the selected Farm Location?")
            left, right = st.columns(2)
            if left.button("Confirm delete", type="primary", icon=":material/delete:"):
                try:
                    repo.delete_farm_location(pending)
                    st.session_state.pop("farm_location_delete_pending", None)
                    st.rerun()
                except (ValueError, RepositoryError) as exc: show_data_error(exc)
            if right.button("Cancel"): st.session_state.pop("farm_location_delete_pending", None); st.rerun()
    keyword = st.text_input(
        "Search", placeholder="Location, Account, city, postal code or phone",
        key="farm_location_keyword",
    )
    account_label = st.selectbox("Account", ["All Accounts", *account_options], key="farm_location_account_filter")
    frame = repo.get_farm_locations(
        account_id=account_options.get(account_label), statuses=statuses, keyword=keyword or None,
    ).drop_duplicates("FARM_LOCATION_ID")
    st.caption(f"{len(frame):,} Farm Location(s) in this view")
    if frame.empty:
        st.session_state.farm_location_list_row_ids = []
        st.info("No Farm Locations match this view and search.")
    else:
        display = frame.copy().reset_index(drop=True)
        display["ACCOUNT"] = display["ACCOUNT_ID"].map(account_names).fillna("Unknown Account")
        st.session_state.farm_location_list_row_ids = display["FARM_LOCATION_ID"].tolist()
        st.dataframe(
            display[["LOCATION_NAME", "ACCOUNT", "CITY", "PROVINCE", "POSTAL_CODE", "PHONE", "STATUS", "UPDATED_AT"]],
            width="stretch", height=520, hide_index=True, on_select="rerun",
            selection_mode="single-row", key="farm_location_list_grid",
            column_config={"LOCATION_NAME": "Farm Location", "UPDATED_AT": timestamp_column("Updated On")},
        )
else:
    current = repo.get_farm_location(view.record_id) if view.record_id else None
    if view.name in {"detail", "edit"} and current is None:
        page_header("Farm Location Not Found", "This record was removed or is no longer available.", "ACCOUNT & FACILITY")
        st.warning("Return to the list and choose an available Farm Location.")
        if st.button("Back to Farm Locations", icon=":material/arrow_back:"): open_view("list")
        st.stop()
    current = current or {}
    page_header(
        "New Farm Location" if view.name == "new" else current.get("LOCATION_NAME", "Farm Location"),
        "Provisional Account-owned address; kept separate from regulated Facilities.",
        "FARM LOCATION",
    )
    action = record_command_bar("farm_location_record", view.name)
    if action == "back": open_view("list")
    if action == "cancel": open_view("detail", view.record_id) if view.record_id else open_view("list")
    if action == "refresh": st.rerun()
    if action == "edit": clear_widget_prefix("farm_location_form_"); open_view("edit", view.record_id)
    if action == "delete" and view.record_id:
        try: repo.delete_farm_location(view.record_id); open_view("list")
        except (ValueError, RepositoryError) as exc: show_data_error(exc)

    if view.name == "detail":
        st.caption(f"Created On: {format_timestamp(current.get('CREATED_AT'))} · Updated On: {format_timestamp(current.get('UPDATED_AT'))}")
        summary, related = st.tabs(["Summary", "Related Records"])
        with summary:
            with st.container(border=True):
                left, right = st.columns(2)
                left.markdown(f"**Location Name**  \n{current.get('LOCATION_NAME') or '—'}")
                left.markdown(f"**Account**  \n{account_names.get(current.get('ACCOUNT_ID'), 'Unknown Account')}")
                left.markdown(f"**Status**  \n{current.get('STATUS') or '—'}")
                right.markdown(f"**Address**  \n{current.get('ADDRESS_1') or '—'}")
                right.write(current.get("ADDRESS_2") or "")
                right.write(" · ".join(filter(None, [current.get("CITY"), current.get("PROVINCE"), current.get("POSTAL_CODE")])))
                right.markdown(f"**Phone**  \n{current.get('PHONE') or '—'}")
        with related:
            st.caption("Farm Location currently has one confirmed relationship: its parent Account.")
            if current.get("ACCOUNT_ID") and st.button("View Account", icon=":material/account_circle:"):
                open_module("Accounts_&_Facilities", "detail", current["ACCOUNT_ID"])
    else:
        if accounts.empty:
            st.error("Create an Account before creating a Farm Location."); st.stop()
        ensure_record_form_state("farm_location_form_", view.record_id)
        expected_key = f"farm_location_form_expected_{view.record_id}"
        if view.name == "edit": st.session_state.setdefault(expected_key, current.get("UPDATED_AT"))
        requested_account = view_parameter("account_id")
        account_id = current.get("ACCOUNT_ID") or (requested_account if requested_account in set(account_options.values()) else None)
        with st.container(border=True):
            left, right = st.columns(2)
            account_label = left.selectbox("Account *", list(account_options), index=option_index(list(account_options), label_for_id(account_options, account_id)), key="farm_location_form_account")
            name = left.text_input("Location Name *", value=str(current.get("LOCATION_NAME") or ""), key="farm_location_form_name")
            address_1 = left.text_input("Address 1", value=str(current.get("ADDRESS_1") or ""), key="farm_location_form_address1")
            address_2 = left.text_input("Address 2", value=str(current.get("ADDRESS_2") or ""), key="farm_location_form_address2")
            city = right.text_input("City", value=str(current.get("CITY") or ""), key="farm_location_form_city")
            province = right.text_input("Province", value=str(current.get("PROVINCE") or "NS"), key="farm_location_form_province")
            postal = right.text_input("Postal Code", value=str(current.get("POSTAL_CODE") or ""), key="farm_location_form_postal")
            phone = right.text_input("Phone", value=str(current.get("PHONE") or ""), key="farm_location_form_phone")
            status = right.selectbox("Status", FARM_LOCATION_STATUSES, index=option_index(list(FARM_LOCATION_STATUSES), current.get("STATUS")), key="farm_location_form_status")
        if action == "save":
            record = {
                "FARM_LOCATION_ID": view.record_id, "ACCOUNT_ID": account_options[account_label],
                "LOCATION_NAME": name.strip(), "ADDRESS_1": address_1.strip() or None,
                "ADDRESS_2": address_2.strip() or None, "CITY": city.strip() or None,
                "PROVINCE": province.strip() or None, "POSTAL_CODE": postal.strip() or None,
                "PHONE": phone.strip() or None, "STATUS": status,
            }
            if not view.record_id: record.pop("FARM_LOCATION_ID")
            else: record["EXPECTED_UPDATED_AT"] = st.session_state.get(expected_key)
            errors = validate_farm_location(repo, record)
            if errors:
                for error in errors: st.error(error)
            else:
                try:
                    saved_id = repo.upsert_farm_location(record)
                    clear_widget_prefix("farm_location_form_"); open_view("detail", saved_id)
                except (ValueError, RepositoryError) as exc: show_data_error(exc)

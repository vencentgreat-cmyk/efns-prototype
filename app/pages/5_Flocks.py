"""Enterprise Flock list, detail, new and edit workspace."""

from __future__ import annotations

import datetime as dt

import pandas as pd
import streamlit as st

from app.auth import require_operational_page
from app.navigation import format_timestamp, list_command_bar, open_view, read_record_view, record_command_bar, selected_row_index, timestamp_column
from app.ui import apply_theme, clear_widget_prefix, page_header, section_intro, show_data_error
from data.constants import EGG_COLOURS, FLOCK_QUOTA_TYPES, FLOCK_STATUSES, UNASSIGNED_LABEL
from data.repositories import get_repository
from data.repositories.base import RepositoryError
from data.validation import validate_flock


require_operational_page()
apply_theme()
if "repo" not in st.session_state:
    st.session_state.repo = get_repository()
repo = st.session_state.repo
view = read_record_view()
accounts = repo.get_accounts()
facilities = repo.get_facilities()
flocks = repo.get_flocks()
account_names = {row.ACCOUNT_ID: row.ORGANIZATION_NAME for row in accounts.itertuples()}
facility_names = {row.FACILITY_ID: row.FACILITY_NAME for row in facilities.itertuples()}
account_options = {f"{row.ORGANIZATION_NAME} · {row.REGISTRATION_NUMBER or row.ACCOUNT_ID[:8]}": row.ACCOUNT_ID for row in accounts.itertuples()}


def option_index(options, value):
    return options.index(value) if value in options else 0


def label_for_id(mapping, value, default=None):
    return next((label for label, record_id in mapping.items() if record_id == value), default)


if view.name == "list":
    page_header("Active Flocks", "Search, filter and maintain validated Flock records.", "FLOCK MANAGEMENT")
    selected_index = selected_row_index("flock_list_grid")
    row_ids = st.session_state.get("flock_list_row_ids", [])
    selected_id = row_ids[selected_index] if selected_index is not None and selected_index < len(row_ids) else None
    action = list_command_bar("flock_list", selected=bool(selected_id))
    if action == "view" and selected_id: open_view("detail", selected_id)
    if action == "new": open_view("new")
    if action == "refresh": clear_widget_prefix("flock_filter_"); st.rerun()
    if action == "delete" and selected_id: st.session_state.flock_delete_pending = selected_id
    if st.session_state.get("flock_delete_pending"):
        with st.container(border=True):
            st.warning("Delete the selected Flock? Related Transactions, Tests or Production will block deletion.")
            with st.container(horizontal=True):
                if st.button("Confirm delete", type="primary", key="flock_confirm_delete"):
                    try:
                        repo.delete_flock(st.session_state.flock_delete_pending)
                        st.session_state.pop("flock_delete_pending", None); st.rerun()
                    except (ValueError, RepositoryError) as exc: show_data_error(exc)
                if st.button("Cancel", key="flock_cancel_delete"):
                    st.session_state.pop("flock_delete_pending", None); st.rerun()
    filters = st.columns([2, 1, 1, 1])
    keyword = filters[0].text_input("Filter by keyword", placeholder="Flock number or permit", key="flock_filter_keyword")
    account_filter = filters[1].selectbox("Account", ["All", *account_options], key="flock_filter_account")
    status_filter = filters[2].selectbox("Status", ["All", *FLOCK_STATUSES], key="flock_filter_status")
    colour_filter = filters[3].selectbox("Egg colour", ["All", *EGG_COLOURS], key="flock_filter_colour")
    display = flocks.copy()
    if keyword:
        display = display[display[["FLOCK_NUMBER", "PERMIT_NUMBER"]].fillna("").astype(str).apply(lambda col: col.str.contains(keyword, case=False, regex=False)).any(axis=1)]
    if account_filter != "All": display = display[display["ACCOUNT_ID"] == account_options[account_filter]]
    if status_filter != "All": display = display[display["STATUS"] == status_filter]
    if colour_filter != "All": display = display[display["EGG_COLOUR"] == colour_filter]
    st.caption(f"{len(display):,} flock record(s)")
    if display.empty:
        st.info("No Flocks match the current filters.")
    else:
        display = display.reset_index(drop=True)
        display["ACCOUNT_NAME"] = display["ACCOUNT_ID"].map(account_names).fillna("Unknown")
        display["FACILITY_NAME"] = display["FACILITY_ID"].map(facility_names).fillna(UNASSIGNED_LABEL)
        st.session_state.flock_list_row_ids = display["FLOCK_ID"].tolist()
        st.dataframe(display[["FLOCK_NUMBER", "ACCOUNT_NAME", "FACILITY_NAME", "PERMIT_NUMBER", "BIRD_COUNT", "HATCH_DATE", "EGG_COLOUR", "STATUS", "CREATED_AT"]], width="stretch", height=540, hide_index=True, on_select="rerun", selection_mode="single-row", key="flock_list_grid", column_config={"FLOCK_NUMBER": "Flock Number", "ACCOUNT_NAME": "Account", "FACILITY_NAME": "Facility", "CREATED_AT": timestamp_column("Created On")})
else:
    current = repo.get_flock(view.record_id) if view.record_id else None
    if view.name in {"detail", "edit"} and current is None:
        st.error("The requested Flock could not be found.")
        if st.button("Back to Flocks"): open_view("list")
        st.stop()
    is_form = view.name in {"new", "edit"}
    page_header("New Flock" if view.name == "new" else current["FLOCK_NUMBER"], "Validated relationships, permit, dates and bird counts.", "FLOCK RECORD")
    action = record_command_bar("flock_record", view.name)
    if action in {"back", "cancel"}: open_view("detail", view.record_id) if action == "cancel" and view.record_id else open_view("list")
    if action == "edit": clear_widget_prefix("flock_form_"); open_view("edit", view.record_id)
    if action == "delete" and view.record_id:
        try: repo.delete_flock(view.record_id); open_view("list")
        except (ValueError, RepositoryError) as exc: show_data_error(exc)
    if not is_form:
        st.caption(f"Created On: {format_timestamp(current.get('CREATED_AT'))} · Updated On: {format_timestamp(current.get('UPDATED_AT'))}")
        summary, details, related = st.tabs(["Summary", "Details", "Related Records"])
        with summary:
            with st.container(border=True):
                left, middle, right = st.columns(3)
                left.markdown(f"**Flock Number**  \n{current.get('FLOCK_NUMBER')}")
                left.markdown(f"**Account**  \n{account_names.get(current.get('ACCOUNT_ID'), 'Unknown')}")
                left.markdown(f"**Facility**  \n{facility_names.get(current.get('FACILITY_ID'), UNASSIGNED_LABEL)}")
                middle.markdown(f"**Permit Number**  \n{current.get('PERMIT_NUMBER')}")
                middle.markdown(f"**Hatch Date**  \n{current.get('HATCH_DATE')}")
                middle.markdown(f"**Placement Date**  \n{current.get('PLACEMENT_DATE') or '—'}")
                right.markdown(f"**Bird Count**  \n{int(current.get('BIRD_COUNT') or 0):,}")
                right.markdown(f"**Egg Colour**  \n{current.get('EGG_COLOUR') or '—'}")
                right.markdown(f"**Status**  \n{current.get('STATUS')}")
        with details:
            detail_fields = [key for key in current if key not in {"CREATED_AT", "UPDATED_AT"}]
            st.dataframe(pd.DataFrame({"Field": [key.replace("_", " ").title() for key in detail_fields], "Value": [str(current[key]) if current[key] is not None else "—" for key in detail_fields]}), width="stretch", hide_index=True)
        with related:
            for heading, frame, key, label, slug in (
                ("Flock Transactions", repo.get_flock_transactions(view.record_id), "FLOCK_TRANSACTION_ID", "TRANSACTION_TYPE", "Flock_Transactions"),
                ("Salmonella Tests", repo.get_salmonella_tests(flock_id=view.record_id), "SALMONELLA_TEST_ID", "PERMIT_NUMBER", "Salmonella_Tests"),
            ):
                section_intro(heading)
                if frame.empty: st.info(f"No related {heading}.")
                else:
                    frame = frame.copy(); frame["RECORD"] = frame.apply(lambda row: f"{row.get(label)} · {str(row[key])[:8]}", axis=1)
                    columns = [column for column in frame.columns if column not in {key, "RECORD", "CREATED_AT", "UPDATED_AT"}][:5]
                    st.dataframe(frame[["RECORD", *columns]], width="stretch", hide_index=True)
            production = repo.get_production_records()
            production = production[production["FLOCK_ID"] == view.record_id] if "FLOCK_ID" in production else production.iloc[0:0]
            section_intro("Matched Production Records")
            if production.empty: st.info("No matched Production Records.")
            else: st.dataframe(production, width="stretch", hide_index=True)
    else:
        current = current or {}
        expected_key = f"flock_form_expected_{view.record_id}"
        if view.name == "edit" and view.record_id:
            st.session_state.setdefault(expected_key, current.get("UPDATED_AT"))
        current_account = current.get("ACCOUNT_ID")
        with st.container(border=True):
            general, lifecycle = st.tabs(["Summary & Relationships", "Flock Details"])
            with general:
                left, right = st.columns(2)
                account_labels = list(account_options)
                account_label = left.selectbox("Account *", account_labels, index=option_index(account_labels, label_for_id(account_options, current_account)), key="flock_form_account")
                account_id = account_options[account_label]
                related_facilities = repo.get_facilities(account_id=account_id)
                facility_options = {row.FACILITY_NAME: row.FACILITY_ID for row in related_facilities.itertuples()}
                facility_labels = list(facility_options)
                facility_label = left.selectbox("Facility *", facility_labels, index=option_index(facility_labels, label_for_id(facility_options, current.get("FACILITY_ID"))), key="flock_form_facility")
                facility_id = facility_options.get(facility_label)
                detail_options = {UNASSIGNED_LABEL: None, **{row.DETAIL_NAME: row.FACILITY_DETAIL_ID for row in repo.get_facility_details(facility_id).itertuples()}}
                detail_label = left.selectbox("Facility Detail", list(detail_options), index=option_index(list(detail_options), label_for_id(detail_options, current.get("FACILITY_DETAIL_ID"), UNASSIGNED_LABEL)), key="flock_form_detail")
                quotas = repo.get_quota_registrations(account_id=account_id, active_only=True)
                quota_options = {UNASSIGNED_LABEL: None, **{f"{row.QUOTA_NAME} · {row.REGISTRATION_NUMBER}": row.QUOTA_ID for row in quotas.itertuples()}}
                quota_label = left.selectbox("Quota Registration", list(quota_options), index=option_index(list(quota_options), label_for_id(quota_options, current.get("QUOTA_ID"), UNASSIGNED_LABEL)), key="flock_form_quota")
                quota_type = left.selectbox("Flock Quota Type", FLOCK_QUOTA_TYPES, index=option_index(list(FLOCK_QUOTA_TYPES), current.get("FLOCK_QUOTA_TYPE")), key="flock_form_quota_type")
                flock_number = right.text_input("Flock Number *", value=str(current.get("FLOCK_NUMBER") or ""), key="flock_form_number")
                status = right.selectbox("Status", FLOCK_STATUSES, index=option_index(list(FLOCK_STATUSES), current.get("STATUS")), key="flock_form_status")
                create_delivery = right.checkbox("Create Delivery Transaction", value=bool(current.get("CREATE_DELIVERY_TRANSACTION")), key="flock_form_delivery")
                permit_number = right.text_input("Permit Number *", value=str(current.get("PERMIT_NUMBER") or ""), key="flock_form_permit")
                hatch_date = right.date_input("Hatch Date *", value=current.get("HATCH_DATE") or dt.date.today(), key="flock_form_hatch")
            with lifecycle:
                left, right = st.columns(2)
                bird_count = left.number_input("Bird Count *", min_value=0, value=int(current.get("BIRD_COUNT") or 0), key="flock_form_birds")
                egg_colour = left.selectbox("Egg Colour", EGG_COLOURS, index=option_index(list(EGG_COLOURS), current.get("EGG_COLOUR")), key="flock_form_colour")
                permit_date = left.date_input("Permit Date", value=current.get("PERMIT_DATE"), key="flock_form_permit_date")
                ordered_date = left.date_input("Date Ordered", value=current.get("DATE_ORDERED"), key="flock_form_ordered")
                placement_date = left.date_input("Placement Date", value=current.get("PLACEMENT_DATE"), key="flock_form_placement")
                estimated_disposal = right.date_input("Estimated Disposal Date", value=current.get("EST_DISPOSAL"), key="flock_form_est_disposal")
                disposal_date = right.date_input("Disposal Date", value=current.get("DISPOSAL_DATE"), key="flock_form_disposal")
                birds_disposed = right.number_input("Birds Disposed", min_value=0, value=int(current.get("BIRDS_DISPOSED") or 0), key="flock_form_disposed")
                bird_strain = right.text_input("Bird Strain", value=str(current.get("BIRD_STRAIN") or ""), key="flock_form_strain")
                comments = st.text_area("Comments", value=str(current.get("COMMENTS") or ""), key="flock_form_comments")
        if action == "save":
            record = {"FLOCK_ID": view.record_id, "FLOCK_NUMBER": flock_number.strip(), "ACCOUNT_ID": account_id, "FACILITY_ID": facility_id, "FACILITY_DETAIL_ID": detail_options[detail_label], "QUOTA_ID": quota_options[quota_label], "FLOCK_QUOTA_TYPE": quota_type, "STATUS": status, "CREATE_DELIVERY_TRANSACTION": create_delivery, "PERMIT_NUMBER": permit_number.strip(), "PERMIT_DATE": permit_date, "HATCH_DATE": hatch_date, "DATE_ORDERED": ordered_date, "BIRD_COUNT": bird_count, "EGG_COLOUR": egg_colour, "BIRD_STRAIN": bird_strain or None, "PLACEMENT_DATE": placement_date, "EST_DISPOSAL": estimated_disposal, "DISPOSAL_DATE": disposal_date, "BIRDS_DISPOSED": birds_disposed, "COMMENTS": comments or None}
            if not view.record_id: record.pop("FLOCK_ID")
            else: record["EXPECTED_UPDATED_AT"] = st.session_state.get(expected_key)
            errors = validate_flock(repo, record)
            if errors:
                for error in errors: st.error(error)
            else:
                try:
                    saved_id = repo.upsert_flock(record); clear_widget_prefix("flock_form_"); open_view("detail", saved_id)
                except (ValueError, RepositoryError) as exc: show_data_error(exc)

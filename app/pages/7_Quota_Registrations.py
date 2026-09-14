"""Enterprise Quota Registration list and record workspace."""

from __future__ import annotations

import datetime as dt

import pandas as pd
import streamlit as st

from app.auth import require_operational_page
from app.navigation import (
    current_page_url,
    ensure_record_form_state,
    format_timestamp,
    list_command_bar,
    module_url,
    module_view_url,
    open_view,
    read_record_view,
    record_command_bar,
    selected_row_index,
)
from app.ui import apply_theme, clear_widget_prefix, page_header, section_intro, show_data_error
from data.constants import QUOTA_STATUSES, QUOTA_TYPES
from data.repositories import get_repository
from data.repositories.base import RepositoryError
from data.validation import validate_quota_registration


require_operational_page()
apply_theme()
if "repo" not in st.session_state:
    st.session_state.repo = get_repository()
repo = st.session_state.repo

if st.query_params.get("quota_id") and not st.query_params.get("view"):
    open_view("detail", str(st.query_params["quota_id"]))
view = read_record_view()
accounts = repo.get_accounts()
all_quotas = repo.get_quota_registrations()
account_names = {row.ACCOUNT_ID: row.ORGANIZATION_NAME for row in accounts.itertuples()}
account_options = {
    f"{row.ORGANIZATION_NAME} · {row.REGISTRATION_NUMBER or row.ACCOUNT_ID[:8]}": row.ACCOUNT_ID
    for row in accounts.itertuples()
}


def as_date(value, default=None):
    converted = pd.to_datetime(value, errors="coerce")
    return default if pd.isna(converted) else converted.date()


def option_index(options, value):
    return options.index(value) if value in options else 0


def label_for_id(mapping, value):
    return next((label for label, record_id in mapping.items() if record_id == value), next(iter(mapping), None))


def quota_title(record):
    return record.get("QUOTA_NAME") or record.get("REGISTRATION_NUMBER") or "Quota Registration"


def get_quota(record_id):
    return repo.get_quota_registration(record_id) if record_id else None


if view.name == "list":
    page_header("Quota Registrations", "Search and maintain provisional account quota registrations.", "QUOTA MANAGEMENT")
    st.info("Quota types and allocation rules remain provisional. This module does not calculate available quota balance.")
    selected_index = selected_row_index("quota_reg_list_grid")
    row_ids = st.session_state.get("quota_reg_list_row_ids", [])
    selected_id = row_ids[selected_index] if selected_index is not None and selected_index < len(row_ids) else None
    action = list_command_bar("quota_reg_list", selected=bool(selected_id))
    if action == "new": open_view("new")
    if action == "refresh": st.rerun()
    if action == "delete" and selected_id: st.session_state.quota_reg_delete_pending = selected_id

    pending_delete = st.session_state.get("quota_reg_delete_pending")
    if pending_delete:
        with st.container(border=True):
            st.warning("Delete the selected Quota Registration? Related Transactions or Flocks will block deletion.")
            with st.container(horizontal=True):
                if st.button("Confirm delete", type="primary", icon=":material/delete:", key="quota_reg_confirm_delete"):
                    try:
                        repo.delete_quota_registration(pending_delete)
                        st.session_state.pop("quota_reg_delete_pending", None)
                        st.rerun()
                    except (ValueError, RepositoryError) as exc: show_data_error(exc)
                if st.button("Cancel", key="quota_reg_cancel_delete"):
                    st.session_state.pop("quota_reg_delete_pending", None); st.rerun()

    filter_header, reset_column = st.columns([5, 1])
    with filter_header:
        keyword = st.text_input("Search", placeholder="Registration number, quota name or account", key="quota_reg_filter_keyword")
    with reset_column:
        st.write("")
        if st.button("Reset Filters", icon=":material/filter_alt_off:", key="quota_reg_reset", width="stretch"):
            clear_widget_prefix("quota_reg_filter_"); st.rerun()
    filters = st.columns(3)
    account_filter = filters[0].selectbox("Account", ["All", *account_options], key="quota_reg_filter_account")
    status_filter = filters[1].selectbox("Status", ["All", *QUOTA_STATUSES], key="quota_reg_filter_status")
    type_filter = filters[2].selectbox("Quota Type", ["All", *QUOTA_TYPES], key="quota_reg_filter_type")
    quotas = repo.get_quota_registrations(
        account_id=account_options.get(account_filter),
        status=None if status_filter == "All" else status_filter,
        quota_type=None if type_filter == "All" else type_filter,
    )
    display = quotas.copy()
    if not display.empty:
        display["ACCOUNT_NAME"] = display["ACCOUNT_ID"].map(account_names)
        if keyword:
            columns = ["REGISTRATION_NUMBER", "QUOTA_NAME", "ACCOUNT_NAME"]
            display = display[display[columns].fillna("").astype(str).apply(lambda column: column.str.contains(keyword, case=False, regex=False)).any(axis=1)]
    st.caption(f"{len(display):,} quota registration(s)")
    if display.empty:
        st.info("No Quota Registrations match the current filters.")
    else:
        display = display.reset_index(drop=True)
        display["REGISTRATION_LINK"] = display.apply(lambda row: current_page_url(row["QUOTA_ID"], row["REGISTRATION_NUMBER"]), axis=1)
        display["QUOTA_LINK"] = display.apply(lambda row: current_page_url(row["QUOTA_ID"], quota_title(row)), axis=1)
        display["ACCOUNT_LINK"] = display.apply(lambda row: module_url("Accounts_&_Facilities", row["ACCOUNT_ID"], row["ACCOUNT_NAME"] or "Unknown"), axis=1)
        st.session_state.quota_reg_list_row_ids = display["QUOTA_ID"].tolist()
        st.dataframe(
            display[["REGISTRATION_LINK", "QUOTA_LINK", "ACCOUNT_LINK", "QUOTA_TYPE", "STATUS", "EFFECTIVE_DATE", "END_DATE", "CREATED_AT"]],
            width="stretch", height=520, hide_index=True, on_select="rerun", selection_mode="single-row", key="quota_reg_list_grid",
            column_config={
                "REGISTRATION_LINK": st.column_config.LinkColumn("Registration Number", display_text=r".*#(.*)$"),
                "QUOTA_LINK": st.column_config.LinkColumn("Quota Name", display_text=r".*#(.*)$"),
                "ACCOUNT_LINK": st.column_config.LinkColumn("Account", display_text=r".*#(.*)$"),
                "EFFECTIVE_DATE": st.column_config.DateColumn("Effective Date", format="YYYY-MM-DD"),
                "END_DATE": st.column_config.DateColumn("End Date", format="YYYY-MM-DD"),
                "CREATED_AT": st.column_config.DatetimeColumn("Created On", format="YYYY-MM-DD HH:mm"),
            },
        )
else:
    current = get_quota(view.record_id)
    if view.name in {"detail", "edit"} and current is None:
        page_header("Quota Registration Not Found", "The requested record does not exist or is no longer available.", "QUOTA MANAGEMENT")
        if st.button("Back to Quota Registrations", icon=":material/arrow_back:"): open_view("list")
        st.stop()
    is_form = view.name in {"new", "edit"}
    page_header("New Quota Registration" if view.name == "new" else quota_title(current), "Account allocation and effective dates. Available balance is not calculated.", "QUOTA REGISTRATION")
    action = record_command_bar("quota_reg_record", view.name)
    if action in {"back", "cancel"}: open_view("detail", view.record_id) if action == "cancel" and view.record_id else open_view("list")
    if action == "refresh": st.rerun()
    if action == "edit": clear_widget_prefix("quota_reg_form_"); open_view("edit", view.record_id)
    if action == "delete" and view.record_id: st.session_state.quota_reg_record_delete_pending = True
    if st.session_state.get("quota_reg_record_delete_pending"):
        with st.container(border=True):
            st.warning("Delete this Quota Registration? Existing Transactions or Flocks will block deletion.")
            with st.container(horizontal=True):
                if st.button("Confirm delete", type="primary", icon=":material/delete:", key="quota_reg_record_confirm"):
                    try:
                        repo.delete_quota_registration(view.record_id)
                        st.session_state.pop("quota_reg_record_delete_pending", None); open_view("list")
                    except (ValueError, RepositoryError) as exc: show_data_error(exc)
                if st.button("Keep record", key="quota_reg_record_keep"):
                    st.session_state.pop("quota_reg_record_delete_pending", None); st.rerun()

    if not is_form:
        st.caption(f"Created On: {format_timestamp(current.get('CREATED_AT'))} · Updated On: {format_timestamp(current.get('UPDATED_AT'))}")
        summary, related = st.tabs(["Summary", "Related Records"])
        with summary:
            with st.container(border=True):
                left, middle, right = st.columns(3)
                left.markdown(f"**Registration Number**  \n{current.get('REGISTRATION_NUMBER') or '—'}")
                left.markdown(f"**Quota Name**  \n{current.get('QUOTA_NAME') or '—'}")
                account_id = current.get("ACCOUNT_ID")
                if account_id:
                    left.markdown(f"**Account**  \n[{account_names.get(account_id, 'Unknown')}]({module_url('Accounts_&_Facilities', account_id, account_names.get(account_id, 'Unknown'))})")
                middle.markdown(f"**Quota Type**  \n{current.get('QUOTA_TYPE') or '—'}")
                middle.markdown(f"**Status**  \n{current.get('STATUS') or '—'}")
                right.markdown(f"**Effective Date**  \n{as_date(current.get('EFFECTIVE_DATE'), '—')}")
                right.markdown(f"**End Date**  \n{as_date(current.get('END_DATE'), '—')}")
                st.markdown(f"**Comments**  \n{current.get('COMMENTS') or 'No comments.'}")
        with related:
            with st.container(horizontal=True, vertical_alignment="center"):
                section_intro("Quota Transactions")
                st.link_button("New Quota Transaction", module_view_url("Quota_Transactions", "new", quota_id=view.record_id), icon=":material/add:", type="primary")
            transactions = repo.get_quota_transactions(quota_id=view.record_id)
            if transactions.empty:
                st.info("No Quota Transactions are connected to this registration.")
            else:
                related_display = transactions.copy()
                related_display["TRANSACTION_LINK"] = related_display.apply(lambda row: module_url("Quota_Transactions", row["QUOTA_TRANSACTION_ID"], f"{row['TRANSACTION_TYPE']} · {str(row['QUOTA_TRANSACTION_ID'])[:8]}"), axis=1)
                st.dataframe(related_display[["TRANSACTION_LINK", "TRANSACTION_TYPE", "EFFECTIVE_DATE", "END_DATE", "QUOTA_COUNT", "PRICE", "CREATED_AT"]], width="stretch", hide_index=True, column_config={"TRANSACTION_LINK": st.column_config.LinkColumn("Transaction", display_text=r".*#(.*)$"), "CREATED_AT": st.column_config.DatetimeColumn("Created On", format="YYYY-MM-DD HH:mm")})
    else:
        current = current or {}
        if accounts.empty:
            st.error("Create an Account before creating a Quota Registration."); st.stop()
        ensure_record_form_state("quota_reg_form_", view.record_id)
        expected_key = f"quota_reg_form_expected_{view.record_id}"
        if view.name == "edit": st.session_state.setdefault(expected_key, current.get("UPDATED_AT"))
        requested_account = st.query_params.get("account_id")
        selected_account_id = current.get("ACCOUNT_ID") or (str(requested_account) if requested_account in set(account_options.values()) else None)
        with st.container(border=True):
            left, right = st.columns(2)
            account_label = left.selectbox("Account *", list(account_options), index=option_index(list(account_options), label_for_id(account_options, selected_account_id)), key="quota_reg_form_account")
            registration = left.text_input("Registration Number *", value=str(current.get("REGISTRATION_NUMBER") or ""), key="quota_reg_form_number")
            quota_name = left.text_input("Quota Name", value=str(current.get("QUOTA_NAME") or ""), key="quota_reg_form_name")
            quota_type = right.selectbox("Quota Type *", QUOTA_TYPES, index=option_index(list(QUOTA_TYPES), current.get("QUOTA_TYPE")), key="quota_reg_form_type")
            status = right.selectbox("Status", QUOTA_STATUSES, index=option_index(list(QUOTA_STATUSES), current.get("STATUS")), key="quota_reg_form_status")
            effective = right.date_input("Effective Date", value=as_date(current.get("EFFECTIVE_DATE"), dt.date.today()), key="quota_reg_form_effective")
            end_date = right.date_input("End Date", value=as_date(current.get("END_DATE")), key="quota_reg_form_end")
            comments = st.text_area("Comments", value=str(current.get("COMMENTS") or ""), key="quota_reg_form_comments")
        if action == "save":
            record = {"QUOTA_ID": view.record_id, "ACCOUNT_ID": account_options[account_label], "REGISTRATION_NUMBER": registration.strip(), "QUOTA_NAME": quota_name.strip() or registration.strip(), "QUOTA_TYPE": quota_type, "STATUS": status, "EFFECTIVE_DATE": effective, "END_DATE": end_date, "COMMENTS": comments.strip() or None}
            if not view.record_id: record.pop("QUOTA_ID")
            else: record["EXPECTED_UPDATED_AT"] = st.session_state.get(expected_key)
            errors = validate_quota_registration(repo, record)
            if errors:
                for error in errors: st.error(error)
            else:
                try:
                    saved_id = repo.upsert_quota_registration(record)
                    clear_widget_prefix("quota_reg_form_"); open_view("detail", saved_id)
                except (ValueError, RepositoryError) as exc: show_data_error(exc)

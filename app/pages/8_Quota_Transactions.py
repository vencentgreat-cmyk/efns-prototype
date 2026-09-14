"""Enterprise Quota Transaction list and record workspace."""

from __future__ import annotations

import datetime as dt

import pandas as pd
import streamlit as st

from app.auth import require_operational_page
from app.navigation import current_page_url, ensure_record_form_state, format_timestamp, list_command_bar, module_url, open_view, read_record_view, record_command_bar, selected_row_index, timestamp_column
from app.ui import apply_theme, clear_widget_prefix, page_header, section_intro, show_data_error
from data.constants import QUOTA_LEASE_TYPES, QUOTA_TRANSACTION_TYPES, QUOTA_TYPES, UNASSIGNED_LABEL
from data.repositories import get_repository
from data.repositories.base import RepositoryError
from data.validation import validate_quota_transaction


require_operational_page()
apply_theme()
if "repo" not in st.session_state:
    st.session_state.repo = get_repository()
repo = st.session_state.repo

if st.query_params.get("transaction_id") and not st.query_params.get("view"):
    open_view("detail", str(st.query_params["transaction_id"]))
view = read_record_view()
accounts = repo.get_accounts()
quotas = repo.get_quota_registrations()
all_transactions = repo.get_quota_transactions()
account_names = {row.ACCOUNT_ID: row.ORGANIZATION_NAME for row in accounts.itertuples()}
account_options = {f"{row.ORGANIZATION_NAME} · {row.REGISTRATION_NUMBER or row.ACCOUNT_ID[:8]}": row.ACCOUNT_ID for row in accounts.itertuples()}
quota_names = {row.QUOTA_ID: (row.QUOTA_NAME or row.REGISTRATION_NUMBER) for row in quotas.itertuples()}
quota_accounts = {row.QUOTA_ID: row.ACCOUNT_ID for row in quotas.itertuples()}
quota_types = {row.QUOTA_ID: row.QUOTA_TYPE for row in quotas.itertuples()}
quota_options = {f"{row.QUOTA_NAME or row.REGISTRATION_NUMBER} · {account_names.get(row.ACCOUNT_ID, 'Unknown')}": row.QUOTA_ID for row in quotas.itertuples()}


def as_date(value, default=None):
    converted = pd.to_datetime(value, errors="coerce")
    return default if pd.isna(converted) else converted.date()


def option_index(options, value):
    return options.index(value) if value in options else 0


def label_for_id(mapping, value, default=None):
    return next((label for label, record_id in mapping.items() if record_id == value), default if default is not None else next(iter(mapping), None))


def transaction_title(record):
    return f"{record.get('TRANSACTION_TYPE') or 'Transaction'} · {str(record.get('QUOTA_TRANSACTION_ID') or '')[:8]}"


def related_transaction_options(current_id=None):
    options = {UNASSIGNED_LABEL: None}
    for row in all_transactions.itertuples():
        if row.QUOTA_TRANSACTION_ID != current_id:
            options[f"{row.TRANSACTION_TYPE} · {str(row.QUOTA_TRANSACTION_ID)[:8]}"] = row.QUOTA_TRANSACTION_ID
    return options


if view.name == "list":
    page_header("Quota Transactions", "Search and maintain provisional quota activity records.", "QUOTA MANAGEMENT")
    st.info("Transactions represent activity. Available quota balance is not calculated or inferred by this prototype.")
    selected_index = selected_row_index("quota_tx_list_grid")
    row_ids = st.session_state.get("quota_tx_list_row_ids", [])
    selected_id = row_ids[selected_index] if selected_index is not None and selected_index < len(row_ids) else None
    action = list_command_bar("quota_tx_list", selected=bool(selected_id))
    if action == "new": open_view("new")
    if action == "refresh": st.rerun()
    if action == "delete" and selected_id: st.session_state.quota_tx_delete_pending = selected_id
    pending_delete = st.session_state.get("quota_tx_delete_pending")
    if pending_delete:
        with st.container(border=True):
            st.warning("Delete the selected Quota Transaction?")
            with st.container(horizontal=True):
                if st.button("Confirm delete", type="primary", icon=":material/delete:", key="quota_tx_confirm_delete"):
                    try:
                        repo.delete_quota_transaction(pending_delete)
                        st.session_state.pop("quota_tx_delete_pending", None); st.rerun()
                    except (ValueError, RepositoryError) as exc: show_data_error(exc)
                if st.button("Cancel", key="quota_tx_cancel_delete"):
                    st.session_state.pop("quota_tx_delete_pending", None); st.rerun()

    search_row = st.columns([5, 1])
    keyword = search_row[0].text_input("Search", placeholder="Transaction, quota or account", key="quota_tx_filter_keyword")
    with search_row[1]:
        st.write("")
        if st.button("Reset Filters", icon=":material/filter_alt_off:", key="quota_tx_reset", width="stretch"):
            clear_widget_prefix("quota_tx_filter_"); st.rerun()
    filters = st.columns(5)
    account_filter = filters[0].selectbox("Account", ["All", *account_options], key="quota_tx_filter_account")
    quota_type_filter = filters[1].selectbox("Quota Type", ["All", *QUOTA_TYPES], key="quota_tx_filter_quota_type")
    transaction_type_filter = filters[2].selectbox("Transaction Type", ["All", *QUOTA_TRANSACTION_TYPES], key="quota_tx_filter_transaction_type")
    date_from = filters[3].date_input("From", value=None, key="quota_tx_filter_from")
    date_to = filters[4].date_input("To", value=None, key="quota_tx_filter_to")
    display = repo.get_quota_transactions(
        account_id=account_options.get(account_filter),
        quota_type=None if quota_type_filter == "All" else quota_type_filter,
        transaction_type=None if transaction_type_filter == "All" else transaction_type_filter,
        date_from=date_from,
        date_to=date_to,
    ).copy()
    if not display.empty:
        display["QUOTA_NAME"] = display["QUOTA_ID"].map(quota_names)
        display["OWNER_NAME"] = display["OWNER_ACCOUNT_ID"].map(account_names)
        display["RELATED_NAME"] = display["RELATED_ACCOUNT_ID"].map(account_names)
        if keyword:
            columns = ["QUOTA_TRANSACTION_ID", "TRANSACTION_TYPE", "QUOTA_NAME", "OWNER_NAME", "RELATED_NAME"]
            display = display[display[columns].fillna("").astype(str).apply(lambda column: column.str.contains(keyword, case=False, regex=False)).any(axis=1)]
    quantity = pd.to_numeric(display.get("QUOTA_COUNT", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()
    metrics = st.columns(2)
    metrics[0].metric("Filtered transactions", f"{len(display):,}")
    metrics[1].metric("Filtered quantity", f"{quantity:,.0f}")
    if display.empty:
        st.info("No Quota Transactions match the current filters.")
    else:
        display = display.reset_index(drop=True)
        display["TRANSACTION_LINK"] = display.apply(lambda row: current_page_url(row["QUOTA_TRANSACTION_ID"], transaction_title(row)), axis=1)
        display["QUOTA_LINK"] = display.apply(lambda row: module_url("Quota_Registrations", row["QUOTA_ID"], row["QUOTA_NAME"] or row["QUOTA_ID"]), axis=1)
        display["OWNER_LINK"] = display.apply(lambda row: module_url("Accounts_&_Facilities", row["OWNER_ACCOUNT_ID"], row["OWNER_NAME"] or "Unknown"), axis=1)
        display["RELATED_ACCOUNT_LINK"] = display.apply(lambda row: module_url("Accounts_&_Facilities", row["RELATED_ACCOUNT_ID"], row["RELATED_NAME"] or "Unknown") if row.get("RELATED_ACCOUNT_ID") else None, axis=1)
        st.session_state.quota_tx_list_row_ids = display["QUOTA_TRANSACTION_ID"].tolist()
        st.dataframe(display[["TRANSACTION_LINK", "QUOTA_LINK", "OWNER_LINK", "RELATED_ACCOUNT_LINK", "TRANSACTION_TYPE", "EFFECTIVE_DATE", "QUOTA_COUNT", "PRICE", "CREATED_AT"]], width="stretch", height=520, hide_index=True, on_select="rerun", selection_mode="single-row", key="quota_tx_list_grid", column_config={"TRANSACTION_LINK": st.column_config.LinkColumn("Quota Transaction", display_text=r".*#(.*)$"), "QUOTA_LINK": st.column_config.LinkColumn("Quota Registration", display_text=r".*#(.*)$"), "OWNER_LINK": st.column_config.LinkColumn("Owner Account", display_text=r".*#(.*)$"), "RELATED_ACCOUNT_LINK": st.column_config.LinkColumn("Related Account", display_text=r".*#(.*)$"), "EFFECTIVE_DATE": st.column_config.DateColumn("Effective Date", format="YYYY-MM-DD"), "QUOTA_COUNT": st.column_config.NumberColumn("Quota Count", format="%.0f"), "PRICE": st.column_config.NumberColumn("Price", format="$%.2f"), "CREATED_AT": timestamp_column("Created On")})
else:
    current = repo.get_quota_transaction(view.record_id) if view.record_id else None
    if view.name in {"detail", "edit"} and current is None:
        page_header("Quota Transaction Not Found", "The requested record does not exist or is no longer available.", "QUOTA MANAGEMENT")
        if st.button("Back to Quota Transactions", icon=":material/arrow_back:"): open_view("list")
        st.stop()
    is_form = view.name in {"new", "edit"}
    page_header("New Quota Transaction" if view.name == "new" else transaction_title(current), "Quota activity record. Available balance is not calculated.", "QUOTA TRANSACTION")
    action = record_command_bar("quota_tx_record", view.name)
    if action in {"back", "cancel"}: open_view("detail", view.record_id) if action == "cancel" and view.record_id else open_view("list")
    if action == "refresh": st.rerun()
    if action == "edit": clear_widget_prefix("quota_tx_form_"); open_view("edit", view.record_id)
    if action == "delete" and view.record_id: st.session_state.quota_tx_record_delete_pending = True
    if st.session_state.get("quota_tx_record_delete_pending"):
        with st.container(border=True):
            st.warning("Delete this Quota Transaction?")
            with st.container(horizontal=True):
                if st.button("Confirm delete", type="primary", icon=":material/delete:", key="quota_tx_record_confirm"):
                    try:
                        repo.delete_quota_transaction(view.record_id)
                        st.session_state.pop("quota_tx_record_delete_pending", None); open_view("list")
                    except (ValueError, RepositoryError) as exc: show_data_error(exc)
                if st.button("Keep record", key="quota_tx_record_keep"):
                    st.session_state.pop("quota_tx_record_delete_pending", None); st.rerun()

    if not is_form:
        st.caption(f"Created On: {format_timestamp(current.get('CREATED_AT'))} · Updated On: {format_timestamp(current.get('UPDATED_AT'))}")
        summary, relationships = st.tabs(["Summary", "Relationships"])
        quota = repo.get_quota_registration(current.get("QUOTA_ID")) or {}
        owner_id = current.get("OWNER_ACCOUNT_ID") or quota.get("ACCOUNT_ID")
        related_account_id = current.get("RELATED_ACCOUNT_ID")
        related_quota = repo.get_quota_registration(current.get("RELATED_QUOTA_ID")) if current.get("RELATED_QUOTA_ID") else None
        related_transaction = repo.get_quota_transaction(current.get("RELATED_TRANSACTION_ID")) if current.get("RELATED_TRANSACTION_ID") else None
        with summary:
            with st.container(border=True):
                left, middle, right = st.columns(3)
                left.markdown(f"**Transaction Type**  \n{current.get('TRANSACTION_TYPE') or '—'}")
                left.markdown(f"**Effective Date**  \n{as_date(current.get('EFFECTIVE_DATE'), '—')}")
                left.markdown(f"**End Date**  \n{as_date(current.get('END_DATE'), '—')}")
                middle.markdown(f"**Quota Count**  \n{float(current.get('QUOTA_COUNT') or 0):,.0f}")
                middle.markdown(f"**Price**  \n${float(current.get('PRICE') or 0):,.2f}")
                middle.markdown(f"**Lease Type**  \n{current.get('QUOTA_LEASE_TYPE') or '—'}")
                right.markdown(f"**Comments**  \n{current.get('COMMENTS') or 'No comments.'}")
                st.info("This page shows transaction activity only. No available quota balance has been inferred.")
        with relationships:
            with st.container(border=True):
                if quota:
                    st.markdown(f"**Quota Registration**  \n[{quota_names.get(quota['QUOTA_ID'], quota['QUOTA_ID'])}]({module_url('Quota_Registrations', quota['QUOTA_ID'], quota_names.get(quota['QUOTA_ID'], quota['QUOTA_ID']))})")
                if owner_id:
                    st.markdown(f"**Owner Account**  \n[{account_names.get(owner_id, 'Unknown')}]({module_url('Accounts_&_Facilities', owner_id, account_names.get(owner_id, 'Unknown'))})")
                if related_account_id:
                    st.markdown(f"**Related Account**  \n[{account_names.get(related_account_id, 'Unknown')}]({module_url('Accounts_&_Facilities', related_account_id, account_names.get(related_account_id, 'Unknown'))})")
                else: st.markdown("**Related Account**  \n—")
                if related_quota:
                    label = quota_names.get(related_quota["QUOTA_ID"], related_quota["QUOTA_ID"])
                    st.markdown(f"**Related Quota**  \n[{label}]({module_url('Quota_Registrations', related_quota['QUOTA_ID'], label)})")
                else: st.markdown("**Related Quota**  \n—")
                if related_transaction:
                    label = transaction_title(related_transaction)
                    st.markdown(f"**Related Transaction**  \n[{label}]({current_page_url(related_transaction['QUOTA_TRANSACTION_ID'], label)})")
                else: st.markdown("**Related Transaction**  \n—")
    else:
        current = current or {}
        if quotas.empty:
            st.error("Create a Quota Registration before creating a Quota Transaction."); st.stop()
        ensure_record_form_state("quota_tx_form_", view.record_id)
        expected_key = f"quota_tx_form_expected_{view.record_id}"
        if view.name == "edit": st.session_state.setdefault(expected_key, current.get("UPDATED_AT"))
        requested_quota = st.query_params.get("quota_id")
        selected_quota_id = current.get("QUOTA_ID") or (str(requested_quota) if requested_quota in set(quota_options.values()) else None)
        optional_accounts = {UNASSIGNED_LABEL: None, **account_options}
        optional_quotas = {UNASSIGNED_LABEL: None, **quota_options}
        transaction_options = related_transaction_options(view.record_id)
        with st.container(border=True):
            left, right = st.columns(2)
            quota_label = left.selectbox("Quota Registration *", list(quota_options), index=option_index(list(quota_options), label_for_id(quota_options, selected_quota_id)), key="quota_tx_form_quota")
            quota_id = quota_options[quota_label]
            owner_id = quota_accounts[quota_id]
            left.text_input("Owner Account", value=account_names.get(owner_id, "Unknown"), disabled=True, key="quota_tx_form_owner")
            transaction_type = left.selectbox("Transaction Type *", QUOTA_TRANSACTION_TYPES, index=option_index(list(QUOTA_TRANSACTION_TYPES), current.get("TRANSACTION_TYPE")), key="quota_tx_form_type")
            effective_date = left.date_input("Effective Date *", value=as_date(current.get("EFFECTIVE_DATE"), dt.date.today()), key="quota_tx_form_effective")
            end_date = left.date_input("End Date", value=as_date(current.get("END_DATE")), key="quota_tx_form_end")
            quota_count = left.number_input("Quota Count *", min_value=0.0, value=float(current.get("QUOTA_COUNT") or 0), step=1.0, key="quota_tx_form_count")
            related_account_label = right.selectbox("Related Account *", list(optional_accounts), index=option_index(list(optional_accounts), label_for_id(optional_accounts, current.get("RELATED_ACCOUNT_ID"), UNASSIGNED_LABEL)), key="quota_tx_form_related_account")
            related_quota_label = right.selectbox("Related Quota", list(optional_quotas), index=option_index(list(optional_quotas), label_for_id(optional_quotas, current.get("RELATED_QUOTA_ID"), UNASSIGNED_LABEL)), key="quota_tx_form_related_quota")
            related_transaction_label = right.selectbox("Related Transaction", list(transaction_options), index=option_index(list(transaction_options), label_for_id(transaction_options, current.get("RELATED_TRANSACTION_ID"), UNASSIGNED_LABEL)), key="quota_tx_form_related_transaction")
            price = right.number_input("Price", min_value=0.0, value=float(current.get("PRICE") or 0), step=1.0, key="quota_tx_form_price")
            lease_options = ["Not applicable", *QUOTA_LEASE_TYPES]
            lease_type = right.selectbox("Quota Lease Type", lease_options, index=option_index(lease_options, current.get("QUOTA_LEASE_TYPE") or "Not applicable"), key="quota_tx_form_lease")
            comments = right.text_area("Comments", value=str(current.get("COMMENTS") or ""), key="quota_tx_form_comments")
        if action == "save":
            record = {"QUOTA_TRANSACTION_ID": view.record_id, "QUOTA_ID": quota_id, "OWNER_ACCOUNT_ID": owner_id, "TRANSACTION_TYPE": transaction_type, "EFFECTIVE_DATE": effective_date, "END_DATE": end_date, "QUOTA_COUNT": quota_count, "RELATED_ACCOUNT_ID": optional_accounts[related_account_label], "RELATED_QUOTA_ID": optional_quotas[related_quota_label], "RELATED_TRANSACTION_ID": transaction_options[related_transaction_label], "PRICE": price, "QUOTA_LEASE_TYPE": None if lease_type == "Not applicable" else lease_type, "COMMENTS": comments.strip() or None}
            if not view.record_id: record.pop("QUOTA_TRANSACTION_ID")
            else: record["EXPECTED_UPDATED_AT"] = st.session_state.get(expected_key)
            errors = validate_quota_transaction(repo, record)
            if errors:
                for error in errors: st.error(error)
            else:
                try:
                    saved_id = repo.upsert_quota_transaction(record)
                    clear_widget_prefix("quota_tx_form_"); open_view("detail", saved_id)
                except (ValueError, RepositoryError) as exc: show_data_error(exc)

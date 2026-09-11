"""Independent flock transaction workspace."""

import datetime as dt

import streamlit as st

from app.ui import apply_theme, clear_widget_prefix, page_header, section_intro
from data.constants import FLOCK_TRANSACTION_TYPES
from data.repositories import get_repository

apply_theme()
if "repo" not in st.session_state:
    st.session_state.repo = get_repository()
repo = st.session_state.repo

def option_index(options, value, default=0):
    return options.index(value) if value in options else default

def label_for_id(mapping, value):
    return next((label for label, item_id in mapping.items() if item_id == value), None)

page_header("Flock Transactions", "Record and review events linked to a stable Flock ID.", "FLOCK MANAGEMENT")
st.caption("Transaction types are provisional; no automatic inventory calculation is performed.")

accounts = repo.get_accounts()
facilities = repo.get_facilities()
flocks = repo.get_flocks()
account_map = {row.ACCOUNT_ID: row.ORGANIZATION_NAME for row in accounts.itertuples()}
facility_map = {row.FACILITY_ID: row.FACILITY_NAME for row in facilities.itertuples()}
flock_labels = {
    f"{row.FLOCK_NUMBER} · {account_map.get(row.ACCOUNT_ID, 'Unknown account')}": row.FLOCK_ID
    for row in flocks.itertuples()
}

filter_label = st.selectbox("Flock filter", ["All", *flock_labels], key="flock_tx_filter")
transactions = repo.get_flock_transactions(flock_id=flock_labels.get(filter_label))
if transactions.empty:
    st.info("No flock transactions match the current filter.")
else:
    context = flocks[["FLOCK_ID", "FLOCK_NUMBER", "ACCOUNT_ID", "FACILITY_ID"]]
    display = transactions.merge(context, on="FLOCK_ID", how="left")
    display["ACCOUNT"] = display["ACCOUNT_ID"].map(account_map)
    display["FACILITY"] = display["FACILITY_ID"].map(facility_map).fillna("Unassigned")
    st.dataframe(
        display[["FLOCK_TRANSACTION_ID", "FLOCK_NUMBER", "ACCOUNT", "FACILITY", "TRANSACTION_TYPE", "QUANTITY", "TRANSACTION_DATE", "NOTES"]],
        width="stretch", height=440, hide_index=True,
    )

with st.expander("Add or edit a flock transaction", expanded=False):
    transaction_options = {
        f"{row.TRANSACTION_TYPE} · {row.TRANSACTION_DATE} · {row.FLOCK_TRANSACTION_ID[:8]}": row.FLOCK_TRANSACTION_ID
        for row in repo.get_flock_transactions().itertuples()
    }
    edit_label = st.selectbox("Record", ["Create new", *transaction_options], key="flock_tx_record", on_change=clear_widget_prefix, args=("flock_tx_", ("flock_tx_record",)))
    current = {}
    if edit_label != "Create new":
        selected_id = transaction_options[edit_label]
        current = repo.get_flock_transactions()
        current = current[current["FLOCK_TRANSACTION_ID"] == selected_id].iloc[0].to_dict()
    left, right = st.columns(2)
    flock_options = list(flock_labels)
    flock_label = left.selectbox("Flock *", flock_options, index=option_index(flock_options, label_for_id(flock_labels, current.get("FLOCK_ID"))), key="flock_tx_flock")
    transaction_type = left.selectbox("Transaction Type *", FLOCK_TRANSACTION_TYPES, index=option_index(list(FLOCK_TRANSACTION_TYPES), current.get("TRANSACTION_TYPE")), key="flock_tx_type")
    quantity = right.number_input("Quantity *", min_value=1, value=max(1, int(current.get("QUANTITY") or 1)), key="flock_tx_quantity")
    transaction_date = right.date_input("Transaction Date *", value=current.get("TRANSACTION_DATE") or dt.date.today(), key="flock_tx_date")
    notes = st.text_area("Notes", value=str(current.get("NOTES") or ""), key="flock_tx_notes")
    if st.button("Save Flock Transaction", type="primary", key="flock_tx_save"):
        try:
            transaction_id = repo.upsert_flock_transaction(
                {
                    "FLOCK_TRANSACTION_ID": current.get("FLOCK_TRANSACTION_ID"),
                    "FLOCK_ID": flock_labels[flock_label],
                    "TRANSACTION_TYPE": transaction_type,
                    "QUANTITY": quantity,
                    "TRANSACTION_DATE": transaction_date,
                    "NOTES": notes or None,
                }
            )
            st.success(f"Flock transaction saved: {transaction_id}")
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))

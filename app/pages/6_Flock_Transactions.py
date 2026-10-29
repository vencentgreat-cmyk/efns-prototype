from app.services.form_safety import open_saved_record, stored_index, capture_form, preserve_form, save_form, stored_options, start_new_form, begin_form, field_changed, delete_confirmation
from data.producer_identity import text as stored_text
from data.business_time import halifax_today
"""Flock Transaction list and record workspace."""
import datetime as dt
import uuid
import pandas as pd
import streamlit as st

from app.auth import require_operational_page, can_current
from app.security import Permission
from app.navigation import format_timestamp, list_command_bar, open_module, open_view, read_record_view, record_command_bar, selected_row_index, timestamp_column
from app.ui import apply_theme, clear_widget_prefix, page_header, show_data_error, optional_form_date
from data.constants import FLOCK_TRANSACTION_TYPES
from data.repositories import get_repository
from data.repositories.base import RepositoryError

require_operational_page()
st.caption('Historical/activity entries do not change Bird Count. New current Count/Removal can explicitly update Bird Count below; Delivery and Sale remain activity only. No automatic lifecycle ending or quota-balance inference.')
apply_theme()
if "repo" not in st.session_state:
    st.session_state.repo = get_repository()
repo = st.session_state.repo; view = read_record_view()
transactions = repo.get_flock_transactions(); flocks = repo.get_flocks(); accounts = repo.get_accounts(); facilities = repo.get_facilities()
account_names = {row.ACCOUNT_ID: row.ORGANIZATION_NAME for row in accounts.itertuples()}
facility_names = {row.FACILITY_ID: row.FACILITY_NAME for row in facilities.itertuples()}
flock_names = {row.FLOCK_ID: row.FLOCK_NUMBER for row in flocks.itertuples()}
flock_options = {f"{row.FLOCK_NUMBER} · {account_names.get(row.ACCOUNT_ID, 'Unknown')}": row.FLOCK_ID for row in flocks.itertuples()}

def option_index(options, value): return options.index(value) if value in options else 0
def label_for_id(mapping, value): return next((label for label, item_id in mapping.items() if item_id == value), next(iter(mapping), None))
def get_record(record_id):
    match = transactions[transactions["FLOCK_TRANSACTION_ID"] == record_id]
    return match.iloc[0].to_dict() if not match.empty else None

if view.name == "list":
    page_header("Flock Transactions", "Search and maintain Flock-linked activity records.", "FLOCK MANAGEMENT")
    selected_index = selected_row_index("flock_tx_grid"); ids = st.session_state.get("flock_tx_row_ids", [])
    selected_id = ids[selected_index] if selected_index is not None and selected_index < len(ids) else None
    action = list_command_bar("flock_tx_list", bool(selected_id))
    if action == "new": start_new_form('flock_tx_form_'); open_view("new")
    if action == "view" and selected_id: open_view("detail", selected_id)
    if action == "refresh": clear_widget_prefix("flock_tx_filter_"); st.rerun()
    if action == "delete" and selected_id: st.session_state['flock_tx_form___delete_pending']=selected_id
    filters = st.columns([2, 1, 1])
    keyword = filters[0].text_input("Filter by keyword", placeholder="Flock, type or notes", key="flock_tx_filter_keyword")
    flock_filter = filters[1].selectbox("Flock", ["All", *flock_options], key="flock_tx_filter_flock")
    type_filter = filters[2].selectbox("Transaction type", ["All", *FLOCK_TRANSACTION_TYPES], key="flock_tx_filter_type")
    display = transactions.copy(); display["FLOCK_NUMBER"] = display["FLOCK_ID"].map(flock_names)
    if keyword: display = display[display[["FLOCK_NUMBER", "TRANSACTION_TYPE", "NOTES"]].fillna("").astype(str).apply(lambda col: col.str.contains(keyword, case=False, regex=False)).any(axis=1)]
    if flock_filter != "All": display = display[display["FLOCK_ID"] == flock_options[flock_filter]]
    if type_filter != "All": display = display[display["TRANSACTION_TYPE"] == type_filter]
    st.caption(f"{len(display):,} flock transaction(s)")
    if display.empty: st.info("No Flock Transactions match the current filters.")
    else:
        display = display.reset_index(drop=True); st.session_state.flock_tx_row_ids = display["FLOCK_TRANSACTION_ID"].tolist()
        display["TRANSACTION"] = display.apply(lambda row: f"{row['TRANSACTION_TYPE']} · {str(row['FLOCK_TRANSACTION_ID'])[:8]}", axis=1)
        st.dataframe(display[["TRANSACTION", "FLOCK_NUMBER", "QUANTITY", "TRANSACTION_DATE", "NOTES", "CREATED_AT"]], width="stretch", height=540, hide_index=True, on_select="rerun", selection_mode="single-row", key="flock_tx_grid", column_config={"TRANSACTION": "Transaction", "FLOCK_NUMBER": "Flock", "CREATED_AT": timestamp_column("Created On")})
else:
    current = get_record(view.record_id) if view.record_id else None
    if view.name in {"detail", "edit"} and current is None: st.error("The requested Transaction could not be found."); st.stop()
    is_form = view.name in {"new", "edit"}; title = "New Flock Transaction" if view.name == "new" else f"{current['TRANSACTION_TYPE']} · {str(current['FLOCK_TRANSACTION_ID'])[:8]}"
    page_header(title, "Flock-linked activity record.", "FLOCK TRANSACTION")
    action = record_command_bar("flock_tx_record", view.name)
    if action in {"back", "cancel"}: start_new_form("flock_tx_form_"); open_view("detail", view.record_id) if action == "cancel" and view.record_id else open_view("list")
    if action == "edit": start_new_form("flock_tx_form_"); open_view("edit", view.record_id)
    if action == "delete": st.session_state['flock_tx_form___delete_pending']=view.record_id
    if not is_form:
        st.caption(f"Created On: {format_timestamp(current.get('CREATED_AT'))} · Updated On: {format_timestamp(current.get('UPDATED_AT'))}")
        summary, related = st.tabs(["Summary", "Related Records"])
        with summary:
            with st.container(border=True):
                st.markdown(f"**Flock**  \n{flock_names.get(current['FLOCK_ID'], 'Unknown')}")
                st.markdown(f"**Transaction Type**  \n{current['TRANSACTION_TYPE']}")
                count_source = current.get("COUNT_SOURCE_LABEL")
                st.markdown(f"**Count Source**  \n{count_source if pd.notna(count_source) else 'Not supplied'}")
                st.markdown(f"**Quantity**  \n{current['QUANTITY']}")
                st.markdown(f"**Transaction Date**  \n{current['TRANSACTION_DATE']}")
                st.markdown(f"**Notes**  \n{current.get('NOTES') or '—'}")
        with related:
            if st.button("Open related Flock", icon=":material/visibility:"):
                open_module("Flocks", "detail", current["FLOCK_ID"])
    else:
        current = current or {}
        begin_form('flock_tx_form_',view.record_id)
        expected_key = f"flock_tx_form_expected_{view.record_id}"
        if view.name == "edit" and view.record_id:
            st.session_state.setdefault(expected_key, current.get("UPDATED_AT"))
        with st.container(border=True):
            flock_label = st.selectbox("Flock *", list(flock_options), index=option_index(list(flock_options), label_for_id(flock_options, current.get("FLOCK_ID"))), key="flock_tx_form_flock")
            transaction_type = st.selectbox("Transaction Type *", stored_options(FLOCK_TRANSACTION_TYPES,current.get("TRANSACTION_TYPE"),bool(view.record_id)), index=(stored_index(FLOCK_TRANSACTION_TYPES,current.get("TRANSACTION_TYPE")) if view.record_id else option_index(list(FLOCK_TRANSACTION_TYPES), current.get("TRANSACTION_TYPE"))), key="flock_tx_form_type")
            quantity_minimum=0 if transaction_type == 'Count' else 1
            stored_quantity=current.get('QUANTITY')
            quantity_default=1 if stored_quantity is None or pd.isna(stored_quantity) else int(stored_quantity)
            quantity = st.text_input("Quantity *",value=stored_text(stored_quantity),key="flock_tx_form_quantity") if view.record_id else st.number_input("Quantity *", min_value=quantity_minimum, value=1, key="flock_tx_form_quantity",help='Zero is valid only when Count is explicitly confirmed as a current quantity observation. Removal, Delivery, Sale and unconfirmed activity require a positive whole number.')
            transaction_date = st.date_input("Transaction Date *", value=(optional_form_date(current.get("TRANSACTION_DATE")) if view.record_id else halifax_today()), key="flock_tx_form_date")
            notes = st.text_area("Notes", value=str(current.get("NOTES") or ""), key="flock_tx_form_notes")
            apply_current=False
            quantity_reason=''
            if not view.record_id and transaction_type in ('Count','Removal'):
                reviewed=repo.get_flock(flock_options[flock_label])
                version_key='flock_tx_form_quantity_version_'+reviewed['FLOCK_ID']
                review_key='flock_tx_form_quantity_review_'+reviewed['FLOCK_ID']
                st.session_state.setdefault(review_key,{'UPDATED_AT':reviewed.get('UPDATED_AT'),'BIRD_COUNT':reviewed.get('BIRD_COUNT')})
                observed=st.session_state[review_key]
                st.session_state.setdefault(version_key,observed['UPDATED_AT'])
                st.caption(f"Reviewed Bird Count: {observed.get('BIRD_COUNT')}. Confirmed Count replaces it, including a genuine zero observation; Removal deducts a positive quantity once. Partial removal does not clear the Flock; Status and Birds Disposed are not changed. Only today's (Halifax) confirmed activity may apply; older rows remain activity only.")
                if st.button('Reload reviewed Bird Count',key='flock_tx_form_reload_quantity'):
                    st.session_state['_flock_tx_reason_draft']=st.session_state.get('flock_tx_form_quantity_reason','')
                    st.session_state[review_key]={'UPDATED_AT':reviewed.get('UPDATED_AT'),'BIRD_COUNT':reviewed.get('BIRD_COUNT')}
                    st.session_state[version_key]=reviewed.get('UPDATED_AT')
                    st.session_state['flock_tx_form_apply_'+reviewed['FLOCK_ID']]=False
                    st.session_state.pop('flock_tx_form_quantity_request',None)
                    st.rerun()
                apply_current=st.checkbox('Apply this confirmed current Count/Removal to Bird Count',key='flock_tx_form_apply_'+reviewed['FLOCK_ID'],disabled=not can_current(Permission.UPDATE_DATA))
                if 'flock_tx_form_quantity_reason' not in st.session_state:
                    st.session_state['flock_tx_form_quantity_reason']=st.session_state.get('_flock_tx_reason_draft','')
                quantity_reason=st.text_input('Reason/evidence for current quantity',key='flock_tx_form_quantity_reason')
                st.session_state.setdefault('flock_tx_form_quantity_request',uuid.uuid4().hex)
        capture_form('flock_tx_form_',current,{'FLOCK_ID': ['flock_tx_form_flock'], 'TRANSACTION_TYPE': ['flock_tx_form_type'], 'QUANTITY': ['flock_tx_form_quantity'], 'TRANSACTION_DATE': ['flock_tx_form_date'], 'NOTES': ['flock_tx_form_notes']})
        if view.record_id: st.text_input("Reason for correction *",key='flock_tx_form_revision_reason')
        if action == "save":
            record = {"FLOCK_TRANSACTION_ID": view.record_id, "FLOCK_ID": flock_options[flock_label], "TRANSACTION_TYPE": transaction_type, "QUANTITY": quantity, "TRANSACTION_DATE": transaction_date, "NOTES": notes or None}
            if not view.record_id: record.pop("FLOCK_TRANSACTION_ID")
            else: record["EXPECTED_UPDATED_AT"] = st.session_state.get(expected_key)
            try:
                if apply_current:
                    saved_id=repo.record_current_flock_quantity(record,st.session_state.flock_tx_form_quantity_request,st.session_state.get(version_key),quantity_reason,confirmed=True,expected_bird_count=st.session_state[review_key]['BIRD_COUNT'])
                else:
                    saved_id=save_form(repo,'FLOCK_TRANSACTION',record,current,'flock_tx_form_')
                open_saved_record(saved_id)
            except Exception as exc: show_data_error(exc)

_pending=st.session_state.get('flock_tx_form___delete_pending')
if _pending and delete_confirmation(repo,'delete_flock_transaction',_pending,'flock_tx_form___delete'):
    st.session_state.pop('flock_tx_form___delete_pending',None)
    open_view("list")

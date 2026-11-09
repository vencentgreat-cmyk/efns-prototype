"""Enterprise Salmonella Test list, detail, new and edit workspace."""

from __future__ import annotations

from app.services.form_safety import open_saved_record, stored_index, capture_form, preserve_form, save_form, stored_options, start_new_form, begin_form, field_changed, delete_confirmation
from data.producer_identity import text as stored_text
from data.business_time import halifax_today

import datetime as dt
import pandas as pd
import streamlit as st

from app.auth import require_operational_page
from app.navigation import format_timestamp, list_command_bar, open_module, open_view, read_record_view, record_command_bar, selected_row_index, timestamp_column
from app.ui import apply_theme, clear_widget_prefix, optional_form_date, page_header, section_intro, show_data_error
from data.constants import SALMONELLA_RESULTS, UNASSIGNED_LABEL
from data.repositories import get_repository
from app.services.selector_options import unique_identity_options, historical_filter_options
from data.repositories.base import RepositoryError
from data.validation import validate_salmonella_test

require_operational_page()
apply_theme()
if "repo" not in st.session_state:
    st.session_state.repo = get_repository()
repo = st.session_state.repo
view = read_record_view()
tests, flocks = repo.get_salmonella_tests(), repo.get_flocks()
accounts, facilities = repo.get_accounts(), repo.get_facilities()
account_names = {row.ACCOUNT_ID: row.ORGANIZATION_NAME for row in accounts.itertuples()}
facility_names = {row.FACILITY_ID: row.FACILITY_NAME for row in facilities.itertuples()}
flock_names = {row.FLOCK_ID: row.FLOCK_NUMBER for row in flocks.itertuples()}
flock_facilities = {row.FLOCK_ID: row.FACILITY_ID for row in flocks.itertuples()}
flock_options = unique_identity_options((f"{row.FLOCK_NUMBER} · {account_names.get(row.ACCOUNT_ID, 'Unknown')} · {row.PERMIT_NUMBER}", row.FLOCK_ID) for row in flocks.itertuples())


def option_index(options, value):
    return options.index(value) if value in options else 0


def label_for_id(mapping, value):
    return next((label for label, record_id in mapping.items() if record_id == value), next(iter(mapping), None))


def test_label(row):
    return f"{row.get('PERMIT_NUMBER') or 'Test'} · {row.get('TESTING_DATE')}"


if view.name == "list":
    page_header("Salmonella Tests", "Search and maintain flock-linked tests and result records.", "FLOCK MANAGEMENT")
    st.info("Inspector is provisional free text. Sample-level business fields await authoritative metadata.")
    selected_index = selected_row_index("salmonella_list_grid")
    row_ids = st.session_state.get("salmonella_list_row_ids", [])
    selected_id = row_ids[selected_index] if selected_index is not None and selected_index < len(row_ids) else None
    action = list_command_bar("salmonella_list", selected=bool(selected_id))
    if action == "new": start_new_form('salmonella_form_'); open_view("new")
    if action == "view" and selected_id: open_view("detail", selected_id)
    if action == "refresh": clear_widget_prefix("salmonella_filter_"); st.rerun()
    if action == "delete" and selected_id: st.session_state['salmonella_form___delete_pending']=selected_id

    filters = st.columns([2, 1, 1])
    keyword = filters[0].text_input("Filter by keyword", placeholder="Permit, flock, inspector or case number", key="salmonella_filter_keyword")
    result_filter = filters[1].selectbox("Result", ["All", *historical_filter_options(SALMONELLA_RESULTS, tests.get("TEST_RESULT", []))], key="salmonella_filter_result")
    account_options = unique_identity_options(((account_names[row.ACCOUNT_ID], row.ACCOUNT_ID) for row in accounts.itertuples()), reserved_labels=('All',))
    account_filter = filters[2].selectbox("Account", ["All", *account_options], key="salmonella_filter_account")
    display = tests.copy()
    if not display.empty:
        display["FLOCK_NUMBER"] = display["FLOCK_ID"].map(flock_names)
        display["ACCOUNT_NAME"] = display["ACCOUNT_ID"].map(account_names)
        display["FACILITY_ID"] = display["FLOCK_ID"].map(flock_facilities)
        display["FACILITY_NAME"] = display["FACILITY_ID"].map(facility_names).fillna(UNASSIGNED_LABEL)
        if keyword:
            cols = ["PERMIT_NUMBER", "FLOCK_NUMBER", "INSPECTOR", "CASE_FILE_NUMBER"]
            display = display[display[cols].fillna("").astype(str).apply(lambda col: col.str.contains(keyword, case=False, regex=False)).any(axis=1)]
        if result_filter != "All": display = display[display["TEST_RESULT"] == result_filter]
        if account_filter != "All": display = display[display["ACCOUNT_ID"] == account_options[account_filter]]
    st.caption(f"{len(display):,} Salmonella test record(s)")
    if display.empty:
        st.info("No Salmonella Tests match the current filters.")
    else:
        display = display.reset_index(drop=True)
        display["TEST"] = display.apply(lambda row: test_label(row), axis=1)
        st.session_state.salmonella_list_row_ids = display["SALMONELLA_TEST_ID"].tolist()
        st.dataframe(display[["TEST", "ACCOUNT_NAME", "FLOCK_NUMBER", "FACILITY_NAME", "TEST_RESULT", "INSPECTOR", "NUMBER_OF_SAMPLES", "DATE_RECEIVED", "CREATED_AT"]], width="stretch", height=540, hide_index=True, on_select="rerun", selection_mode="single-row", key="salmonella_list_grid", column_config={"TEST": "Test", "ACCOUNT_NAME": "Account", "FLOCK_NUMBER": "Flock", "FACILITY_NAME": "Facility", "CREATED_AT": timestamp_column("Created On")})
else:
    current = repo.get_salmonella_test(view.record_id) if view.record_id else None
    if view.name in {"detail", "edit"} and current is None:
        st.error("The requested Salmonella Test could not be found.")
        if st.button("Back to Salmonella Tests"): open_view("list")
        st.stop()
    is_form = view.name in {"new", "edit"}
    page_header("New Salmonella Test" if view.name == "new" else test_label(current), "Test result, sample count, case and invoice information.", "SALMONELLA TEST")
    action = record_command_bar("salmonella_record", view.name)
    if action in {"back", "cancel"}: start_new_form("salmonella_form_"); open_view("detail", view.record_id) if action == "cancel" and view.record_id else open_view("list")
    if action == "edit": start_new_form("salmonella_form_"); open_view("edit", view.record_id)
    if action == "delete" and view.record_id: st.session_state['salmonella_form___delete_pending']=view.record_id
    if not is_form:
        st.caption(f"Created On: {format_timestamp(current.get('CREATED_AT'))} · Updated On: {format_timestamp(current.get('UPDATED_AT'))}")
        summary, details, related = st.tabs(["Summary", "Details", "Related Records"])
        flock = repo.get_flock(current.get("FLOCK_ID")) or {}
        with summary:
            with st.container(border=True):
                left, middle, right = st.columns(3)
                left.markdown(f"**Permit Number**  \n{current.get('PERMIT_NUMBER') or '—'}")
                left.markdown(f"**Flock**  \n{flock.get('FLOCK_NUMBER') or 'Unknown'}")
                left.markdown(f"**Account**  \n{account_names.get(current.get('ACCOUNT_ID'), 'Unknown')}")
                middle.markdown(f"**Testing Date**  \n{current.get('TESTING_DATE')}")
                middle.markdown(f"**Test Result**  \n{current.get('TEST_RESULT')}")
                middle.markdown(f"**Samples**  \n{int(current.get('NUMBER_OF_SAMPLES') or 0):,}")
                right.markdown(f"**Inspector**  \n{current.get('INSPECTOR') or '—'}")
                right.markdown(f"**Case / File Number**  \n{current.get('CASE_FILE_NUMBER') or '—'}")
                right.markdown(f"**Invoice Number**  \n{current.get('INVOICE_NUMBER') or '—'}")
        with details:
            detail_fields = [key for key in current if key not in {"CREATED_AT", "UPDATED_AT"}]
            st.dataframe(pd.DataFrame({"Field": [key.replace("_", " ").title() for key in detail_fields], "Value": [str(current[key]) if current[key] is not None else "—" for key in detail_fields]}), width="stretch", hide_index=True)
        with related:
            section_intro("Flock")
            if flock:
                st.write(flock["FLOCK_NUMBER"])
                if st.button("Open related Flock", icon=":material/visibility:"):
                    open_module("Flocks", "detail", flock["FLOCK_ID"])
            else: st.info("The related Flock is unavailable.")
            section_intro("Test Samples")
            sample_rows = repo.get_salmonella_test_samples(view.record_id)
            if sample_rows.empty: st.info("No related Test Samples.")
            else: st.dataframe(sample_rows, width="stretch", hide_index=True)
    else:
        current = current or {}
        begin_form('salmonella_form_',view.record_id)
        expected_key = f"salmonella_form_expected_{view.record_id}"
        if view.name == "edit" and view.record_id:
            st.session_state.setdefault(expected_key, current.get("UPDATED_AT"))
        if not flock_options:
            st.error("Create a Flock before creating a Salmonella Test."); st.stop()
        with st.container(border=True):
            summary, result_details = st.tabs(["Summary & Relationship", "Result & Invoice"])
            with summary:
                left, right = st.columns(2)
                flock_label = left.selectbox("Flock / Permit Number *", list(flock_options), index=option_index(list(flock_options), label_for_id(flock_options, current.get("FLOCK_ID"))), key="salmonella_form_flock")
                flock = repo.get_flock(flock_options[flock_label])
                left.text_input("Account", value=account_names.get(flock["ACCOUNT_ID"], ""), disabled=True)
                left.text_input("Permit Number", value=str(flock.get("PERMIT_NUMBER") or ""), disabled=True)
                testing_date = right.date_input("Testing Date *", value=(optional_form_date(current.get("TESTING_DATE")) if view.record_id else halifax_today()), key="salmonella_form_testing")
                samples = right.text_input("Number of Samples *",value=stored_text(current.get("NUMBER_OF_SAMPLES")),key='salmonella_form_samples') if view.record_id else right.number_input("Number of Samples *", min_value=0, value=int(current.get("NUMBER_OF_SAMPLES") or 0), key="salmonella_form_samples")
                inspector = right.text_input("Inspector", value=str(current.get("INSPECTOR") or ""), key="salmonella_form_inspector")
            with result_details:
                left, right = st.columns(2)
                result = left.selectbox("Test Result", stored_options(SALMONELLA_RESULTS,current.get("TEST_RESULT"),bool(view.record_id)), index=(stored_index(SALMONELLA_RESULTS,current.get("TEST_RESULT")) if view.record_id else option_index(list(SALMONELLA_RESULTS), current.get("TEST_RESULT"))), key="salmonella_form_result")
                received = left.date_input("Date Received", value=optional_form_date(current.get("DATE_RECEIVED")), key="salmonella_form_received")
                result_sent = left.date_input("Date Result Sent", value=optional_form_date(current.get("DATE_RESULT_SENT")), key="salmonella_form_sent")
                case_number = left.text_input("Case / File Number", value=str(current.get("CASE_FILE_NUMBER") or ""), key="salmonella_form_case")
                invoice_number = right.text_input("Invoice Number", value=str(current.get("INVOICE_NUMBER") or ""), key="salmonella_form_invoice")
                invoice_date = right.date_input("Invoice Date", value=optional_form_date(current.get("INVOICE_DATE")), key="salmonella_form_invoice_date")
                comments = right.text_area("Comments", value=str(current.get("COMMENTS") or ""), key="salmonella_form_comments")
        capture_form('salmonella_form_',current,{'FLOCK_ID': ['salmonella_form_flock'], 'ACCOUNT_ID': ['salmonella_form_flock'], 'PERMIT_NUMBER': ['salmonella_form_flock'], 'TESTING_DATE': ['salmonella_form_testing'], 'INSPECTOR': ['salmonella_form_inspector'], 'NUMBER_OF_SAMPLES': ['salmonella_form_samples'], 'TEST_RESULT': ['salmonella_form_result'], 'DATE_RECEIVED': ['salmonella_form_received'], 'DATE_RESULT_SENT': ['salmonella_form_sent'], 'CASE_FILE_NUMBER': ['salmonella_form_case'], 'INVOICE_NUMBER': ['salmonella_form_invoice'], 'INVOICE_DATE': ['salmonella_form_invoice_date'], 'COMMENTS': ['salmonella_form_comments']})
        if view.record_id: st.text_input("Reason for correction *",key='salmonella_form_revision_reason')
        if action == "save":
            record = {"SALMONELLA_TEST_ID": view.record_id, "FLOCK_ID": flock["FLOCK_ID"], "ACCOUNT_ID": flock["ACCOUNT_ID"], "PERMIT_NUMBER": flock["PERMIT_NUMBER"], "TESTING_DATE": testing_date, "INSPECTOR": inspector or None, "NUMBER_OF_SAMPLES": samples, "TEST_RESULT": result, "DATE_RECEIVED": received, "DATE_RESULT_SENT": result_sent, "CASE_FILE_NUMBER": case_number or None, "INVOICE_NUMBER": invoice_number or None, "INVOICE_DATE": invoice_date, "COMMENTS": comments or None}
            if not view.record_id: record.pop("SALMONELLA_TEST_ID")
            else: record["EXPECTED_UPDATED_AT"] = st.session_state.get(expected_key)
            errors = validate_salmonella_test(repo, record) if not view.record_id else []
            if errors:
                for error in errors: st.error(error)
            else:
                try:
                    saved_id = save_form(repo,'SALMONELLA_TEST',record,current,'salmonella_form_')
                    open_saved_record(saved_id)
                except Exception as exc: show_data_error(exc)

_pending=st.session_state.get('salmonella_form___delete_pending')
if _pending and delete_confirmation(repo,'delete_salmonella_test',_pending,'salmonella_form___delete'):
    st.session_state.pop('salmonella_form___delete_pending',None)
    open_view("list")

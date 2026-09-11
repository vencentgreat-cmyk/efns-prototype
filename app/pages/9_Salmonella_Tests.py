"""Independent Salmonella testing workspace."""

import datetime as dt

import streamlit as st

from app.services.salmonella_reporting import build_salmonella_report
from app.ui import apply_theme, page_header
from data.constants import SALMONELLA_RESULTS
from data.repositories import get_repository
from data.validation import validate_salmonella_test

apply_theme()
if "repo" not in st.session_state:
    st.session_state.repo = get_repository()
repo = st.session_state.repo
page_header("Salmonella Tests", "Maintain flock-linked tests, result dates, case references, and invoices.", "FLOCK MANAGEMENT")
st.info("Inspector is provisional free text. Sample-level business fields await authoritative metadata.")

flocks = repo.get_flocks()
accounts = repo.get_accounts()
facilities = repo.get_facilities()
account_names = {row.ACCOUNT_ID: row.ORGANIZATION_NAME for row in accounts.itertuples()}
facility_names = {row.FACILITY_ID: row.FACILITY_NAME for row in facilities.itertuples()}
flock_labels = {f"{row.FLOCK_NUMBER} · {account_names.get(row.ACCOUNT_ID)} · {row.PERMIT_NUMBER}": row.FLOCK_ID for row in flocks.itertuples()}
tests = build_salmonella_report(repo)
if tests.empty:
    st.info("No Salmonella tests are available.")
else:
    st.dataframe(tests, width="stretch", height=440, hide_index=True)

with st.expander("Create or edit a Salmonella test", expanded=False):
    options = {f"{row.PERMIT_NUMBER} · {row.TESTING_DATE} · {row.SALMONELLA_TEST_ID[:8]}": row.SALMONELLA_TEST_ID for row in repo.get_salmonella_tests().itertuples()}
    edit_label = st.selectbox("Record", ["Create new", *options], key="salmonella_record")
    current = repo.get_salmonella_test(options[edit_label]) if edit_label != "Create new" else {}
    left, right = st.columns(2)
    flock_label = left.selectbox("Flock / Permit Number *", list(flock_labels), key="salmonella_flock")
    flock = repo.get_flock(flock_labels[flock_label])
    left.text_input("Account", value=account_names.get(flock["ACCOUNT_ID"], ""), disabled=True, key="salmonella_account_display")
    left.text_input("Permit Number", value=str(flock.get("PERMIT_NUMBER") or ""), disabled=True, key="salmonella_permit_display")
    testing_date = left.date_input("Testing Date *", value=current.get("TESTING_DATE") or dt.date.today(), key="salmonella_testing_date")
    samples = left.number_input("Number of Samples *", min_value=0, value=int(current.get("NUMBER_OF_SAMPLES") or 0), key="salmonella_samples")
    inspector = left.text_input("Inspector", value=str(current.get("INSPECTOR") or ""), key="salmonella_inspector")
    result = right.selectbox("Salmonella Test Result", SALMONELLA_RESULTS, key="salmonella_result")
    received = right.date_input("Date Received", value=current.get("DATE_RECEIVED"), key="salmonella_received")
    result_sent = right.date_input("Date Result Sent", value=current.get("DATE_RESULT_SENT"), key="salmonella_sent")
    case_number = right.text_input("Case / File Number", value=str(current.get("CASE_FILE_NUMBER") or ""), key="salmonella_case")
    invoice_number = right.text_input("Invoice Number", value=str(current.get("INVOICE_NUMBER") or ""), key="salmonella_invoice")
    invoice_date = right.date_input("Invoice Date", value=current.get("INVOICE_DATE"), key="salmonella_invoice_date")
    comments = st.text_area("Comments", value=str(current.get("COMMENTS") or ""), key="salmonella_comments")
    if st.button("Save Salmonella Test", type="primary", key="salmonella_save"):
        record = {
            "SALMONELLA_TEST_ID": current.get("SALMONELLA_TEST_ID"),
            "FLOCK_ID": flock["FLOCK_ID"], "ACCOUNT_ID": flock["ACCOUNT_ID"],
            "PERMIT_NUMBER": flock["PERMIT_NUMBER"], "TESTING_DATE": testing_date,
            "INSPECTOR": inspector or None, "NUMBER_OF_SAMPLES": samples,
            "TEST_RESULT": result, "DATE_RESULT_SENT": result_sent,
            "DATE_RECEIVED": received, "CASE_FILE_NUMBER": case_number or None,
            "INVOICE_NUMBER": invoice_number or None, "INVOICE_DATE": invoice_date,
            "COMMENTS": comments or None,
        }
        errors = validate_salmonella_test(repo, record)
        if errors:
            for error in errors:
                st.error(error)
        else:
            try:
                test_id = repo.upsert_salmonella_test(record)
                st.success(f"Salmonella test saved: {test_id}")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

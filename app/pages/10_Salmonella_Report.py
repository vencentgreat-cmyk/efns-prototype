"""Dedicated filterable Salmonella Test report."""

import io

import pandas as pd
import streamlit as st

from app.services.export import spreadsheet_safe
from app.services.salmonella_reporting import build_salmonella_report
from app.ui import apply_theme, page_header, section_intro
from data.constants import SALMONELLA_RESULTS
from data.repositories import get_repository

apply_theme()
if "repo" not in st.session_state:
    st.session_state.repo = get_repository()
repo = st.session_state.repo
page_header("Salmonella Test Report", "Filter flock testing activity and export a spreadsheet-safe result.", "REPORTING")

filter_keys = ("sal_rpt_account", "sal_rpt_facility", "sal_rpt_flock", "sal_rpt_permit", "sal_rpt_dates", "sal_rpt_result", "sal_rpt_inspector", "sal_rpt_case", "sal_rpt_invoice")
def reset_filters():
    for key in filter_keys:
        st.session_state.pop(key, None)

accounts, facilities, flocks, tests = repo.get_accounts(), repo.get_facilities(), repo.get_flocks(), repo.get_salmonella_tests()
account_labels = {row.ORGANIZATION_NAME: row.ACCOUNT_ID for row in accounts.itertuples()}
facility_labels = {row.FACILITY_NAME: row.FACILITY_ID for row in facilities.itertuples()}
flock_labels = {row.FLOCK_NUMBER: row.FLOCK_ID for row in flocks.itertuples()}
section_intro("Report filters", "Use one or more fields; all filters are combined.")
st.button("Reset Filters", on_click=reset_filters, key="sal_rpt_reset")
row1 = st.columns(4)
account = row1[0].selectbox("Account", ["All", *account_labels], key="sal_rpt_account")
facility = row1[1].selectbox("Facility", ["All", *facility_labels], key="sal_rpt_facility")
flock = row1[2].selectbox("Flock Number", ["All", *flock_labels], key="sal_rpt_flock")
permit_values = sorted(tests["PERMIT_NUMBER"].dropna().astype(str).unique()) if not tests.empty else []
permit = row1[3].selectbox("Permit Number", ["All", *permit_values], key="sal_rpt_permit")
row2 = st.columns(3)
date_range = row2[0].date_input("Testing Date range", value=(), key="sal_rpt_dates")
result = row2[1].selectbox("Test Result", ["All", *SALMONELLA_RESULTS], key="sal_rpt_result")
inspectors = sorted(tests["INSPECTOR"].dropna().astype(str).unique()) if not tests.empty else []
inspector = row2[2].selectbox("Inspector", ["All", *inspectors], key="sal_rpt_inspector")
row3 = st.columns(2)
case_number = row3[0].text_input("Case / File Number", key="sal_rpt_case")
invoice_number = row3[1].text_input("Invoice Number", key="sal_rpt_invoice")
date_from = date_range[0] if len(date_range) >= 1 else None
date_to = date_range[1] if len(date_range) >= 2 else None
report = build_salmonella_report(
    repo, account_id=account_labels.get(account), facility_id=facility_labels.get(facility),
    flock_id=flock_labels.get(flock), permit_number=None if permit == "All" else permit,
    test_result=None if result == "All" else result, inspector=None if inspector == "All" else inspector,
    case_number=case_number or None, invoice_number=invoice_number or None,
    date_from=date_from, date_to=date_to,
)
section_intro(f"Results · {len(report):,} records", "Dates, numbers, and unassigned relationships use a consistent display.")
if report.empty:
    st.info("No Salmonella tests match the current filters.")
else:
    st.dataframe(report, width="stretch", height=470, hide_index=True)
    export = spreadsheet_safe(report)
    csv_col, excel_col = st.columns(2)
    csv_col.download_button("Export report as CSV", export.to_csv(index=False), "salmonella_test_report.csv", "text/csv", width="stretch")
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        export.to_excel(writer, index=False, sheet_name="Salmonella Tests")
    excel_col.download_button("Export report as Excel", buffer.getvalue(), "salmonella_test_report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")

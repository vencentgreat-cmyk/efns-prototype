"""Enterprise Salmonella Test list, detail, new and edit workspace."""

from __future__ import annotations

import datetime as dt
import pandas as pd
import streamlit as st

from app.navigation import current_page_url, format_timestamp, list_command_bar, module_url, open_view, read_record_view, record_command_bar, selected_row_index
from app.ui import apply_theme, clear_widget_prefix, page_header, section_intro
from data.constants import SALMONELLA_RESULTS, UNASSIGNED_LABEL
from data.repositories import get_repository
from data.validation import validate_salmonella_test

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
flock_options = {f"{row.FLOCK_NUMBER} · {account_names.get(row.ACCOUNT_ID, 'Unknown')} · {row.PERMIT_NUMBER}": row.FLOCK_ID for row in flocks.itertuples()}


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
    if action == "new": open_view("new")
    if action == "refresh": clear_widget_prefix("salmonella_filter_"); st.rerun()
    if action == "delete" and selected_id: st.session_state.salmonella_delete_pending = selected_id
    pending_delete = st.session_state.get("salmonella_delete_pending")
    if pending_delete:
        with st.container(border=True):
            st.warning("Delete the selected Salmonella Test? Related samples will block deletion.")
            with st.container(horizontal=True):
                if st.button("Confirm delete", type="primary", key="salmonella_confirm_delete"):
                    try:
                        repo.delete_salmonella_test(pending_delete)
                        st.session_state.pop("salmonella_delete_pending", None); st.rerun()
                    except ValueError as exc: st.error(str(exc))
                if st.button("Cancel", key="salmonella_cancel_delete"):
                    st.session_state.pop("salmonella_delete_pending", None); st.rerun()
    filters = st.columns([2, 1, 1])
    keyword = filters[0].text_input("Filter by keyword", placeholder="Permit, flock, inspector or case number", key="salmonella_filter_keyword")
    result_filter = filters[1].selectbox("Result", ["All", *SALMONELLA_RESULTS], key="salmonella_filter_result")
    account_options = {account_names[row.ACCOUNT_ID]: row.ACCOUNT_ID for row in accounts.itertuples()}
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
    if display.empty:
        st.info("No Salmonella Tests match the current filters.")
    else:
        display = display.reset_index(drop=True)
        display["TEST_LINK"] = display.apply(lambda row: current_page_url(row["SALMONELLA_TEST_ID"], test_label(row)), axis=1)
        display["FLOCK_LINK"] = display.apply(lambda row: module_url("Flocks", row["FLOCK_ID"], row["FLOCK_NUMBER"]), axis=1)
        display["ACCOUNT_LINK"] = display.apply(lambda row: module_url("Accounts_&_Facilities", row["ACCOUNT_ID"], row["ACCOUNT_NAME"]), axis=1)
        st.session_state.salmonella_list_row_ids = display["SALMONELLA_TEST_ID"].tolist()
        st.dataframe(display[["TEST_LINK", "ACCOUNT_LINK", "FLOCK_LINK", "FACILITY_NAME", "TEST_RESULT", "INSPECTOR", "NUMBER_OF_SAMPLES", "DATE_RECEIVED", "CREATED_AT"]], width="stretch", height=540, hide_index=True, on_select="rerun", selection_mode="single-row", key="salmonella_list_grid", column_config={"TEST_LINK": st.column_config.LinkColumn("Test", display_text=r".*#(.*)$"), "ACCOUNT_LINK": st.column_config.LinkColumn("Account", display_text=r".*#(.*)$"), "FLOCK_LINK": st.column_config.LinkColumn("Flock", display_text=r".*#(.*)$"), "FACILITY_NAME": "Facility", "CREATED_AT": st.column_config.DatetimeColumn("Created On", format="YYYY-MM-DD HH:mm")})
else:
    current = repo.get_salmonella_test(view.record_id) if view.record_id else None
    if view.name in {"detail", "edit"} and current is None:
        st.error("The requested Salmonella Test could not be found.")
        if st.button("Back to Salmonella Tests"): open_view("list")
        st.stop()
    is_form = view.name in {"new", "edit"}
    page_header("New Salmonella Test" if view.name == "new" else test_label(current), "Test result, sample count, case and invoice information.", "SALMONELLA TEST")
    action = record_command_bar("salmonella_record", view.name)
    if action in {"back", "cancel"}: open_view("detail", view.record_id) if action == "cancel" and view.record_id else open_view("list")
    if action == "edit": clear_widget_prefix("salmonella_form_"); open_view("edit", view.record_id)
    if action == "delete" and view.record_id:
        if not repo.get_salmonella_test_samples(view.record_id).empty: st.error("Salmonella Test cannot be deleted while related samples exist.")
        else: repo.delete_salmonella_test(view.record_id); open_view("list")
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
            st.dataframe(pd.DataFrame({"Field": [key.replace("_", " ").title() for key in current], "Value": [str(value) if value is not None else "—" for value in current.values()]}), width="stretch", hide_index=True)
        with related:
            section_intro("Flock")
            if flock: st.markdown(f"[{flock['FLOCK_NUMBER']}]({module_url('Flocks', flock['FLOCK_ID'], flock['FLOCK_NUMBER'])})")
            else: st.info("The related Flock is unavailable.")
            section_intro("Test Samples")
            sample_rows = repo.get_salmonella_test_samples(view.record_id)
            if sample_rows.empty: st.info("No related Test Samples.")
            else: st.dataframe(sample_rows, width="stretch", hide_index=True)
    else:
        current = current or {}
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
                testing_date = right.date_input("Testing Date *", value=current.get("TESTING_DATE") or dt.date.today(), key="salmonella_form_testing")
                samples = right.number_input("Number of Samples *", min_value=0, value=int(current.get("NUMBER_OF_SAMPLES") or 0), key="salmonella_form_samples")
                inspector = right.text_input("Inspector", value=str(current.get("INSPECTOR") or ""), key="salmonella_form_inspector")
            with result_details:
                left, right = st.columns(2)
                result = left.selectbox("Test Result", SALMONELLA_RESULTS, index=option_index(list(SALMONELLA_RESULTS), current.get("TEST_RESULT")), key="salmonella_form_result")
                received = left.date_input("Date Received", value=current.get("DATE_RECEIVED"), key="salmonella_form_received")
                result_sent = left.date_input("Date Result Sent", value=current.get("DATE_RESULT_SENT"), key="salmonella_form_sent")
                case_number = left.text_input("Case / File Number", value=str(current.get("CASE_FILE_NUMBER") or ""), key="salmonella_form_case")
                invoice_number = right.text_input("Invoice Number", value=str(current.get("INVOICE_NUMBER") or ""), key="salmonella_form_invoice")
                invoice_date = right.date_input("Invoice Date", value=current.get("INVOICE_DATE"), key="salmonella_form_invoice_date")
                comments = right.text_area("Comments", value=str(current.get("COMMENTS") or ""), key="salmonella_form_comments")
        if action == "save":
            record = {"SALMONELLA_TEST_ID": view.record_id, "FLOCK_ID": flock["FLOCK_ID"], "ACCOUNT_ID": flock["ACCOUNT_ID"], "PERMIT_NUMBER": flock["PERMIT_NUMBER"], "TESTING_DATE": testing_date, "INSPECTOR": inspector or None, "NUMBER_OF_SAMPLES": samples, "TEST_RESULT": result, "DATE_RECEIVED": received, "DATE_RESULT_SENT": result_sent, "CASE_FILE_NUMBER": case_number or None, "INVOICE_NUMBER": invoice_number or None, "INVOICE_DATE": invoice_date, "COMMENTS": comments or None}
            if not view.record_id: record.pop("SALMONELLA_TEST_ID")
            errors = validate_salmonella_test(repo, record)
            if errors:
                for error in errors: st.error(error)
            else:
                try:
                    saved_id = repo.upsert_salmonella_test(record)
                    clear_widget_prefix("salmonella_form_"); open_view("detail", saved_id)
                except ValueError as exc: st.error(str(exc))

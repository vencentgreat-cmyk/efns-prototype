"""Enterprise Flock list, detail, new and edit workspace."""

from __future__ import annotations

from app.services.form_safety import open_saved_record, stored_index, capture_form, preserve_form, save_form, stored_options, start_new_form, begin_form, field_changed, delete_confirmation
from data.producer_identity import text as stored_text
from data.business_time import halifax_today

import datetime as dt
import uuid
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from app.auth import require_operational_page
from app.navigation import format_timestamp, list_command_bar, open_module, open_view, read_record_view, record_command_bar, related_records_table, saved_view_selector, selected_row_index, timestamp_column
from app.ui import apply_theme, clear_widget_prefix, optional_form_date, page_header, section_intro, show_data_error
from data.constants import EGG_COLOURS, FLOCK_QUOTA_TYPES, FLOCK_STATUSES, UNASSIGNED_LABEL
from data.repositories import get_repository
from data.repositories.base import RepositoryError
from data.validation import validate_flock
from data.repositories.continuity import changed_attributes
from data.producer_identity import text
from app.services.quota_usage import render_quota_usage
from data.flock_stock import flock_stock
from data.quota_position import load_rules
from data.repositories.snowflake import normalize_numeric_bind


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
    page_header("Flocks", "Search, filter and maintain validated Flock records.", "FLOCK MANAGEMENT")
    statuses, _ = saved_view_selector("FLOCK", "Flocks", key="flock_saved_view", selection_keys=("flock_list_grid", "flock_list_row_ids", "flock_delete_pending"))
    selected_index = selected_row_index("flock_list_grid")
    row_ids = st.session_state.get("flock_list_row_ids", [])
    selected_id = row_ids[selected_index] if selected_index is not None and selected_index < len(row_ids) else None
    action = list_command_bar("flock_list", selected=bool(selected_id))
    if action == "view" and selected_id: open_view("detail", selected_id)
    if action == "new": start_new_form('flock_form_'); open_view("new")
    if action == "refresh": clear_widget_prefix("flock_filter_"); st.rerun()
    if action == "delete" and selected_id: st.session_state['flock_form___delete_pending']=selected_id
    filters = st.columns([2, 1, 1])
    keyword = filters[0].text_input("Filter by keyword", placeholder="Flock number or permit", key="flock_filter_keyword")
    account_filter = filters[1].selectbox("Account", ["All", *account_options], key="flock_filter_account")
    colour_filter = filters[2].selectbox("Egg colour", ["All", *EGG_COLOURS], key="flock_filter_colour")
    display = repo.get_flocks(statuses=statuses).copy()
    if keyword:
        display = display[display[["FLOCK_NUMBER", "PERMIT_NUMBER"]].fillna("").astype(str).apply(lambda col: col.str.contains(keyword, case=False, regex=False)).any(axis=1)]
    if account_filter != "All": display = display[display["ACCOUNT_ID"] == account_options[account_filter]]
    if colour_filter != "All": display = display[display["EGG_COLOUR"] == colour_filter]
    st.caption(f"{len(display):,} flock record(s) in this view")
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
    if action in {"back", "cancel"}: start_new_form("flock_form_"); open_view("detail", view.record_id) if action == "cancel" and view.record_id else open_view("list")
    if action == "edit": start_new_form("flock_form_"); open_view("edit", view.record_id)
    if action == "delete" and view.record_id: st.session_state['flock_form___delete_pending']=view.record_id
    if not is_form:
        st.caption(f"Created On: {format_timestamp(current.get('CREATED_AT'))} · Updated On: {format_timestamp(current.get('UPDATED_AT'))}")
        summary, details, related = st.tabs(["Summary", "Details", "Related Records"])
        with summary:
            with st.container(border=True):
                left, middle, right = st.columns(3)
                left.markdown(f"**Flock Number**  \n{current.get('FLOCK_NUMBER')}")
                left.markdown(f"**Account**  \n{account_names.get(current.get('ACCOUNT_ID'), 'Unknown')}")
                left.markdown(f"**Facility**  \n{facility_names.get(current.get('FACILITY_ID'), UNASSIGNED_LABEL)}")
                if current.get("ACCOUNT_ID") and left.button("View Account", key="flock_parent_account", icon=":material/account_circle:"):
                    open_module("Accounts_&_Facilities", "detail", current["ACCOUNT_ID"])
                if current.get("FACILITY_ID") and left.button("View Facility", key="flock_parent_facility", icon=":material/domain:"):
                    open_module("Facilities", "detail", current["FACILITY_ID"])
                middle.markdown(f"**Permit Number**  \n{current.get('PERMIT_NUMBER')}")
                middle.markdown(f"**Hatch Date**  \n{current.get('HATCH_DATE')}")
                middle.markdown(f"**Placement Date**  \n{current.get('PLACEMENT_DATE') or '—'}")
                known_count=current.get('BIRD_COUNT')
                right.markdown(f"**Bird Count**  \n{int(known_count) if pd.notna(known_count) else 'Unknown'}")
                try:
                    observed = flock_stock(current, repo.get_flock_transactions(view.record_id), halifax_today(), load_rules())
                    if observed['latest_count_date'] in observed['count_conflict_dates']:
                        right.warning('Latest Count: same-day source/quantity conflict; no observation selected.')
                    elif observed['latest_count_date']:
                        right.markdown(f"**Latest Count observation**  \n{observed['latest_count_date']} · {observed['latest_count_quantity'] if observed['latest_count_quantity'] is not None else 'Unknown'}")
                    else:
                        right.caption('Latest Count: not available.')
                    right.caption('Count is an observation, not a current stock total.')
                    if observed['latest_counts']:
                        count_rows = pd.DataFrame(observed['latest_counts'])
                        st.dataframe(count_rows[[c for c in ('FLOCK_TRANSACTION_ID', 'TRANSACTION_DATE', 'QUANTITY', 'COUNT_SOURCE_LABEL') if c in count_rows.columns]], hide_index=True, width='stretch')
                except Exception:
                    right.caption('Calculation draft unavailable for this record')
                right.markdown(f"**Egg Colour**  \n{current.get('EGG_COLOUR') or '—'}")
                right.markdown(f"**Status**  \n{current.get('STATUS')}")
            render_quota_usage(repo, current)
        with details:
            detail_fields = [key for key in current if key not in {"CREATED_AT", "UPDATED_AT"}]
            st.dataframe(pd.DataFrame({"Field": [key.replace("_", " ").title() for key in detail_fields], "Value": [str(current[key]) if current[key] is not None else "—" for key in detail_fields]}), width="stretch", hide_index=True)
        with related:
            for heading, frame, key, label, slug in (
                ("Flock Transactions", repo.get_flock_transactions(view.record_id), "FLOCK_TRANSACTION_ID", "TRANSACTION_TYPE", "Flock_Transactions"),
                ("Salmonella Tests", repo.get_salmonella_tests(flock_id=view.record_id), "SALMONELLA_TEST_ID", "PERMIT_NUMBER", "Salmonella_Tests"),
            ):
                related_records_table(heading, frame, id_column=key, label_column=label, page_slug=slug, key=f"flock_related_{slug}")
            production = repo.get_production_records()
            production = production[production["FLOCK_ID"] == view.record_id] if "FLOCK_ID" in production else production.iloc[0:0]
            section_intro(f"Matched Production Records ({len(production)})")
            if production.empty: st.info("No matched Production Records.")
            else: st.dataframe(production, width="stretch", hide_index=True)
    else:
        current = current or {}
        begin_form('flock_form_',view.record_id)
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
                facility_options = {**{row.FACILITY_NAME: row.FACILITY_ID for row in related_facilities.itertuples()}, UNASSIGNED_LABEL: None}
                facility_labels = list(facility_options)
                facility_label = left.selectbox("Facility *", facility_labels, index=0 if not view.record_id else option_index(facility_labels, label_for_id(facility_options, current.get("FACILITY_ID"),UNASSIGNED_LABEL)), key="flock_form_facility")
                facility_id = facility_options.get(facility_label)
                detail_options = {UNASSIGNED_LABEL: None, **{row.DETAIL_NAME: row.FACILITY_DETAIL_ID for row in repo.get_facility_details(facility_id).itertuples()}}
                detail_label = left.selectbox("Facility Detail", list(detail_options), index=option_index(list(detail_options), label_for_id(detail_options, current.get("FACILITY_DETAIL_ID"), UNASSIGNED_LABEL)), key="flock_form_detail")
                quotas = repo.get_quota_registrations(account_id=account_id, active_only=not bool(view.record_id))
                quota_options = {UNASSIGNED_LABEL: None, **{f"{row.QUOTA_NAME} · {row.REGISTRATION_NUMBER}": row.QUOTA_ID for row in quotas.itertuples()}}
                quota_label = left.selectbox("Quota Registration", list(quota_options), index=option_index(list(quota_options), label_for_id(quota_options, current.get("QUOTA_ID"), UNASSIGNED_LABEL)), key="flock_form_quota")
                quota_type = left.selectbox("Flock Quota Type", stored_options(FLOCK_QUOTA_TYPES,current.get("FLOCK_QUOTA_TYPE"),bool(view.record_id)), index=(stored_index(FLOCK_QUOTA_TYPES,current.get("FLOCK_QUOTA_TYPE")) if view.record_id else option_index(list(FLOCK_QUOTA_TYPES), current.get("FLOCK_QUOTA_TYPE"))), key="flock_form_quota_type")
                flock_number = right.text_input("Flock Number *", value=str(current.get("FLOCK_NUMBER") or ""), key="flock_form_number")
                status = right.selectbox("Status", stored_options(FLOCK_STATUSES,current.get("STATUS"),bool(view.record_id)), index=(stored_index(FLOCK_STATUSES,current.get("STATUS")) if view.record_id else option_index(list(FLOCK_STATUSES), current.get("STATUS"))), key="flock_form_status")
                create_delivery = right.checkbox("Create Delivery Transaction", value=bool(current.get("CREATE_DELIVERY_TRANSACTION")), key="flock_form_delivery")
                permit_number = right.text_input("Permit Number *", value=str(current.get("PERMIT_NUMBER") or ""), key="flock_form_permit")
                hatch_date = right.date_input("Hatch Date *", value=(optional_form_date(current.get("HATCH_DATE")) if view.record_id else halifax_today()), key="flock_form_hatch")
            with lifecycle:
                left, right = st.columns(2)
                bird_count_input = left.text_input("Bird Count *",value=text(current.get("BIRD_COUNT")) or "",key="flock_form_birds_text") if view.record_id else None
                bird_count = left.number_input("Bird Count *", min_value=0, value=0,key="flock_form_birds") if not view.record_id else None
                egg_colour = left.selectbox("Egg Colour", stored_options(EGG_COLOURS,current.get("EGG_COLOUR"),bool(view.record_id)), index=(stored_index(EGG_COLOURS,current.get("EGG_COLOUR")) if view.record_id else option_index(list(EGG_COLOURS), current.get("EGG_COLOUR"))), key="flock_form_colour")
                permit_date = left.date_input("Permit Date", value=optional_form_date(current.get("PERMIT_DATE")), key="flock_form_permit_date")
                ordered_date = left.date_input("Date Ordered", value=optional_form_date(current.get("DATE_ORDERED")), key="flock_form_ordered")
                placement_date = left.date_input("Placement Date", value=optional_form_date(current.get("PLACEMENT_DATE")), key="flock_form_placement")
                estimated_disposal = right.date_input("Estimated Disposal Date", value=optional_form_date(current.get("EST_DISPOSAL")), key="flock_form_est_disposal")
                disposal_date = right.date_input("Disposal Date", value=optional_form_date(current.get("DISPOSAL_DATE")), key="flock_form_disposal")
                birds_disposed_input = right.text_input("Birds Disposed",value=text(current.get("BIRDS_DISPOSED")) or "",key="flock_form_disposed_text")
                bird_strain = right.text_input("Bird Strain", value=str(current.get("BIRD_STRAIN") or ""), key="flock_form_strain")
                comments = st.text_area("Comments", value=str(current.get("COMMENTS") or ""), key="flock_form_comments")
            if view.record_id:
                revision_reason = st.text_input("Reason for correction *",key="flock_form_revision_reason")
                st.session_state.setdefault("flock_form_revision_request",uuid.uuid4().hex)
            else:
                initial_confirmed = st.checkbox('Record an evidence-confirmed initial Facility and placement time',key='flock_form_initial_confirmed')
                initial_time = st.time_input('Confirmed initial placement time (Atlantic / Halifax)',value=dt.time(12),key='flock_form_initial_time')
                initial_reason = st.text_input('Evidence for initial position',key='flock_form_initial_reason')
                st.session_state.setdefault('flock_form_initial_request',uuid.uuid4().hex)
        capture_form('flock_form_',current,{'FLOCK_NUMBER': ['flock_form_number'], 'ACCOUNT_ID': ['flock_form_account'], 'FACILITY_ID': ['flock_form_account', 'flock_form_facility'], 'FACILITY_DETAIL_ID': ['flock_form_account', 'flock_form_detail', 'flock_form_facility'], 'QUOTA_ID': ['flock_form_account', 'flock_form_quota'], 'FLOCK_QUOTA_TYPE': ['flock_form_quota_type'], 'STATUS': ['flock_form_status'], 'CREATE_DELIVERY_TRANSACTION': ['flock_form_delivery'], 'PERMIT_NUMBER': ['flock_form_permit'], 'PERMIT_DATE': ['flock_form_permit_date'], 'HATCH_DATE': ['flock_form_hatch'], 'DATE_ORDERED': ['flock_form_ordered'], 'BIRD_COUNT': ['flock_form_birds_text','flock_form_birds'], 'EGG_COLOUR': ['flock_form_colour'], 'BIRD_STRAIN': ['flock_form_strain'], 'PLACEMENT_DATE': ['flock_form_placement'], 'EST_DISPOSAL': ['flock_form_est_disposal'], 'DISPOSAL_DATE': ['flock_form_disposal'], 'BIRDS_DISPOSED': ['flock_form_disposed_text'], 'COMMENTS': ['flock_form_comments']})
        if action == "save":
            try:
                if view.record_id: bird_count = normalize_numeric_bind(bird_count_input,"BIRD_COUNT",1,integer=True) if field_changed("flock_form_","BIRD_COUNT") else current.get("BIRD_COUNT")
                birds_disposed = normalize_numeric_bind(birds_disposed_input,"BIRDS_DISPOSED",1,integer=True)
            except RepositoryError as exc:
                show_data_error(exc)
                st.stop()
            record = {"FLOCK_ID": view.record_id, "FLOCK_NUMBER": flock_number.strip(), "ACCOUNT_ID": account_id, "FACILITY_ID": facility_id, "FACILITY_DETAIL_ID": detail_options[detail_label], "QUOTA_ID": quota_options[quota_label], "FLOCK_QUOTA_TYPE": quota_type, "STATUS": status, "CREATE_DELIVERY_TRANSACTION": create_delivery, "PERMIT_NUMBER": permit_number.strip(), "PERMIT_DATE": permit_date, "HATCH_DATE": hatch_date, "DATE_ORDERED": ordered_date, "BIRD_COUNT": bird_count, "EGG_COLOUR": egg_colour, "BIRD_STRAIN": bird_strain or None, "PLACEMENT_DATE": placement_date, "EST_DISPOSAL": estimated_disposal, "DISPOSAL_DATE": disposal_date, "BIRDS_DISPOSED": birds_disposed, "COMMENTS": comments or None}
            if not view.record_id: record.pop("FLOCK_ID")
            else: record["EXPECTED_UPDATED_AT"] = st.session_state.get(expected_key)
            errors = validate_flock(repo, record) if not view.record_id else []
            if errors:
                for error in errors: st.error(error)
            else:
                try:
                    if view.record_id:
                        record=preserve_form(record,current,'flock_form_')
                        repo.check_flock_reference_change(record)
                        saved_id = save_form(repo,'FLOCK',record,current,'flock_form_',revision_reason)
                    elif initial_confirmed:
                        if not placement_date or not initial_reason.strip(): raise RepositoryError('Confirmed initial position requires placement date, time and evidence.')
                        saved_id = repo.create_flock_with_initial_position(record,dt.datetime.combine(placement_date,initial_time,ZoneInfo('America/Halifax')),initial_reason,st.session_state.flock_form_initial_request)
                    else: saved_id = save_form(repo,'FLOCK',record,current,'flock_form_')
                    open_saved_record(saved_id)
                except Exception as exc: show_data_error(exc)

_pending=st.session_state.get('flock_form___delete_pending')
if _pending and delete_confirmation(repo,'delete_flock',_pending,'flock_form___delete'):
    st.session_state.pop('flock_form___delete_pending',None)
    open_view("list")

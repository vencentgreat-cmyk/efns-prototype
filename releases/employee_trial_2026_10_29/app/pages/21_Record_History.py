"""Explicit producer decisions, original-file retrieval and business history."""
import datetime as dt
from decimal import Decimal, InvalidOperation
import uuid
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from app.auth import can_current, require_page_permission
from app.security import Permission
from app.ui import apply_theme, page_header, show_data_error
from app.services.form_safety import request_for,finish_request
from data.business_time import halifax_today
from data.repositories import get_repository
from data.producer_identity import production_identities
from data.source_trace import trace_summary

require_page_permission(Permission.VIEW_DATA)
apply_theme()
if "repo" not in st.session_state: st.session_state.repo = get_repository()
repo = st.session_state.repo
page_header("Record Review & History", "Original evidence, producer decisions and recorded Flock movements.", "REVIEW")
producer, flock, correction, originals = st.tabs(["Producer matching", "Flock history", "Attribute corrections", "Original files"])
accounts = repo.get_accounts()
account_options = {f"{row.ORGANIZATION_NAME} | {row.ACCOUNT_ID}": row.ACCOUNT_ID for row in accounts.itertuples()}
with producer:
    production = production_identities(repo.get_production_records())
    unmatched = production[production.PRODUCER_ACCOUNT_ID.isna() | production.get("MATCH_STATUS",pd.Series(None,index=production.index,dtype=object)).isin(["UNIQUE_MATCHED","UNIQUE_CANDIDATE"])]
    st.dataframe(unmatched, hide_index=True, width="stretch")
    if not unmatched.empty:
        chosen = st.selectbox("Production record to review", unmatched.PRODUCTION_ID.tolist())
        if st.button("Check exact producer number", disabled=not can_current(Permission.UPDATE_DATA)):
            try:
                result = repo.match_production_producer(chosen)
                st.success(f"Matching result: {result['status']}. Automatic matching is not staff confirmation.")
            except Exception as exc: show_data_error(exc)
        decision_prefix = 'producer_decision_' + str(chosen) + '_'
        if st.session_state.get('_producer_decision_record') != chosen:
            for key in list(st.session_state):
                if key.startswith('producer_decision_'):
                    st.session_state.pop(key, None)
            st.session_state['_producer_decision_record'] = chosen
        target = st.selectbox("Confirmed producer Account", ["Choose an Account", *account_options], key=decision_prefix+'account')
        basis = st.text_area("Evidence for this producer decision", key=decision_prefix+'evidence')
        confirmation = st.checkbox("I verified this Account against source evidence.", key=decision_prefix+'confirmed')
        if st.button("Confirm producer Account", disabled=not can_current(Permission.UPDATE_DATA) or target not in account_options or not basis.strip() or not confirmation):
            try:
                repo.match_production_producer(chosen, account_id=account_options[target], basis=basis)
                st.success("Producer decision saved without creating another production record.")
            except Exception as exc: show_data_error(exc)
    with st.expander("New production record"):
        manual_account = st.selectbox("Producer Account", ["Choose an Account", *account_options], key="manual_producer")
        year = st.number_input("Reporting year", min_value=1, max_value=9999, value=halifax_today().year)
        week = st.number_input("Reporting week", min_value=1, max_value=53, value=1)
        total = st.text_input("Source Total", help="Leave empty when unknown; 0 is a known zero.")
        st.session_state.setdefault("manual_production_request", uuid.uuid4().hex)
        if st.button("Save new production record", disabled=not can_current(Permission.CREATE_DATA) or manual_account not in account_options):
            try:
                value = Decimal(total) if total.strip() else None
                if value is not None and not value.is_finite(): raise InvalidOperation()
                payload=dict(PRODUCER_ACCOUNT_ID=account_options[manual_account],REPORTING_YEAR=year,REPORTING_WEEK=week,TOTAL=value)
                request=request_for('manual_production',payload)
                st.session_state.manual_production_request=request
                prior=st.session_state.get('_efns_request_manual_production',{}).get('result')
                saved = repo.create_manual_production(payload,request)
                finish_request('manual_production',saved)
                st.success(f"This exact entry was already saved as {saved}. Use Start another new production record for a separate identical entry." if prior else f"Saved production record {saved}.")
            except InvalidOperation: st.error("Source Total must be a finite number or empty.")
            except Exception as exc: show_data_error(exc)
        if st.button("Start another new production record"):
            st.session_state.manual_production_request = uuid.uuid4().hex
            st.session_state.pop('_efns_request_manual_production',None)
            st.rerun()
with flock:
    flocks = repo.get_flocks()
    options = {f"{row.FLOCK_NUMBER} | {row.FLOCK_ID}": row.FLOCK_ID for row in flocks.itertuples()}
    if options:
        selected = st.selectbox("Flock", list(options))
        flock_id = options[selected]
        event_prefix = 'flock_event_form_' + str(flock_id) + '_'
        if st.session_state.get('_flock_event_form_record') != flock_id:
            for key in list(st.session_state):
                if key.startswith('flock_event_form_'):
                    st.session_state.pop(key, None)
            st.session_state['_flock_event_form_record'] = flock_id
        current = repo.get_flock(flock_id)
        st.caption("Current reference is a snapshot, not evidence of past movements. Estimated disposal does not end a Flock.")
        st.dataframe(repo.get_flock_events(flock_id), hide_index=True, width="stretch")
        event_type = st.selectbox("Business event", ["Move to another Facility", "Actual lifecycle end"], key=event_prefix+"type")
        facilities = repo.get_facilities(account_id=current["ACCOUNT_ID"])
        destinations = {f"{row.FACILITY_NAME} | {row.FACILITY_ID}": row.FACILITY_ID for row in facilities.itertuples()}
        destination = st.selectbox("Destination Facility", ["Choose a Facility", *destinations], disabled=event_type == "Actual lifecycle end", key=event_prefix+"destination")
        day = st.date_input("Business date", value=halifax_today(), max_value=halifax_today(), key=event_prefix+"day")
        clock = st.time_input("Business time (Atlantic / Halifax)", value=dt.time(12), key=event_prefix+"time")
        reason = st.text_area("Reason for the event", key=event_prefix+"reason")
        st.write("Recorded original Facility:",current.get('FACILITY_ID') or 'Unknown')
        confirmation_scope = (flock_id, event_type, destination, day.isoformat(), clock.isoformat())
        if st.session_state.get('_flock_event_confirmation_scope') != confirmation_scope:
            st.session_state[event_prefix+'confirmed'] = False
            st.session_state['_flock_event_confirmation_scope'] = confirmation_scope
        position_confirmed=st.checkbox("I checked the recorded original Facility, destination and business time against evidence. An unknown origin remains unknown.", key=event_prefix+'confirmed')
        events = repo.get_flock_events(flock_id)
        supersedes = st.selectbox("Correct a previous event", ["No correction", *(events.EVENT_ID.tolist() if not events.empty else [])])
        token_key = f"flock_event_request_{flock_id}"
        st.session_state.setdefault(token_key, uuid.uuid4().hex)
        if st.button("Record business event", disabled=not can_current(Permission.UPDATE_DATA) or not reason.strip() or not position_confirmed or (event_type.startswith("Move") and destination not in destinations)):
            try:
                saved = repo.record_flock_event(flock_id,"MOVE" if event_type.startswith("Move") else "END",dt.datetime.combine(day,clock,ZoneInfo("America/Halifax")),reason,st.session_state[token_key],to_facility_id=destinations.get(destination),supersedes_event_id=None if supersedes == "No correction" else supersedes,position_confirmed=position_confirmed)
                st.success(f"Event {saved} recorded. Repeat submission reuses this request.")
            except Exception as exc: show_data_error(exc)
        if st.button("Start another event"):
            st.session_state[token_key] = uuid.uuid4().hex
            st.rerun()
        as_of_day = st.date_input("Position as of date", key="history_day")
        if st.button("Look up recorded position"):
            try: st.write(repo.get_flock_position(flock_id,dt.datetime.combine(as_of_day,dt.time(23,59),ZoneInfo("America/Halifax"))))
            except Exception as exc: show_data_error(exc)
with correction:
    with st.expander("Production corrections"):
        production = repo.get_production_records()
        if not production.empty:
            production_id = st.selectbox("Original Production ID",production.PRODUCTION_ID.tolist())
            opened = production[production.PRODUCTION_ID == production_id].iloc[0]
            version_key = 'production_correction_version_' + production_id
            st.session_state.setdefault(version_key,opened.UPDATED_AT)
            amount = st.text_input("Corrected Source Total",value='' if pd.isna(opened.get('TOTAL')) else str(opened.TOTAL),key='production_total_'+production_id)
            why = st.text_area("Reason for production correction")
            st.session_state.setdefault('production_correction_request',uuid.uuid4().hex)
            if st.button("Save production correction",disabled=not can_current(Permission.UPDATE_DATA) or not why.strip()):
                try:
                    repo.revise_record('PRODUCTION_RECORD',production_id,{'TOTAL':amount or None},why,st.session_state.production_correction_request,expected_updated_at=st.session_state[version_key])
                    st.success('Original production record updated; previous value retained in correction history.')
                except Exception as exc: show_data_error(exc)
            if st.button('Reload production correction'):
                st.session_state.pop(version_key,None)
                st.session_state.pop('production_total_'+production_id,None)
                st.session_state.production_correction_request=uuid.uuid4().hex
                st.rerun()
    entity = st.selectbox("Record type", ["FLOCK", "FACILITY"])
    records = repo.get_flocks() if entity == "FLOCK" else repo.get_facilities()
    key = entity + "_ID"
    if not records.empty:
        record_id = st.selectbox("Record ID", records[key].tolist())
        review_key='attribute_review_'+entity+'_'+record_id
        st.session_state.setdefault(review_key,records[records[key]==record_id].iloc[0].to_dict())
        reviewed=st.session_state[review_key]
        field = st.selectbox("Attribute", ["FLOCK_NUMBER", "COMMENTS"] if entity == "FLOCK" else ["FACILITY_NAME", "COMMENTS"])
        st.caption(f"Reviewed stored value: {reviewed.get(field)}; version {reviewed.get('UPDATED_AT')}")
        value = st.text_input("Corrected value")
        if st.button('Reload attribute correction'):
            st.session_state.pop(review_key,None)
            st.session_state.pop('_efns_request_attribute_revision',None)
            st.rerun()
        reason = st.text_area("Reason for attribute correction", key="revision_reason")
        st.session_state.setdefault("revision_request", uuid.uuid4().hex)
        if st.button("Save attribute correction", disabled=not can_current(Permission.UPDATE_DATA) or not reason.strip()):
            try:
                request=request_for('attribute_revision',dict(entity=entity,id=record_id,changes={field:value or None},reason=reason))
                repo.revise_record(entity,record_id,{field:value or None},reason,request,expected_updated_at=reviewed.get('UPDATED_AT'))
                finish_request('attribute_revision',record_id)
                st.session_state[review_key]=(repo.get_flock(record_id) if entity=='FLOCK' else repo.get_facility(record_id))
                st.success("Correction recorded with previous and new values. It is not a movement or quantity transaction.")
            except Exception as exc: show_data_error(exc)
        if st.button("Start another correction"):
            st.session_state.revision_request = uuid.uuid4().hex
            st.session_state.pop('_efns_request_attribute_revision',None)
            st.rerun()
    st.dataframe(repo.get_record_revisions(), hide_index=True, width="stretch")
with originals:
    files = repo.get_source_files()
    st.dataframe(files, hide_index=True, width="stretch")
    if not files.empty:
        file_id = st.selectbox("Archived source file", files.SOURCE_FILE_ID.tolist())
        if can_current(Permission.IMPORT_DATA):
            try:
                review_rows = repo.get_source_review_rows(file_id)
                st.caption(f"{len(review_rows)} retained source rows for this archived file, across the linked batches. Source rows include rejected and unmapped records; they are not a count of successful business imports.")
                st.dataframe(trace_summary(review_rows), hide_index=True, width="stretch")
                front = ['SOURCE_TYPE','TRACE_BATCH_ID','SOURCE_FILENAME','SOURCE_ENTITY',
                    'SOURCE_ROW_NUMBER','VALIDATION_STATUS','BATCH_STATUS','MAPPING_STATUS',
                    'COMMIT_STATUS','SOURCE_ID','TARGET_ID','MAPPED_TARGET_ID','CORE_TARGET_COUNT',
                    'TRACE_ROW_ID','MAPPING_COUNT','FILE_LINK_COUNT','TRACE_METHOD']
                columns = [c for c in front if c in review_rows]
                st.dataframe(review_rows.reindex(columns=columns), hide_index=True, width="stretch")
                st.caption("TARGET_ID is the retained proposed target; MAPPED_TARGET_ID is the original migration mapping. Only 'Committed target verified' confirms a unique current target and a committed original mapping/batch. Repeated date source rows may share one DAY target. Later correction decisions do not rewrite the original rejection shown here. Ordinary import batch status is shown separately; historical target verification does not apply to that path.")
                if not review_rows.empty:
                    with st.expander("Retained row details (original values and tracking)"):
                        st.dataframe(review_rows, hide_index=True, width="stretch")
            except Exception as exc:
                show_data_error(exc)
        if st.button("Verify and retrieve original", disabled=not can_current(Permission.IMPORT_DATA)):
            try:
                content = repo.get_source_file_bytes(file_id)
                metadata = files[files.SOURCE_FILE_ID == file_id].iloc[0]
                st.success("Retrieved original bytes match the saved SHA-256 checksum.")
                st.download_button("Download original file", content,file_name=metadata.ORIGINAL_FILENAME)
            except Exception as exc: show_data_error(exc)

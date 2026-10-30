"""Explicit form review snapshots and replay identities; no business inference."""
import copy,uuid
import pandas as pd
import streamlit as st
from data.source_evidence import evidence_json
from data.repositories.continuity import changed_attributes
from data.repositories.base import RepositoryError

def stored_options(options,value,editing):
    values=list(options)
    if editing:
        value=None if value is None or pd.isna(value) else value
        if value not in values:values.insert(0,value)
    return values

def stored_index(options,value):
    value=None if value is None or pd.isna(value) else value
    return stored_options(options,value,True).index(value)

def capture_form(prefix,current,field_keys):
    key=prefix+'__review'
    if key not in st.session_state:
        st.session_state[key]=dict(original=copy.deepcopy(current),widgets={k:copy.deepcopy(st.session_state.get(k)) for keys in field_keys.values() for k in keys},fields=field_keys)
    return st.session_state[key]

def begin_form(prefix,identity):
    key='_efns_context_'+prefix
    if key not in st.session_state or st.session_state[key]!=identity:
        for old in list(st.session_state):
            if old.startswith(prefix):st.session_state.pop(old,None)
        st.session_state[key]=identity

def field_changed(prefix,field):
    snap=st.session_state.get(prefix+'__review',{})
    keys=snap.get('fields',{}).get(field,[])
    return not keys or any(evidence_json(st.session_state.get(k))!=evidence_json(snap['widgets'].get(k)) for k in keys)

def preserve_form(record,current,prefix):
    snapshot=st.session_state.get(prefix+'__review')
    if not current or not snapshot:return record
    result=dict(record)
    for field,keys in snapshot['fields'].items():
        if field in snapshot['original'] and all(evidence_json(st.session_state.get(k))==evidence_json(snapshot['widgets'].get(k)) for k in keys):
            result[field]=copy.deepcopy(snapshot['original'][field])
    return result

def request_for(scope,payload):
    key='_efns_request_'+scope;fingerprint=evidence_json(payload)
    slot=st.session_state.get(key)
    if not slot or (slot.get('committed') and slot['fingerprint']!=fingerprint):
        slot=dict(id=uuid.uuid4().hex,fingerprint=fingerprint,committed=False)
        st.session_state[key]=slot
    return slot['id']

def finish_request(scope,result):
    key='_efns_request_'+scope
    if key in st.session_state:st.session_state[key].update(committed=True,result=result)

def open_saved_record(record_id):
    from app.navigation import open_view
    try:open_view('detail',record_id)
    except Exception:
        st.success(f'Record {record_id} was saved.')
        st.warning('Navigation could not be completed. Do not start a new request to retry this save; the existing request can return the saved result.')

def start_new_form(prefix):
    for key in list(st.session_state):
        if key.startswith(prefix):st.session_state.pop(key,None)
    st.session_state.pop('_efns_request_'+prefix,None)

def save_form(repo,entity,record,current,prefix,reason=None):
    from data.repositories.snowflake import MODEL
    record=preserve_form(record,current,prefix)
    key=MODEL[entity][0]
    if current:
        baseline=st.session_state[prefix+'__review']['original']
        changes=changed_attributes(baseline,record)
        changes={k:v for k,v in changes.items() if k in MODEL[entity][1].split()}
        if not changes:return current[key]
        reason=reason if reason is not None else st.session_state.get(prefix+'revision_reason','')
        if not str(reason or '').strip():raise RepositoryError('A reason for the correction is required.')
        payload=dict(entity=entity,id=current[key],changes=changes,reason=reason)
        request=request_for(prefix,payload)
        result=repo.revise_record(entity,current[key],changes,reason,request,expected_updated_at=baseline.get('UPDATED_AT'))
    else:
        record={k:v for k,v in record.items() if k not in (key,'EXPECTED_UPDATED_AT')}
        request=request_for(prefix,dict(entity=entity,record=record))
        result=repo.create_record_once(entity,record,request)
    finish_request(prefix,result)
    if getattr(repo,'last_audit_warning',None):st.warning(repo.last_audit_warning)
    return result

def delete_confirmation(repo,method,record_id,prefix):
    st.warning('Confirm deletion. Referenced records are protected; the before-image will remain in history.')
    reason=st.text_input('Reason for deletion *',key=prefix+'_reason')
    confirmed=st.checkbox('I confirm this deletion.',key=prefix+'_confirmed')
    if st.button('Confirm delete',key=prefix+'_confirm',disabled=not confirmed or not reason.strip()):
        try:
            result=getattr(repo,method)(record_id,reason=reason,request_id=request_for(prefix,dict(method=method,id=record_id,reason=reason)))
            finish_request(prefix,result)
            return True
        except (ValueError,RepositoryError) as exc:
            from app.ui import show_data_error
            show_data_error(exc)
    if st.button('Cancel deletion',key=prefix+'_cancel'):return True
    return False

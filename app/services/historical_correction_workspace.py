"""Finite manual-decision editor embedded in the historical migration page."""
import uuid

import streamlit as st

from data.correction_decisions import FIELDS
from data.historical_corrections import _variant
from data.migration import normalize_migration_row


def render_correction_editor(repo,preview,may_save):
    st.subheader('Manual correction decisions')
    entity=st.selectbox('Correction entity',['All',*FIELDS],key='manual_correction_entity')
    state=st.selectbox('Decision state',['Needs confirmation','Eligible for CORE','Committed to CORE','All'],key='manual_correction_state')
    status={'Needs confirmation':'PENDING_CONFIRMATION','Eligible for CORE':'READY_CORE','Committed to CORE':'ALREADY_COMMITTED'}
    rows=[row for row in preview.rows if row['SOURCE_ENTITY'] in FIELDS
          and (entity=='All' or row['SOURCE_ENTITY']==entity)
          and (state=='All' or row['DISPOSITION']==status[state])]
    if not rows:
        st.info('No records match these filters.')
        return
    by_id={row['MIGRATION_RAW_ROW_ID']:row for row in rows}
    raw_id=st.selectbox('Original record',list(by_id),format_func=lambda key:
        f"{by_id[key]['SOURCE_ENTITY']} | {by_id[key]['SOURCE_FILENAME']} | Excel row {by_id[key]['SOURCE_ROW_NUMBER']} | {by_id[key]['SOURCE_ID']}",
        key=f'manual_row_{preview.batch_id}')
    row=by_id[raw_id]
    source=repo.get_historical_correction_source(preview.batch_id,raw_id)
    original,_=normalize_migration_row(row['SOURCE_ENTITY'],_variant(source['RAW_DATA']),int(source['SOURCE_ROW_NUMBER']))
    st.write('Original rejection:',row['ORIGINAL_VALIDATION_MESSAGES'])
    left,right=st.columns(2)
    with left:
        st.caption('Preserved original values')
        st.json(original)
    with right:
        st.caption('Currently proposed values')
        st.json(row['CORRECTED_DATA'])
    for message in row['CURRENT_VALIDATION_MESSAGES']: st.warning(message)
    history=repo.get_historical_correction_decisions(preview.batch_id)
    if not history.empty:
        history=history[history.MIGRATION_RAW_ROW_ID==raw_id].sort_values('VERSION')
        st.dataframe(history[['VERSION','BASIS','ACTOR_EMAIL','RECORDED_AT','STATUS']],hide_index=True)
    if row['DISPOSITION']=='ALREADY_COMMITTED':
        st.success('This correction is committed and cannot be overwritten.')
        return
    accounts=repo.get_accounts()
    account_names={str(item.ACCOUNT_ID):str(item.ORGANIZATION_NAME) for item in accounts.itertuples()}
    frames={'ACCOUNT_ID':(accounts,'ACCOUNT_ID','ORGANIZATION_NAME'),
            'FACILITY_ID':(repo.get_facilities(),'FACILITY_ID','FACILITY_NAME'),
            'FLOCK_ID':(repo.get_flocks(),'FLOCK_ID','FLOCK_NUMBER'),
            'QUOTA_ID':(repo.get_quota_registrations(),'QUOTA_ID','REGISTRATION_NUMBER')}
    for field in FIELDS[row['SOURCE_ENTITY']]:
        frame,key,name=frames[field]
        for title,values in [('Original',original),('Proposed',row['CORRECTED_DATA'])]:
            identifier=values.get(field)
            matches=frame[frame[key]==identifier] if key in frame else frame.iloc[0:0]
            label=matches.iloc[0].get(name) if len(matches)==1 else 'Unknown or not linked'
            st.caption(f'{title} {field}: {label} | {identifier}')
    version=int(row.get('DECISION_VERSION') or 0)
    prefix=f'{preview.batch_id}:{raw_id}:{version}'
    with st.form('decision:'+prefix):
        changes={}
        for field in FIELDS[row['SOURCE_ENTITY']]:
            frame,key,name=frames[field]
            labels={None:'Not selected'}
            for item in frame.to_dict('records'):
                identifier=str(item[key]);owner=item.get('ACCOUNT_ID')
                title=item.get(name) or (item.get('QUOTA_NAME') if field=='QUOTA_ID' else None) or 'Unnamed'
                labels[identifier]=f"{title} | {identifier}"+(f" | Account: {account_names.get(str(owner),'Unknown')} ({owner})" if owner else '')
            current=row['CORRECTED_DATA'].get(field)
            if current and current not in labels: labels[current]='Unresolved original: '+str(current)
            changes[field]=st.selectbox(field.replace('_',' ').title(),list(labels),
                index=list(labels).index(current) if current in labels else 0,format_func=labels.get,key=prefix+field)
        basis=st.text_area('Confirmation basis / evidence',key=prefix+'basis',max_chars=2000)
        confirmed=st.checkbox('I confirm these relationship values are supported by the stated evidence.',key=prefix+'confirmed')
        submitted=st.form_submit_button('Save correction decision',disabled=not may_save)
    if row['SOURCE_ENTITY']=='QUOTA_TRANSACTION':
        selected=frames['QUOTA_ID'][0]
        owners=selected[selected['QUOTA_ID']==changes['QUOTA_ID']]
        if len(owners)==1:
            owner=owners.iloc[0].get('ACCOUNT_ID')
            st.write('Quota owner:',f"{account_names.get(str(owner),'Unknown')} | {owner}")
        st.caption('Owner is read from the selected Quota and revalidated after saving; Owner is not an editable field.')
    if row['SOURCE_ENTITY']=='FLOCK':
        st.warning('Do not assume current Facility ownership proves historical ownership. If that history cannot be represented by the current Account relationship, keep this record pending.')
    if submitted:
        try:
            request_key=prefix+':request'
            if request_key not in st.session_state: st.session_state[request_key]=str(uuid.uuid4())
            repo.save_historical_correction_decision(preview.batch_id,raw_id,changes,basis,version,
                st.session_state[request_key],confirmed=confirmed)
            st.session_state.eims_correction_preview=repo.preview_historical_correction_review(preview.batch_id)
            st.success('Decision saved and revalidated. No CORE records were written.')
            st.rerun()
        except Exception as error:
            from app.ui import show_data_error
            show_data_error(error)

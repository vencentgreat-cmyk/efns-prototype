"""Lease-only entry; ordinary allocation form/payload stays unchanged."""
from decimal import Decimal, InvalidOperation
import streamlit as st

from app.services.form_safety import save_form,open_saved_record
from data.business_time import halifax_today
from data.quota_leases import lease_input_errors
from data.quota_lease_persistence import IMMUTABLE_LEASE
from data.producer_identity import text
from data.quota_types import quota_type_key


def render_lease_form(repo,current,action):
    if current:
        st.info(IMMUTABLE_LEASE)
        return
    accounts={str(r['ACCOUNT_ID']):r for r in repo.get_accounts().to_dict('records')}
    regs=repo.get_quota_registrations()
    active=[r for r in regs.to_dict('records') if (text(r.get('STATUS')) or '').casefold()=='active']
    kinds=sorted({quota_type_key(r.get('QUOTA_TYPE')) for r in active if quota_type_key(r.get('QUOTA_TYPE'))})
    if not kinds:
        st.info('Active Quota Registrations are required before recording a lease.');return
    kind=st.selectbox('Quota Type',kinds,index=kinds.index('Egg Production') if 'Egg Production' in kinds else 0,key='quota_lease_form_type')
    selected=[r for r in active if quota_type_key(r.get('QUOTA_TYPE'))==kind]
    ids=sorted({str(r['ACCOUNT_ID']) for r in selected if str(r['ACCOUNT_ID']) in accounts})
    if not ids:
        st.info('No Accounts have an Active Registration for this Quota Type.');return
    def label(identity):
        row=accounts[identity]
        return ' - '.join(filter(None,[text(row.get('ORGANIZATION_NAME')),text(row.get('REGISTRATION_NUMBER'))])) or identity
    lessor=st.selectbox('Lessor',ids,format_func=label,key='quota_lease_form_lessor')
    lessee=st.selectbox('Lessee',ids,index=1 if len(ids)>1 else 0,format_func=label,key='quota_lease_form_lessee')
    owned={str(r['QUOTA_ID']):r for r in selected if str(r['ACCOUNT_ID'])==lessor}
    quota_id=st.selectbox('Lessor Quota Registration',list(owned),format_func=lambda identity:text(owned[identity].get('QUOTA_NAME')) or text(owned[identity].get('REGISTRATION_NUMBER')) or identity,key='quota_lease_form_quota')
    amount=st.text_input('Lease amount (birds)',key='quota_lease_form_amount')
    start=st.date_input('Start Date',value=halifax_today(),key='quota_lease_form_start')
    end=st.date_input('Quota End Date',value=None,key='quota_lease_form_end')
    comments=st.text_area('Comments',key='quota_lease_form_comments')
    st.caption('Quota is leased out of the lessor and leased in to the lessee through the Quota End Date, inclusive. It returns the next day. Own quota less other leases out is checked for the whole period when saved. Leased-in quota cannot be leased onward.')
    if action!='save':return
    try:value=Decimal(amount)
    except (InvalidOperation,ValueError):value=None
    record={'TRANSACTION_METHOD':'Lease','TRANSACTION_TYPE':'Lease (Out)','QUOTA_ID':quota_id,
            'OWNER_ACCOUNT_ID':lessor,'RELATED_ACCOUNT_ID':lessee,'QUOTA_COUNT':value,
            'EFFECTIVE_DATE':start,'END_DATE':end,'COMMENTS':comments.strip() or None}
    errors=lease_input_errors(record,regs)
    if errors:
        for error in errors:st.error(error)
        return
    try:
        saved=save_form(repo,'QUOTA_TRANSACTION',record,None,'quota_lease_form_')
        open_saved_record(saved)
    except Exception as exc:
        from app.ui import show_data_error
        show_data_error(exc)

"""Role-scoped append-only lease adjustments; existing void remains separate."""
from decimal import Decimal, InvalidOperation
import pandas as pd
import streamlit as st
from app.auth import current_user
from app.services.form_safety import request_for, finish_request, open_saved_record
from app.ui import show_data_error
from data.quota_lease_adjustments import LEASE_WRITER_ROLES
from data.quota_leases import is_voided, effective_lease_end
from data.business_time import halifax_today
from data.lease_confirmation import confirmation_required, REPORT_CHANGE_WARNING


def confirm_report_changes(scope,when,token=''):
    if not confirmation_required(when):return False
    import hashlib
    st.warning(REPORT_CHANGE_WARNING)
    key=hashlib.sha256(f'{when}|{token}'.encode()).hexdigest()[:16]
    return st.checkbox('I understand that reports already produced for this period will change.',key=scope+'_reports_confirm_'+key)


def render_lease_adjustments(repo, current):
    identity=current['QUOTA_TRANSACTION_ID']
    adjustments=repo.get_quota_lease_adjustments([identity]).get(identity.lower(),[])
    if adjustments:
        rows=[{'Adjustment':row['KIND'],'Effective Date':str(row['EFFECTIVE_DATE']),
               'Quota End Date':str(row.get('NEW_END_DATE') or ''),
               'Returned Amount':str(row.get('RETURNED_AMOUNT') or '')} for row in adjustments]
        st.dataframe(pd.DataFrame(rows),hide_index=True,width='stretch')
    if is_voided(current):return
    target=dict(current,_LEASE_ADJUSTMENTS=adjustments)
    try:end=effective_lease_end(target)
    except ValueError:
        st.warning('Lease adjustment history needs review; adjustments are unavailable.');return
    st.caption('Current Quota End Date: '+(end.isoformat() if end else 'Unknown'))
    actor=current_user()
    if actor is None or actor.role.value not in LEASE_WRITER_ROLES:return
    scope='lease_adjust_'+identity
    st.caption('The original lease is retained. End dates are inclusive; a partial return takes effect on its Return Date.')
    kind=st.selectbox('Lease adjustment',['Ended early','Partial return'],
        format_func=lambda value:'End lease early' if value=='Ended early' else 'Return part of the lease',key=scope+'_kind')
    when=st.date_input('New Quota End Date' if kind=='Ended early' else 'Return Date',value=halifax_today(),key=scope+'_date')
    value=st.text_input('Returned Amount (birds)',key=scope+'_amount') if kind=='Partial return' else None
    reason=st.text_input('Reason for adjustment *',max_chars=2000,key=scope+'_reason')
    confirmed=confirm_report_changes(scope,when,f'{kind}|{value}')
    if st.button('Save lease adjustment',key=scope+'_save',disabled=not reason.strip() or (confirmation_required(when) and not confirmed)):
        try:
            try:amount=Decimal(value) if value is not None else None
            except InvalidOperation:amount=None
            payload=dict(id=identity,kind=kind,date=when,amount=amount,reason=reason.strip(),
                **({'reports_confirmed':True} if confirmed else {}))
            request=request_for(scope,payload)
            saved=repo.adjust_quota_lease(identity,kind,when,amount,reason.strip(),request,
                current.get('UPDATED_AT'),[row['ADJUSTMENT_ID'] for row in adjustments],reports_confirmed=confirmed)
            finish_request(scope,saved)
            open_saved_record(saved)
        except Exception as exc:show_data_error(exc)

"""Admin-only, reasoned correction of a saved lease; no delete or undo."""
import streamlit as st
from app.auth import current_user
from app.security import Role
from app.services.form_safety import request_for,finish_request,open_saved_record
from app.ui import show_data_error
from data.quota_leases import is_voided


def render_void_action(repo,current):
    if is_voided(current):
        st.info('Voided. This lease no longer affects quota. The original record and reason remain in Record History; create a new lease if needed.')
        return
    actor=current_user()
    if actor is None or actor.role!=Role.ADMIN:
        return
    identity=current['QUOTA_TRANSACTION_ID'];scope='lease_void_'+identity
    st.caption('Void lease corrects the whole saved lease period. It does not delete the record and cannot be undone here.')
    reason=st.text_input('Reason for voiding *',key=scope+'_reason',max_chars=2000)
    if st.button('Void lease',key=scope+'_submit',disabled=not reason.strip()):
        try:
            request=request_for(scope,dict(id=identity,reason=reason.strip()))
            result=repo.void_quota_lease(identity,reason.strip(),request,current.get('UPDATED_AT'))
            finish_request(scope,result)
            open_saved_record(result)
        except Exception as exc:
            show_data_error(exc)

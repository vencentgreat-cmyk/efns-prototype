"""Small Admin-only supplement workspace, separate from rejected-row corrections."""
import pandas as pd
import streamlit as st

from app.security import Role
from app.services.export import spreadsheet_safe
from app.ui import show_data_error


def render_flock_supplement(repo,user):
    if user.role != Role.ADMIN:
        return
    with st.expander("Historical Flock transaction supplement"):
        upload=st.file_uploader("Original associated-view workbook",type=['xlsx'],key='ft_supplement_file')
        batch_id=st.text_input("Original committed migration batch ID",key='ft_supplement_original_batch')
        flock_id=st.text_input("Explicit target Flock GUID",key='ft_supplement_flock')
        anchor_id=st.text_input("Existing Delivery transaction GUID",key='ft_supplement_anchor')
        basis=st.text_area("Reviewed binding evidence",max_chars=500,key='ft_supplement_basis')
        binding=dict(original_batch_id=batch_id.strip(),flock_id=flock_id.strip(),
                     anchor_transaction_id=anchor_id.strip(),basis=basis.strip())
        if st.button("Preview supplement",disabled=not upload,key='ft_supplement_preview'):
            try:
                st.session_state.ft_supplement_report=repo.preview_flock_transaction_supplement(upload.name,upload.getvalue(),binding)
            except Exception as exc:
                st.session_state.pop('ft_supplement_report',None)
                show_data_error(exc)
        preview=st.session_state.get('ft_supplement_report')
        if preview is None:
            return
        target,account,facility=preview['target'],preview['account'],preview['facility']
        st.write(dict(Flock=target['FLOCK_ID'],Flock_number=target['FLOCK_NUMBER'],
                      Account=account.get('ORGANIZATION_NAME'),Account_ID=target['ACCOUNT_ID'],
                      Facility=facility.get('FACILITY_NAME'),Facility_ID=target['FACILITY_ID'],
                      Binding_evidence=preview['binding']['basis']))
        st.write(dict(Source_rows=preview['source_rows'],**preview['counts']))
        table=pd.DataFrame([dict(Source_row=row['source_row'],GUID=(row['record'] or {}).get('FLOCK_TRANSACTION_ID'),
            Classification=row['classification'],Date=(row['record'] or {}).get('TRANSACTION_DATE'),
            Quantity=(row['record'] or {}).get('QUANTITY'),Count_source=(row['record'] or {}).get('COUNT_SOURCE_LABEL'),
            Errors=' '.join(row['errors'])) for row in preview['rows']])
        st.dataframe(table,hide_index=True,width='stretch')
        st.download_button('Download supplement preview',spreadsheet_safe(table).to_csv(index=False).encode('utf-8-sig'),
                           'flock-transaction-supplement-preview.csv',key='ft_supplement_download')
        confirmed=st.checkbox('I reviewed the original workbook, explicit parent binding and all row classifications.',
                              key=f"ft_supplement_confirm_{preview['review_token']}")
        if st.button('Commit historical transaction supplement',key='ft_supplement_commit',
                     disabled=not confirmed or not preview['can_commit'] or not upload or binding!=preview['binding']):
            try:
                result=repo.commit_flock_transaction_supplement(upload.name,upload.getvalue(),binding,
                    preview['review_token'],confirmed=confirmed)
                st.success(f"Supplement committed: {result['created_count']} new; {result['existing_count']} existing matches; 0 updated. Import reference: {result['import_id']}")
                st.session_state.pop('ft_supplement_report',None)
            except Exception as exc:
                show_data_error(exc)

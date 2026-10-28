"""Admin-only RAW-backed date repair, separate from rejected-row corrections."""
import csv
import io
from uuid import UUID
import pandas as pd
import streamlit as st
from app.security import Role
from app.ui import show_data_error
from app.services.export import spreadsheet_safe
from data.repositories.continuity import stable_id


def read_date_holds(content):
    reader=csv.DictReader(io.StringIO(content.decode('utf-8-sig')))
    if reader.fieldnames!=['FLOCK_ID','REASON']:
        raise ValueError('Exclusion file columns must be FLOCK_ID,REASON.')
    holds={}
    for row in reader:
        g=str(UUID(row['FLOCK_ID'].strip())).upper()
        if g in holds or not row['REASON'].strip():
            raise ValueError('Exclusions require unique GUIDs and a specific reason.')
        holds[g]=row['REASON'].strip()
    return holds


def render_flock_date_repair(repo,user):
    if user.role!=Role.ADMIN:return
    with st.expander('Historical Flock disposal date mapping repair'):
        if st.button('Inspect date repair runtime (read-only)',key='date_repair_runtime'):
            try:
                st.session_state.date_repair_runtime_report=repo.diagnose_flock_date_repair_context()
            except Exception as exc:
                st.session_state.pop('date_repair_runtime_report',None)
                show_data_error(exc)
        if st.session_state.get('date_repair_runtime_report'):
            st.json(st.session_state.date_repair_runtime_report)
        batch=st.text_input('Original committed batch',key='date_repair_batch')
        basis=st.text_area('Mapping evidence and approval basis',max_chars=1500,key='date_repair_basis')
        upload=st.file_uploader('Reviewed exclusions (CSV)',type=['csv'],key='date_repair_holds')
        holds=None
        if upload:
            try: holds=read_date_holds(upload.getvalue())
            except (ValueError,UnicodeError) as exc: st.error(str(exc))
        if st.button('Preview disposal date repair',disabled=holds is None,key='date_repair_preview'):
            try:st.session_state.date_repair_report=repo.preview_flock_date_repair(batch.strip(),basis,holds)
            except Exception as exc:
                st.session_state.pop('date_repair_report',None);show_data_error(exc)
                if getattr(exc,'date_identity_diagnostic',None):
                    st.json(exc.date_identity_diagnostic)
        report=st.session_state.get('date_repair_report')
        if report:
            table=pd.DataFrame([dict(FLOCK_ID=r['flock_id'],SOURCE_ROW=r['source_row'],STATUS=r['status'],REASON=r['reason'],
                OLD_ESTIMATED=(r['before'] or {}).get('EST_DISPOSAL'),OLD_ACTUAL=(r['before'] or {}).get('DISPOSAL_DATE'),
                NEW_ESTIMATED=(r['proposed'] or {}).get('EST_DISPOSAL'),NEW_ACTUAL=(r['proposed'] or {}).get('DISPOSAL_DATE')) for r in report['rows']])
            st.write(report['counts']);st.dataframe(table,hide_index=True,width='stretch')
            st.download_button('Download date repair preview',spreadsheet_safe(table).to_csv(index=False).encode('utf-8-sig'),'date-repair-preview.csv',key='date_repair_download')
            confirmed=st.checkbox('I approve only the eligible date corrections and the reviewed exclusions.',key='date_repair_confirm_'+report['review_token'])
            if st.button('Commit reviewed disposal date repair',disabled=not confirmed or not report['counts'].get('READY') or report['holds']!=holds or report['basis']!=basis.strip() or report['batch_id']!=batch.strip(),key='date_repair_commit'):
                operation_id=stable_id('flock-date-repair',report['batch_id'],report['review_token'])
                st.session_state.date_repair_operation_id=operation_id
                st.info(f'Operation reference: {operation_id}')
                bar=st.progress(0,text='Validating reviewed scope; no final commit yet.')
                def show_progress(event):
                    stage=event['stage'];done=event['processed'];total=event['total']
                    fraction=done/total if total else 0
                    if stage=='COMMITTED':
                        bar.progress(1.0,text=f'Commit confirmed: {done} records verified.')
                    elif stage=='NOT_CONFIRMED':
                        bar.progress(min(fraction,0.99),text='Final commit not confirmed. Do not resubmit; check the operation status.')
                    else:
                        label='Final verification and audit; not committed' if stage=='FINALIZING' else 'Processed inside transaction; not committed'
                        bar.progress(min(fraction,0.99),text=f'{label}: {done}/{total}.')
                try:
                    result=repo.commit_flock_date_repair(batch.strip(),basis,holds,report['review_token'],confirmed=True,progress=show_progress)
                    if result['already_committed']:
                        st.success(f"Repair already committed; no new date changes. Operation: {result['operation_id']}")
                    else:
                        st.success(f"Date corrections committed: {result['changed']}. Operation: {result['operation_id']}")
                    st.session_state.pop('date_repair_report',None)
                except Exception as exc:
                    show_data_error(exc)
                    st.warning(f'Final commit is not confirmed. Do not resubmit. Ask an administrator to check operation {operation_id} using the read-only status queries.')
        if st.session_state.get('date_repair_operation_id'):
            st.caption('Last requested date repair operation: '+st.session_state.date_repair_operation_id)
        operation=st.text_input('Original repair operation ID for protected reversal',key='date_reverse_operation')
        why=st.text_area('Reversal basis',max_chars=1500,key='date_reverse_basis')
        if st.button('Preview protected date reversal',key='date_reverse_preview'):
            try:st.session_state.date_reverse_report=repo.preview_flock_date_reversal(operation.strip(),why)
            except Exception as exc:
                st.session_state.pop('date_reverse_report',None);show_data_error(exc)
        reverse=st.session_state.get('date_reverse_report')
        if reverse:
            st.write({'Records_to_restore':len(reverse['rows'])})
            st.dataframe(pd.DataFrame([dict(FLOCK_ID=r['flock_id'],CURRENT_ESTIMATED=r['after'].get('EST_DISPOSAL'),CURRENT_ACTUAL=r['after'].get('DISPOSAL_DATE'),RESTORE_ESTIMATED=r['before'].get('EST_DISPOSAL'),RESTORE_ACTUAL=r['before'].get('DISPOSAL_DATE')) for r in reverse['rows']]),hide_index=True)
            ok=st.checkbox('I approve this protected reversal.',key='date_reverse_confirm_'+reverse['review_token'])
            if st.button('Commit protected date reversal',disabled=not ok or operation.strip()!=reverse['operation_id'] or why.strip()!=reverse['basis'],key='date_reverse_commit'):
                try:
                    st.success(str(repo.commit_flock_date_reversal(operation.strip(),why,reverse['review_token'],confirmed=True)))
                    st.session_state.pop('date_reverse_report',None)
                except Exception as exc:show_data_error(exc)

"""R3 regressions migrated from the audit; actual AppTest/Mock, never company writes."""
import os,re
from pathlib import Path
import pandas as pd
import pytest
from tests.auth_support import authenticated_app
from tests.test_staff_workflows import chain
from tests.test_operational_flock_quota_import import csv_upload
ROOT=Path(__file__).resolve().parents[1]

def page(repo,tmp_path,monkeypatch,filename):
    app=authenticated_app(ROOT/'streamlit_app.py',tmp_path,monkeypatch)
    app.session_state['_base_repo']=repo
    return app.switch_page('app/pages/'+filename).run()

def test_A01_daily_commit_unknown_is_not_reported_as_rollback(chain,tmp_path,monkeypatch):
    import streamlit as st
    # Installed AppTest cannot serialize segmented_control state on rerun.
    # Replace this display-only row filter with an equivalent native selectbox;
    # import/save/error code remains the actual unmodified page.
    monkeypatch.setattr(st,'segmented_control',lambda label,options,default=None,key=None,**kw: st.selectbox(label,options,index=list(options).index(default),key=key))
    from data.operational_flock_quota_import import analyze_operational_files
    from data.repositories.base import RepositoryError
    repo,account,other,facility,quota,*_=chain
    report=analyze_operational_files([csv_upload('DEV_TEST audit.csv',[dict(ACTION='CREATE',QUOTA_ID=quota,
        QUOTA_TRANSACTION_ID='DEV_TEST unknown',TRANSACTION_TYPE='Adjustment',QUOTA_COUNT=2,
        EFFECTIVE_DATE='2026-01-01')])],'Quota Transactions',repo)
    assert len(report.ready_rows)==1
    def unknown(*args,**kwargs):raise RepositoryError('COMMIT outcome is unknown. Do not save again; verify receipt.')
    monkeypatch.setattr(repo,'commit_staged_operational',unknown)
    app=authenticated_app(ROOT/'streamlit_app.py',tmp_path,monkeypatch)
    app.session_state['_base_repo']=repo
    app.session_state.daily_flock_quota_report=report
    app.session_state.daily_prepared_package_hash=report.package_hash
    app.session_state.daily_prepared_import_id='DEV_TEST staged'
    app.switch_page('app/pages/19_Daily_Flock_Quota_Import.py').run()
    assert not app.exception
    app.checkbox(key='daily_flock_quota_confirm_'+report.package_hash[:16]).check().run()
    next(b for b in app.button if b.label=='Confirm import').click().run()
    assert not app.exception
    assert not any('No business rows were committed' in e.value for e in app.error)
    assert any('unknown' in e.value.lower() for e in app.error)

    assert app.session_state.daily_flock_quota_submitted_hash==report.package_hash
    assert app.session_state.daily_flock_quota_unknown_outcomes[report.package_hash]=='DEV_TEST staged'
    app.run()
    assert next(b for b in app.button if b.label=='Confirm import').disabled
    # Re-review's ordinary transient guard reset must not unlock an unknown save.
    del app.session_state['daily_flock_quota_submitted_hash']
    app.run()
    assert next(b for b in app.button if b.label=='Confirm import').disabled
    assert any('reference: DEV_TEST staged' in e.value for e in app.error)


@pytest.mark.parametrize('error,known_no_write',[
    (Exception('DEV_TEST unclassified failure'),False),
    (__import__('data.repositories.base',fromlist=['RepositoryError']).RepositoryError('DEV_TEST validation failure'),False),
    (__import__('data.repositories.base',fromlist=['RepositoryError']).RepositoryError('System busy: no write transaction started within 30 seconds. Reload before trying again.'),True)])
def test_daily_failure_only_claims_no_write_with_explicit_evidence(chain,tmp_path,monkeypatch,error,known_no_write):
    import streamlit as st
    # Installed AppTest cannot serialize segmented_control state on rerun.
    # Replace this display-only row filter with an equivalent native selectbox;
    # import/save/error code remains the actual unmodified page.
    monkeypatch.setattr(st,'segmented_control',lambda label,options,default=None,key=None,**kw: st.selectbox(label,options,index=list(options).index(default),key=key))
    from data.operational_flock_quota_import import analyze_operational_files
    from data.repositories.base import RepositoryError
    repo,account,other,facility,quota,*_=chain
    report=analyze_operational_files([csv_upload('DEV_TEST audit.csv',[dict(ACTION='CREATE',QUOTA_ID=quota,
        QUOTA_TRANSACTION_ID='DEV_TEST unknown',TRANSACTION_TYPE='Adjustment',QUOTA_COUNT=2,
        EFFECTIVE_DATE='2026-01-01')])],'Quota Transactions',repo)
    assert len(report.ready_rows)==1
    def unknown(*args,**kwargs):raise error
    monkeypatch.setattr(repo,'commit_staged_operational',unknown)
    app=authenticated_app(ROOT/'streamlit_app.py',tmp_path,monkeypatch)
    app.session_state['_base_repo']=repo
    app.session_state.daily_flock_quota_report=report
    app.session_state.daily_prepared_package_hash=report.package_hash
    app.session_state.daily_prepared_import_id='DEV_TEST staged'
    app.switch_page('app/pages/19_Daily_Flock_Quota_Import.py').run()
    assert not app.exception
    app.checkbox(key='daily_flock_quota_confirm_'+report.package_hash[:16]).check().run()
    next(b for b in app.button if b.label=='Confirm import').click().run()
    assert not app.exception

    assert any('No business rows were committed' in e.value for e in app.error) is known_no_write
    assert ('daily_flock_quota_submitted_hash' not in app.session_state) is known_no_write


def test_A02_producer_confirmation_is_cleared_on_record_switch(chain,tmp_path,monkeypatch):
    repo,*_=chain
    repo._production=pd.concat([repo._production,pd.DataFrame([dict(PRODUCTION_ID='DEV_TEST producer '+str(i),
        PRODUCER_ACCOUNT_ID=None,MATCH_STATUS='NO_CANDIDATE',PRODUCER_NUMBER=str(i),
        SOURCE_FILE_ID='DEV_TEST source',SOURCE_ROW_NUMBER=i+1) for i in range(2)])],ignore_index=True)
    app=page(repo,tmp_path,monkeypatch,'21_Record_History.py')
    assert not app.exception
    checkbox=lambda:next(c for c in app.checkbox if c.label=='I verified this Account against source evidence.')
    checkbox().check().run()
    chosen=next(s for s in app.selectbox if s.label=='Production record to review')
    chosen.select('DEV_TEST producer 1').run()
    assert not app.exception
    assert checkbox().value is False

    account=next(w for w in app.selectbox if w.label=='Confirmed producer Account')
    assert account.value=='Choose an Account'
    assert next(w for w in app.text_area if w.label=='Evidence for this producer decision').value==''
    button=lambda:next(b for b in app.button if b.label=='Confirm producer Account')
    assert button().disabled
    account.select(next(o for o in account.options if 'counterparty' in o))
    next(w for w in app.text_area if w.label=='Evidence for this producer decision').input('DEV_TEST record-specific evidence')
    app.run()
    assert button().disabled
    checkbox().check().run()
    assert not button().disabled
    assert repo.get_production_records().PRODUCER_ACCOUNT_ID.isna().all()


def test_A03_flock_event_confirmation_is_cleared_on_switch(chain,tmp_path,monkeypatch):
    repo,account,other,facility,quota,flock,record=chain
    second=repo.upsert_flock(dict(record,FLOCK_NUMBER='DEV_TEST second',PERMIT_NUMBER='DEV_TEST second'))
    app=page(repo,tmp_path,monkeypatch,'21_Record_History.py')
    assert not app.exception
    label='I checked the recorded original Facility, destination and business time against evidence. An unknown origin remains unknown.'
    next(c for c in app.checkbox if c.label==label).check().run()
    select=next(s for s in app.selectbox if s.label=='Flock')
    select.select(next(o for o in select.options if second in o)).run()
    assert not app.exception
    assert next(c for c in app.checkbox if c.label==label).value is False


@pytest.mark.parametrize('change',['destination','type','day','time'])
def test_event_confirmation_resets_when_reviewed_inputs_change(chain,tmp_path,monkeypatch,change):
    import datetime as dt
    repo,account,*_=chain
    repo.upsert_facility(dict(ACCOUNT_ID=account,FACILITY_NAME='DEV_TEST destination',FACILITY_TYPE='Layer',STATUS='Active'))
    app=page(repo,tmp_path,monkeypatch,'21_Record_History.py')
    confirm=lambda:next(c for c in app.checkbox if c.label.startswith('I checked the recorded original Facility'))
    next(t for t in app.text_area if t.label=='Reason for the event').input('DEV_TEST movement evidence')
    dest=next(s for s in app.selectbox if s.label=='Destination Facility')
    dest.select(dest.options[1]).run()
    confirm().check().run()
    button=lambda:next(b for b in app.button if b.label=='Record business event')
    assert not button().disabled
    if change=='destination':
        dest=next(s for s in app.selectbox if s.label=='Destination Facility')
        dest.select(dest.options[2]).run()
    elif change=='type':next(s for s in app.selectbox if s.label=='Business event').select('Actual lifecycle end').run()
    elif change=='day':
        widget=next(s for s in app.date_input if s.label=='Business date')
        widget.set_value(widget.value-dt.timedelta(days=1)).run()
    else:next(s for s in app.time_input if s.label=='Business time (Atlantic / Halifax)').set_value(dt.time(11)).run()
    assert not app.exception and confirm().value is False and button().disabled
    confirm().check().run()
    assert not button().disabled
    assert repo.get_flock_events(chain[5]).empty

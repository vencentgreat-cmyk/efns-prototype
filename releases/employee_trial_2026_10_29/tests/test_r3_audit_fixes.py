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

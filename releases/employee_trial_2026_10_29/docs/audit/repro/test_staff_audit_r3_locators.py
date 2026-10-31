"""Audit repros: assertions describe desired safety; failures are findings, not fixes.
Run from the release directory with its offline root conftest.py/network block.
Synthetic records and fake executors only. No company connection is used.
"""
import os,re
from pathlib import Path
import pandas as pd
from tests.auth_support import authenticated_app
from tests.test_staff_workflows import chain
from tests.test_operational_flock_quota_import import csv_upload
ROOT=Path(__file__).resolve().parents[3]

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


def test_A04_user_delete_confirmation_is_bound_to_user(tmp_path,monkeypatch):
    from app.security import SQLiteAuthStore
    from tests.test_snowflake_security import user
    app=authenticated_app(ROOT/'streamlit_app.py',tmp_path,monkeypatch)
    store=SQLiteAuthStore(Path(os.environ['EFNS_AUTH_DB']),seeds=[])
    admin=store.list_users(user())[0]
    from app.security import Role
    for label in ('One','Two'):
        store.create_user(admin,'dev_test_'+label.lower()+'@nsegg.ca','DEV_TEST '+label,Role.DATA_EDITOR)
    app.switch_page('app/pages/15_User_Management.py').run()
    select=app.selectbox(key='admin_selected_user')
    select.select(next(o for o in select.options if 'DEV_TEST One' in o)).run()
    next(c for c in app.checkbox if c.label=='Confirm deletion').check().run()
    select=app.selectbox(key='admin_selected_user')
    select.select(next(o for o in select.options if 'DEV_TEST Two' in o)).run()
    assert not app.exception
    assert next(c for c in app.checkbox if c.label=='Confirm deletion').value is False


def test_A05_salmonella_facility_filter_keeps_same_name_identities(chain,tmp_path,monkeypatch):
    repo,account,other,facility,*_=chain
    repo.upsert_facility(dict(ACCOUNT_ID=other,FACILITY_NAME=repo.get_facility(facility)['FACILITY_NAME'],
        FACILITY_TYPE='Layer',STATUS='Active'))
    assert len(repo.get_facilities())==2
    app=page(repo,tmp_path,monkeypatch,'10_Salmonella_Report.py')
    assert not app.exception
    assert len(app.selectbox(key='sal_rpt_facility').options)-1==2


def test_A06_user_update_has_review_version_predicate():
    from tests.test_snowflake_security import QueueExecutor,user_frame,user
    from app.snowflake_security import SnowflakeAuthStore
    from app.security import Role
    executor=QueueExecutor([user_frame(),user_frame(role=Role.REPORTING_VIEWER.value)])
    store=SnowflakeAuthStore(executor)
    store.update_user(user(),'u-1',role=Role.REPORTING_VIEWER,active=True)
    sql=next(sql for kind,sql,params in executor.calls if kind=='execute' and sql.startswith('UPDATE '))
    assert 'UPDATED_AT' in sql.split('WHERE',1)[1]


def test_A08_salmonella_historical_result_remains_filterable(chain,tmp_path,monkeypatch):
    repo,account,other,facility,quota,flock,*_=chain
    repo._salmonella_tests=pd.concat([repo._salmonella_tests,pd.DataFrame([dict(
        SALMONELLA_TEST_ID='DEV_TEST legacy result',FLOCK_ID=flock,ACCOUNT_ID=account,
        PERMIT_NUMBER='DEV_TEST permit',TEST_RESULT='DEV_TEST historical code',
        TESTING_DATE='2026-01-01')])],ignore_index=True)
    app=page(repo,tmp_path,monkeypatch,'10_Salmonella_Report.py')
    assert not app.exception
    assert 'DEV_TEST historical code' in app.selectbox(key='sal_rpt_result').options


def test_A09_salmonella_report_cannot_multiply_on_duplicate_parent(chain):
    from app.services.salmonella_reporting import build_salmonella_report
    repo,account,other,facility,quota,flock,*_=chain
    repo._salmonella_tests=pd.concat([repo._salmonella_tests,pd.DataFrame([dict(
        SALMONELLA_TEST_ID='DEV_TEST one test',FLOCK_ID=flock,ACCOUNT_ID=account,
        PERMIT_NUMBER='DEV_TEST permit',TEST_RESULT='Negative',TESTING_DATE='2026-01-01')])],ignore_index=True)
    repo._flocks=pd.concat([repo._flocks,repo._flocks.copy(deep=True)],ignore_index=True)
    assert len(repo.get_salmonella_tests())==1
    assert len(build_salmonella_report(repo))==1


def test_A07_last_admin_check_is_inside_write_transaction():
    from tests.test_snowflake_security import QueueExecutor,user_frame,user
    from app.snowflake_security import SnowflakeAuthStore
    from app.security import Role
    executor=QueueExecutor([user_frame(role=Role.ADMIN.value),
        pd.DataFrame([{'ADMIN_COUNT':1}]),user_frame(role=Role.DATA_EDITOR.value)])
    SnowflakeAuthStore(executor).update_user(user(),'u-1',role=Role.DATA_EDITOR,active=True)
    check=next(i for i,(kind,sql,params) in enumerate(executor.calls) if 'ADMIN_COUNT' in sql)
    begin=next(i for i,(kind,sql,params) in enumerate(executor.calls) if kind=='begin')
    assert check>begin

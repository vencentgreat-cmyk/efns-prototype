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


def test_A04_user_delete_confirmation_is_bound_to_user(tmp_path,monkeypatch):
    from app.security import SQLiteAuthStore
    from tests.test_snowflake_security import user
    app=authenticated_app(ROOT/'streamlit_app.py',tmp_path,monkeypatch)
    store=SQLiteAuthStore(Path(os.environ['EFNS_AUTH_DB']),seeds=[])
    admin=store.list_users(user())[0]
    from app.security import Role
    for label in ('One','Two'):
        store.create_user(admin,'dev_test_'+label.lower()+'@nsegg.ca','DEV_TEST '+label,Role.DATA_EDITOR)
    users_before={u.user_id for u in store.list_users(admin)}
    app.switch_page('app/pages/15_User_Management.py').run()
    select=app.selectbox(key='admin_selected_user')
    select.select(next(o for o in select.options if 'DEV_TEST One' in o)).run()
    next(c for c in app.checkbox if c.label=='Confirm deletion').check().run()
    select=app.selectbox(key='admin_selected_user')
    select.select(next(o for o in select.options if 'DEV_TEST Two' in o)).run()
    assert not app.exception
    assert next(c for c in app.checkbox if c.label=='Confirm deletion').value is False

    assert next(b for b in app.button if b.label=='Delete user').disabled
    assert {u.user_id for u in store.list_users(admin)}==users_before


def test_A05_salmonella_facility_filter_keeps_same_name_identities(chain,tmp_path,monkeypatch):
    repo,account,other,facility,*_=chain
    repo.upsert_facility(dict(ACCOUNT_ID=other,FACILITY_NAME=repo.get_facility(facility)['FACILITY_NAME'],
        FACILITY_TYPE='Layer',STATUS='Active'))
    assert len(repo.get_facilities())==2
    app=page(repo,tmp_path,monkeypatch,'10_Salmonella_Report.py')
    assert not app.exception
    assert len(app.selectbox(key='sal_rpt_facility').options)-1==2


def test_selector_ids_are_stable_even_with_common_prefixes_and_natural_suffixes():
    from app.services.selector_options import unique_identity_options
    pairs=[('Barn','12345678-a'),('Barn','12345678-b'),('Normal','other-id'),
           ('Barn · 12345678-a','natural-id'),('All','all-id')]
    options=unique_identity_options(pairs,reserved_labels=('All',))
    assert options==unique_identity_options(reversed(pairs),reserved_labels=('All',))
    assert len(options)==len(pairs) and set(options.values())=={i for _,i in pairs}
    assert options['Normal']=='other-id' and options['Barn · 12345678-a']=='natural-id'
    assert 'All' not in options


@pytest.mark.parametrize('filename,view_key,widget_key,kind',[
 ('6_Flock_Transactions.py','6_Flock_Transactions','flock_tx_form_flock','flock'),
 ('9_Salmonella_Tests.py','9_Salmonella_Tests','salmonella_form_flock','flock'),
 ('13_Facility_Details.py','13_Facility_Details','facility_detail_form_facility','facility')])
def test_collision_selectors_keep_both_targets(chain,tmp_path,monkeypatch,filename,view_key,widget_key,kind):
    repo,account,other,facility,quota,flock,record=chain
    if kind=='flock':
        second=repo.upsert_flock(dict(record))
        ids={flock,second}
    else:
        first=repo.get_facility(facility)
        first.pop('FACILITY_ID')
        second=repo.upsert_facility(first)
        ids={facility,second}
    app=authenticated_app(ROOT/'streamlit_app.py',tmp_path,monkeypatch)
    app.session_state['_base_repo']=repo
    app.session_state['_efns_record_'+view_key+'_view']='new'
    app.switch_page('app/pages/'+filename).run()
    assert not app.exception
    selector=app.selectbox(key=widget_key)
    assert len(selector.options)==2 and len(set(selector.options))==2
    for identity in ids:
        assert any(identity[:8] in label for label in selector.options)
    selector.select(selector.options[1]).run()
    assert not app.exception and app.selectbox(key=widget_key).value==selector.options[1]


def test_A08_salmonella_historical_result_remains_filterable(chain,tmp_path,monkeypatch):
    repo,account,other,facility,quota,flock,*_=chain
    repo._salmonella_tests=pd.concat([repo._salmonella_tests,pd.DataFrame([dict(
        SALMONELLA_TEST_ID='DEV_TEST legacy result',FLOCK_ID=flock,ACCOUNT_ID=account,
        PERMIT_NUMBER='DEV_TEST permit',TEST_RESULT='DEV_TEST historical code',
        TESTING_DATE='2026-01-01')])],ignore_index=True)
    app=page(repo,tmp_path,monkeypatch,'10_Salmonella_Report.py')
    assert not app.exception
    assert 'DEV_TEST historical code' in app.selectbox(key='sal_rpt_result').options


def test_historical_filter_union_is_ordered_and_null_safe():
    from app.services.selector_options import historical_filter_options
    assert historical_filter_options(('Pending','Negative'),[None,pd.NA,float('nan'),'z-old','A-old','Pending',''])==['Pending','Negative','A-old','z-old']


@pytest.mark.parametrize('filename,key,entity,field',[
 ('9_Salmonella_Tests.py','salmonella_filter_result','test','TEST_RESULT'),
 ('11_Facilities.py','facility_filter_type','facility','FACILITY_TYPE')])
def test_staff_filters_include_historical_values_without_changing_new_choices(chain,tmp_path,monkeypatch,filename,key,entity,field):
    repo,account,other,facility,quota,flock,*_=chain
    if entity=='test':
        repo._salmonella_tests=pd.concat([repo._salmonella_tests,pd.DataFrame([dict(
            SALMONELLA_TEST_ID='DEV_TEST historical result',FLOCK_ID=flock,ACCOUNT_ID=account,
            PERMIT_NUMBER='DEV_TEST permit',TEST_RESULT='DEV_TEST historical result',TESTING_DATE='2026-01-01')])],ignore_index=True)
        selected='DEV_TEST historical result'
    else:
        repo._facilities.loc[repo._facilities.FACILITY_ID==facility,'FACILITY_TYPE']='DEV_TEST historical type'
        selected='DEV_TEST historical type'
    app=page(repo,tmp_path,monkeypatch,filename)
    assert not app.exception and selected in app.selectbox(key=key).options
    app.selectbox(key=key).select(selected).run()
    assert not app.exception
    assert any(len(f.value)==1 for f in app.dataframe)
    # Existing edit compatibility is retained; new-entry choices are unchanged.
    view_key=filename[:-3]
    app.session_state['_efns_record_'+view_key+'_view']='new'
    app.run()
    new_key='salmonella_form_result' if entity=='test' else 'facility_form_type'
    assert selected not in app.selectbox(key=new_key).options


def test_audit_log_discloses_loaded_filter_scope(chain,tmp_path,monkeypatch):
    app=page(chain[0],tmp_path,monkeypatch,'16_Audit_Log.py')
    assert not app.exception
    assert any(c.value=='Filters apply to the latest 5,000 audit events loaded.' for c in app.caption)

"""Synthetic daily lease amounts, append-only atomicity and role boundaries."""
import datetime as dt
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from threading import RLock
import pandas as pd
import pytest
from tests.test_quota_leases import repository, lease, ledger, pos
from tests.test_quota_lease_void import saved, void, ADMIN
from tests.test_report_center import user
from data.quota_leases import effective_lease_amount, effective_lease_end, validate_lease_period
from data.quota_position import load_rules
from data.repositories.base import RepositoryError, ConcurrencyError
from data.repositories.snowflake import SnowflakeRepository
from app.services.authorized_repository import AuthorizedRepository
from app.security import Role, SQLiteAuthStore, AuthorizationError, Permission, has_permission
from app.services.report_center import build_quota_summary, report_csv
from app.services.revision_history import revision_changes

START=dt.date(2026,12,20)


def adjust(repo, identity, kind='Partial return', when='2026-12-22', amount=7, request='adjust', expected=None):
    current=repo.get_quota_transaction(identity)
    ids=[row['ADJUSTMENT_ID'] for row in repo.get_quota_lease_adjustments([identity])[identity.lower()]]
    return repo.adjust_quota_lease(identity,kind,when,amount,'Synthetic correction',request,
        current['UPDATED_AT'],ids if expected is None else expected,actor=ADMIN)


def position(repo, when, owner='a'):
    return pos(repo.get_quota_registrations(),repo.get_quota_transactions(),owner,when)['net_position']


def test_incoming_quota_cannot_be_leased_onward_even_when_incoming_covers_period():
    r,identity=saved()
    with pytest.raises(RepositoryError,match='exceeds'):
        r.upsert_quota_transaction(lease(QUOTA_TRANSACTION_ID='onward',QUOTA_ID='qb',OWNER_ACCOUNT_ID='b',RELATED_ACCOUNT_ID='a',QUOTA_COUNT=60))
    assert r.upsert_quota_transaction(lease(QUOTA_TRANSACTION_ID='own',QUOTA_ID='qb',OWNER_ACCOUNT_ID='b',RELATED_ACCOUNT_ID='a',QUOTA_COUNT=50))
    assert len(r.get_quota_transactions())==4


@pytest.mark.parametrize('end',[START,START+dt.timedelta(days=1)])
def test_early_end_inclusive_original_immutable_history_audit_and_retry(end):
    r,identity=saved();original=r.get_quota_transaction(identity)
    adjust(r,identity,'Ended early',end,None)
    assert position(r,end)==80 and position(r,end+dt.timedelta(days=1))==100
    pd.testing.assert_series_equal(pd.Series(original),pd.Series(r.get_quota_transaction(identity)))
    change=revision_changes(r.get_record_revisions_for('QUOTA_TRANSACTION',identity))
    assert 'Ended early' in set(change['Change type'])
    assert 'Quota End Date' in set(change.Field)
    before=len(r._continuity_rows['RECORD_REVISION']);audit=len(r._migration_review_audit)
    adjust(r,identity,'Ended early',end,None)
    assert len(r._continuity_rows['RECORD_REVISION'])==before and len(r._migration_review_audit)==audit


def test_partial_returns_daily_effects_and_own_capacity_recovered():
    r,identity=saved();adjust(r,identity)
    assert position(r,'2026-12-21')==80
    assert position(r,'2026-12-22')==87 and position(r,'2026-12-22','b')==63
    adjust(r,identity,when='2026-12-24',amount=3,request='second')
    assert position(r,'2026-12-24')==90
    candidate=lease(QUOTA_TRANSACTION_ID='second-deal',QUOTA_COUNT=90,EFFECTIVE_DATE='2026-12-24')
    assert not validate_lease_period(candidate,r.get_quota_registrations(),r.get_quota_transactions(),set(),load_rules())
    assert validate_lease_period(dict(candidate,QUOTA_COUNT=91),r.get_quota_registrations(),r.get_quota_transactions(),set(),load_rules())
    with pytest.raises(RepositoryError):adjust(r,identity,when='2026-12-23',amount=11,request='too-much')


def test_full_return_equals_end_previous_day_and_void_removes_all_adjustments():
    r,identity=saved();other,other_id=saved()
    adjust(r,identity,amount=20)
    adjust(other,other_id,'Ended early','2026-12-21',None)
    for day in ('2026-12-19','2026-12-20','2026-12-21','2026-12-22','2027-01-11'):
        for owner in ('a','b'):assert position(r,day,owner)==position(other,day,owner)
    void(r,identity)
    assert position(r,'2026-12-20')==100 and position(r,'2026-12-20','b')==50
    assert len(r.get_quota_lease_adjustments([identity])[identity.lower()])==1


@pytest.mark.parametrize('kind,when,amount',[
    ('Partial return','2026-12-20',1),('Partial return','2027-01-11',1),
    ('Partial return','2026-12-22',0),('Partial return','2026-12-22',21),
    ('Partial return','2026-12-22','1.5'),('Partial return','2026-12-22','NaN'),
    ('Ended early','2026-12-19',None),('Ended early','2027-01-10',None)])
def test_invalid_adjustments_leave_history_and_original_untouched(kind,when,amount):
    r,identity=saved();before=deepcopy(r._continuity_rows)
    with pytest.raises(RepositoryError):adjust(r,identity,kind,when,amount)
    assert r._continuity_rows==before


@pytest.mark.parametrize('failure',['revision','audit'])
def test_mandatory_history_or_audit_failure_rolls_back(monkeypatch,failure):
    r,identity=saved();before=deepcopy(r._continuity_rows)
    if failure=='revision':
        monkeypatch.setattr(r,'_append_history',lambda *args: (_ for _ in ()).throw(RepositoryError('Synthetic history failure')))
    else:
        monkeypatch.setattr(r,'_review_insert',lambda *args: (_ for _ in ()).throw(RepositoryError('Synthetic audit failure')))
    with pytest.raises(RepositoryError):adjust(r,identity)
    assert r._continuity_rows==before
    assert position(r,'2026-12-22')==80


def test_two_concurrent_returns_cannot_overreturn_and_stale_review_rejected():
    r,identity=saved()
    def run(i):
        try:return adjust(r,identity,amount=12,request=str(i),expected=[])
        except RepositoryError:return None
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,(1,2)))
    assert sum(value is not None for value in results)==1
    assert position(r,'2026-12-22')==92
    with pytest.raises(ConcurrencyError):adjust(r,identity,amount=1,request='stale',expected=[])


@pytest.mark.parametrize('role',list(Role))
def test_role_scoped_create_and_adjust_without_other_permission_changes(tmp_path,role):
    r=repository();actor=user(role);proxy=AuthorizedRepository(r,SQLiteAuthStore(tmp_path/(role.name+'.db')),actor)
    row=lease();row.pop('QUOTA_TRANSACTION_ID')
    if role==Role.REPORTING_VIEWER:
        with pytest.raises((RepositoryError,AuthorizationError)):proxy.create_record_once('QUOTA_TRANSACTION',row,'create')
        r,identity=saved();proxy=AuthorizedRepository(r,proxy.auth_store,actor)
        with pytest.raises((RepositoryError,AuthorizationError)):proxy.adjust_quota_lease(identity,'Partial return','2026-12-22',1,'Synthetic reason','adjust',r.get_quota_transaction(identity)['UPDATED_AT'],[])
    else:
        identity=proxy.create_record_once('QUOTA_TRANSACTION',row,'create')
        assert proxy.adjust_quota_lease(identity,'Partial return','2026-12-22',1,'Synthetic reason','adjust',r.get_quota_transaction(identity)['UPDATED_AT'],[])==identity
        if role==Role.DEVELOPER:
            assert not has_permission(actor,Permission.CREATE_DATA) and not has_permission(actor,Permission.UPDATE_DATA)
            with pytest.raises(RepositoryError):proxy.create_record_once('ACCOUNT',{'ORGANIZATION_NAME':'Synthetic'},'denied')
            with pytest.raises((RepositoryError,AuthorizationError)):proxy.void_quota_lease(identity,'Synthetic reason','void',r.get_quota_transaction(identity)['UPDATED_AT'])


def test_no_adjustment_preserves_existing_positions_and_no_lease_csv():
    r,identity=saved()
    for owner in ('a','b'):
        assert pos(r._quota_registrations,r._quota_transactions,owner,'2026-12-22')==pos(r.get_quota_registrations(),r.get_quota_transactions(),owner,'2026-12-22')
    baseline=repository();before,_=build_quota_summary(baseline,user=user(),as_of_date=START,quota_type='Egg Production')
    after,_=build_quota_summary(repository(),user=user(),as_of_date=START,quota_type='Egg Production')
    assert report_csv(user(),after)==report_csv(user(),before)


@pytest.mark.parametrize('entrypoint',['streamlit_app.py','app/Home.py'])
def test_developer_new_lease_ui_and_unchanged_allocation_denial(tmp_path,monkeypatch,entrypoint):
    from tests.auth_support import authenticated_app
    root=Path(__file__).parents[1];r=repository()
    app=authenticated_app(root/entrypoint,tmp_path,monkeypatch,role=Role.DEVELOPER)
    app.session_state['_base_repo']=r
    app.switch_page(('app/pages/' if entrypoint=='streamlit_app.py' else 'pages/')+'8_Quota_Transactions.py').run()
    app.button(key='quota_tx_new_lease').click().run()
    assert not app.exception and app.selectbox(key='quota_tx_form_method').value=='Lease'
    assert app.selectbox(key='quota_tx_form_method').disabled
    assert any(button.label=='Save lease' for button in app.button)
    app.text_input(key='quota_lease_form_amount').set_value('5')
    app.date_input(key='quota_lease_form_start').set_value(START)
    app.date_input(key='quota_lease_form_end').set_value(dt.date(2027,1,10))
    app.button(key='quota_tx_save_lease').click().run()
    assert not app.exception and not app.error
    assert len(r._quota_transactions)==3
    identity=r._quota_transactions.iloc[-1]['QUOTA_TRANSACTION_ID']
    # Reopen the saved record in a fresh page tree after form-safety clears the
    # obsolete creation widgets; no private AppTest/widget-state bypass.
    app=authenticated_app(root/entrypoint,tmp_path,monkeypatch,role=Role.DEVELOPER)
    app.session_state['_base_repo']=r
    app.session_state['_efns_record_8_Quota_Transactions_view']='detail'
    app.session_state['_efns_record_8_Quota_Transactions_id']=identity
    app.switch_page(('app/pages/' if entrypoint=='streamlit_app.py' else 'pages/')+'8_Quota_Transactions.py').run()
    scope='lease_adjust_'+identity
    app.selectbox(key=scope+'_kind').set_value('Partial return').run()
    app.date_input(key=scope+'_date').set_value(dt.date(2026,12,22))
    app.text_input(key=scope+'_amount').set_value('2')
    app.text_input(key=scope+'_reason').set_value('Synthetic reason')
    app.button(key=scope+'_save').click().run()
    assert not app.exception and not app.error
    assert position(r,'2026-12-22')==97


def test_adjusted_quotas_reach_utilization_producers_and_quota_reports():
    from app.services.flock_age_report import build_flock_age_quotas, utilization
    from app.services.producers_over_quota_report import build_producers_over_quota_report
    from app.services.quota_reports import build_quota_history_report, build_quota_leases_report
    r,identity=saved();adjust(r,identity)
    when=dt.date(2026,12,23);activity=r.get_quota_transactions()
    quotas,_,_=build_flock_age_quotas(r.get_quota_registrations(),activity,r.get_accounts(),when,set(),load_rules())
    assert quotas=={'a':87,'b':63} and utilization(40,quotas['a'])=='45.98%'
    flocks=pd.DataFrame([dict(FLOCK_ID=k,PERMIT_NUMBER=k,FLOCK_NUMBER=k,ACCOUNT_ID=k,FACILITY_ID='barn',
        FLOCK_QUOTA_TYPE='Egg Production',STATUS='Active',HATCH_DATE='2026-01-01',PLACEMENT_DATE='2026-05-01',
        EST_DISPOSAL='2028-01-01',DISPOSAL_DATE=None,BIRD_COUNT=40) for k in ('a','b')])
    observations=pd.DataFrame([dict(FLOCK_ID=k,FLOCK_TRANSACTION_ID=k,TRANSACTION_TYPE='Count',TRANSACTION_DATE=when,QUANTITY=40) for k in ('a','b')])
    frame,_=build_producers_over_quota_report(flocks,observations,r.get_accounts(),pd.DataFrame([dict(FACILITY_ID='barn',FACILITY_NAME='Synthetic')]),quotas,when)
    assert '45.98%' in frame['% Quota'].tolist()
    summary,_=build_quota_summary(r,user=user(),as_of_date=when,quota_type='Egg Production')
    assert list(summary.Issuance)==[150,87,63]
    history,_=build_quota_history_report(r.get_accounts(),r.get_quota_registrations(),activity,set(),when,rules=load_rules())
    assert history.loc[history['Reg No'].eq('001'),'Current Quota'].eq(87).all()
    leases,_=build_quota_leases_report(r.get_accounts(),r.get_quota_registrations(),activity,set(),when)
    assert leases['Bird Count'].tolist()==[13,13]


def test_two_snowflake_sessions_share_existing_lock_and_append_only(monkeypatch):
    lock=RLock();revisions=[];audits=[];locks=[]
    original=dict(lease(),UPDATED_AT='2026-01-01',LEASE_STATUS=None)
    class Executor:
        @contextmanager
        def transaction(self):
            with lock:
                before=deepcopy(revisions),deepcopy(audits)
                try:yield self
                except Exception:
                    revisions[:]=before[0];audits[:]=before[1]
                    raise
        intake_transaction=transaction
        def query(self,sql,params=None):
            if 'RECORD_REVISION' in sql:
                rows=revisions
                if 'REVISION_ID = %s' in sql:rows=[row for row in rows if row['REVISION_ID']==params[0]]
                return pd.DataFrame(deepcopy(rows))
            assert 'QUOTA_TRANSACTION' in sql
            return pd.DataFrame([original])
        def execute(self,sql,params):
            if 'INTAKE_LOCK' in sql:locks.append(sql);return 1
            if 'RECORD_REVISION' in sql:
                fields=sql.split('(',1)[1].split(')',1)[0].replace(' ','').split(',')
                revisions.append(dict(zip(fields,params)));return 1
            assert 'AUDIT_EVENT' in sql
            audits.append(params);return 1
    executor=Executor();repos=[SnowflakeRepository(executor),SnowflakeRepository(executor)]
    def run(index):
        try:return repos[index].adjust_quota_lease('deal','Partial return','2026-12-22',12,'Synthetic reason',str(index),'2026-01-01',[],actor=ADMIN)
        except RepositoryError:return None
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,(0,1)))
    assert sum(item is not None for item in results)==1
    assert len(locks)==2 and len(revisions)==len(audits)==1
    assert original['QUOTA_COUNT']==20 and original['END_DATE']=='2027-01-10'


def test_corrupt_adjustments_fail_closed():
    row=lease(_LEASE_ADJUSTMENTS=[dict(KIND='Partial return',EFFECTIVE_DATE='2026-12-22',RETURNED_AMOUNT=21)])
    assert effective_lease_amount(row,'2026-12-23') is None
    _,regs,tx=ledger()
    result=pos(regs,pd.concat([tx,pd.DataFrame([row])],ignore_index=True),'a','2026-12-23')
    assert result['net_position'] is None

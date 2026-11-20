"""Synthetic void corrections, downstream parity, authorization and rollback."""
import datetime as dt
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from copy import deepcopy

import pandas as pd
import pytest

from tests.test_quota_leases import repository, lease, ledger, pos
from tests.test_report_center import user
from data.quota_lease_void import void_errors
from data.quota_leases import is_voided
from data.quota_position import load_rules
from data.repositories.base import RepositoryError, ConcurrencyError
from data.repositories.snowflake import SnowflakeRepository
from app.services.report_center import build_quota_summary, build_quota_summary_details, report_csv, report_xlsx
from app.services.flock_age_report import build_flock_age_quotas, build_flock_age_report
from app.services.flock_reports import build_flock_status_report
from app.services.producers_over_quota_report import build_producers_over_quota_report
from app.services.quota_reports import build_quota_history_report, build_quota_leases_report, build_quota_transactions_report
from app.services.revision_history import revision_changes,record_option_label
from app.security import Role,SQLiteAuthStore
from app.services.authorized_repository import AuthorizedRepository

ADMIN={'user_id':'synthetic-admin','email':'test.admin@nsegg.ca','role':'Admin'}
WHEN=dt.date(2026,12,21)


def saved(r=None):
    r=repository() if r is None else r
    record=lease();record.pop('QUOTA_TRANSACTION_ID')
    identity=r.create_record_once('QUOTA_TRANSACTION',record,'new-lease',actor='synthetic-staff')
    return r,identity


def void(r,identity,request='void-one',reason='Synthetic entry mistake',actor=ADMIN):
    return r.void_quota_lease(identity,reason,request,r.get_quota_transaction(identity)['UPDATED_AT'],actor=actor)


def test_void_restores_position_allocation_sum_original_record_history_and_retry():
    r,identity=saved();before=deepcopy(r.get_quota_transaction(identity))
    quotas,_,_=build_flock_age_quotas(r._quota_registrations,r._quota_transactions,r._accounts,WHEN,set(),load_rules())
    assert quotas=={'a':80,'b':70}
    assert void(r,identity)==identity
    after=r.get_quota_transaction(identity)
    assert is_voided(after) and len(r._quota_transactions)==3
    for field in before:
        if field not in {'LEASE_STATUS','UPDATED_AT'}:
            assert (pd.isna(after[field]) and pd.isna(before[field])) or after[field]==before[field]
    quotas,_,_=build_flock_age_quotas(r._quota_registrations,r._quota_transactions,r._accounts,WHEN,set(),load_rules())
    assert quotas=={'a':100,'b':50} and sum(quotas.values())==150
    history=r.get_record_revisions_for('QUOTA_TRANSACTION',identity)
    changes=revision_changes(history)
    assert 'Voided' in set(changes['Change type']) and 'Voided' in set(changes['New value'])
    assert record_option_label('QUOTA_TRANSACTION',after,'QUOTA_TRANSACTION_ID').startswith('Voided lease')
    assert history.iloc[0].RECORDED_BY==ADMIN['user_id']
    assert history.iloc[0].REASON=='Synthetic entry mistake'
    assert len(r._migration_review_audit)==2 and r._migration_review_audit[-1]['ACTION']=='UPDATE'
    assert void(r,identity)==identity  # Same request is idempotent.
    assert len(r.get_record_revisions_for('QUOTA_TRANSACTION',identity))==2
    with pytest.raises(RepositoryError,match='already Voided'):void(r,identity,request='different')
    with pytest.raises(RepositoryError):r.upsert_quota_transaction(dict(after,LEASE_STATUS=None))


def test_voided_lease_excluded_from_every_quota_projection_and_exports():
    baseline=repository();r,identity=saved();void(r,identity)
    for builder in (build_quota_summary,build_quota_summary_details):
        before,metrics=builder(baseline,user=user(),as_of_date=WHEN,quota_type='Egg Production')
        after,actual=builder(r,user=user(),as_of_date=WHEN,quota_type='Egg Production')
        pd.testing.assert_frame_equal(after,before);assert metrics==actual
        assert report_csv(user(),after)==report_csv(user(),before)
        pd.testing.assert_frame_equal(pd.read_excel(BytesIO(report_xlsx(user(),after))),pd.read_excel(BytesIO(report_xlsx(user(),before))))
    builders=[lambda tx:build_quota_history_report(r._accounts,r._quota_registrations,tx,set(),WHEN,rules=load_rules()),
        lambda tx:build_quota_leases_report(r._accounts,r._quota_registrations,tx,set(),WHEN),
        lambda tx:build_quota_leases_report(r._accounts,r._quota_registrations,tx,set(),WHEN,by_end_date=True),
        lambda tx:build_quota_transactions_report(r._accounts,r._quota_registrations,tx,set(),WHEN,WHEN)]
    for build in builders:
        before,metrics=build(baseline._quota_transactions);after,actual=build(r._quota_transactions)
        pd.testing.assert_frame_equal(after,before);assert metrics==actual
    # Flock reports receive precisely the same confirmed quotas after void.
    quotas,_,_=build_flock_age_quotas(r._quota_registrations,r._quota_transactions,r._accounts,WHEN,set(),load_rules())
    original,_,_=build_flock_age_quotas(baseline._quota_registrations,baseline._quota_transactions,baseline._accounts,WHEN,set(),load_rules())
    flocks=pd.DataFrame([dict(FLOCK_ID='f'+a,ACCOUNT_ID=a,FACILITY_ID='barn'+a,PERMIT_NUMBER='p'+a,FLOCK_NUMBER='p'+a,
        FLOCK_QUOTA_TYPE='Egg Production',STATUS='Active',HATCH_DATE='2026-01-01',PLACEMENT_DATE='2026-05-01',
        EST_DISPOSAL='2028-01-01',DISPOSAL_DATE=None,BIRD_COUNT=40) for a in ('a','b')])
    activity=pd.DataFrame([dict(FLOCK_ID='f'+a,FLOCK_TRANSACTION_ID='count'+a,TRANSACTION_TYPE='Count',QUANTITY=40,
        TRANSACTION_DATE=WHEN) for a in ('a','b')])
    facilities=pd.DataFrame([dict(FACILITY_ID='barn'+a,FACILITY_NAME='Synthetic barn '+a) for a in ('a','b')])
    for build in (build_flock_age_report,build_flock_status_report,build_producers_over_quota_report):
        before,metrics=build(flocks,activity,r._accounts,facilities,original,WHEN)
        after,actual=build(flocks,activity,r._accounts,facilities,quotas,WHEN)
        pd.testing.assert_frame_equal(after,before);assert metrics==actual


@pytest.mark.parametrize('kind',['onward-lease','sale','historical-lease-out'])
def test_rejects_void_when_another_record_consumed_the_quota(kind):
    r,identity=saved()
    if kind=='onward-lease':
        r._accounts=pd.concat([r._accounts,pd.DataFrame([dict(ACCOUNT_ID='c',REGISTRATION_NUMBER='003',ORGANIZATION_NAME='Synthetic c')])],ignore_index=True)
        r._quota_registrations=pd.concat([r._quota_registrations,pd.DataFrame([dict(QUOTA_ID='qc',ACCOUNT_ID='c',QUOTA_TYPE='Egg Production',STATUS='Active')])],ignore_index=True)
        record=lease(QUOTA_TRANSACTION_ID='onward',QUOTA_ID='qb',OWNER_ACCOUNT_ID='b',RELATED_ACCOUNT_ID='c',QUOTA_COUNT=60)
    else:
        record=dict(QUOTA_TRANSACTION_ID='consumed',QUOTA_ID='qb',OWNER_ACCOUNT_ID='b',RELATED_ACCOUNT_ID='a',
            TRANSACTION_TYPE='Sale' if kind=='sale' else 'Lease (Out)',QUOTA_COUNT=60,EFFECTIVE_DATE='2026-12-20',END_DATE='2027-01-10')
    r.upsert_quota_transaction(record)
    before=r._quota_transactions.copy(deep=True);history=len(r.get_record_revisions())
    with pytest.raises(RepositoryError,match='depends|onward'):void(r,identity)
    pd.testing.assert_frame_equal(r._quota_transactions,before)
    assert len(r.get_record_revisions())==history


@pytest.mark.parametrize('role',[Role.DATA_EDITOR,Role.REPORTING_VIEWER,Role.DEVELOPER])
def test_unauthorized_void_denied_at_proxy_and_data_boundary(tmp_path,role):
    r,identity=saved()
    proxy=AuthorizedRepository(r,SQLiteAuthStore(tmp_path/'synthetic.db',seeds=[]),user(role))
    with pytest.raises(RepositoryError,match='permission|Admin'):
        proxy.void_quota_lease(identity,'Reason','denied',r.get_quota_transaction(identity)['UPDATED_AT'])
    with pytest.raises(RepositoryError,match='Admin'):
        void(r,identity,actor=dict(ADMIN,role=role.value))
    assert not is_voided(r.get_quota_transaction(identity))


@pytest.mark.parametrize('method',[None,'Allocation'])
def test_allocation_and_legacy_lease_cannot_be_voided(method):
    r=repository()
    r._quota_transactions=pd.concat([r._quota_transactions,pd.DataFrame([dict(lease(),TRANSACTION_METHOD=method,UPDATED_AT='2026-01-01')])],ignore_index=True)
    with pytest.raises(RepositoryError,match='Only a saved new-method Lease'):void(r,'deal')
    assert r.get_quota_transaction('deal')['TRANSACTION_METHOD']==method


@pytest.mark.parametrize('failure',['missing-column','revision','audit'])
def test_missing_schema_and_history_failures_leave_lease_unchanged(monkeypatch,failure):
    r,identity=saved()
    if failure=='missing-column':r._quota_transactions=r._quota_transactions.drop(columns=['LEASE_STATUS'])
    else:
        def fail(*args):raise RepositoryError('Synthetic history failure')
        monkeypatch.setattr(r,'_append_history' if failure=='revision' else '_review_insert',fail)
    before=r._quota_transactions.copy(deep=True);count=len(r.get_record_revisions())
    with pytest.raises(RepositoryError,match='schema update|history failure'):void(r,identity)
    pd.testing.assert_frame_equal(r._quota_transactions,before)
    assert len(r.get_record_revisions())==count


def test_required_reason_version_and_no_void_status_on_creation():
    r,identity=saved()
    with pytest.raises(RepositoryError,match='reason'):void(r,identity,reason=' ')
    with pytest.raises(ConcurrencyError):
        r.void_quota_lease(identity,'Reason','stale','2000-01-01',actor=ADMIN)
    with pytest.raises(RepositoryError,match='New leases cannot set'):
        r.upsert_quota_transaction(lease(LEASE_STATUS='Voided'))
    assert not is_voided(r.get_quota_transaction(identity))


def test_snowflake_missing_status_column_rejects_without_any_write(monkeypatch):
    r=SnowflakeRepository();writes=[]
    class Tx:
        def query(self,sql,params):return pd.DataFrame([dict(lease(),UPDATED_AT='2026-01-01')])
        def execute(self,*args):writes.append(args);return 1
    @contextmanager
    def transaction():yield Tx()
    monkeypatch.setattr(r,'_continuity_transaction',transaction)
    with pytest.raises(RepositoryError,match='schema update'):
        r.void_quota_lease('deal','Reason','request','2026-01-01',actor=ADMIN)
    assert not writes


@pytest.mark.parametrize('role',[Role.ADMIN,Role.DATA_EDITOR])
def test_saved_lease_page_admin_action_and_voided_label(tmp_path,monkeypatch,role):
    from tests.auth_support import authenticated_app
    r,identity=saved();root=Path(__file__).resolve().parents[1]
    app=authenticated_app(root/'streamlit_app.py',tmp_path,monkeypatch,role)
    app.session_state['_base_repo']=r
    app.session_state['_efns_record_8_Quota_Transactions_view']='detail'
    app.session_state['_efns_record_8_Quota_Transactions_id']=identity
    app.switch_page('app/pages/8_Quota_Transactions.py').run()
    assert not app.exception
    if role!=Role.ADMIN:
        assert not any(button.label=='Void lease' for button in app.button)
        return
    app.text_input(key='lease_void_'+identity+'_reason').input('Synthetic correction')
    app.button(key='lease_void_'+identity+'_submit').click().run()
    assert not app.exception and not app.error
    assert is_voided(r.get_quota_transaction(identity))
    assert any('Voided' in message.value for message in app.info)


def test_concurrent_void_and_onward_save_cannot_both_succeed():
    from concurrent.futures import ThreadPoolExecutor
    r,identity=saved()
    def act(which):
        try:
            if which=='void':void(r,identity)
            else:r.upsert_quota_transaction(lease(QUOTA_TRANSACTION_ID='onward',QUOTA_ID='qb',
                OWNER_ACCOUNT_ID='b',RELATED_ACCOUNT_ID='a',QUOTA_COUNT=60))
            return True
        except RepositoryError:return False
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(act,('void','save')))
    assert sum(results)==1
    assert pos(r._quota_registrations,r._quota_transactions,'b',WHEN)['net_position']>=0


def test_snowflake_void_reads_updates_and_audit_use_one_executor(monkeypatch):
    r=SnowflakeRepository();accounts,regs,activity=ledger()
    target=dict(lease(),LEASE_STATUS=None,UPDATED_AT='2026-01-01',CREATED_AT='2026-01-01')
    activity=pd.concat([activity,pd.DataFrame([target])],ignore_index=True)
    calls=[];histories=[];boundaries=[]
    class Tx:
        def query(self,sql,params=None):
            calls.append((sql,params))
            if 'RECORD_REVISION' in sql:return pd.DataFrame()
            if 'MIGRATION_RAW_ROW' in sql:return pd.DataFrame(columns=['TRANSACTION_ID','TRANSACTION_STATE'])
            if sql.startswith('SELECT qt.*'):return activity
            if 'QUOTA_REGISTRATION' in sql:return regs.iloc[:1] if 'QUOTA_ID=%s' in sql else regs
            return pd.DataFrame([target])
        def execute(self,sql,params):
            assert 'APP.AUDIT_EVENT' in sql
            calls.append((sql,params));return 1
    executor=Tx()
    @contextmanager
    def transaction():
        boundaries.append('begin')
        try:yield executor
        except Exception:boundaries.append('rollback');raise
        else:boundaries.append('commit')
    def update(active,table,row):
        assert active is executor and table=='QUOTA_TRANSACTION'
        assert set(row)=={'QUOTA_TRANSACTION_ID','LEASE_STATUS','EXPECTED_UPDATED_AT'}
        target['LEASE_STATUS']='Voided';target['UPDATED_AT']='2026-01-02'
        return 'deal'
    monkeypatch.setattr(r,'_continuity_transaction',transaction)
    monkeypatch.setattr(r,'_upsert_with_executor',update)
    monkeypatch.setattr(r,'_append_history',lambda active,table,row:histories.append((active,table,row)))
    monkeypatch.setattr(r,'_query',lambda *args:pytest.fail('Read outside owning transaction'))
    assert r.void_quota_lease('deal','Synthetic reason','request','2026-01-01',actor=ADMIN)=='deal'
    assert boundaries==['begin','commit'] and histories[0][0] is executor
    assert histories[0][2]['CHANGE_KIND']=='Voided'
    assert any('APP.AUDIT_EVENT' in sql for sql,_ in calls)

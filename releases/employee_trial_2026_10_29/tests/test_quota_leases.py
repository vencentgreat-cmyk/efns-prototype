"""Synthetic leases only; no Snowflake connection or production fixture values."""
import datetime as dt
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from io import BytesIO

import pandas as pd
import pytest
from pypdf import PdfReader

from data.quota_leases import (LEASE_END_DATE_INCLUSIVE, lease_input_errors,
    validate_lease_period, projected_lease_rows)
from data.confirmed_quota_position import confirmed_quota_position
from data.quota_position import load_rules, quota_position
from data.repositories.mock import MockRepository
from data.repositories.snowflake import SnowflakeRepository
from data.repositories.base import RepositoryError
from app.services.flock_age_report import build_flock_age_quotas, utilization
from app.services.quota_reports import build_quota_history_report, build_quota_transactions_report
from app.services.report_center import build_quota_summary, report_csv, report_xlsx
from tests.test_report_center import user


def ledger():
    accounts = pd.DataFrame([dict(ACCOUNT_ID=a, REGISTRATION_NUMBER='00'+str(i),
        ORGANIZATION_NAME='Synthetic '+a, PRODUCER_ROLE=True) for i,a in enumerate(('a','b'),1)])
    regs = pd.DataFrame([dict(QUOTA_ID='q'+a, ACCOUNT_ID=a, QUOTA_TYPE='Egg Production',
        STATUS='Active') for a in ('a','b')])
    transactions = pd.DataFrame([dict(QUOTA_TRANSACTION_ID='base'+a, QUOTA_ID='q'+a,
        OWNER_ACCOUNT_ID=a, RELATED_ACCOUNT_ID=None, TRANSACTION_TYPE='Base',
        QUOTA_COUNT=n, EFFECTIVE_DATE='2025-01-01', END_DATE=None, CREATED_AT='2025-01-01')
        for a,n in [('a',100),('b',50)]])
    return accounts, regs, transactions


def lease(**changes):
    return dict(dict(QUOTA_TRANSACTION_ID='deal', TRANSACTION_METHOD='Lease',
        TRANSACTION_TYPE='Lease (Out)', QUOTA_ID='qa', OWNER_ACCOUNT_ID='a',
        RELATED_ACCOUNT_ID='b', QUOTA_COUNT=20, EFFECTIVE_DATE='2026-12-20',
        END_DATE='2027-01-10'), **changes)


def pos(regs, tx, owner, when, inactive=set()):
    return confirmed_quota_position(regs,tx,owner,'Egg Production',when,inactive,load_rules())


def repository():
    repo=MockRepository()
    accounts,regs,tx=ledger()
    repo._accounts=accounts.reindex(columns=repo._accounts.columns.union(accounts.columns))
    repo._quota_registrations=regs.reindex(columns=repo._quota_registrations.columns.union(regs.columns))
    repo._quota_registrations['QUOTA_NAME']=['Synthetic registration a','Synthetic registration b']
    repo._quota_registrations['REGISTRATION_NUMBER']=['001','002']
    repo._quota_transactions=tx.reindex(columns=repo._quota_transactions.columns.union(tx.columns))
    return repo


def test_conserved_effective_dates_inclusive_boundary_and_utilization():
    accounts,regs,tx=ledger()
    with_lease=pd.concat([tx,pd.DataFrame([lease()])],ignore_index=True)
    assert LEASE_END_DATE_INCLUSIVE is True
    for day in ('2026-12-19','2027-01-11'):
        for owner in ('a','b'):
            assert pos(regs,tx,owner,day)==pos(regs,with_lease,owner,day)
        before=build_flock_age_quotas(regs,tx,accounts,day,set(),load_rules())
        assert before==build_flock_age_quotas(regs,with_lease,accounts,day,set(),load_rules())
    for day in ('2026-12-20','2026-12-31','2027-01-10'):
        quotas,count,reasons=build_flock_age_quotas(regs,with_lease,accounts,day,set(),load_rules())
        assert quotas=={'a':80,'b':70} and sum(quotas.values())==150 and count==2
        assert utilization(40,quotas['a'])=='50.00%'
        assert not any(reasons.values())
    assert pos(regs,with_lease,'a','2026-12-21',{'deal'})==pos(regs,tx,'a','2026-12-21')
    assert pos(regs,with_lease,'a','2026-12-21',None)['net_position'] is None


def test_several_leases_overlay_later_base_and_whole_period_capacity():
    _,regs,tx=ledger()
    first=lease(QUOTA_COUNT=60)
    rows=pd.concat([tx,pd.DataFrame([first])],ignore_index=True)
    assert not validate_lease_period(lease(QUOTA_TRANSACTION_ID='two',QUOTA_COUNT=40),regs,rows,set(),load_rules())
    assert validate_lease_period(lease(QUOTA_TRANSACTION_ID='two',QUOTA_COUNT=41),regs,rows,set(),load_rules())
    future=dict(tx.iloc[0],QUOTA_TRANSACTION_ID='reset',QUOTA_COUNT=30,EFFECTIVE_DATE='2027-01-02')
    rows=pd.concat([tx,pd.DataFrame([future])],ignore_index=True)
    assert validate_lease_period(lease(QUOTA_COUNT=31),regs,rows,set(),load_rules())
    assert not validate_lease_period(lease(QUOTA_COUNT=30),regs,rows,set(),load_rules())
    assert pos(regs,pd.concat([rows,pd.DataFrame([lease()])]),'a','2027-01-03')['net_position']==10
    incoming=lease(QUOTA_TRANSACTION_ID='incoming',QUOTA_ID='qb',OWNER_ACCOUNT_ID='b',RELATED_ACCOUNT_ID='a',END_DATE='2026-12-25')
    rows=pd.concat([tx,pd.DataFrame([incoming])],ignore_index=True)
    assert validate_lease_period(lease(QUOTA_COUNT=110),regs,rows,set(),load_rules())


@pytest.mark.parametrize('changes',[
    {'RELATED_ACCOUNT_ID':'a'},{'RELATED_ACCOUNT_ID':None},{'QUOTA_COUNT':0},
    {'QUOTA_COUNT':-1},{'QUOTA_COUNT':'NaN'},{'QUOTA_COUNT':'1.5'},
    {'END_DATE':None},{'END_DATE':'2026-01-01'},{'EFFECTIVE_DATE':None},
    {'QUOTA_ID':'missing'},{'OWNER_ACCOUNT_ID':'b'},
])
def test_invalid_inputs(changes):
    _,regs,_=ledger()
    assert lease_input_errors(lease(**changes),regs)


def test_no_lease_legacy_method_null_and_allocation_are_identical():
    _,regs,tx=ledger()
    expected=pos(regs,tx,'a','2026-12-21')
    for value in (None,'Allocation'):
        copy=tx.assign(TRANSACTION_METHOD=value)
        assert pos(regs,copy,'a','2026-12-21')==expected


def test_reports_plain_directions_exports_and_outside_period_unchanged():
    repo=repository(); accounts,regs,tx=ledger()
    repo._quota_transactions=pd.concat([tx,pd.DataFrame([lease()])],ignore_index=True)
    when=dt.date(2026,12,21)
    result,meta=build_quota_summary(repo,user=user(),as_of_date=when,quota_type='Egg Production')
    assert list(result.Issuance)==[150,80,70]
    frame,_=build_quota_history_report(accounts,regs,repo._quota_transactions,set(),when,rules=load_rules())
    assert {'Leased out','Leased in'}<=set(frame['Quota Transaction Type'])
    assert frame[frame['Account Name']=='Synthetic b']['Current Quota'].eq(70).all()
    from app.services.report_pdf import render_report_pdf
    pdf=render_report_pdf('Synthetic lease history',['Synthetic period'],frame,report_id='quota-history')
    pdf_text=' '.join(page.extract_text() for page in PdfReader(BytesIO(pdf)).pages)
    assert 'Leased in' in pdf_text and 'Leased out' in pdf_text
    assert b'Leased in' in report_csv(user(),frame)
    assert 'Leased out' in pd.read_excel(BytesIO(report_xlsx(user(),frame))).to_string()
    for day in (dt.date(2026,12,19),dt.date(2027,1,11)):
        expected,_=build_quota_history_report(accounts,regs,tx,set(),day,rules=load_rules())
        actual,_=build_quota_history_report(accounts,regs,repo._quota_transactions,set(),day,rules=load_rules())
        pd.testing.assert_frame_equal(actual,expected)
    frame,_=build_quota_transactions_report(accounts,regs,repo._quota_transactions,set(),when,when)
    assert set(frame['Quota Transaction Type'])=={'Leased in','Leased out'}
    frame,_=build_quota_transactions_report(accounts,regs,repo._quota_transactions,set(),
        dt.date(2026,12,1),dt.date(2027,2,1))
    assert len(frame)==2  # Range reports retain leases that overlap any requested day.


def test_memory_history_idempotency_immutability_and_concurrent_capacity():
    repo=repository();record=lease();record.pop('QUOTA_TRANSACTION_ID')
    identity=repo.create_record_once('QUOTA_TRANSACTION',record,'request',actor='synthetic-staff')
    assert repo.create_record_once('QUOTA_TRANSACTION',record,'request',actor='synthetic-staff')==identity
    history=repo.get_record_revisions_for('QUOTA_TRANSACTION',identity)
    assert len(history)==1 and history.iloc[0].AFTER_DATA['TRANSACTION_METHOD']=='Lease'
    assert history.iloc[0].RECORDED_BY=='synthetic-staff'
    events=repo._migration_review_audit
    assert len(events)==1 and events[0]['ACTION']=='CREATE'
    assert events[0]['ACTOR_USER_ID']=='synthetic-staff'
    with pytest.raises(RepositoryError,match='cannot be edited or deleted'):
        repo.upsert_quota_transaction(dict(repo.get_quota_transaction(identity),COMMENTS='change'))
    with pytest.raises(RepositoryError,match='cannot be edited or deleted'):
        repo.delete_quota_transaction(identity)
    repo=repository()
    def save(i):
        record=lease(QUOTA_COUNT=60);record.pop('QUOTA_TRANSACTION_ID')
        try:return repo.create_record_once('QUOTA_TRANSACTION',record,'request'+str(i),actor='synthetic-staff')
        except RepositoryError:return None
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(save,(1,2)))
    assert sum(v is not None for v in results)==1
    assert len(repo._quota_transactions)==3
    assert len(repo.get_record_revisions())==1


def test_draft_usage_keeps_evidence_gate_and_lease_overlay():
    _,regs,tx=ledger();rows=pd.concat([tx,pd.DataFrame([lease()])],ignore_index=True)
    result=quota_position(regs,rows,'b','Egg Production','2026-12-21',load_rules(),
        source_verified=True,missing_source_rows=0,inactive_source_rows=0)
    assert result['net_position']==70 and result['components']['Leased in']==20
    assert len(result['active_leases'])==1
    other_regs=pd.concat([regs,regs.assign(QUOTA_ID=['pa','pb'],QUOTA_TYPE='Commercial Pullet Grower')])
    other=quota_position(other_regs,rows,'b','Commercial Pullet Grower','2026-12-21',load_rules(),
        source_verified=True,missing_source_rows=0,inactive_source_rows=0)
    assert other['components']=={} and other['active_leases']==[]
    assert quota_position(regs,rows,'b','Egg Production','2026-12-21',load_rules())['net_position'] is None


def test_snowflake_validation_and_write_use_same_existing_transaction(monkeypatch):
    accounts,regs,txs=ledger();queries=[];writes=[];boundaries=[]
    class Tx:
        def query(self,sql,params):
            queries.append((sql,params))
            if 'RECORD_REVISION' in sql:return pd.DataFrame()
            if 'MIGRATION_RAW_ROW' in sql:return pd.DataFrame(columns=['TRANSACTION_ID','TRANSACTION_STATE'])
            if 'FROM EFNS_DEV.CORE.ACCOUNT' in sql:return accounts[['ACCOUNT_ID']]
            if 'QUOTA_REGISTRATION' in sql:return regs.iloc[:1] if 'QUOTA_ID=%s' in sql else regs
            if 'WHERE QUOTA_TRANSACTION_ID=%s' in sql:return txs.iloc[:0]
            return txs.assign(TRANSACTION_METHOD=None)
    executor=Tx();repo=SnowflakeRepository()
    @contextmanager
    def transaction():
        boundaries.append('begin')
        try:yield executor
        except Exception:boundaries.append('rollback');raise
        else:boundaries.append('commit')
    monkeypatch.setattr(repo,'_continuity_transaction',transaction)
    monkeypatch.setattr(repo,'_query',lambda *a:pytest.fail('Independent executor read'))
    monkeypatch.setattr(repo,'_upsert_with_executor',lambda active,table,row:writes.append((active,table,row)) or 'saved')
    assert repo.upsert_quota_transaction(lease())=='saved'
    assert boundaries==['begin','commit'] and writes[0][0] is executor
    assert any('PARSE_JSON(%s)' in sql for sql,_ in queries)
    with pytest.raises(RepositoryError,match='exceeds'):
        repo.upsert_quota_transaction(lease(QUOTA_COUNT=101))
    assert boundaries[-1]=='rollback' and len(writes)==1


def test_lease_form_create_and_allocation_default(tmp_path,monkeypatch):
    from tests.test_daily_quota_entry import quota_app
    repo=repository();app=quota_app(repo,tmp_path,monkeypatch)
    assert not app.exception
    assert app.selectbox(key='quota_tx_form_method').value=='Allocation'
    app.selectbox(key='quota_tx_form_method').select('Lease').run()
    assert not app.exception
    app.text_input(key='quota_lease_form_amount').input('20')
    app.date_input(key='quota_lease_form_start').set_value(dt.date(2026,12,20))
    app.date_input(key='quota_lease_form_end').set_value(dt.date(2027,1,10))
    app.button(key='quota_tx_record_save').click().run()
    assert not app.exception and not app.error
    assert len(repo._quota_transactions)==3
    assert repo._quota_transactions.iloc[-1].TRANSACTION_METHOD=='Lease'


def test_two_snowflake_sessions_reuse_existing_global_lock(monkeypatch):
    """A fake database row lock, never a live connection or new lock implementation."""
    from threading import RLock
    accounts,regs,activity=ledger()
    activity=activity.assign(TRANSACTION_METHOD=None)
    database_lock=RLock();lock_statements=[]
    class Executor:
        @contextmanager
        def transaction(self):
            with database_lock:
                yield self
        intake_transaction=transaction
        def execute(self,sql,params):
            assert 'RAW.INTAKE_LOCK' in sql and "LOCK_ID='continuity'" in sql
            lock_statements.append(sql)
            return 1
        def query(self,sql,params):
            if 'RECORD_REVISION' in sql:return pd.DataFrame()
            if 'MIGRATION_RAW_ROW' in sql:return pd.DataFrame(columns=['TRANSACTION_ID','TRANSACTION_STATE'])
            if 'FROM EFNS_DEV.CORE.ACCOUNT' in sql:return accounts[['ACCOUNT_ID']]
            if 'QUOTA_REGISTRATION' in sql:return regs.iloc[:1] if 'QUOTA_ID=%s' in sql else regs
            if 'WHERE QUOTA_TRANSACTION_ID=%s' in sql:
                return activity.loc[activity.QUOTA_TRANSACTION_ID==params[0]]
            return activity
    executor=Executor()
    def writer(active,table,row):
        nonlocal activity
        assert active is executor
        activity=pd.concat([activity,pd.DataFrame([row])],ignore_index=True)
        return row['QUOTA_TRANSACTION_ID']
    repositories=[SnowflakeRepository(),SnowflakeRepository()]
    for repo in repositories:
        monkeypatch.setattr(repo,'_executor',lambda:executor)
        monkeypatch.setattr(repo,'_upsert_with_executor',writer)
    def save(i):
        try:return repositories[i].upsert_quota_transaction(lease(QUOTA_TRANSACTION_ID='deal'+str(i),QUOTA_COUNT=60))
        except RepositoryError:return None
    with ThreadPoolExecutor(max_workers=2) as pool:result=list(pool.map(save,(0,1)))
    assert sum(value is not None for value in result)==1
    assert len(activity)==3 and len(lock_statements)==2


def test_audit_failure_rolls_back_lease_and_history(monkeypatch):
    repo=repository();before=repo._quota_transactions.copy(deep=True)
    def fail(*args):raise RepositoryError('Synthetic audit failure')
    monkeypatch.setattr(repo,'_review_insert',fail)
    record=lease();record.pop('QUOTA_TRANSACTION_ID')
    with pytest.raises(RepositoryError,match='audit failure'):
        repo.create_record_once('QUOTA_TRANSACTION',record,'audit-fail',actor='synthetic-staff')
    pd.testing.assert_frame_equal(repo._quota_transactions,before)
    assert repo.get_record_revisions().empty


def test_permission_denied_lease_keeps_existing_authorization(tmp_path):
    from app.security import SQLiteAuthStore
    from app.services.authorized_repository import AuthorizedRepository
    repo=repository()
    authorized=AuthorizedRepository(repo,SQLiteAuthStore(tmp_path/'synthetic-auth.db'),user())
    record=lease();record.pop('QUOTA_TRANSACTION_ID')
    with pytest.raises(RepositoryError,match="permission"):
        authorized.create_record_once('QUOTA_TRANSACTION',record,'denied')
    assert len(repo._quota_transactions)==2 and repo.get_record_revisions().empty


def test_virtual_rows_do_not_leak_to_another_quota_type():
    accounts,regs,tx=ledger()
    regs=pd.concat([regs,regs.assign(QUOTA_ID=['other-a','other-b'],QUOTA_TYPE='Non Commercial Pullet Quota')])
    tx=pd.concat([tx,pd.DataFrame([lease()])],ignore_index=True)
    frame,_=build_quota_history_report(accounts,regs,tx,set(),dt.date(2026,12,21),
        quota_type='Non Commercial Pullet Quota',rules=load_rules())
    assert frame.empty


def test_projection_keeps_legacy_inactive_exclusion_with_new_leases():
    accounts,regs,tx=ledger()
    sale=dict(tx.iloc[0],QUOTA_TRANSACTION_ID='inactive-sale',TRANSACTION_TYPE='Sale',RELATED_ACCOUNT_ID='b',EFFECTIVE_DATE='2026-12-21')
    tx=pd.concat([tx,pd.DataFrame([sale,lease()])],ignore_index=True)
    result,_=build_quota_transactions_report(accounts,regs,tx,{'inactive-sale'},dt.date(2026,12,21),dt.date(2026,12,21))
    assert list(result['Quota Transaction Type'])==['Leased out','Leased in']

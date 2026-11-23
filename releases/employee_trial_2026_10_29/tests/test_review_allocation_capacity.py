"""Synthetic manual allocations protected by the existing lease lock/resolver."""
import datetime as dt
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from copy import deepcopy
from threading import RLock
import pandas as pd
import pytest
from app.security import Role,SQLiteAuthStore
from app.services.authorized_repository import AuthorizedRepository
from data.quota_allocation_capacity import allocation_capacity_error,guard_allocation_change
from data.quota_leases import own_quota_capacity_rows,is_lease
from data.record_safety import delete_with_history
from data.repositories.base import RepositoryError
from data.repositories.snowflake import SnowflakeRepository
from tests.test_quota_leases import repository,lease,ledger,pos
from tests.test_quota_lease_void import ADMIN,void
from tests.test_quota_lease_adjustments import adjust
from tests.test_report_center import user


def allocation(kind='Sale',quantity=50,when='2026-12-22',**extra):
    return dict(dict(QUOTA_ID='qa',OWNER_ACCOUNT_ID='a',RELATED_ACCOUNT_ID='b',
        TRANSACTION_TYPE=kind,QUOTA_COUNT=quantity,EFFECTIVE_DATE=when,END_DATE=None),**extra)


def committed_lease(amount=90):
    repo=repository();record=lease(QUOTA_COUNT=amount);record.pop('QUOTA_TRANSACTION_ID')
    identity=repo.create_record_once('QUOTA_TRANSACTION',record,'lease',actor='synthetic-user')
    return repo,identity


def create(repo,record,request='allocation'):
    return repo.create_record_once('QUOTA_TRANSACTION',record,request,actor='synthetic-user')


@pytest.mark.parametrize('kind,quantity',[('Sale',50),('Adjustment',-50),('Base',50)])
def test_decrease_rejected_with_date_shortfall_lease_and_full_rollback(kind,quantity):
    repo,identity=committed_lease();before=deepcopy(repo._continuity_rows);rows=repo._quota_transactions.copy(deep=True)
    with pytest.raises(RepositoryError,match='2026-12-22.*shortfall of 40') as error:
        create(repo,allocation(kind,quantity))
    assert identity in str(error.value) and 'End, reduce or void' in str(error.value)
    assert repo._continuity_rows==before
    pd.testing.assert_frame_equal(rows,repo._quota_transactions)


@pytest.mark.parametrize('record',[allocation(quantity=5),allocation(when='2027-01-11'),
    allocation('Adjustment',-5)])
def test_safe_decrease_or_after_lease_end_is_accepted(record):
    repo,_=committed_lease()
    assert create(repo,record)


def test_no_new_terminate_formula_and_different_account_or_type_unaffected():
    repo,_=committed_lease()
    regs,rows=repo.get_quota_registrations(),repo.get_quota_transactions()
    assert allocation_capacity_error(regs,rows,set(),'a','Egg Production',None,
        allocation('Terminate Quota',500,QUOTA_TRANSACTION_ID='synthetic-terminate')) is None
    # Terminate remains an unsupported new manual choice, not a balancing rule.
    with pytest.raises((ValueError,RepositoryError),match='Transaction Type'):
        create(repo,allocation('Terminate Quota',500),'unsupported')
    assert create(repo,allocation(QUOTA_ID='qb',OWNER_ACCOUNT_ID='b',RELATED_ACCOUNT_ID='a'),'other-account')
    new=dict(repo.get_quota_registration('qa'),QUOTA_ID='pullet',QUOTA_TYPE='Commercial Pullet Grower')
    repo._quota_registrations=pd.concat([repo._quota_registrations,pd.DataFrame([new])],ignore_index=True)
    assert create(repo,allocation(QUOTA_ID='pullet'),'other-type')


def test_edit_and_delete_of_earlier_increase_are_guarded_but_notes_remain_editable():
    repo=repository();increase=create(repo,allocation('Adjustment',20,'2026-12-19'),'increase')
    record=lease(QUOTA_COUNT=110);record.pop('QUOTA_TRANSACTION_ID')
    repo.create_record_once('QUOTA_TRANSACTION',record,'lease',actor='synthetic-user')
    for changes in ({'QUOTA_COUNT':5},{'EFFECTIVE_DATE':'2027-01-11'},{'TRANSACTION_TYPE':'Sale'}):
        with pytest.raises(RepositoryError,match='shortfall'):
            repo.revise_record('QUOTA_TRANSACTION',increase,changes,'Synthetic correction','edit-'+next(iter(changes)),
                actor='synthetic-user',expected_updated_at=repo.get_quota_transaction(increase)['UPDATED_AT'])
    with pytest.raises(RepositoryError,match='shortfall'):
        delete_with_history(repo,'QUOTA_TRANSACTION',increase,repo.delete_quota_transaction,
            ADMIN,'delete','Synthetic deletion')
    assert repo.revise_record('QUOTA_TRANSACTION',increase,{'COMMENTS':'Synthetic note'},'Note only','note',
        actor='synthetic-user',expected_updated_at=repo.get_quota_transaction(increase)['UPDATED_AT'])==increase
    assert repo.get_quota_transaction(increase)['QUOTA_COUNT']==20


def test_partial_return_early_end_and_void_increase_capacity_without_new_block(monkeypatch):
    # All dates are synthetic; freeze before the period so confirmation is irrelevant here.
    monkeypatch.setattr('data.business_time.halifax_today',lambda:dt.date(2026,12,1))
    repo,identity=committed_lease();adjust(repo,identity,amount=40)
    assert create(repo,allocation(quantity=40,when='2026-12-23'))
    repo,identity=committed_lease();adjust(repo,identity,'Ended early','2026-12-22',None)
    assert create(repo,allocation(quantity=50,when='2026-12-23'))
    repo,identity=committed_lease();adjust(repo,identity,amount=90)
    assert create(repo,allocation(quantity=50,when='2026-12-23'))
    repo,identity=committed_lease();void(repo,identity)
    assert create(repo,allocation())


def test_incoming_new_and_legacy_quota_cannot_cover_outgoing_commitment():
    repo,identity=committed_lease()
    incoming=dict(lease(),QUOTA_TRANSACTION_ID='synthetic-incoming',QUOTA_ID='qb',
        OWNER_ACCOUNT_ID='b',RELATED_ACCOUNT_ID='a',QUOTA_COUNT=100)
    legacy=dict(incoming,TRANSACTION_METHOD=None,TRANSACTION_TYPE='Lease (In)',QUOTA_ID='qa',OWNER_ACCOUNT_ID='a')
    repo._quota_transactions=pd.concat([repo._quota_transactions,pd.DataFrame([incoming,legacy])],ignore_index=True)
    with pytest.raises(RepositoryError,match='shortfall of 40'):create(repo,allocation())
    rows=repo.get_quota_transactions()
    old=[row for row in rows.to_dict('records') if ((is_lease(row) and row['OWNER_ACCOUNT_ID']=='a')
        or (not is_lease(row) and row['TRANSACTION_TYPE'] not in {'Lease (In)','Lease In'}))]
    pd.testing.assert_frame_equal(pd.DataFrame(own_quota_capacity_rows(rows,'a')),pd.DataFrame(old))


def test_authorized_direct_manual_upsert_and_delete_are_guarded_bulk_is_exempt(tmp_path):
    repo,_=committed_lease();proxy=AuthorizedRepository(repo,SQLiteAuthStore(tmp_path/'auth.db'),user(Role.ADMIN))
    with pytest.raises(RepositoryError,match='shortfall'):proxy.upsert_quota_transaction(allocation())
    # Explicit historical import remains an intentional gap, not a manual bypass.
    record=allocation(QUOTA_TRANSACTION_ID='synthetic-import',ACTION='CREATE')
    repo.import_operational_flock_quota_batch({}, {'QUOTA_TRANSACTION':[record]}, [])
    assert repo.get_quota_transaction('synthetic-import') is not None


@pytest.mark.parametrize('order',[('lease','sale'),('sale','lease')])
def test_concurrent_manual_sale_and_lease_cannot_both_commit(order):
    repo=repository();record=lease(QUOTA_COUNT=90);record.pop('QUOTA_TRANSACTION_ID')
    def save(which):
        try:return create(repo,record if which=='lease' else allocation(),which)
        except RepositoryError:return None
    with ThreadPoolExecutor(max_workers=2) as pool:result=list(pool.map(save,order))
    assert sum(value is not None for value in result)==1
    assert len(repo._quota_transactions)==3


@pytest.mark.parametrize('order',[('lease','sale'),('sale','lease')])
def test_two_snowflake_sessions_share_existing_lock_for_sale_vs_lease(monkeypatch,order):
    accounts,regs,activity=ledger();activity=activity.assign(TRANSACTION_METHOD=None)
    database_lock=RLock();locks=[]
    class Executor:
        @contextmanager
        def transaction(self):
            with database_lock:yield self
        intake_transaction=transaction
        def execute(self,sql,params):
            assert 'RAW.INTAKE_LOCK' in sql;locks.append(sql);return 1
        def query(self,sql,params):
            if 'RECORD_REVISION' in sql:return pd.DataFrame()
            if 'MIGRATION_RAW_ROW' in sql:return pd.DataFrame(columns=['TRANSACTION_ID','TRANSACTION_STATE'])
            if 'FROM EFNS_DEV.CORE.ACCOUNT' in sql:return accounts[['ACCOUNT_ID']]
            if 'FROM EFNS_DEV.CORE.QUOTA_REGISTRATION' in sql:return regs.loc[regs.QUOTA_ID.eq(params[0])] if 'QUOTA_ID=%s' in sql else regs
            if 'WHERE QUOTA_TRANSACTION_ID=%s' in sql:return activity.loc[activity.QUOTA_TRANSACTION_ID.eq(params[0])]
            return activity
    executor=Executor();repos=[SnowflakeRepository(),SnowflakeRepository()]
    def writer(tx,record):
        nonlocal activity
        assert tx is executor
        activity=pd.concat([activity,pd.DataFrame([record])],ignore_index=True)
        return record['QUOTA_TRANSACTION_ID']
    for repo in repos:
        monkeypatch.setattr(repo,'_executor',lambda:executor)
        monkeypatch.setattr(repo,'_query',lambda *a:pytest.fail('Capacity read escaped its transaction'))
    monkeypatch.setattr(repos[0],'_upsert_with_executor',lambda tx,table,row:writer(tx,row))
    sale=allocation(QUOTA_TRANSACTION_ID='synthetic-sale')
    def save(which):
        try:
            if which=='lease':return repos[0].upsert_quota_transaction(lease(QUOTA_COUNT=90))
            with repos[1]._continuity_transaction() as tx:
                guard_allocation_change(repos[1],tx,None,sale)
                return writer(tx,sale)
        except RepositoryError:return None
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(save,order))
    assert sum(value is not None for value in results)==1 and len(activity)==3 and len(locks)==2

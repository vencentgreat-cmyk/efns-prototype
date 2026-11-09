"""Daily preview and both commit controllers reuse manual rules; synthetic only."""
from contextlib import contextmanager
from copy import deepcopy
from decimal import Decimal

import pandas as pd
import pytest

from data.operational_flock_quota_import import analyze_operational_files
from data.repositories.base import RepositoryError
from data.repositories.snowflake import SnowflakeRepository
from tests.test_operational_flock_quota_import import csv_upload
from tests.test_round2 import _commit_daily
from tests.test_staff_workflows import chain


BAD=[({'TRANSACTION_TYPE':'Global Adjustment'},'Transaction Type'),
     ({'TRANSACTION_TYPE':'Adjustment','QUOTA_COUNT':0},'non-zero'),
     ({'QUOTA_COUNT':-1},'greater than zero'),
     ({'RELATED_ACCOUNT_ID':None},'Related Account'),
     ({'PRICE':-1},'Price'),({'PRICE':'NaN'},'Price'),
     ({'END_DATE':'2019-01-01'},'End Date')]


def valid(quota,other,**extra):
    row=dict(ACTION='CREATE',QUOTA_TRANSACTION_ID='DEV_TEST daily quota transaction',
             QUOTA_ID=quota,TRANSACTION_TYPE='Purchase',QUOTA_COUNT=2,
             RELATED_ACCOUNT_ID=other,PRICE=None,EFFECTIVE_DATE='2020-01-01',END_DATE=None)
    row.update(extra);return row


@pytest.mark.parametrize('changes,message',[
    ({'PRICE':'Infinity'},message) if changes.get('PRICE')=='NaN' else (changes,message)
    for changes,message in BAD])
def test_preview_rejects_bad_new_quota_activity(chain,changes,message):
    repo,account,other,facility,quota,*_=chain
    row=valid(quota,other,**changes)
    before=repo._quota_transactions.copy(deep=True)
    report=analyze_operational_files([csv_upload('DEV_TEST.csv',[row])],'Quota Transactions',repo)
    assert not report.ready_rows and len(report.rejected_rows)==1
    assert any(message.lower() in str(e).lower() for e in report.rejected_rows[0].messages)
    pd.testing.assert_frame_equal(repo._quota_transactions,before)


@pytest.mark.parametrize('changes,message',BAD)
def test_mock_commit_refuses_bad_new_rows_and_rolls_back_tracking(chain,changes,message):
    repo,account,other,facility,quota,*_=chain
    before=repo._quota_transactions.copy(deep=True)
    batches=deepcopy(repo._import_batches);raw=deepcopy(repo._raw_rows)
    with pytest.raises((RepositoryError,ValueError)):
        repo.import_operational_flock_quota_batch({'FILE_HASH':'DEV_TEST bad'},
            {'QUOTA_TRANSACTION':[valid(quota,other,**changes)]},[])
    pd.testing.assert_frame_equal(repo._quota_transactions,before)
    assert repo._import_batches==batches and repo._raw_rows==raw


@pytest.mark.parametrize('changes,message',BAD)
def test_native_commit_controller_refuses_invalid_rows_before_business_writer(chain,changes,message):
    _,account,other,facility,quota,*_=chain
    class Tx:
        rolled_back=False
        def query(self,sql,params=None):
            if 'SELECT *' in sql and 'CORE.QUOTA_TRANSACTION' in sql:return pd.DataFrame()
            if 'CORE.QUOTA_REGISTRATION' in sql:return pd.DataFrame([{'ACCOUNT_ID':account}])
            if 'CORE.ACCOUNT' in sql:return pd.DataFrame([{'ACCOUNT_ID':other}])
            return pd.DataFrame()
    tx=Tx();repo=SnowflakeRepository();writes=[]
    @contextmanager
    def transaction():
        try:yield tx
        except Exception:tx.rolled_back=True;raise
    repo._continuity_transaction=transaction
    repo._upsert_with_executor=lambda *args:writes.append(args)
    with pytest.raises(RepositoryError):
        repo.import_operational_flock_quota_batch({}, {'QUOTA_TRANSACTION':[valid(quota,other,**changes)]},[])
    assert not writes and tx.rolled_back


def test_signed_adjustment_and_null_price_preview_and_staged_commit(chain):
    repo,account,other,facility,quota,*_=chain
    row=valid(quota,other,TRANSACTION_TYPE='Adjustment',QUOTA_COUNT='-5.1250',RELATED_ACCOUNT_ID=None)
    report=analyze_operational_files([csv_upload('DEV_TEST.csv',[row])],'Quota Transactions',repo)
    assert len(report.ready_rows)==1 and not report.rejected_rows
    result=_commit_daily(repo,report,'DEV_TEST.csv')
    assert result['total_count']==1
    stored=repo.get_quota_transactions().iloc[0]
    assert stored.QUOTA_COUNT==Decimal('-5.1250') and pd.isna(stored.PRICE)


def test_historical_type_notes_only_update_stays_unchanged_through_commit(chain):
    repo,account,other,facility,quota,*_=chain
    old=valid(quota,other,TRANSACTION_TYPE='Terminate Quota',QUOTA_COUNT=0,
              QUOTA_LEASE_TYPE='Non One Time Credit',UPDATED_AT='2020-01-01T00:00:00.123456789')
    old.pop('ACTION');repo._quota_transactions=pd.concat([repo._quota_transactions,pd.DataFrame([old])],ignore_index=True)
    row={'ACTION':'UPDATE','QUOTA_TRANSACTION_ID':old['QUOTA_TRANSACTION_ID'],
         'COMMENTS':'DEV_TEST notes only'}
    report=analyze_operational_files([csv_upload('DEV_TEST_update.csv',[row])],'Quota Transactions',repo)
    assert len(report.ready_rows)==1 and not report.rejected_rows
    _commit_daily(repo,report,'DEV_TEST_update.csv')
    actual=repo.get_quota_transaction(old['QUOTA_TRANSACTION_ID'])
    assert actual['TRANSACTION_TYPE']==old['TRANSACTION_TYPE'] and actual['QUOTA_COUNT']==0
    assert actual['QUOTA_LEASE_TYPE']==old['QUOTA_LEASE_TYPE'] and pd.isna(actual['PRICE'])


@pytest.mark.parametrize('change',[{'QUOTA_COUNT':-2},{'RELATED_ACCOUNT_ID':None},{'TRANSACTION_TYPE':'Global Adjustment'}])
def test_update_changed_fields_are_revalidated_at_preview_and_commit(chain,change):
    repo,account,other,facility,quota,*_=chain
    old=valid(quota,other)
    if change.get('RELATED_ACCOUNT_ID','not provided') is None:
        # Blank UPDATE means keep under the unchanged file contract. Exercise
        # a real counterparty-required change: unlinked Adjustment -> Purchase.
        old.update(TRANSACTION_TYPE='Adjustment',RELATED_ACCOUNT_ID=None)
        change=dict(change,TRANSACTION_TYPE='Purchase')
    old.pop('ACTION');target=repo.upsert_quota_transaction(old)
    before=repo._quota_transactions.copy(deep=True)
    row=dict(ACTION='UPDATE',QUOTA_TRANSACTION_ID=target,**change)
    report=analyze_operational_files([csv_upload('DEV_TEST_update.csv',[row])],'Quota Transactions',repo)
    assert not report.ready_rows and report.rejected_rows
    full=dict(repo.get_quota_transaction(target),ACTION='UPDATE',**change)
    with pytest.raises(RepositoryError):
        repo.import_operational_flock_quota_batch({}, {'QUOTA_TRANSACTION':[full]},[])
    pd.testing.assert_frame_equal(repo._quota_transactions,before)


def test_existing_csv_nan_and_blank_update_contracts_preserve_unknown_and_existing_link(chain):
    repo,account,other,facility,quota,*_=chain
    row=valid(quota,other,PRICE='NaN')
    report=analyze_operational_files([csv_upload('DEV_TEST_nan.csv',[row])],'Quota Transactions',repo)
    assert len(report.ready_rows)==1 and pd.isna(report.ready_rows[0].write_record['PRICE'])
    assert repo.get_quota_transactions().empty  # Preview still never writes.
    old=valid(quota,other);old.pop('ACTION');target=repo.upsert_quota_transaction(old)
    update={'ACTION':'UPDATE','QUOTA_TRANSACTION_ID':target,'RELATED_ACCOUNT_ID':None,'COMMENTS':'DEV_TEST keep link'}
    report=analyze_operational_files([csv_upload('DEV_TEST_blank.csv',[update])],'Quota Transactions',repo)
    assert len(report.ready_rows)==1 and report.ready_rows[0].write_record['RELATED_ACCOUNT_ID']==other

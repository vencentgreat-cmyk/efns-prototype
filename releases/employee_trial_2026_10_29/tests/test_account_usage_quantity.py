"""Provisional account arithmetic and explicit current quantity transactions."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from decimal import Decimal
import datetime as dt
import json
import pandas as pd
import pytest
from app.services.quota_usage import account_usage_context,usage_numbers
from app.services.authorized_repository import AuthorizedRepository
from app.security import Role
from data.repositories.base import RepositoryError,ConcurrencyError
from data.repositories.snowflake import SnowflakeRepository
from tests.test_staff_workflows import chain
from tests.test_report_center import user

ACTOR={'user_id':'synthetic-staff','email':'synthetic.staff@nsegg.ca'}


def current(r,fid,kind,quantity,request='request',**kwargs):
    return r.record_current_flock_quantity(dict(FLOCK_ID=fid,TRANSACTION_TYPE=kind,QUANTITY=quantity,TRANSACTION_DATE=dt.date.today()),request,r.get_flock(fid)['UPDATED_AT'],'Synthetic current observation/removal',confirmed=True,actor=ACTOR,**kwargs, expected_bird_count=(r.get_flock((dict(FLOCK_ID=fid,TRANSACTION_TYPE=kind,QUANTITY=quantity,TRANSACTION_DATE=dt.date.today())).get('FLOCK_ID')) or {}).get('BIRD_COUNT'))


@pytest.mark.parametrize('baseline,total,missing,compatible,percent,remaining',[
    (20,10,0,True,50,10),(10,12,0,True,120,-2),(0,10,0,True,None,-10),
    (None,10,0,True,None,None),(20,10,1,True,None,None),(20,None,2,True,None,None),
    (20,0,0,True,0,20),(20,10,0,False,None,None)])
def test_synthetic_baseline_arithmetic_not_a_company_baseline(baseline,total,missing,compatible,percent,remaining):
    actual=usage_numbers(total,missing,baseline,compatible_units=compatible)
    assert actual['usage_percent']==percent and actual['remaining_capacity']==remaining


def test_account_facility_type_grain_unknowns_and_no_facility(chain):
    r,a,o,f,q,fid,record=chain
    other_facility=r.upsert_facility(dict(ACCOUNT_ID=a,FACILITY_NAME='DEV_TEST second barn',STATUS='Active'))
    r.upsert_flock(dict(record,FLOCK_NUMBER='DEV_TEST 2',PERMIT_NUMBER='DEV_TEST 2',FACILITY_ID=other_facility,BIRD_COUNT=5))
    unlocated=dict(record,FLOCK_ID='DEV_TEST historical no facility',FLOCK_NUMBER='DEV_TEST no facility',FACILITY_ID=None,BIRD_COUNT=None)
    # Existing historical state, not a bypass of daily requiredness.
    r._flocks=pd.concat([r._flocks,pd.DataFrame([unlocated])],ignore_index=True)
    r._flocks=pd.concat([r._flocks,r._flocks.iloc[:1]],ignore_index=True)
    r.upsert_flock(dict(record,FLOCK_NUMBER='DEV_TEST other type',PERMIT_NUMBER='DEV_TEST other type',FLOCK_QUOTA_TYPE='Commercial Pullet',QUOTA_ID=None,BIRD_COUNT=100))
    actual=account_usage_context(r,a)
    egg=next(v for v in actual['summaries'] if v['quota_type']=='Egg Production')
    assert egg['flock_count']==3 and egg['known_bird_count']==15 and egg['missing_count']==1
    assert egg['current_occupancy'] is None and egg['usage_percent'] is None
    assert 'No Facility' in actual['facility_details']['Facility ID'].tolist()
    assert next(v for v in actual['summaries'] if v['quota_type']=='Commercial Pullet')['known_bird_count']==100


def test_count_partial_and_complete_removal_refresh_without_replay(chain):
    r,a,o,f,q,fid,record=chain
    before=r.get_flock(fid)
    current(r,fid,'Count',12,'count')
    version=r.get_flock(fid)['UPDATED_AT']
    request=dict(FLOCK_ID=fid,TRANSACTION_TYPE='Removal',QUANTITY=5,TRANSACTION_DATE=dt.date.today())
    first=r.record_current_flock_quantity(request,'partial',version,'Synthetic partial disposal',confirmed=True,actor=ACTOR, expected_bird_count=(r.get_flock((request).get('FLOCK_ID')) or {}).get('BIRD_COUNT'))
    assert r.get_flock(fid)['BIRD_COUNT']==7
    assert r.record_current_flock_quantity(request,'partial',version,'Synthetic partial disposal',confirmed=True,actor=ACTOR, expected_bird_count=(r.get_flock((request).get('FLOCK_ID')) or {}).get('BIRD_COUNT'))==first
    assert r.get_flock(fid)['BIRD_COUNT']==7
    current(r,fid,'Removal',7,'complete')
    after=r.get_flock(fid)
    assert after['BIRD_COUNT']==0 and after['STATUS']==before['STATUS']
    for key in ('BIRDS_DISPOSED','PLACEMENT_DATE','DISPOSAL_DATE','FACILITY_ID'):
        assert pd.isna(after.get(key)) and pd.isna(before.get(key)) or after.get(key)==before.get(key)
    assert len(r.get_record_revisions())==3 and len(r._migration_review_audit)==3
    assert r.get_flock_events(fid).empty
    assert account_usage_context(r,a)['summaries'][0]['known_bird_count']==0
    from app.services.report_center import build_custom_report,report_csv,report_xlsx
    from io import BytesIO
    report=build_custom_report(r,user=user(),dataset='Flocks',selected_fields=['FLOCK_ID','BIRD_COUNT'])
    assert report.iloc[0]['Bird Count']==0
    assert pd.read_csv(BytesIO(report_csv(user(),report)))['Bird Count'].tolist()==[0]
    assert pd.read_excel(BytesIO(report_xlsx(user(),report)))['Bird Count'].tolist()==[0]


def test_stale_invalid_and_audit_failure_leave_no_partial_writes(chain,monkeypatch):
    r,a,o,f,q,fid,record=chain
    # A stale-version test must establish a distinct earlier version instead
    # of depending on whether the Windows wall clock advances between calls.
    r._flocks.loc[r._flocks.FLOCK_ID==fid,'UPDATED_AT']=pd.Timestamp('2020-01-01T00:00:00Z')
    old=r.get_flock(fid)['UPDATED_AT']; current(r,fid,'Count',15,'initial')
    request=dict(FLOCK_ID=fid,TRANSACTION_TYPE='Removal',QUANTITY=3,TRANSACTION_DATE=dt.date.today())
    with pytest.raises(ConcurrencyError): r.record_current_flock_quantity(request,'stale',old,'Synthetic',confirmed=True,actor=ACTOR, expected_bird_count=(r.get_flock((request).get('FLOCK_ID')) or {}).get('BIRD_COUNT'))
    before=r._flocks.copy(deep=True); transactions=r._flock_transactions.copy(deep=True); audits=deepcopy(r._migration_review_audit)
    def fail(*args): raise RuntimeError('Synthetic audit failure')
    monkeypatch.setattr(r,'_review_insert',fail)
    with pytest.raises(RuntimeError): current(r,fid,'Removal',3,'failed')
    pd.testing.assert_frame_equal(before,r._flocks);pd.testing.assert_frame_equal(transactions,r._flock_transactions)
    assert r._migration_review_audit==audits and len(r.get_record_revisions())==1


def test_concurrent_same_request_once_and_changed_payload_rejected(chain):
    r,a,o,f,q,fid,record=chain
    version=r.get_flock(fid)['UPDATED_AT']
    payload=dict(FLOCK_ID=fid,TRANSACTION_TYPE='Removal',QUANTITY=2,TRANSACTION_DATE=dt.date.today())
    def submit(_):return r.record_current_flock_quantity(payload,'same',version,'Synthetic',confirmed=True,actor=ACTOR, expected_bird_count=(r.get_flock((payload).get('FLOCK_ID')) or {}).get('BIRD_COUNT'))
    with ThreadPoolExecutor(max_workers=2) as pool: ids=list(pool.map(submit,range(2)))
    assert ids[0]==ids[1] and r.get_flock(fid)['BIRD_COUNT']==8
    with pytest.raises(RepositoryError): r.record_current_flock_quantity(dict(payload,QUANTITY=3),'same',version,'Synthetic',confirmed=True,actor=ACTOR, expected_bird_count=(r.get_flock((dict(payload,QUANTITY=3)).get('FLOCK_ID')) or {}).get('BIRD_COUNT'))


def test_permission_and_operator_are_authenticated(chain):
    r,a,o,f,q,fid,record=chain
    class Audit:
        def record_action(self,*args,**kwargs):pass
    args=(dict(FLOCK_ID=fid,TRANSACTION_TYPE='Count',QUANTITY=8,TRANSACTION_DATE=dt.date.today()),'auth',r.get_flock(fid)['UPDATED_AT'],'Synthetic')
    with pytest.raises(RepositoryError): AuthorizedRepository(r,Audit(),user(Role.REPORTING_VIEWER)).record_current_flock_quantity(*args,confirmed=True, expected_bird_count=(AuthorizedRepository(r,Audit(),user(Role.REPORTING_VIEWER)).get_flock((args[0]).get('FLOCK_ID')) or {}).get('BIRD_COUNT'))
    editor=user(Role.DATA_EDITOR)
    AuthorizedRepository(r,Audit(),editor).record_current_flock_quantity(*args,confirmed=True,actor={'user_id':'spoof','email':'spoof@nsegg.ca'}, expected_bird_count=(AuthorizedRepository(r,Audit(),editor).get_flock((args[0]).get('FLOCK_ID')) or {}).get('BIRD_COUNT'))
    assert r._migration_review_audit[0]['ACTOR_EMAIL']==editor.email


@pytest.mark.parametrize('kind,quantity,expected',[('Removal',2,8),('Count',0,0)])
def test_snowflake_quantity_cas_and_actual_rollback_contract(chain,kind,quantity,expected):
    r,a,o,f,q,fid,record=chain
    r._flocks['UPDATED_AT']=pd.Timestamp('2026-10-28 10:00:00.123456789')
    class Executor:
        fail=False
        calls=[]
        @contextmanager
        def transaction(self):
            before=deepcopy((r._flocks,r._flock_transactions,r._continuity_rows,r._migration_review_audit))
            try:yield self
            except Exception:
                r._flocks,r._flock_transactions,r._continuity_rows,r._migration_review_audit=before
                raise
        def query(self,sql,params=None):
            self.calls.append(sql)
            if 'SELECT CONVERT_TIMEZONE' in sql:return pd.DataFrame([{'RECORDED_AT':dt.datetime.now()}])
            if '.FLOCK_TRANSACTION ' in sql:return r._flock_transactions[r._flock_transactions.FLOCK_TRANSACTION_ID==params[0]].copy()
            if '.RECORD_REVISION ' in sql:return pd.DataFrame([v for v in r._continuity_rows['RECORD_REVISION'] if v['REVISION_ID']==params[0]])
            if '.FLOCK ' in sql:
                result=r._flocks[r._flocks.FLOCK_ID==params[0]].copy()
                result['UPDATED_AT']=result.UPDATED_AT.map(lambda v:pd.Timestamp(v).isoformat() if 'FF9' in sql else pd.Timestamp(v).to_pydatetime(warn=False))
                return result
            raise AssertionError(sql)
        def execute(self,sql,params=None):
            self.calls.append(sql)
            if '.INTAKE_LOCK ' in sql:return 1
            if sql.startswith('UPDATE '):
                assert 'BIRD_COUNT IS NOT DISTINCT FROM' in sql and 'UPDATED_AT=TO_TIMESTAMP_NTZ(%s)' in sql
                assert params[2].endswith('123456789')
                assert params[0]==expected
                r._upsert_frame('_flocks','FLOCK_ID',dict(FLOCK_ID=params[1],BIRD_COUNT=params[0],EXPECTED_UPDATED_AT=params[2]));return 1
            if '.AUDIT_EVENT ' in sql:
                if self.fail:raise RuntimeError('Synthetic SQL audit failure')
                r._migration_review_audit.append(dict(AUDIT_ID=params[0]));return 1
            raise AssertionError(sql)
    ex=Executor(); target=SnowflakeRepository(ex)
    target.get_flock=r.get_flock
    target._upsert_with_executor=lambda tx,table,payload:r._upsert_frame('_flock_transactions','FLOCK_TRANSACTION_ID',payload)
    target._append_history=lambda tx,table,payload:r._append_history(None,table,payload)
    with pytest.raises(ConcurrencyError,match='changed after review'):
        target.record_current_flock_quantity(dict(FLOCK_ID=fid,TRANSACTION_TYPE=kind,QUANTITY=quantity,TRANSACTION_DATE=dt.date.today()),'same-microsecond-stale','2026-10-28T10:00:00.123456788','Synthetic',confirmed=True,actor=ACTOR,expected_bird_count=10)
    assert r.get_flock(fid)['BIRD_COUNT']==10 and r._flock_transactions.empty
    before=r._flocks.copy(deep=True);ex.fail=True
    with pytest.raises(RuntimeError): current(target,fid,kind,quantity,'sql-failure')
    pd.testing.assert_frame_equal(before,r._flocks)
    assert r._flock_transactions.empty and not r._continuity_rows['RECORD_REVISION']
    ex.fail=False;current(target,fid,kind,quantity,'sql-success')
    assert r.get_flock(fid)['BIRD_COUNT']==expected and len(r._flock_transactions)==1


def test_unknown_count_overdraw_and_historical_activity(chain):
    r,a,o,f,q,fid,record=chain
    r._flocks.loc[r._flocks.FLOCK_ID==fid,'BIRD_COUNT']=None
    with pytest.raises(RepositoryError):current(r,fid,'Removal',1,'unknown')
    current(r,fid,'Count',4,'known')
    with pytest.raises(RepositoryError):current(r,fid,'Removal',5,'overdraw')
    assert r.get_flock(fid)['BIRD_COUNT']==4
    historical=dict(FLOCK_ID=fid,TRANSACTION_TYPE='Count',QUANTITY=999,TRANSACTION_DATE=dt.date.today()-dt.timedelta(days=1))
    r.upsert_flock_transaction(historical)
    assert r.get_flock(fid)['BIRD_COUNT']==4
    with pytest.raises(RepositoryError): r.record_current_flock_quantity(historical,'old',r.get_flock(fid)['UPDATED_AT'],'Historical observation',confirmed=True,actor=ACTOR, expected_bird_count=(r.get_flock((historical).get('FLOCK_ID')) or {}).get('BIRD_COUNT'))


def test_current_count_not_deducted_again_by_disposed_attribute(chain):
    r,a,o,f,q,fid,record=chain
    current(r,fid,'Count',5,'known-count')
    current_record=r.get_flock(fid)
    r.upsert_flock(dict(current_record,BIRDS_DISPOSED=10,EXPECTED_UPDATED_AT=current_record['UPDATED_AT']))
    assert r.get_flock(fid)['BIRD_COUNT']==5
    assert r.get_flock(fid)['BIRDS_DISPOSED']==10


def test_conflicting_duplicates_and_missing_account_fail_closed(chain):
    r,a,o,f,q,fid,record=chain
    r._flocks=pd.concat([r._flocks,pd.DataFrame([dict(r.get_flock(fid),BIRD_COUNT=999)])],ignore_index=True)
    context=account_usage_context(r,a)
    assert context['reasons']
    unknown=next(v for v in context['summaries'] if v['quota_type']=='Ambiguous type')
    assert unknown['missing_count']==1 and unknown['known_bird_count'] is None
    assert not account_usage_context(r,None)['summaries']


def test_applied_activity_cannot_be_edited_or_deleted_without_quantity_reconciliation(chain):
    r,a,o,f,q,fid,record=chain
    txid=current(r,fid,'Removal',2,'protected')
    saved=r.get_flock_transactions(flock_id=fid).iloc[0].to_dict()
    with pytest.raises(RepositoryError,match='protected'):r.upsert_flock_transaction(dict(saved,QUANTITY=9))
    with pytest.raises(RepositoryError,match='protected'):r.delete_flock_transaction(txid)
    assert r.get_flock(fid)['BIRD_COUNT']==8 and len(r.get_flock_transactions(flock_id=fid))==1

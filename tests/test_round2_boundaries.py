"""Correct-behavior edges; fake drivers are not Snowflake engine evidence."""
from contextlib import contextmanager
from copy import deepcopy
import threading
import pandas as pd
import pytest
from data.business_time import precise_version_sql,version_bind
from data.connection import SnowparkExecutor,ConnectorExecutor
from data.repositories.snowflake import SnowflakeRepository
from data.repositories.base import RepositoryError,ConcurrencyError
from tests.test_round2 import chain,_app,_open,_commit_daily,csv_upload,analyze_operational_files
from tests.test_connection import FakeRow,FakeStatement,FakeSession

@pytest.mark.parametrize('alias,table',[('ft','FLOCK_TRANSACTION'),('st','SALMONELLA_TEST'),('qt','QUOTA_TRANSACTION'),('fl','FARM_LOCATION'),('fd','FACILITY_DETAIL')])
def test_all_alias_versions_are_lossless(alias,table):
    version='2026-10-28T10:00:00.123456789'
    seen=[]
    class Ex:
        def query(self,sql,params=None):
            seen.append(sql)
            return pd.DataFrame([{'UPDATED_AT':version if 'FF9' in sql else pd.Timestamp(version).to_pydatetime(warn=False)}])
    repo=SnowflakeRepository(Ex())
    result=repo._query(f'SELECT DISTINCT {alias}.* FROM EFNS_DEV.CORE.{table} {alias} WHERE 1=1')
    assert result.iloc[0].UPDATED_AT==version
    assert f'TO_CHAR({alias}.UPDATED_AT' in seen[0]
    assert precise_version_sql(seen[0])==seen[0]
    assert version_bind(result.iloc[0].UPDATED_AT)!=version_bind('2026-10-28T10:00:00.123456788')

@pytest.mark.parametrize('null',[None,float('nan'),pd.NA,''])
def test_daily_optional_detail_nulls_commit(chain,null):
    r,a,o,f,q,fid,_=chain
    r._flocks['FACILITY_DETAIL_ID']=r._flocks.FACILITY_DETAIL_ID.astype(object)
    r._flocks.loc[r._flocks.FLOCK_ID==fid,'FACILITY_DETAIL_ID']=null
    report=analyze_operational_files([csv_upload('update.csv',[{'Flock Number':r.get_flock(fid)['FLOCK_NUMBER'],'Account':a,'Comments':'changed'}])],'Flocks',r)
    _commit_daily(r,report)
    assert r.get_flock(fid)['COMMENTS']=='changed'

class LockSession(FakeSession):
    def __init__(self,old='43200',level='ACCOUNT',fail=False,commit_fail=False):
        self.old=old;self.level=level;self.fail=fail;self.commit_fail=commit_fail
        super().__init__(self.respond)
    def respond(self,sql,params):
        if sql.startswith('SHOW PARAMETERS'):
            return FakeStatement([FakeRow(key='LOCK_TIMEOUT',value=self.old,level=self.level)],['key','value','level'])
        if sql=='COMMIT' and self.commit_fail:raise RuntimeError('synthetic connection lost')
        if 'INTAKE_LOCK' in sql and self.fail:raise RuntimeError('synthetic lock timeout')
        return FakeStatement([FakeRow(**{'number of rows updated':1})],['number of rows updated'])

@pytest.mark.parametrize('level,old,restore',[('ACCOUNT','43200','ALTER SESSION UNSET LOCK_TIMEOUT'),('SESSION','90','ALTER SESSION SET LOCK_TIMEOUT=90'),('SESSION','5',None),('ACCOUNT','0',None)])
def test_lock_timeout_restores_scope(level,old,restore):
    session=LockSession(old,level);ex=SnowparkExecutor(session)
    with ex.intake_transaction():ex.execute("UPDATE EFNS_DEV.RAW.INTAKE_LOCK SET VERSION=VERSION+1 WHERE LOCK_ID='continuity'")
    sql=[s for s,_ in session.calls]
    assert sql.count('BEGIN')==sql.count('COMMIT')==1
    if restore:
        assert sql.index('ALTER SESSION SET LOCK_TIMEOUT=30')<sql.index('BEGIN')
        assert sql.index(restore)>sql.index('COMMIT')
    else:assert not any(s.startswith('ALTER SESSION') for s in sql)

def test_lock_failure_rolls_back_and_restores():
    session=LockSession(fail=True);ex=SnowparkExecutor(session)
    with pytest.raises(RepositoryError):
        with ex.intake_transaction():ex.execute('UPDATE EFNS_DEV.RAW.INTAKE_LOCK SET VERSION=VERSION+1')
    sql=[s for s,_ in session.calls]
    assert 'ROLLBACK' in sql and 'COMMIT' not in sql
    assert sql[-1]=='ALTER SESSION UNSET LOCK_TIMEOUT'

def test_commit_unknown_never_suggests_duplicate_save():
    session=LockSession(commit_fail=True);ex=SnowparkExecutor(session)
    with pytest.raises(RepositoryError,match='COMMIT outcome is unknown.*Do not save again'):
        with ex.intake_transaction():ex.execute('UPDATE EFNS_DEV.RAW.INTAKE_LOCK SET VERSION=VERSION+1')
    assert [s for s,_ in session.calls].count('COMMIT')==1

def test_failed_metadata_does_not_start_transaction():
    ex=SnowparkExecutor(FakeSession())
    with pytest.raises(RepositoryError,match='Cannot verify'):
        with ex.intake_transaction():pytest.fail('body must not execute')
    assert not any(s=='BEGIN' for s,_ in ex.session.calls)

def test_restore_failure_blocks_all_wrappers_of_the_same_session():
    class Session(LockSession):
        def respond(self,sql,params):
            if sql.startswith('ALTER SESSION UNSET'):raise RuntimeError('synthetic restore failure')
            return super().respond(sql,params)
    session=Session();first=SnowparkExecutor(session);second=SnowparkExecutor(session)
    with pytest.raises(RepositoryError,match='committed.*Do not repeat'):
        with first.intake_transaction():pass
    before=len(session.calls)
    with pytest.raises(RepositoryError,match='Reconnect before saving'):
        with second.intake_transaction():pytest.fail('unreachable')
    assert len(session.calls)==before

def test_delete_has_one_business_audit_and_before_image(chain):
    from tests.test_round2 import EDITOR
    from app.security import Role,User
    from app.services.authorized_repository import AuthorizedRepository
    r,a,o,f,q,fid,_=chain
    tx=r.upsert_flock_transaction(dict(FLOCK_ID=fid,TRANSACTION_TYPE='Delivery',QUANTITY=2,TRANSACTION_DATE='2026-10-01'))
    class Store:
        def record_action(self,*args):pytest.fail('duplicate secondary audit')
    admin=User('admin','admin@nsegg.ca','Admin',Role.ADMIN,True,False,'now','now',None)
    repo=AuthorizedRepository(r,Store(),admin)
    repo.delete_flock_transaction(tx,reason='Wrong entry',request_id='delete-once')
    assert len(r._migration_review_audit)==1
    rev=r.get_record_revisions().iloc[0]
    assert rev.BEFORE_DATA['QUANTITY']==2 and rev.REASON=='Wrong entry'

@pytest.mark.parametrize('failure',[False,True])
def test_connector_scoped_wait_restores_and_rolls_back(failure):
    from tests.test_connection import FakeConnection,FakeCursor
    class Cursor(FakeCursor):
        def execute(self,sql,params=()):
            self.calls.append(('execute',sql,params))
            if sql.startswith('SHOW PARAMETERS'):
                self.rows=[('LOCK_TIMEOUT','45','SESSION')];self.description=[('key',),('value',),('level',)]
            else:self.rows=[];self.description=[]
            if failure and 'INTAKE_LOCK' in sql:raise RuntimeError('synthetic blocked lock')
            self.rowcount=1;return self
    cursor=Cursor();connection=FakeConnection(cursor);ex=ConnectorExecutor(lambda:connection)
    def run():
        with ex.intake_transaction():ex.execute('UPDATE EFNS_DEV.RAW.INTAKE_LOCK SET VERSION=VERSION+1')
    if failure:
        with pytest.raises(RepositoryError):run()
        assert connection.rollbacks==1 and connection.commits==0
    else:run();assert connection.commits==1
    assert cursor.calls[-1][1]=='ALTER SESSION SET LOCK_TIMEOUT=45'

def test_process_wait_has_finite_bound_without_starting_sql():
    class Denied:
        def acquire(self,*,timeout):assert timeout==30;return False
    ex=ConnectorExecutor(lambda:pytest.fail('no connection should be opened'))
    ex._operation_lock=Denied()
    with pytest.raises(RepositoryError,match='System busy.*30 seconds'):
        with ex.intake_transaction():pytest.fail('unreachable')

def test_production_exact_retry_has_explicit_message(chain,tmp_path,monkeypatch):
    r,a,*_=chain
    app=_app(r,tmp_path,monkeypatch).switch_page('app/pages/21_Record_History.py').run()
    app.selectbox(key='manual_producer').select(next(s for s in app.selectbox(key='manual_producer').options if a in s))
    next(b for b in app.button if b.label=='Save new production record').click().run()
    assert not app.error and len(r._production)==1
    next(b for b in app.button if b.label=='Save new production record').click().run()
    assert len(r._production)==1 and any('already saved' in s.value for s in app.success)
    next(b for b in app.button if b.label=='Start another new production record').click().run()
    next(b for b in app.button if b.label=='Save new production record').click().run()
    assert len(r._production)==2

def test_quantity_intent_is_cleared_only_by_explicit_new_scope(chain,tmp_path,monkeypatch):
    r,a,o,f,q,fid,_=chain
    app=_open(_app(r,tmp_path,monkeypatch),'app/pages/6_Flock_Transactions.py',None,view='new')
    app.checkbox(key='flock_tx_form_apply_'+fid).check().run()
    assert app.session_state['flock_tx_form_quantity_intent']
    app.button(key='flock_tx_record_cancel').click().run()
    app.button(key='flock_tx_list_new').click().run()
    assert not app.checkbox(key='flock_tx_form_apply_'+fid).value

    assert not app.session_state['flock_tx_form_quantity_intent']

def test_switching_flock_requires_fresh_confirmation(chain,tmp_path,monkeypatch):
    r,a,o,f,q,fid,_=chain
    second=dict(r.get_flock(fid),FLOCK_ID='second',FLOCK_NUMBER='SECOND')
    r._flocks=pd.concat([r._flocks,pd.DataFrame([second])],ignore_index=True)
    app=_open(_app(r,tmp_path,monkeypatch),'app/pages/6_Flock_Transactions.py',None,view='new')
    original=app.selectbox(key='flock_tx_form_flock').value
    app.checkbox(key='flock_tx_form_apply_'+fid).check().run()
    app.selectbox(key='flock_tx_form_flock').select(next(v for v in app.selectbox(key='flock_tx_form_flock').options if v.startswith('SECOND'))).run()
    assert not app.checkbox(key='flock_tx_form_apply_second').value
    app.selectbox(key='flock_tx_form_flock').select(original).run()
    assert not app.checkbox(key='flock_tx_form_apply_'+fid).value
    app.button(key='flock_tx_record_save').click().run()
    assert app.error and r._flock_transactions.empty

@pytest.mark.parametrize('null',[None,float('nan'),pd.NA,''])
def test_snowflake_daily_create_then_update_optional_detail_contract(null):
    # Exercise repository commit branches with a fake executor, not a live DB.
    class Ex:
        stored={}
        @contextmanager
        def transaction(self):
            before=deepcopy(self.stored)
            try:yield self
            except Exception:self.stored=before;raise
        def query(self,sql,params=None):
            if 'CORE.FACILITY_DETAIL' in sql:pytest.fail('null detail must not query a parent')
            if 'CORE.FLOCK' in sql:return pd.DataFrame(list(self.stored.values()))
            if 'CORE.ACCOUNT' in sql:return pd.DataFrame([{'ACCOUNT_ID':'a'}])
            if 'CORE.FACILITY' in sql:return pd.DataFrame([{'FACILITY_ID':'f','ACCOUNT_ID':'a'}])
            return pd.DataFrame()
        def execute(self,sql,params=None):return 1
    ex=Ex();repo=SnowflakeRepository(ex)
    def save(tx,entity,row):
        assert row.get('FACILITY_DETAIL_ID') is None
        ex.stored[row['FLOCK_ID']]=dict(row,UPDATED_AT='2026-10-28T12:00:00.123456789')
        return row['FLOCK_ID']
    repo._upsert_with_executor=save
    repo._insert_batch=lambda *args:None
    repo._insert_raw=lambda *args:None
    row=dict(FLOCK_ID='flock',ACCOUNT_ID='a',FACILITY_ID='f',FLOCK_NUMBER='SYNTHETIC',FACILITY_DETAIL_ID=null)
    result=repo.import_operational_flock_quota_batch({}, {'FLOCK':[dict(row,ACTION='CREATE')]},[])
    assert result['created_count']==1
    result=repo.import_operational_flock_quota_batch({'_REVISION_ACTOR':'synthetic-staff','IMPORT_ID':'synthetic-update'}, {'FLOCK':[dict(row,ACTION='UPDATE',COMMENTS='later')]},[])
    assert result['updated_count']==1 and ex.stored['flock']['COMMENTS']=='later'

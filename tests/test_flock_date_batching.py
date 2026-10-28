"""Synthetic batching, real executor request counts and commit-aware progress."""
from copy import deepcopy
from datetime import datetime
from types import SimpleNamespace
from uuid import UUID
import json
import threading

import pandas as pd
import pytest

import data.repositories.flock_date_repair as repair
from data.connection import SnowparkExecutor, ConnectorExecutor
from data.repositories.snowflake import SnowflakeRepository
from data.repositories.base import RepositoryError, ConcurrencyError
from tests.test_connection import FakeRow, FakeStatement, FakeSession
from tests.test_flock_date_repair import repo, BATCH, BASIS, ACTOR
from tests.test_flock_date_repair_sql import DateSql


def expand(state, count):
    source=deepcopy(state._migration_raw_rows[0])
    mapping=deepcopy(state._migration_id_map[0])
    flock=state._flocks.iloc[0].to_dict()
    raw=[];maps=[];flocks=[]
    for n in range(count):
        guid=str(UUID(int=10000+n)).upper();raw_id=f'synthetic-batch-{n}'
        r=deepcopy(source);r.update(MIGRATION_RAW_ROW_ID=raw_id,SOURCE_ID=guid,TARGET_ID=guid,SOURCE_ROW_NUMBER=n+2)
        r['RAW_DATA']['NEW_FLOCKSID']=guid;r['NORMALIZED_DATA']['FLOCK_ID']=guid
        m=deepcopy(mapping);m.update(MIGRATION_RAW_ROW_ID=raw_id,SOURCE_ID=guid,TARGET_ID=guid)
        f=deepcopy(flock);f.update(FLOCK_ID=guid,FLOCK_NUMBER=f'SYNTHETIC-{n}')
        raw.append(r);maps.append(m);flocks.append(f)
    state._migration_raw_rows=raw;state._migration_id_map=maps;state._flocks=pd.DataFrame(flocks)


def submit(r, callback=None, token=None):
    p=r.preview_flock_date_repair(BATCH,BASIS,{})
    return r.commit_flock_date_repair(BATCH,BASIS,{},token or p['review_token'],confirmed=True,actor=ACTOR,progress=callback)


def test_1803_rows_emit_31_sql_calls_not_5424(repo,monkeypatch):
    expand(repo,1803)
    engine=DateSql(repo);r=SnowflakeRepository(engine)
    p=r.preview_flock_date_repair(BATCH,BASIS,{})
    engine.calls.clear()
    original=repair.load_mapping;loads=[]
    def counted(*args,**kwargs):loads.append(1);return original(*args,**kwargs)
    monkeypatch.setattr(repair,'load_mapping',counted)
    events=[]
    def progress(event):
        if event['committed']:assert engine.calls[-1][0]=='COMMIT'
        events.append(event)
    result=r.commit_flock_date_repair(BATCH,BASIS,{},p['review_token'],confirmed=True,actor=ACTOR,progress=progress)
    assert result['changed']==1803 and len(engine.calls)==31
    assert len(loads)==1  # hash is reused from the fresh in-transaction preview
    updates=[c for c in engine.calls if c[0].startswith('UPDATE EFNS_DEV.CORE.FLOCK AS')]
    reads=[c for c in engine.calls if 'FROM EFNS_DEV.CORE.FLOCK WHERE FLOCK_ID IN' in c[0]]
    inserts=[c for c in engine.calls if c[0].startswith('INSERT INTO EFNS_DEV.APP.RECORD_REVISION ')]
    assert len(updates)==len(reads)==len(inserts)==4
    assert [len(json.loads(p[0])) for _,p in updates]==[500,500,500,303]
    assert [v['processed'] for v in events if v['stage']=='PROCESSING']==[0,500,1000,1500,1803]
    assert all(not v['committed'] for v in events[:-1]) and events[-1]['stage']=='COMMITTED'
    assert len(repo._continuity_rows['RECORD_REVISION'])==1803


@pytest.mark.parametrize('failure',['second_cas','history_count','history_failure','readback','audit','commit'])
def test_partial_processing_and_final_failures_leave_no_business_or_history(repo,monkeypatch,failure):
    monkeypatch.setattr(repair,'DATE_BATCH_SIZE',1)
    original=repo._flocks.copy(deep=True)
    class Failure(DateSql):
        updates=0
        def execute(self,sql,params=None):
            if sql.startswith('UPDATE EFNS_DEV.CORE.FLOCK AS'):
                self.updates+=1
                if failure=='second_cas' and self.updates==2:return 0
            if 'INSERT INTO EFNS_DEV.APP.RECORD_REVISION ' in sql and 'FLATTEN' in sql:
                if failure=='history_failure':raise RuntimeError('synthetic history failure')
                count=super().execute(sql,params)
                return count-1 if failure=='history_count' else count
            return super().execute(sql,params)
        def query(self,sql,params=None):
            frame=super().query(sql,params)
            if failure=='readback' and 'WHERE FLOCK_ID IN' in sql:return frame.iloc[:0]
            return frame
    ex=Failure(repo);ex.fail_audit=failure=='audit'
    if failure=='commit':
        # Inject failure at the transaction boundary after the body has completed.
        from contextlib import contextmanager
        base=ex.transaction
        @contextmanager
        def fail_commit():
            with base() as tx:
                yield tx
                raise RuntimeError('synthetic commit failure')
        ex.transaction=fail_commit
    events=[]
    with pytest.raises((RepositoryError,RuntimeError)):submit(SnowflakeRepository(ex),events.append)
    pd.testing.assert_frame_equal(repo._flocks,original)
    assert not repo._continuity_rows['RECORD_REVISION'] and not getattr(repo,'_migration_review_audit',[])
    assert events[-1]['stage']=='NOT_CONFIRMED' and not any(e['committed'] for e in events)


@pytest.mark.parametrize('error',[RuntimeError,BaseException])
def test_progress_failure_cannot_abort_or_misreport_committed_transaction(repo,error):
    def broken(event):raise error('synthetic disconnected browser/control flow')
    assert submit(SnowflakeRepository(DateSql(repo)),broken)['changed']==2
    assert len(repo._migration_review_audit)==1


def test_original_receipt_format_replay_and_protected_reverse_remain_valid(repo):
    # Legacy receipt is exactly the same shape; do not add a new required format.
    ex=DateSql(repo);r=SnowflakeRepository(ex)
    p=r.preview_flock_date_repair(BATCH,BASIS,{})
    operation=repair.stable_id('flock-date-repair',BATCH,p['review_token'])
    written=[]
    # Reproduce the pre-batch writer, not the new batch commit, to create evidence.
    with r._review_transaction() as tx:
        for row in p['rows']:
            if row['status']!='READY':continue
            after=r._date_update(tx,row['before'],row['proposed'])
            revision_id=repair.stable_id(operation,row['raw_id'])
            r._date_revision(tx,dict(REVISION_ID=revision_id,ENTITY_TYPE='FLOCK',ENTITY_ID=row['flock_id'],
                CHANGE_KIND=repair.KIND,BUSINESS_AT=None,RECORDED_AT=datetime(2026,1,1),RECORDED_BY=ACTOR['user_id'],
                REASON=BASIS,BEFORE_DATA=row['before'],AFTER_DATA=dict(after,_DATE_REPAIR=dict(operation_id=operation,
                batch_id=BATCH,raw_id=row['raw_id'],raw_hash=row['raw_hash'],mapping_revision=row['mapping_revision'],
                mapping_hash=repair.fingerprint(repair.load_mapping())))))
            written.append(dict(flock_id=row['flock_id'],revision_id=revision_id,before=row['before'],after=after))
        r._date_finish(tx,operation,dict(operation_id=operation,batch_id=BATCH,basis=BASIS,holds={},
            review_token=p['review_token'],kind=repair.KIND,written=written),ACTOR)
    receipt=repo._migration_review_audit[0]['DETAILS']
    assert set(receipt)=={'operation_id','batch_id','basis','holds','review_token','kind','written'}
    assert r.commit_flock_date_repair(BATCH,BASIS,{},p['review_token'],confirmed=True,actor=ACTOR)['already_committed']
    rev=r.preview_flock_date_reversal(operation,'Synthetic protected reversal')
    assert r.commit_flock_date_reversal(operation,rev['basis'],rev['review_token'],confirmed=True,actor=ACTOR)['changed']==2


def test_duplicate_submissions_across_repository_instances_serialize_and_write_once(repo):
    from concurrent.futures import ThreadPoolExecutor
    ex=DateSql(repo);left=SnowflakeRepository(ex);right=SnowflakeRepository(ex)
    p=left.preview_flock_date_repair(BATCH,BASIS,{})
    with ThreadPoolExecutor(2) as pool:
        results=list(pool.map(lambda r:r.commit_flock_date_repair(BATCH,BASIS,{},p['review_token'],confirmed=True,actor=ACTOR),(left,right)))
    assert sum(r['changed'] for r in results)==2
    assert len(repo._continuity_rows['RECORD_REVISION'])==2 and len(repo._migration_review_audit)==1


def test_large_history_payload_is_split_by_bytes_without_rowwise_fallback(repo,monkeypatch):
    ex=DateSql(repo);r=SnowflakeRepository(ex)
    records=[dict(REVISION_ID=f'synthetic-{n}',ENTITY_ID=str(UUID(int=n+1)),ENTITY_TYPE='FLOCK',
        CHANGE_KIND=repair.KIND,BUSINESS_AT=None,RECORDED_AT=datetime(2026,1,1),RECORDED_BY=ACTOR['user_id'],
        REASON=BASIS,BEFORE_DATA={'COMMENTS':'synthetic '*50},AFTER_DATA={'COMMENTS':'synthetic '*50}) for n in range(4)]
    two=len(repair.evidence_json(records[:2]).encode('utf-8'))
    monkeypatch.setattr(repair,'MAX_HISTORY_BIND_BYTES',two+1)
    r._date_revisions_many(ex,records)
    inserts=[c for c in ex.calls if c[0].startswith('INSERT INTO')]
    assert len(inserts)==2 and all(len(json.loads(params[0]))==2 for _,params in inserts)


@pytest.mark.parametrize('kind',['snowpark','connector'])
def test_actual_executors_issue_set_sql_not_hidden_row_loops(repo,kind):
    engine=DateSql(repo);wire=[]
    def respond(sql,params):
        canonical=sql.replace('?','%s')
        wire.append((sql,list(params or [])))
        if sql in {'BEGIN','COMMIT','ROLLBACK'}:return [],[]
        if sql.startswith('SELECT '):
            frame=engine.query(canonical,params)
            return frame.to_dict('records'),list(frame.columns)
        count=engine.execute(canonical,params)
        name='number of rows updated' if sql.startswith('UPDATE') else 'number of rows inserted'
        return [{name:count}],[name]
    if kind=='snowpark':
        def statement(sql,params):
            records,columns=respond(sql,params)
            return FakeStatement([FakeRow(**r) for r in records],columns)
        ex=SnowparkExecutor(FakeSession(statement))
    else:
        class Cursor:
            rowcount=0
            def execute(self,sql,params=()):
                records,columns=respond(sql,params)
                self.rows=[tuple(r[c] for c in columns) for r in records]
                self.description=[(c,) for c in columns]
                if records and columns and columns[0].startswith('number of rows'):self.rowcount=self.rows[0][0]
                return self
            def fetchall(self):return self.rows
            def close(self):pass
        class Connection:
            def cursor(self):return Cursor()
            def commit(self):wire.append(('COMMIT',[]))
            def rollback(self):wire.append(('ROLLBACK',[]))
        connection=Connection();ex=ConnectorExecutor(lambda:connection)
    assert submit(SnowflakeRepository(ex))['changed']==2
    assert len([sql for sql,_ in wire if sql.startswith('UPDATE EFNS_DEV.CORE.FLOCK AS')])==1
    assert len([sql for sql,_ in wire if 'INSERT INTO EFNS_DEV.APP.RECORD_REVISION ' in sql])==1
    assert not any('UNION ALL' in sql for sql,_ in wire)
    assert all(len(params)==1 for sql,params in wire if 'FLATTEN' in sql)
    assert wire[-1][0]=='COMMIT'


def test_nanosecond_version_not_truncated_and_full_readback_uses_ff9(repo):
    repo._flocks['CREATED_AT']=pd.Timestamp('2025-10-01T00:00:00.123456789')
    repo._flocks['UPDATED_AT']=pd.Timestamp('2025-10-01T00:00:00.123456789')
    engine=DateSql(repo)
    submit(SnowflakeRepository(engine))
    update=next(params for sql,params in engine.calls if sql.startswith('UPDATE EFNS_DEV.CORE.FLOCK AS'))
    assert all(row['VERSION'].endswith('123456789') for row in json.loads(update[0]))
    assert all('HH24:MI:SS.FF9' in sql for sql,_ in engine.calls if 'FROM EFNS_DEV.CORE.FLOCK WHERE' in sql)


def test_receipt_compact_history_full_and_reversal_compatible(repo):
    engine=DateSql(repo);r=SnowflakeRepository(engine)
    result=submit(r)
    receipt=repo._migration_review_audit[0]['DETAILS']
    assert receipt['receipt_version']==2
    assert all(set(row['before'])=={'FLOCK_ID','EST_DISPOSAL','DISPOSAL_DATE','UPDATED_AT'} for row in receipt['written'])
    assert all('PLACEMENT_DATE' in repair.obj(row['BEFORE_DATA']) for row in repo._continuity_rows['RECORD_REVISION'])
    reverse=r.preview_flock_date_reversal(result['operation_id'],'Synthetic reverse of compact receipt')
    assert r.commit_flock_date_reversal(result['operation_id'],reverse['basis'],reverse['review_token'],confirmed=True,actor=ACTOR)['changed']==2


def test_oversize_final_receipt_rejected_before_audit_sql(repo,monkeypatch):
    engine=DateSql(repo);r=SnowflakeRepository(engine)
    monkeypatch.setattr(repair,'MAX_HISTORY_BIND_BYTES',10)
    with pytest.raises(RepositoryError,match='receipt exceeds'):
        r._date_finish(engine,'synthetic',{'written':['synthetic '*20]},ACTOR)
    assert not engine.calls


def test_equal_total_with_duplicate_and_missing_guid_is_rejected(repo):
    class DuplicateReadback(DateSql):
        def query(self,sql,params=None):
            rows=super().query(sql,params)
            if 'WHERE FLOCK_ID IN' in sql and len(rows)==2:
                return pd.concat([rows.iloc[:1],rows.iloc[:1]],ignore_index=True)
            return rows
    before=repo._flocks.copy(deep=True);ex=DuplicateReadback(repo)
    with pytest.raises(RepositoryError,match='ambiguous targets'):submit(SnowflakeRepository(ex))
    pd.testing.assert_frame_equal(before,repo._flocks)
    assert ex.calls[-1][0]=='ROLLBACK'


def test_uncertain_commit_exposes_stable_operation_reference(repo,caplog):
    engine=DateSql(repo);engine.fail_audit=True;r=SnowflakeRepository(engine)
    p=r.preview_flock_date_repair(BATCH,BASIS,{})
    with pytest.raises(RuntimeError) as caught:
        r.commit_flock_date_repair(BATCH,BASIS,{},p['review_token'],confirmed=True,actor=ACTOR)
    assert caught.value.date_repair_operation_id==repair.stable_id('flock-date-repair',BATCH,p['review_token'])
    assert caught.value.date_repair_operation_id in caplog.text and BASIS not in caplog.text


def test_control_flow_interruption_during_write_enters_existing_rollback(repo,monkeypatch):
    engine=DateSql(repo);r=SnowflakeRepository(engine);before=repo._flocks.copy(deep=True)
    def interrupted(*args):raise BaseException('Synthetic stop/rerun outside progress')
    monkeypatch.setattr(r,'_date_revisions_many',interrupted)
    with pytest.raises(RepositoryError,match='interrupted') as caught:submit(r)
    assert isinstance(caught.value.__cause__,BaseException)
    pd.testing.assert_frame_equal(before,repo._flocks)
    assert engine.calls[-1][0]=='ROLLBACK' and not repo._continuity_rows['RECORD_REVISION']


def test_duplicate_receipt_guid_cannot_hide_missing_target(repo):
    r=SnowflakeRepository(DateSql(repo));submit(r)
    receipt=deepcopy(repo._migration_review_audit[0]['DETAILS'])
    receipt['written'][1]=deepcopy(receipt['written'][0])
    with pytest.raises(RepositoryError,match='duplicated'):r._date_verify_receipt(receipt)

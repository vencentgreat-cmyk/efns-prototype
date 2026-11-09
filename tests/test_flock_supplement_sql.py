"""Offline SQL executor integration: exercise real SnowflakeRepository statements."""
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from io import BytesIO
import json
import re
import threading

import pandas as pd
import pytest

from data.repositories.snowflake import SnowflakeRepository
from tests.test_flock_transaction_supplement import repo, workbook, BINDING, ACTOR


class OfflineSql:
    """A local statement recorder/state machine, NOT a Snowflake server test."""
    def __init__(self,state):
        self.state=state; self.calls=[]; self.files={};self.lock=threading.RLock()
        self.fail_audit=False;self.missing_lock=False

    @contextmanager
    def transaction(self):
        with self.lock:
            names=('_flock_transactions','_import_batches','_raw_rows','_continuity_rows')
            before={key:deepcopy(getattr(self.state,key)) for key in names}
            self.calls.append(('BEGIN',None))
            try:
                yield self
                self.calls.append(('COMMIT',None))
            except Exception:
                for key,value in before.items(): setattr(self.state,key,value)
                self.calls.append(('ROLLBACK',None))
                raise

    def query(self,sql,params=None):
        self.calls.append((sql,params))
        if 'CURRENT_ORGANIZATION_NAME' in sql:
            return pd.DataFrame([dict(ORG='QDCTNKN',ACCOUNT_NAME='UW19058',LOCATOR='CB12755',DB='EFNS_DEV')])
        for table,attribute in (
            ('MIGRATION_ID_MAP','_migration_id_map'),('MIGRATION_RAW_ROW','_migration_raw_rows'),
            ('MIGRATION_BATCH','_migration_batches'),('IMPORT_BATCH','_import_batches')):
            if f'.{table} ' in sql:
                frame=pd.DataFrame(getattr(self.state,attribute))
                if table=='IMPORT_BATCH' and not frame.empty:
                    frame=frame[frame.IMPORT_ID==params[0]]
                return frame.copy()
        if '.SOURCE_FILE' in sql:
            rows=self.state._continuity_rows['SOURCE_FILE']
            return pd.DataFrame([row for row in rows if not params or row['SOURCE_FILE_ID']==params[0]])
        for table,attribute,key in (
            ('FLOCK_TRANSACTION','_flock_transactions','FLOCK_TRANSACTION_ID'),
            ('FLOCK','_flocks','FLOCK_ID'),('ACCOUNT','_accounts','ACCOUNT_ID'),
            ('FACILITY','_facilities','FACILITY_ID')):
            if f'.{table} ' in sql:
                frame=getattr(self.state,attribute)
                return frame[frame[key].astype(str).str.upper().isin(str(x).upper() for x in params)].copy()
        raise AssertionError(sql)

    def execute(self,sql,params=None):
        self.calls.append((sql,params))
        if '.INTAKE_LOCK ' in sql:
            return 0 if self.missing_lock else 1
        match=re.search(r'INSERT INTO EFNS_DEV\.(?:CORE|RAW|APP)\.(\w+) \(([^)]+)\)',sql)
        assert match,sql
        table,columns=match.groups()
        values=dict(zip(columns.replace(' ','').split(','),params))
        if table=='FLOCK_TRANSACTION':
            self.state._flock_transactions=pd.concat([self.state._flock_transactions,pd.DataFrame([values])],ignore_index=True)
        elif table=='SOURCE_FILE': self.state._continuity_rows['SOURCE_FILE'].append(values)
        elif table=='IMPORT_BATCH': self.state._import_batches.append(values)
        elif table=='IMPORT_RAW_ROW':
            values['RAW_DATA']=json.loads(values['RAW_DATA'])
            self.state._raw_rows.append(values)
        elif table=='AUDIT_EVENT':
            if self.fail_audit: raise RuntimeError('synthetic mandatory audit failure')
        else: raise AssertionError(table)
        return 1

    def executemany(self,sql,params):
        return sum(self.execute(sql,row) for row in params)

    def put_stream(self,stream,path): self.files[path]=stream.read()
    def get_stream(self,path): return BytesIO(self.files[path])


def test_sql_first_commit_retries_and_parameters(repo):
    ex=OfflineSql(repo);r=SnowflakeRepository(ex);content=workbook()
    report=r.preview_flock_transaction_supplement('synthetic.xlsx',content,BINDING)
    assert not any(sql=='BEGIN' for sql,_ in ex.calls)
    result=r.commit_flock_transaction_supplement('synthetic.xlsx',content,BINDING,
        report['review_token'],confirmed=True,actor=ACTOR)
    assert result['created_count']==12 and result['existing_count']==1
    assert len(repo._flock_transactions)==13 and len(repo._raw_rows)==13
    inserts=[(sql,params) for sql,params in ex.calls if sql.startswith('INSERT INTO EFNS_DEV.CORE.FLOCK_TRANSACTION')]
    assert len(inserts)==12 and all('COUNT_SOURCE_LABEL' in sql for sql,_ in inserts)
    assert not any(sql.startswith('UPDATE EFNS_DEV.CORE.') for sql,_ in ex.calls)
    audit_index=next(i for i,(sql,_) in enumerate(ex.calls) if 'INSERT INTO EFNS_DEV.APP.AUDIT_EVENT' in sql)
    assert ex.calls[audit_index+1][0]=='COMMIT'
    assert 'CONVERT_TIMEZONE' in ex.calls[audit_index][0]
    raw=repo._raw_rows[0]
    assert raw['RAW_DATA']['classification']=='EXISTING_MATCH'
    # Distinct repository instance: idempotency is database state, not a local cache.
    again=SnowflakeRepository(ex)
    after=again.preview_flock_transaction_supplement('synthetic.xlsx',content,BINDING)
    replay=again.commit_flock_transaction_supplement('synthetic.xlsx',content,BINDING,
        after['review_token'],confirmed=True,actor=ACTOR)
    assert replay['created_count']==0 and replay['existing_count']==13
    assert len(repo._raw_rows)==13


def test_sql_audit_failure_rolls_back_all_database_writes_leaves_archive(repo):
    ex=OfflineSql(repo);r=SnowflakeRepository(ex);content=workbook()
    report=r.preview_flock_transaction_supplement('synthetic.xlsx',content,BINDING)
    old_batches=len(repo._import_batches)
    ex.fail_audit=True
    with pytest.raises(RuntimeError,match='audit failure'):
        r.commit_flock_transaction_supplement('synthetic.xlsx',content,BINDING,report['review_token'],confirmed=True,actor=ACTOR)
    assert ex.calls[-1][0]=='ROLLBACK'
    assert len(repo._flock_transactions)==1 and not repo._raw_rows and len(repo._import_batches)==old_batches
    assert len(repo._continuity_rows['SOURCE_FILE'])==1 and ex.files


def test_sql_missing_lock_row_blocks_before_any_insert(repo):
    ex=OfflineSql(repo);r=SnowflakeRepository(ex);ex.missing_lock=True
    content=workbook();report=r.preview_flock_transaction_supplement('synthetic.xlsx',content,BINDING)
    with pytest.raises(Exception,match='lock'):
        r.commit_flock_transaction_supplement('synthetic.xlsx',content,BINDING,report['review_token'],confirmed=True,actor=ACTOR)
    assert not any(sql.startswith('INSERT') for sql,_ in ex.calls)


def test_two_repository_instances_share_database_lock_not_only_python_lock(repo):
    ex=OfflineSql(repo);first=SnowflakeRepository(ex);second=SnowflakeRepository(ex)
    assert first._continuity_lock is not second._continuity_lock
    content=workbook()
    token=first.preview_flock_transaction_supplement('synthetic.xlsx',content,BINDING)['review_token']
    def submit(r):
        return r.commit_flock_transaction_supplement('synthetic.xlsx',content,BINDING,token,confirmed=True,actor=ACTOR)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(submit,[first,second]))
    assert sorted(row['created_count'] for row in results)==[0,12]
    assert len(repo._flock_transactions)==13 and len(repo._raw_rows)==13
    assert sum(sql.startswith('UPDATE EFNS_DEV.RAW.INTAKE_LOCK') for sql,_ in ex.calls)>=2

"""Exercise actual SnowflakeRepository SQL using isolated synthetic state only."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime
import json
import re
import threading
import pandas as pd
import pytest
from data.repositories.snowflake import SnowflakeRepository
from data.repositories.base import ConcurrencyError, RepositoryError
from tests.test_flock_date_repair import repo, BATCH, BASIS, ACTOR


class DateSql:
    def __init__(self,state):
        self.state=state;self.calls=[];self.lock=threading.RLock();self.fail_audit=False;self.fail_cas=False

    @contextmanager
    def transaction(self):
        with self.lock:
            before=deepcopy((self.state._flocks,self.state._continuity_rows,getattr(self.state,'_migration_review_audit',[])))
            self.calls.append(('BEGIN',None))
            try:
                yield self;self.calls.append(('COMMIT',None))
            except Exception:
                self.state._flocks,self.state._continuity_rows,self.state._migration_review_audit=before
                self.calls.append(('ROLLBACK',None));raise

    def query(self,sql,params=None):
        self.calls.append((sql,params))
        if 'CURRENT_ORGANIZATION_NAME' in sql:return pd.DataFrame([['QDCTNKN','UW19058','CB12755','AWS_CA_CENTRAL_1','EFNS_DEV']],columns=['ORG','ACCOUNT_NAME','LOCATOR','REGION','DB'])
        for table,attr in [('MIGRATION_BATCH','_migration_batches'),('MIGRATION_RAW_ROW','_migration_raw_rows'),('MIGRATION_ID_MAP','_migration_id_map')]:
            if f'.{table} ' in sql:return pd.DataFrame(deepcopy(getattr(self.state,attr)))
        if '.CORE.FLOCK ' in sql:
            return self.state._flocks[self.state._flocks.FLOCK_ID.astype(str).str.upper().isin(str(v).upper() for v in params)].copy()
        if '.RECORD_REVISION ' in sql:rows=self.state._continuity_rows['RECORD_REVISION'];field='ENTITY_ID'
        elif '.FLOCK_EVENT ' in sql:rows=self.state._continuity_rows['FLOCK_EVENT'];field='FLOCK_ID'
        elif '.AUDIT_EVENT ' in sql:rows=getattr(self.state,'_migration_review_audit',[]);field='AUDIT_ID' if 'WHERE AUDIT_ID=' in sql else 'ENTITY_ID'
        else:raise AssertionError(sql)
        return pd.DataFrame([deepcopy(r) for r in rows if str(r[field]).upper() in {str(v).upper() for v in params}])

    def execute(self,sql,params=None):
        self.calls.append((sql,params))
        if '.INTAKE_LOCK ' in sql:return 1
        if sql.startswith('UPDATE '):
            assert sql.startswith('UPDATE EFNS_DEV.CORE.FLOCK SET EST_DISPOSAL=%s,DISPOSAL_DATE=%s,UPDATED_AT=')
            assert 'IS NOT DISTINCT FROM %s' in sql and 'AND UPDATED_AT=%s' in sql
            if self.fail_cas:return 0
            a,b,g,version,old_a,old_b=params
            idx=self.state._flocks.index[self.state._flocks.FLOCK_ID==g][0]
            for f,v in [('EST_DISPOSAL',a),('DISPOSAL_DATE',b)]:
                self.state._flocks[f]=self.state._flocks[f].astype(object);self.state._flocks.at[idx,f]=v
            self.state._flocks.at[idx,'UPDATED_AT']=datetime(2026,1,1)
            return 1
        match=re.search(r'INSERT INTO EFNS_DEV.APP.(\w+) \(([^)]+)\)',sql)
        assert match,sql
        table,columns=match.groups();record={};values=iter(params)
        for f in columns.split(','):
            if f in {'RECORDED_AT','OCCURRED_AT'}:
                record[f]=datetime(2026,1,1)
            else:
                v=next(values);record[f]=json.loads(v) if f in {'BEFORE_DATA','AFTER_DATA','DETAILS'} else v
        if table=='RECORD_REVISION':self.state._continuity_rows[table].append(record)
        elif table=='AUDIT_EVENT':
            if self.fail_audit:raise RuntimeError('synthetic SQL audit failure')
            if not hasattr(self.state,'_migration_review_audit'):self.state._migration_review_audit=[]
            self.state._migration_review_audit.append(record)
        else:raise AssertionError(table)
        return 1


def test_sql_atomic_cas_null_parameters_and_server_history(repo):
    ex=DateSql(repo);r=SnowflakeRepository(ex)
    p=r.preview_flock_date_repair(BATCH,BASIS,{})
    assert not any(sql=='BEGIN' for sql,_ in ex.calls)
    result=r.commit_flock_date_repair(BATCH,BASIS,{},p['review_token'],confirmed=True,actor=ACTOR)
    assert result['changed']==2
    updates=[(sql,params) for sql,params in ex.calls if sql.startswith('UPDATE EFNS_DEV.CORE.FLOCK')]
    assert len(updates)==2 and updates[1][1][1] is None
    assert not any('STATUS=' in sql or 'PLACEMENT_DATE=' in sql for sql,_ in updates)
    assert ex.calls[-1][0]=='COMMIT'
    assert r.commit_flock_date_repair(BATCH,BASIS,{},p['review_token'],confirmed=True,actor=ACTOR)['changed']==0
    inserts=[sql for sql,_ in ex.calls if 'INSERT INTO EFNS_DEV.APP.' in sql]
    assert len(inserts)==3 and all('CURRENT_TIMESTAMP()' in sql for sql in inserts)


@pytest.mark.parametrize('failure',['audit','cas'])
def test_sql_failures_roll_back_core_and_history(repo,failure):
    before=repo._flocks.copy(deep=True);ex=DateSql(repo);r=SnowflakeRepository(ex)
    p=r.preview_flock_date_repair(BATCH,BASIS,{})
    ex.fail_audit=failure=='audit';ex.fail_cas=failure=='cas'
    with pytest.raises((RuntimeError,ConcurrencyError)):
        r.commit_flock_date_repair(BATCH,BASIS,{},p['review_token'],confirmed=True,actor=ACTOR)
    pd.testing.assert_frame_equal(before,repo._flocks)
    assert not repo._continuity_rows['RECORD_REVISION'] and ex.calls[-1][0]=='ROLLBACK'


@pytest.mark.parametrize('reverse',[False,True])
def test_wrong_database_blocked_before_lock_or_begin(repo,reverse):
    ex=DateSql(repo);r=SnowflakeRepository(ex);r.database='NOT_THE_DEV_DATABASE'
    with pytest.raises(RepositoryError,match='company DEV'):
        if reverse:r.commit_flock_date_reversal('synthetic-operation',BASIS,'0'*64,confirmed=True,actor=ACTOR)
        else:r.commit_flock_date_repair(BATCH,BASIS,{},'0'*64,confirmed=True,actor=ACTOR)
    assert ex.calls==[]

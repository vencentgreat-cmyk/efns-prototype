"""Round-3 scoped closure checks at 41a9c88.

Fake executors only; not real Snowflake engine evidence.
"""
from contextlib import contextmanager
import pandas as pd
import pytest
from data.connection import SnowparkExecutor
from data.repositories.base import RepositoryError, ConcurrencyError
from data.repositories.snowflake import SnowflakeRepository
from tests.test_round2_boundaries import LockSession

def test_N3_intake_inside_open_transaction_does_not_alter_session_mid_transaction():
    session=LockSession();executor=SnowparkExecutor(session)
    with executor.transaction():
        with pytest.raises(RepositoryError,match='inside an ordinary transaction'):
            with executor.intake_transaction():pytest.fail('unsupported nested write')
    statements=[sql for sql,_ in session.calls]
    begin=statements.index('BEGIN');commit=statements.index('COMMIT')
    inside=[sql for sql in statements[begin:commit] if sql.startswith('ALTER SESSION')]
    print('SEQUENCE',statements)
    assert not inside,inside
    assert statements==['BEGIN','COMMIT']

def test_N3_owner_rights_uses_supported_warehouse_bound_without_session_commands():
    class Denied(LockSession):
        def respond(self,sql,params):
            if sql.startswith('ALTER SESSION') or ('SHOW PARAMETERS' in sql and 'IN SESSION' in sql):
                pytest.fail('warehouse-runtime must not issue session parameter SQL')
            return super().respond(sql,params)
    session=Denied();executor=SnowparkExecutor(session)
    with executor.intake_transaction():
        executor.execute('UPDATE EFNS_DEV.RAW.INTAKE_LOCK SET VERSION=VERSION+1')
    statements=[sql for sql,_ in session.calls]
    assert statements.count('BEGIN')==statements.count('COMMIT')==1
    assert not any('IN WAREHOUSE' in sql or 'CURRENT_WAREHOUSE' in sql for sql in statements)

class _Ex:
    """Fake executor containing a Flock with a nanosecond version."""
    runtime_name='fake'
    def __init__(self,version):
        self.version=version;self.clock=pd.Timestamp(version);self.executed=[]
        self.birds=10;self.transactions={};self.revisions=[];self.audits=0
    @contextmanager
    def transaction(self):yield self
    def query(self,sql,params=None):
        from data.business_time import precise_version_sql
        sql=precise_version_sql(sql)
        if 'RECORD_REVISION' in sql:return pd.DataFrame([r for r in self.revisions if r['REVISION_ID']==params[0]])
        if 'FLOCK_TRANSACTION' in sql:return pd.DataFrame([r for key,r in self.transactions.items() if key==params[0]])
        if sql.startswith('SELECT CONVERT_TIMEZONE'):return pd.DataFrame([{'RECORDED_AT':self.clock}])
        if 'CORE.FLOCK' in sql:
            stamp=self.version if 'FF9' in sql else pd.Timestamp(self.version).to_pydatetime(warn=False)
            return pd.DataFrame([dict(FLOCK_ID='f1',ACCOUNT_ID='a',FACILITY_ID='x',FLOCK_NUMBER='N',PERMIT_NUMBER='P',BIRD_COUNT=self.birds,COMMENTS='old',UPDATED_AT=stamp)])
        return pd.DataFrame()
    def execute(self,sql,params=None):
        self.executed.append(sql)
        if 'SET BIRD_COUNT' in sql:
            assert 'GREATEST(' in sql and 'DATEADD(nanosecond,1' in sql
            if pd.Timestamp(params[2])!=pd.Timestamp(self.version):return 0
            self.birds=params[0]
            self.version=max(self.clock,pd.Timestamp(self.version)+pd.Timedelta(1,unit='ns')).isoformat()
        if 'AUDIT_EVENT' in sql:self.audits+=1
        return 1

def test_U1_revise_conflicts_when_versions_differ_inside_same_microsecond():
    executor=_Ex('2026-10-28T12:00:00.123456789');repo=SnowflakeRepository(executor)
    with pytest.raises(ConcurrencyError):
        repo.revise_record('FLOCK','f1',{'COMMENTS':'new'},'reason','req-1',actor={'user_id':'u','email':'u@nsegg.ca'},expected_updated_at='2026-10-28T12:00:00.123456788')
    assert not any(sql.lstrip().upper().startswith('UPDATE EFNS_DEV.CORE') for sql in executor.executed)

def test_U1_quantity_conflicts_when_versions_differ_inside_same_microsecond():
    from data.business_time import halifax_today
    executor=_Ex('2026-10-28T12:00:00.123456789');repo=SnowflakeRepository(executor)
    with pytest.raises(ConcurrencyError):
        repo.record_current_flock_quantity(dict(FLOCK_ID='f1',TRANSACTION_TYPE='Count',QUANTITY=5,TRANSACTION_DATE=halifax_today()),'req-q','2026-10-28T12:00:00.123456788','count',confirmed=True,actor={'user_id':'u','email':'u@nsegg.ca'},expected_bird_count=10)
    assert not any('SET BIRD_COUNT' in sql for sql in executor.executed)

def test_U1_quantity_accepts_identical_ns_version():
    from data.business_time import halifax_today
    executor=_Ex('2026-10-28T12:00:00.123456789');repo=SnowflakeRepository(executor)
    repo._upsert_with_executor=lambda tx,table,row:executor.transactions.update({row['FLOCK_TRANSACTION_ID']:dict(row)})
    repo._append_history=lambda tx,table,row:executor.revisions.append(dict(row))
    payload=dict(FLOCK_ID='f1',TRANSACTION_TYPE='Count',QUANTITY=5,TRANSACTION_DATE=halifax_today())
    kwargs=dict(confirmed=True,actor={'user_id':'u','email':'u@nsegg.ca'},expected_bird_count=10)
    first=repo.record_current_flock_quantity(payload,'req-q2','2026-10-28T12:00:00.123456789','count',**kwargs)
    assert executor.birds==5 and executor.version=='2026-10-28T12:00:00.123456790'
    assert len(executor.revisions)==executor.audits==len(executor.transactions)==1
    assert repo.record_current_flock_quantity(payload,'req-q2','2026-10-28T12:00:00.123456789','count',**kwargs)==first
    assert len(executor.revisions)==executor.audits==1
    repo.record_current_flock_quantity(payload,'req-q3',executor.version,'second',confirmed=True,actor=kwargs['actor'],expected_bird_count=5)
    assert executor.version=='2026-10-28T12:00:00.123456791'
    with pytest.raises(ConcurrencyError):
        repo.record_current_flock_quantity(payload,'req-stale','2026-10-28T12:00:00.123456790','stale',confirmed=True,actor=kwargs['actor'],expected_bird_count=5)
    assert any('SET BIRD_COUNT' in sql for sql in executor.executed)

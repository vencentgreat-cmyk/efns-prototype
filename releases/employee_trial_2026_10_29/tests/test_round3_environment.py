"""Restricted-runtime and repeated-clock contracts; no engine execution."""
import datetime as dt
import pandas as pd
import pytest
from data.connection import SnowparkExecutor
from data.repositories.base import RepositoryError
from tests.test_round2_boundaries import LockSession,ordinary_connector
from tests.test_connection import FakeRow,FakeStatement

def test_warehouse_runtime_bounds_only_the_lock_statement_without_session_or_warehouse_commands():
    """Review r4: no warehouse-wide timeout prerequisite; only INTAKE_LOCK is bounded per statement."""
    from data.repositories.snowflake import SnowflakeRepository
    seen=[]
    class Session(LockSession):
        def respond(self,sql,params):
            assert 'IN SESSION' not in sql and not sql.startswith('ALTER ') and 'IN WAREHOUSE' not in sql and 'CURRENT_WAREHOUSE' not in sql
            statement=super().respond(sql,params)
            original=statement.collect
            def collect(statement_params=None):
                seen.append((sql,statement_params));return original()
            statement.collect=collect
            return statement
    session=Session();ex=SnowparkExecutor(session);repo=SnowflakeRepository(ex)
    with repo._continuity_transaction():pass
    lock=[p for s,p in seen if 'INTAKE_LOCK' in s]
    assert lock==[{'STATEMENT_TIMEOUT_IN_SECONDS':'30'}]
    assert all(p is None for s,p in seen if 'INTAKE_LOCK' not in s)
    statements=[s for s,_ in session.calls]
    assert statements[0]=='BEGIN' and statements[-1]=='COMMIT'

@pytest.mark.parametrize('code',['000630','000604'])
def test_lock_statement_timeout_rolls_back_with_busy_message(code):
    from data.repositories.snowflake import SnowflakeRepository
    class Timeout(Exception):
        errno=int(code);sql_error_code=int(code)
    class Session(LockSession):
        def respond(self,sql,params):
            if 'INTAKE_LOCK' in sql:raise Timeout('Statement reached its statement or warehouse timeout')
            return super().respond(sql,params)
    session=Session();repo=SnowflakeRepository(SnowparkExecutor(session))
    with pytest.raises(RepositoryError,match='System busy'):
        with repo._continuity_transaction():pytest.fail('body must not run')
    statements=[s for s,_ in session.calls]
    assert 'ROLLBACK' in statements and 'COMMIT' not in statements

def test_connector_nested_intake_rejected_before_session_inspection():
    session=LockSession();ex=ordinary_connector(session)
    with ex.transaction():
        with pytest.raises(RepositoryError,match='inside an ordinary transaction'):
            with ex.intake_transaction():pytest.fail('unsupported nesting')
        assert session.calls==[]
    assert [s for s,_ in session.calls]==['COMMIT']

@pytest.mark.parametrize('route',['match','event','production'])
def test_three_other_cas_writers_advance_under_frozen_sql_clock(route):
    from tests.test_continuity_bindings import Executor,repository
    class Frozen(Executor):
        def __init__(self):
            super().__init__();self.clock=pd.Timestamp('2026-01-01T00:00:00.123456789');self.version=self.clock
        def query(self,sql,params=None):
            if 'RECORD_REVISION' in sql:return pd.DataFrame()
            frame=super().query(sql,params)
            if 'UPDATED_AT' in frame:frame['UPDATED_AT']=self.version.isoformat()
            return frame
        def execute(self,sql,params=None):
            if sql.startswith('UPDATE EFNS_DEV.CORE.'):
                assert 'GREATEST(' in sql and 'DATEADD(nanosecond,1' in sql
                expected=params[-2] if route=='match' else params[-1]
                assert pd.Timestamp(expected)==self.version
                self.version=max(self.clock,self.version+pd.Timedelta(1,unit='ns'))
            return super().execute(sql,params)
    ex=Frozen();repo=repository(ex)
    for index in range(2):
        if route=='match':repo.match_production_producer('p',actor='automatic')
        elif route=='event':repo.record_flock_event('f','MOVE',dt.datetime(2026,2+index,1,tzinfo=dt.timezone.utc),'Synthetic',str(index),'new',actor='staff',position_confirmed=True)
        else:repo.revise_record('PRODUCTION_RECORD','p',{'TOTAL':650+index},'Synthetic',str(index),actor='staff',expected_updated_at=ex.version.isoformat())
    assert ex.version==ex.clock+pd.Timedelta(2,unit='ns')

"""Runtime-specific identity regression; synthetic data, no network."""
from types import SimpleNamespace
import pandas as pd
import pytest
from data.connection import SnowparkExecutor, ConnectorExecutor
from data.repositories.snowflake import SnowflakeRepository
from data.repositories.flock_date_repair import COMPANY_IDENTITY, IDENTITY_SQL
from data.repositories.base import RepositoryError
from app.services.authorized_repository import AuthorizedRepository
from app.security import Role
from tests.test_connection import FakeSession, FakeRow, FakeStatement, FakeCursor, FakeConnection
from tests.test_flock_date_repair import repo, BATCH, BASIS, ACTOR
from tests.test_flock_date_repair_sql import DateSql


def test_actual_snowpark_quoted_expression_shape_reproduces_old_failure():
    labels=['CURRENT_ORGANIZATION_NAME()','CURRENT_ACCOUNT_NAME()','CURRENT_ACCOUNT()',
            'CURRENT_REGION()','CURRENT_DATABASE()']
    row=FakeRow(**dict(zip(labels,COMPANY_IDENTITY.values())))
    executor=SnowparkExecutor(FakeSession(lambda *_:FakeStatement([row],['"'+c+'"' for c in labels])))
    frame=executor.query('SELECT '+','.join(labels))
    assert frame.isna().all().all()


@pytest.mark.parametrize('kind',['snowpark','connector'])
def test_aliased_identity_uses_names_not_column_position(kind):
    names=list(reversed(COMPANY_IDENTITY))
    if kind=='snowpark':
        def respond(sql,params):
            assert sql==IDENTITY_SQL
            return FakeStatement([FakeRow(**COMPANY_IDENTITY)],names)
        executor=SnowparkExecutor(FakeSession(respond))
    else:
        cursor=FakeCursor(rows=[tuple(COMPANY_IDENTITY[n] for n in names)],description=[(n,) for n in names])
        executor=ConnectorExecutor(lambda:FakeConnection(cursor))
    r=SnowflakeRepository(executor)
    r._date_company()
    context=r.diagnose_flock_date_repair_context()
    assert context['verified'] and context['repository_database']=='EFNS_DEV'
    assert context['values']==COMPANY_IDENTITY and set(context['types'].values())=={'str'}


@pytest.mark.parametrize('field',list(COMPANY_IDENTITY))
@pytest.mark.parametrize('operation',['preview','commit','reversal'])
def test_every_wrong_identity_field_blocks_before_batch_read_or_transaction(repo,field,operation):
    class Wrong(DateSql):
        def query(self,sql,params=None):
            if sql==IDENTITY_SQL:
                self.calls.append((sql,params))
                return pd.DataFrame([dict(COMPANY_IDENTITY,**{field:'NOT_THE_COMPANY'})])
            return super().query(sql,params)
    ex=Wrong(repo);r=SnowflakeRepository(ex)
    with pytest.raises(RepositoryError) as caught:
        if operation=='preview':r.preview_flock_date_repair(BATCH,BASIS,{})
        elif operation=='commit':r.commit_flock_date_repair(BATCH,BASIS,{},'0'*64,confirmed=True,actor=ACTOR)
        else:r.commit_flock_date_reversal('synthetic-operation',BASIS,'0'*64,confirmed=True,actor=ACTOR)
    assert caught.value.date_identity_diagnostic['mismatches']==[field]
    assert ex.calls==[(IDENTITY_SQL,None)]


@pytest.mark.parametrize('shape',['empty','two_rows','missing','duplicate','nan','non_string'])
def test_unknown_or_malformed_identity_fails_closed(repo,shape):
    good=pd.DataFrame([COMPANY_IDENTITY])
    frames={'empty':good.iloc[:0],'two_rows':pd.concat([good,good]),
            'missing':good.drop(columns=['DB']),
            'duplicate':pd.concat([good,good[['DB']]],axis=1),
            'nan':good.assign(DB=float('nan')),'non_string':good.assign(DB=123)}
    ex=SimpleNamespace(query=lambda *a,**k:frames[shape])
    with pytest.raises(RepositoryError):SnowflakeRepository(ex)._date_company()


def test_scope_uses_one_shared_aliased_guard(repo):
    ex=DateSql(repo)
    p=SnowflakeRepository(ex).preview_flock_date_repair(BATCH,BASIS,{})
    assert p['counts']['READY']==2
    assert [sql for sql,_ in ex.calls if 'CURRENT_ORGANIZATION_NAME' in sql]==[IDENTITY_SQL]
    assert not any(sql=='BEGIN' for sql,_ in ex.calls)


def test_runtime_diagnostic_is_readonly_and_admin_only(repo):
    ex=DateSql(repo);r=SnowflakeRepository(ex)
    reader=SimpleNamespace(role=Role.REPORTING_VIEWER,user_id='reader',email='reader@nsegg.ca',active=True)
    with pytest.raises(RepositoryError):AuthorizedRepository(r,SimpleNamespace(),reader).diagnose_flock_date_repair_context()
    assert not ex.calls
    admin=SimpleNamespace(role=Role.ADMIN,user_id=ACTOR['user_id'],email=ACTOR['email'],active=True)
    report=AuthorizedRepository(r,SimpleNamespace(),admin).diagnose_flock_date_repair_context()
    assert report['verified'] and ex.calls==[(IDENTITY_SQL,None)]
    assert set(report)=={'repository_database','runtime','result_columns','row_count','expected','values','types','mismatches','verified'}


def test_diagnostic_can_report_wrong_context_without_authorizing_it(repo):
    r=SnowflakeRepository(DateSql(repo));r.database='WRONG_DATABASE'
    assert r.diagnose_flock_date_repair_context()['mismatches']==['repository_database']
    with pytest.raises(RepositoryError,match='repository_database'):r._date_company()

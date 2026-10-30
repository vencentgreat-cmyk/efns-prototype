"""R4 fail-closed statement bounds; synthetic executor evidence only."""
import pytest
from data.connection import SnowparkExecutor
from data.repositories.base import RepositoryError
from data.repositories.snowflake import SnowflakeRepository
from tests.test_round2_boundaries import LockSession

@pytest.mark.parametrize("timeout", [0,-1,31,1.5,float("nan"),True,None,"30"])
def test_invalid_bound_never_sends_sql(timeout):
    session=LockSession()
    with pytest.raises(RepositoryError,match="unbounded fallback is disabled"):
        SnowparkExecutor(session).execute_bounded("UPDATE synthetic",timeout_seconds=timeout)
    assert session.calls==[]

def test_missing_bounded_api_blocks_before_begin():
    session=LockSession(); ex=SnowparkExecutor(session)
    ex.execute_bounded=None
    with pytest.raises(RepositoryError,match="no write transaction started"):
        with ex.intake_transaction(): pytest.fail("body ran")
    assert session.calls==[]

def test_statement_params_denied_rolls_back_without_fallback():
    class Session(LockSession):
        def respond(self,sql,params):
            statement=super().respond(sql,params)
            original=statement.collect
            def collect(statement_params=None):
                if statement_params is not None:
                    raise RuntimeError("synthetic statement parameter rejected")
                return original()
            statement.collect=collect
            return statement
    session=Session();repo=SnowflakeRepository(SnowparkExecutor(session))
    with pytest.raises(RepositoryError):
        with repo._continuity_transaction():pytest.fail("body ran")
    statements=[s for s,_ in session.calls]
    assert statements.count("BEGIN")==1
    assert statements.count("ROLLBACK")==1
    assert not any(s=="COMMIT" or s.startswith(("ALTER ","SHOW ")) for s in statements)
    assert sum("INTAKE_LOCK" in s for s in statements)==1

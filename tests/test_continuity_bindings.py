"""Persistence-boundary tests for pandas values returned by real SQL reads."""
from contextlib import contextmanager
import datetime as dt
from types import SimpleNamespace

import pandas as pd

from data.repositories.snowflake import SnowflakeRepository


class Executor:
    def __init__(self): self.calls=[]
    @contextmanager
    def transaction(self): yield self
    def execute(self,sql,params=None):
        self.calls.append((sql,params))
        assert not any(isinstance(value,pd.Timestamp) for value in params or ()), 'Connector does not bind pandas.Timestamp'
        return 1
    def query(self,sql,params=None):
        if 'FLOCK_EVENT' in sql or 'PRODUCTION_MATCH_DECISION' in sql: return pd.DataFrame()
        if 'PRODUCTION_RECORD' in sql:
            return pd.DataFrame([dict(PRODUCTION_ID='p',PRODUCER_ACCOUNT_ID=None,PRODUCER_NUMBER='001',UPDATED_AT=pd.Timestamp('2026-01-01'))])
        return pd.DataFrame([dict(FLOCK_ID='f',ACCOUNT_ID='a',FACILITY_ID='old',UPDATED_AT=pd.Timestamp('2026-01-01'),DISPOSAL_DATE=None)])


def repository(ex):
    repo=SnowflakeRepository(ex)
    repo.get_accounts=lambda: pd.DataFrame([dict(ACCOUNT_ID='a',REGISTRATION_NUMBER='001')])
    repo.get_facilities=lambda: pd.DataFrame([dict(FACILITY_ID='new',ACCOUNT_ID='a')])
    return repo


def test_event_converts_saved_pandas_timestamp_to_native_bind():
    ex=Executor(); repo=repository(ex)
    repo.record_flock_event('f','MOVE',dt.datetime(2026,2,1,tzinfo=dt.timezone.utc),'Synthetic','request','new',actor='staff',position_confirmed=True)
    params=next(params for sql,params in ex.calls if 'UPDATE EFNS_DEV.CORE.FLOCK ' in sql)
    assert type(params[-1]) is dt.datetime


def test_matching_converts_saved_pandas_timestamp_to_native_bind():
    ex=Executor(); repo=repository(ex)
    repo.match_production_producer('p',actor='automatic')
    params=next(params for sql,params in ex.calls if 'UPDATE EFNS_DEV.CORE.PRODUCTION_RECORD ' in sql)
    assert type(params[-2]) is dt.datetime

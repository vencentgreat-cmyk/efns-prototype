"""Offline contract checks for parameterized Snowflake reads."""

import pandas as pd
import pytest

from data.repositories.base import RepositoryError
from data.repositories.snowflake import SnowflakeRepository


def repository_without_connection():
    repo = SnowflakeRepository.__new__(SnowflakeRepository)
    repo.database = "EFNS_DEV"
    repo.schema_core = "CORE"
    repo.schema_raw = "RAW"
    repo.schema_reporting = "REPORTING"
    return repo


def test_flock_filters_are_passed_as_query_parameters():
    repo = repository_without_connection()
    captured = {}

    def query(sql, params=None):
        captured["sql"] = sql
        captured["params"] = params
        return pd.DataFrame()

    repo._query = query
    repo.get_flocks(account_id="account'quoted", facility_id="facility'quoted")

    assert "account'quoted" not in captured["sql"]
    assert "facility'quoted" not in captured["sql"]
    assert captured["sql"].count("%s") == 2
    assert captured["params"] == ("account'quoted", "facility'quoted")


class FakeCursor:
    def __init__(self, fail_executemany=False, duplicate=False):
        self.calls = []
        self.rowcount = 0
        self.description = []
        self.fail_executemany = fail_executemany
        self.duplicate = duplicate
    def execute(self, sql, params=()):
        self.calls.append((sql, params))
        self.rowcount = 0 if sql.startswith("UPDATE") else 1
        return self
    def executemany(self, sql, params):
        self.calls.append((sql, list(params)))
        if self.fail_executemany:
            raise RuntimeError("write failed")
    def fetchone(self): return ("prior-import",) if self.duplicate else None
    def fetchall(self): return []
    def close(self): pass


class FakeConnection:
    def __init__(self, **kwargs):
        self.cursor_instance = FakeCursor(**kwargs)
        self.commits = self.rollbacks = 0
    def cursor(self): return self.cursor_instance
    def commit(self): self.commits += 1
    def rollback(self): self.rollbacks += 1


def repository_with_connection(connection):
    repo = repository_without_connection()
    repo._connect = lambda: connection
    return repo


def test_upsert_binds_values_and_commits():
    connection = FakeConnection()
    repo = repository_with_connection(connection)
    result = repo.upsert_account({"ORGANIZATION_NAME": "O'Reilly"})
    sql, params = connection.cursor_instance.calls[-1]
    assert "O'Reilly" not in sql
    assert sql.startswith("INSERT INTO EFNS_DEV.CORE.ACCOUNT")
    assert params[0] == result
    assert params[1:] == ("O'Reilly",)
    assert connection.commits == 1


def test_import_bundle_rolls_back_all_writes_on_failure():
    connection = FakeConnection(fail_executemany=True)
    repo = repository_with_connection(connection)
    with pytest.raises(RepositoryError):
        repo.import_production_bundle(
            {"FILENAME": "x.xlsx", "FILE_HASH": "abc"},
            [{"SOURCE_ROW_NUMBER": 2, "RAW_DATA": {"A": 1}}],
            pd.DataFrame([{"REPORTING_YEAR": 2026}]),
        )
    assert connection.commits == 0
    assert connection.rollbacks == 1


def test_duplicate_import_is_rejected_before_insert():
    connection = FakeConnection(duplicate=True)
    repo = repository_with_connection(connection)
    with pytest.raises(RepositoryError, match="already been imported"):
        repo.import_production_bundle({"FILENAME": "x.xlsx", "FILE_HASH": "abc"}, [], pd.DataFrame())
    assert connection.rollbacks == 1


def test_production_filters_are_pushed_to_sql():
    repo = repository_without_connection(); captured = {}
    repo._query = lambda sql, params=None: captured.update(sql=sql, params=params) or pd.DataFrame()
    repo.get_production_records(reporting_week=5, egg_colour="Brown")
    assert "REPORTING_WEEK = %s" in captured["sql"]
    assert "EGG_COLOUR = %s" in captured["sql"]
    assert captured["params"] == (5, "Brown")

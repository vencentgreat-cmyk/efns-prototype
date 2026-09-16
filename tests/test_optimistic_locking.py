"""Optimistic-locking contract for Account updates (UPDATED_AT stamp).

These run fully offline against the mock repository plus a stubbed
Snowflake cursor, so no real Snowflake credentials are required.
"""

import datetime as dt
import time

import pandas as pd
import pytest

from data.repositories.base import ConcurrencyError
from data.repositories.mock import MockRepository
from data.repositories.snowflake import SnowflakeRepository


def _new_account(repo: MockRepository) -> str:
    return repo.upsert_account(
        {"ORGANIZATION_NAME": "Lock Co", "REGISTRATION_NUMBER": "LOCK-1"}
    )


def test_update_with_matching_stamp_succeeds():
    repo = MockRepository(seed=1)
    aid = _new_account(repo)
    stamp = repo.get_account(aid)["UPDATED_AT"]

    repo.upsert_account(
        {
            "ACCOUNT_ID": aid,
            "ORGANIZATION_NAME": "Lock Co Renamed",
            "REGISTRATION_NUMBER": "LOCK-1",
            "EXPECTED_UPDATED_AT": stamp,
        }
    )
    assert repo.get_account(aid)["ORGANIZATION_NAME"] == "Lock Co Renamed"


def test_stale_stamp_raises_concurrency_error():
    repo = MockRepository(seed=1)
    aid = _new_account(repo)
    stale = repo.get_account(aid)["UPDATED_AT"]

    # A first editor saves, advancing UPDATED_AT.
    time.sleep(0.001)
    repo.upsert_account(
        {
            "ACCOUNT_ID": aid,
            "ORGANIZATION_NAME": "Saved by editor A",
            "REGISTRATION_NUMBER": "LOCK-1",
            "EXPECTED_UPDATED_AT": stale,
        }
    )
    fresh = repo.get_account(aid)["UPDATED_AT"]

    # A second editor still holding the stale stamp is blocked, not silently
    # overwriting editor A's work.
    with pytest.raises(ConcurrencyError):
        repo.upsert_account(
            {
                "ACCOUNT_ID": aid,
                "ORGANIZATION_NAME": "Saved by editor B",
                "REGISTRATION_NUMBER": "LOCK-1",
                "EXPECTED_UPDATED_AT": stale,
            }
        )
    assert repo.get_account(aid)["ORGANIZATION_NAME"] == "Saved by editor A"

    # After reloading the fresh stamp, the save goes through.
    repo.upsert_account(
        {
            "ACCOUNT_ID": aid,
            "ORGANIZATION_NAME": "Saved by editor B",
            "REGISTRATION_NUMBER": "LOCK-1",
            "EXPECTED_UPDATED_AT": fresh,
        }
    )
    assert repo.get_account(aid)["ORGANIZATION_NAME"] == "Saved by editor B"


def test_missing_expected_stamp_is_backward_compatible():
    repo = MockRepository(seed=1)
    aid = _new_account(repo)
    # Callers that don't pass a stamp keep working (no forced lock).
    repo.upsert_account(
        {
            "ACCOUNT_ID": aid,
            "ORGANIZATION_NAME": "Unlocked update",
            "REGISTRATION_NUMBER": "LOCK-1",
        }
    )
    assert repo.get_account(aid)["ORGANIZATION_NAME"] == "Unlocked update"


def test_expected_stamp_is_not_persisted_as_a_column():
    repo = MockRepository(seed=1)
    aid = _new_account(repo)
    stamp = repo.get_account(aid)["UPDATED_AT"]
    repo.upsert_account(
        {
            "ACCOUNT_ID": aid,
            "ORGANIZATION_NAME": "Still clean",
            "REGISTRATION_NUMBER": "LOCK-1",
            "EXPECTED_UPDATED_AT": stamp,
        }
    )
    assert "EXPECTED_UPDATED_AT" not in repo.get_accounts().columns


# --- Snowflake SQL-shape contract (stubbed cursor, no live connection) -------


class _FakeCursor:
    def __init__(self, rowcount=1):
        self.calls = []
        self.rowcount = rowcount

    def execute(self, sql, params=None):
        self.calls.append((sql, params))

    def fetchall(self):
        if self.calls and self.calls[-1][0].startswith("SELECT CREATED_AT"):
            self.description = [("CREATED_AT",), ("UPDATED_AT",)]
            return [("2025-01-01T00:00:00", "2026-01-01T00:00:00")]
        self.description = []
        return []

    def fetchone(self):
        return (0,)


class _FakeCtx:
    def __init__(self, cursor):
        self._cursor = cursor

    def __enter__(self):
        return self._cursor

    def __exit__(self, *args):
        return False


def _snowflake_repo(cursor):
    repo = SnowflakeRepository.__new__(SnowflakeRepository)
    repo.database = "EFNS_DEV"
    repo.schema_core = "CORE"
    repo._cursor = lambda transaction=False: _FakeCtx(cursor)
    repo.find_accounts_by_registration_number = lambda registration: pd.DataFrame()
    return repo


def test_snowflake_update_binds_expected_stamp_in_where_clause():
    cursor = _FakeCursor(rowcount=1)
    repo = _snowflake_repo(cursor)

    repo.upsert_account(
        {
            "ACCOUNT_ID": "a1",
            "ORGANIZATION_NAME": "X",
            "REGISTRATION_NUMBER": "R1",
            "EXPECTED_UPDATED_AT": "2026-01-01T00:00:00",
        }
    )

    update_sql, update_params = next(call for call in cursor.calls if call[0].startswith("UPDATE"))
    assert "WHERE ACCOUNT_ID = %s AND UPDATED_AT = %s" in update_sql
    # The stamp is bound as a parameter, never interpolated into the SQL text.
    assert "2026-01-01T00:00:00" not in update_sql
    assert update_params[-1] == dt.datetime(2026, 1, 1)


def test_snowflake_update_without_stamp_has_no_lock_clause():
    cursor = _FakeCursor(rowcount=1)
    repo = _snowflake_repo(cursor)

    repo.upsert_account(
        {"ACCOUNT_ID": "a1", "ORGANIZATION_NAME": "X", "REGISTRATION_NUMBER": "R1"}
    )

    update_sql, _ = next(call for call in cursor.calls if call[0].startswith("UPDATE"))
    assert "AND UPDATED_AT = %s" not in update_sql

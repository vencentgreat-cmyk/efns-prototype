"""Offline contracts for Snowflake DDL alignment and write semantics."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import re

import pandas as pd
import pytest

from app.navigation import format_timestamp
from data.repositories.base import RepositoryError
from data.repositories.snowflake import (
    IMPORT_BATCH_COLUMNS,
    MODEL,
    PRODUCTION_COLUMNS,
    RAW_ROW_COLUMNS,
    SnowflakeRepository,
    UTC_NOW_NTZ,
)


ROOT = Path(__file__).resolve().parents[1]


def _ddl_columns(path: str, table: str) -> list[str]:
    text = (ROOT / path).read_text(encoding="utf-8")
    match = re.search(
        rf"CREATE TABLE IF NOT EXISTS EFNS_DEV\.[A-Z_]+\.{table}\s*\((.*?)\)\s*(?:COMMENT\s*=|;)",
        text,
        flags=re.DOTALL,
    )
    assert match, f"DDL for {table} was not found"
    return [
        line.split()[0]
        for line in match.group(1).splitlines()
        if line.strip()
        and not line.strip().startswith(("CONSTRAINT", "REFERENCES"))
        for line in [line.strip().rstrip(",")]
    ]


class RecordingExecutor:
    runtime_name = "Offline contract"

    def __init__(self, *, existing=False, affected=1, fail=False):
        self.existing = existing
        self.affected = affected
        self.fail = fail
        self.calls = []
        self.commits = 0
        self.rollbacks = 0

    def query(self, sql, params=None):
        self.calls.append(("query", sql, tuple(params or ())))
        if "SELECT CREATED_AT, UPDATED_AT" in sql and self.existing:
            return pd.DataFrame([{
                "CREATED_AT": "2026-02-01T12:00:00",
                "UPDATED_AT": "2026-02-02T12:00:00",
            }])
        if "SELECT CREATED_AT, UPDATED_AT" in sql and self.affected < 0:
            return pd.DataFrame([{
                "CREATED_AT": "2026-02-01T12:00:00",
                "UPDATED_AT": "2026-02-01T12:00:00",
            }])
        return pd.DataFrame()

    def execute(self, sql, params=None):
        self.calls.append(("execute", sql, tuple(params or ())))
        if self.fail:
            raise RepositoryError("safe write failure")
        return self.affected

    def executemany(self, sql, rows, *, batch_size=500):
        values = list(rows)
        self.calls.append(("executemany", sql, values))
        if self.fail:
            raise RepositoryError("safe bulk failure")
        return len(values)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    @contextmanager
    def transaction(self):
        self.calls.append(("begin", "", ()))
        try:
            yield self
            self.commit()
        except Exception:
            self.rollback()
            raise


def _repo(executor) -> SnowflakeRepository:
    repo = SnowflakeRepository.__new__(SnowflakeRepository)
    repo.executor = executor
    repo.database = "EFNS_DEV"
    repo.schema_core = "CORE"
    repo.schema_raw = "RAW"
    repo.schema_reporting = "REPORTING"
    return repo


def test_core_model_columns_exactly_match_repository_order():
    for table, (key, allowed_text) in MODEL.items():
        assert _ddl_columns("sql/02_core_tables.sql", table) == [
            key,
            *allowed_text.split(),
            "CREATED_AT",
            "UPDATED_AT",
        ]


def test_import_and_production_insert_columns_align_with_ddl():
    assert _ddl_columns("sql/03_production_tables.sql", "IMPORT_BATCH") == [
        "IMPORT_ID", *IMPORT_BATCH_COLUMNS, "UPLOAD_TIMESTAMP", "CREATED_AT", "UPDATED_AT"
    ]
    raw_columns = _ddl_columns("sql/03_production_tables.sql", "IMPORT_RAW_ROW")
    assert raw_columns[: len(RAW_ROW_COLUMNS)] == RAW_ROW_COLUMNS
    assert raw_columns[-2:] == ["CREATED_AT", "UPDATED_AT"]
    assert _ddl_columns("sql/03_production_tables.sql", "PRODUCTION_RECORD") == [
        "PRODUCTION_ID", "IMPORT_ID", *PRODUCTION_COLUMNS, "CREATED_AT", "UPDATED_AT"
    ]


@pytest.mark.parametrize("table", list(MODEL))
def test_every_entity_create_uses_direct_insert_and_server_utc(table):
    executor = RecordingExecutor()
    repo = _repo(executor)
    key, fields = MODEL[table]
    first_field = fields.split()[0]
    result = repo._upsert(table, {first_field: f"value-{table.lower()}"})
    writes = [call for call in executor.calls if call[0] == "execute"]
    assert len(writes) == 1
    _, sql, params = writes[0]
    assert sql.startswith(f"INSERT INTO EFNS_DEV.CORE.{table}")
    assert "UPDATE EFNS_DEV" not in sql
    assert sql.count(UTC_NOW_NTZ) == 2
    assert len(params) == sql.count("%s")
    assert params == (result, f"value-{table.lower()}")
    assert len(result) == 36
    assert executor.commits == 1 and executor.rollbacks == 0


def test_account_insert_field_and_parameter_order_matches_real_ddl():
    executor = RecordingExecutor()
    repo = _repo(executor)
    account_fields = MODEL["ACCOUNT"][1].split()
    record = {name: None for name in reversed(account_fields)}
    record.update({
        "ORGANIZATION_NAME": "DEV contract account",
        "DEFAULT_ON_REPORTS": False,
        "NO_SVG": True,
        "STATUS": "Active",
    })
    result = repo._upsert("ACCOUNT", record)
    _, sql, params = next(call for call in executor.calls if call[0] == "execute")
    insert_columns = re.search(r"ACCOUNT \((.*?)\) VALUES", sql).group(1).split(", ")
    assert insert_columns == ["ACCOUNT_ID", *account_fields, "CREATED_AT", "UPDATED_AT"]
    assert params[0] == result
    assert params[1:] == tuple(record[field] for field in account_fields)
    assert len(params) == sql.count("%s")


def test_update_preserves_created_at_and_advances_only_updated_at():
    executor = RecordingExecutor(existing=True)
    repo = _repo(executor)
    result = repo._upsert("ACCOUNT", {
        "ACCOUNT_ID": "account-1",
        "ORGANIZATION_NAME": "Updated",
        "EXPECTED_UPDATED_AT": "2026-02-02T12:00:00",
    })
    _, sql, params = next(call for call in executor.calls if call[0] == "execute")
    assert result == "account-1"
    assert sql.startswith("UPDATE EFNS_DEV.CORE.ACCOUNT")
    assert "CREATED_AT" not in sql
    assert f"UPDATED_AT = {UTC_NOW_NTZ}" in sql
    assert params == ("Updated", "account-1", "2026-02-02T12:00:00")
    assert len(params) == sql.count("%s")


def test_unknown_insert_affected_rows_is_verified_and_returned():
    executor = RecordingExecutor(affected=-1)
    repo = _repo(executor)
    result = repo._upsert("ACCOUNT", {"ORGANIZATION_NAME": "Verified"})
    assert len(result) == 36
    assert any(call[0] == "query" and call[2] == (result,) for call in executor.calls)
    assert executor.commits == 1


def test_failed_write_rolls_back_without_returning_an_id():
    executor = RecordingExecutor(fail=True)
    repo = _repo(executor)
    with pytest.raises(RepositoryError, match="safe write failure"):
        repo._upsert("ACCOUNT", {"ORGANIZATION_NAME": "Fails"})
    assert executor.commits == 0 and executor.rollbacks == 1


def test_persisted_ddl_and_seed_use_server_generated_utc_timestamps():
    for path in ("sql/02_core_tables.sql", "sql/03_production_tables.sql"):
        text = (ROOT / path).read_text(encoding="utf-8")
        assert "DEFAULT CURRENT_TIMESTAMP()" not in text
        assert "DEFAULT CONVERT_TIMEZONE('UTC', CURRENT_TIMESTAMP())::TIMESTAMP_NTZ" in text
    seed = (ROOT / "sql/09_dev_synthetic_seed.sql").read_text(encoding="utf-8")
    assert "TO_TIMESTAMP_NTZ('2026-01-01 00:00:00')" not in seed
    assert seed.count(UTC_NOW_NTZ) >= 2
    assert "WHEN MATCHED" not in seed.upper()


def test_timestamp_display_converts_utc_to_halifax_with_timezone_label():
    assert format_timestamp("2026-01-15T12:00:00Z") == (
        "2026-01-15 08:00 AST (America/Halifax)"
    )
    assert format_timestamp("2026-07-15T12:00:00Z") == (
        "2026-07-15 09:00 ADT (America/Halifax)"
    )

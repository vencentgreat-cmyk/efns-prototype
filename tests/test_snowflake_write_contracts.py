"""Offline contracts for Snowflake DDL alignment and write semantics."""

from __future__ import annotations

from contextlib import contextmanager
import datetime as dt
from decimal import Decimal
from pathlib import Path
import re

import pandas as pd
import pytest

from app.navigation import format_timestamp
from app.security import Role, User
from app.services.authorized_repository import AuthorizedRepository
from data.repositories.base import RepositoryError
from data.repositories.snowflake import (
    IMPORT_BATCH_COLUMNS,
    DATE_FIELDS,
    MODEL,
    PRODUCTION_COLUMNS,
    PRODUCTION_DECIMAL_COLUMNS,
    PRODUCTION_INTEGER_COLUMNS,
    RAW_ROW_COLUMNS,
    SnowflakeRepository,
    UTC_NOW_NTZ,
    normalize_date_bind,
    normalize_numeric_bind,
    normalize_timestamp_bind,
)
from data.repositories.mock import MockRepository


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


FINAL_MODEL_DDL_PATHS = (
    "sql/02_core_tables.sql",
    "sql/12_real_eims_additive_migration.sql",
)


def _final_model_ddl() -> str:
    return "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in FINAL_MODEL_DDL_PATHS
    )


def _final_model_columns(table: str) -> list[str]:
    ddl = _final_model_ddl()

    match = re.search(
        rf"CREATE TABLE IF NOT EXISTS "
        rf"EFNS_DEV\.[A-Z_]+\.{table}\s*"
        rf"\((.*?)\)\s*(?:COMMENT\s*=|;)",
        ddl,
        flags=re.DOTALL,
    )
    assert match, f"DDL for {table} was not found"

    columns = [
        line.split()[0]
        for line in match.group(1).splitlines()
        if line.strip()
        and not line.strip().startswith(
            ("CONSTRAINT", "REFERENCES")
        )
        for line in [line.strip().rstrip(",")]
    ]

    added_columns = re.findall(
        rf"ALTER TABLE IF EXISTS "
        rf"EFNS_DEV\.[A-Z_]+\.{table}\s+"
        rf"ADD COLUMN IF NOT EXISTS\s+"
        rf"([A-Z0-9_]+)\s+",
        ddl,
    )

    for column in added_columns:
        if column not in columns:
            columns.append(column)

    return columns


def _final_model_date_columns(table: str) -> set[str]:
    ddl = _final_model_ddl()

    match = re.search(
        rf"CREATE TABLE IF NOT EXISTS "
        rf"EFNS_DEV\.[A-Z_]+\.{table}\s*"
        rf"\((.*?)\)\s*(?:COMMENT\s*=|;)",
        ddl,
        flags=re.DOTALL,
    )
    assert match, f"DDL for {table} was not found"

    dates = set(
        re.findall(
            r"^\s+([A-Z_]+)\s+DATE\b",
            match.group(1),
            flags=re.MULTILINE,
        )
    )

    dates.update(
        re.findall(
            rf"ALTER TABLE IF EXISTS "
            rf"EFNS_DEV\.[A-Z_]+\.{table}\s+"
            rf"ADD COLUMN IF NOT EXISTS\s+"
            rf"([A-Z0-9_]+)\s+DATE\b",
            ddl,
        )
    )

    return dates


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


def test_final_model_columns_match_repository_contract():
    for table, (key, allowed_text) in MODEL.items():
        expected = {
            key,
            *allowed_text.split(),
            "CREATED_AT",
            "UPDATED_AT",
        }
        actual = set(_final_model_columns(table))

        assert actual == expected, {
            "table": table,
            "missing": sorted(expected - actual),
            "unexpected": sorted(actual - expected),
        }

def test_every_model_date_column_is_normalized_at_repository_boundary():
    for table in MODEL:
        actual = _final_model_date_columns(table)
        expected = set(DATE_FIELDS.get(table, ()))

        assert actual == expected, {
            "table": table,
            "missing_normalizers": sorted(actual - expected),
            "non_ddl_date_fields": sorted(expected - actual),
        }

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


def test_production_numeric_contract_matches_ddl_integer_and_decimal_scales():
    ddl = (ROOT / "sql/03_production_tables.sql").read_text(encoding="utf-8")
    body = re.search(
        r"CREATE TABLE IF NOT EXISTS EFNS_DEV\.CORE\.PRODUCTION_RECORD\s*\((.*?)\)\s*COMMENT",
        ddl,
        flags=re.DOTALL,
    ).group(1)
    types = {
        name: (int(precision), int(scale))
        for name, precision, scale in re.findall(
            r"^\s+([A-Z0-9_]+)\s+NUMBER\((\d+),\s*(\d+)\)", body, flags=re.MULTILINE
        )
    }
    assert {name for name, (_, scale) in types.items() if scale == 0} == set(
        PRODUCTION_INTEGER_COLUMNS
    )
    assert {name for name, (_, scale) in types.items() if scale > 0} == set(
        PRODUCTION_DECIMAL_COLUMNS
    )


@pytest.mark.parametrize("table", list(MODEL))
def test_every_entity_create_uses_direct_insert_and_server_utc(table):
    executor = RecordingExecutor()
    repo = _repo(executor)
    key, fields = MODEL[table]
    first_field = fields.split()[0]

    if table == "DIM_EFC_DATE":
        record = {
            key: dt.date(2026, 2, 3),
            first_field: 2026,
        }
        expected_params = (
            dt.date(2026, 2, 3),
            2026,
        )
        expected_schema = "REPORTING"
    else:
        record = {
            first_field: f"value-{table.lower()}",
        }
        expected_params = None
        expected_schema = "CORE"

    result = repo._upsert(table, record)

    writes = [
        call
        for call in executor.calls
        if call[0] == "execute"
    ]
    assert len(writes) == 1

    _, sql, params = writes[0]

    assert sql.startswith(
        f"INSERT INTO EFNS_DEV.{expected_schema}.{table}"
    )
    assert "UPDATE EFNS_DEV" not in sql
    assert sql.count(UTC_NOW_NTZ) == 2
    assert len(params) == sql.count("%s")

    if table == "DIM_EFC_DATE":
        assert params == expected_params
        assert result == dt.date(2026, 2, 3)
    else:
        assert params == (
            result,
            f"value-{table.lower()}",
        )
        assert len(result) == 36

    assert executor.commits == 1
    assert executor.rollbacks == 0

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
    assert params == ("Updated", "account-1", dt.datetime(2026, 2, 2, 12, 0))
    assert len(params) == sql.count("%s")


def test_optimistic_lock_timestamp_is_connector_compatible_and_canonical_utc():
    assert normalize_timestamp_bind(pd.Timestamp("2026-09-15T12:34:56")) == dt.datetime(
        2026, 9, 15, 12, 34, 56
    )
    assert normalize_timestamp_bind("2026-09-15T15:34:56+03:00") == dt.datetime(
        2026, 9, 15, 12, 34, 56
    )
    assert normalize_timestamp_bind(pd.NaT) is None


@pytest.mark.parametrize("table", list(MODEL))
def test_every_entity_normalizes_pandas_optimistic_lock_timestamp(table):
    executor = RecordingExecutor(existing=True)
    repo = _repo(executor)

    key, fields = MODEL[table]
    first_field = fields.split()[0]

    if table == "DIM_EFC_DATE":
        entity_id = dt.date(2026, 2, 3)
        updated_value = 2026
        expected_schema = "REPORTING"
    else:
        entity_id = f"record-{table.lower()}"
        updated_value = "Updated"
        expected_schema = "CORE"

    repo._upsert(
        table,
        {
            key: entity_id,
            first_field: updated_value,
            "EXPECTED_UPDATED_AT": pd.Timestamp(
                "2026-02-02T12:00:00"
            ),
        },
    )

    _, sql, params = next(
        call
        for call in executor.calls
        if call[0] == "execute"
    )

    assert sql.startswith(
        f"UPDATE EFNS_DEV.{expected_schema}.{table}"
    )
    assert params[-1] == dt.datetime(
        2026,
        2,
        2,
        12,
        0,
    )
    assert type(params[-1]) is dt.datetime

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


@pytest.mark.parametrize("table", list(MODEL))
def test_every_entity_delete_binds_id_and_commits(table):
    executor = RecordingExecutor()
    repo = _repo(executor)
    key = MODEL[table][0]
    assert repo._delete(table, key, "record-1") is True
    _, sql, params = next(call for call in executor.calls if call[0] == "execute")
    assert sql == f"DELETE FROM EFNS_DEV.CORE.{table} WHERE {key} = %s"
    assert params == ("record-1",)
    assert executor.commits == 1 and executor.rollbacks == 0


def test_import_write_parameter_order_and_server_timestamps():
    executor = RecordingExecutor()
    repo = _repo(executor)
    import_id = repo.create_import_batch({
        "STATUS": "Uploaded",
        "FILENAME": "synthetic.xlsx",
        "REPORTING_WEEK": 5,
    })
    _, sql, params = next(call for call in executor.calls if call[0] == "execute")
    assert "(IMPORT_ID, FILENAME, REPORTING_WEEK, STATUS, UPLOAD_TIMESTAMP, CREATED_AT, UPDATED_AT)" in sql
    assert params == (import_id, "synthetic.xlsx", 5, "Uploaded")
    assert sql.count(UTC_NOW_NTZ) == 3
    assert len(params) == sql.count("%s")

    executor.calls.clear()
    assert repo.insert_raw_rows(import_id, [{
        "SOURCE_ROW_NUMBER": 7,
        "RAW_DATA": {"optional": None},
        "VALIDATION_MESSAGES": [],
    }]) == 1
    _, raw_sql, raw_params = next(call for call in executor.calls if call[0] == "executemany")
    assert len(raw_params[0]) == raw_sql.count("%s") == 7
    assert raw_params[0][1] == import_id
    assert raw_params[0][2] == 7
    assert raw_params[0][3] == '{"optional": null}'
    assert raw_params[0][4:7] == ("PENDING", "UNMATCHED", "[]")

    executor.calls.clear()
    assert repo.insert_production_records([{
        "SOURCE_TYPE": "EIMS_IMPORT",
        "REPORTING_YEAR": 2026,
        "REPORTING_WEEK": 5,
    }], import_id) == 1
    _, production_sql, production_params = next(
        call for call in executor.calls if call[0] == "executemany"
    )
    assert len(production_params[0]) == production_sql.count("%s")
    assert production_params[0][1] == import_id
    values = dict(zip(PRODUCTION_COLUMNS, production_params[0][2:]))
    assert values["SOURCE_TYPE"] == "EIMS_IMPORT"
    assert values["MATCH_STATUS"] == "UNMATCHED"
    assert values["REPORTING_WEEK"] == 5


@pytest.mark.parametrize("value", [None, pd.NA, pd.NaT, float("nan"), "", "None", "nan", "NaN", "null"])
def test_missing_numeric_values_bind_as_python_none(value):
    assert normalize_numeric_bind(value, "FLOCK_AGE", 14, integer=True) is None


def test_numeric_strings_preserve_integer_and_decimal_semantics():
    assert normalize_numeric_bind("1,234", "FLOCK_AGE", 14, integer=True) == 1234
    assert normalize_numeric_bind("1,234.50", "TOTAL", 14, integer=False) == Decimal("1234.50")
    with pytest.raises(RepositoryError, match="FLOCK_AGE.*source row 14"):
        normalize_numeric_bind("not-a-number", "FLOCK_AGE", 14, integer=True)
    with pytest.raises(RepositoryError, match="whole number.*source row 14"):
        normalize_numeric_bind("12.5", "FLOCK_AGE", 14, integer=True)


def test_production_rows_bind_in_exact_column_order_with_typed_numbers():
    executor = RecordingExecutor()
    repo = _repo(executor)
    repo.insert_production_records([{
        "PRODUCTION_ID": "production-1",
        "SOURCE_ROW_NUMBER": "14",
        "FLOCK_AGE": "None",
        "NET_WEIGHT": float("nan"),
        "TOTAL": "1,234.50",
        "REPORTING_YEAR": 2026.0,
        "REPORTING_WEEK": "5",
        "SOURCE_TYPE": "EIMS_IMPORT",
        "MATCH_STATUS": "UNMATCHED",
    }], "import-1")
    _, sql, rows = next(call for call in executor.calls if call[0] == "executemany")
    columns = re.search(r"PRODUCTION_RECORD \((.*?)\) VALUES", sql).group(1).split(", ")[:-2]
    assert columns == ["PRODUCTION_ID", "IMPORT_ID", *PRODUCTION_COLUMNS]
    assert len(rows[0]) == sql.count("%s")
    bound = dict(zip(columns, rows[0]))
    assert bound["FLOCK_AGE"] is None
    assert bound["NET_WEIGHT"] is None
    assert bound["TOTAL"] == Decimal("1234.50")
    assert bound["REPORTING_YEAR"] == 2026
    assert bound["REPORTING_WEEK"] == 5
    assert bound["SOURCE_ROW_NUMBER"] == 14


def test_invalid_production_numeric_rolls_back_batch_and_raw_rows():
    executor = RecordingExecutor()
    repo = _repo(executor)
    with pytest.raises(RepositoryError, match="FLOCK_AGE.*source row 27"):
        repo.import_production_bundle(
            {"FILENAME": "synthetic.xlsm", "FILE_HASH": "hash-1"},
            [{"SOURCE_ROW_NUMBER": 27, "RAW_DATA": {"Flock Age": "bad"}}],
            [{
                "SOURCE_ROW_NUMBER": 27,
                "FLOCK_AGE": "bad",
                "SOURCE_TYPE": "EIMS_IMPORT",
            }],
        )
    assert executor.commits == 0
    assert executor.rollbacks == 1
    assert any(call[0] == "execute" and "IMPORT_BATCH" in call[1] for call in executor.calls)
    assert any(call[0] == "executemany" and "IMPORT_RAW_ROW" in call[1] for call in executor.calls)
    assert not any(call[0] == "executemany" and "PRODUCTION_RECORD" in call[1] for call in executor.calls)


def test_late_import_finalization_failure_rolls_back_every_prior_write():
    class FinalizationFailureExecutor(RecordingExecutor):
        def execute(self, sql, params=None):
            self.calls.append(("execute", sql, tuple(params or ())))
            if sql.startswith("UPDATE EFNS_DEV.RAW.IMPORT_BATCH"):
                raise RepositoryError("safe finalization failure")
            return self.affected

    executor = FinalizationFailureExecutor()
    repo = _repo(executor)
    with pytest.raises(RepositoryError, match="safe finalization failure"):
        repo.import_production_bundle(
            {"FILENAME": "synthetic.xlsm", "FILE_HASH": "hash-late-failure"},
            [{"SOURCE_ROW_NUMBER": 14, "RAW_DATA": {"synthetic": True}}],
            [{
                "PRODUCTION_ID": "DEV_VERIFY_PRODUCTION_ROLLBACK_1",
                "SOURCE_ROW_NUMBER": 14,
                "FLOCK_AGE": None,
                "SOURCE_TYPE": "EIMS_IMPORT",
                "MATCH_STATUS": "UNMATCHED",
            }],
        )
    assert executor.commits == 0 and executor.rollbacks == 1
    assert any(call[0] == "executemany" and "IMPORT_RAW_ROW" in call[1] for call in executor.calls)
    assert any(call[0] == "executemany" and "PRODUCTION_RECORD" in call[1] for call in executor.calls)


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


def test_quota_summary_orders_distinct_results_by_projected_aliases():
    executor = RecordingExecutor()
    repo = _repo(executor)
    repo.get_quota_summary(dt.date(2026, 9, 15), "Egg Production", status="Active")
    _, sql, params = next(call for call in executor.calls if call[0] == "query")
    assert "SELECT DISTINCT" in sql
    assert "ORDER BY ACCOUNT_NAME, REGISTRATION_NUMBER, QUOTA_ID" in sql
    assert "ORDER BY a.ORGANIZATION_NAME" not in sql
    assert params == (
        "Egg Production",
        dt.date(2026, 9, 15),
        dt.date(2026, 9, 15),
        "Active",
    )


@pytest.mark.parametrize("value", [None, pd.NaT, "", "  ", "None", "NaT", "null", " NULL "])
def test_optional_date_sentinels_bind_as_python_none(value):
    normalized = normalize_date_bind(value, "EST_DISPOSAL")
    assert normalized is None
    assert normalized not in {"None", "NaT", "null"}


def test_date_and_datetime_values_bind_as_dates():
    expected = dt.date(2026, 9, 14)
    assert normalize_date_bind(expected) == expected
    assert normalize_date_bind(dt.datetime(2026, 9, 14, 15, 30)) == expected
    assert normalize_date_bind(pd.Timestamp("2026-09-14T15:30:00Z")) == expected
    assert normalize_date_bind("2026-09-14") == expected
    with pytest.raises(RepositoryError, match="valid ISO date"):
        normalize_date_bind("September someday", "HATCH_DATE")


def test_flock_create_binds_unset_optional_dates_as_sql_null():
    executor = RecordingExecutor()
    repo = _repo(executor)
    repo.get_facilities = lambda account_id=None: pd.DataFrame([
        {"ACCOUNT_ID": "account-1", "FACILITY_ID": "facility-1"}
    ])
    repo.get_facility_details = lambda facility_id=None: pd.DataFrame()
    repo.get_quota_registrations = lambda **kwargs: pd.DataFrame()
    class AuditStore:
        def __init__(self):
            self.events = []

        def record_action(self, *event):
            self.events.append(event)

    store = AuditStore()
    actor = User(
        "editor-1", "editor@nsegg.ca", "Editor", Role.DATA_EDITOR, True,
        False, "2026-01-01", "2026-01-01", None,
    )
    authorized = AuthorizedRepository(repo, store, actor)
    result = authorized.upsert_flock({
        "FLOCK_NUMBER": "DEV-FLOCK-1",
        "ACCOUNT_ID": "account-1",
        "FACILITY_ID": "facility-1",
        "PERMIT_NUMBER": "DEV-PERMIT-1",
        "HATCH_DATE": dt.datetime(2026, 9, 14, 8, 0),
        "BIRD_COUNT": 100,
        "PERMIT_DATE": "",
        "DATE_ORDERED": "None",
        "PLACEMENT_DATE": pd.NaT,
        "EST_DISPOSAL": "None",
        "DISPOSAL_DATE": None,
    })
    _, sql, params = next(call for call in executor.calls if call[0] == "execute")
    fields = re.search(r"FLOCK \((.*?)\) VALUES", sql).group(1).split(", ")[:-2]
    bound = dict(zip(fields, params))
    assert bound["FLOCK_ID"] == result
    assert bound["HATCH_DATE"] == dt.date(2026, 9, 14)
    for field in ("PERMIT_DATE", "DATE_ORDERED", "PLACEMENT_DATE", "EST_DISPOSAL", "DISPOSAL_DATE"):
        assert bound[field] is None
    assert len(params) == sql.count("%s")
    assert store.events[0][1:4] == ("CREATE", "FLOCK", result)


@pytest.mark.parametrize("table,field", [
    (table, field) for table, fields in DATE_FIELDS.items() for field in fields
])
def test_all_snowflake_date_fields_share_the_same_null_normalizer(table, field):
    normalized = SnowflakeRepository._normalize_date_fields(table, {field: "NaT"})
    assert normalized[field] is None


def test_required_flock_date_validation_remains_enforced():
    executor = RecordingExecutor()
    repo = _repo(executor)
    repo.get_facilities = lambda account_id=None: pd.DataFrame([
        {"ACCOUNT_ID": "account-1", "FACILITY_ID": "facility-1"}
    ])
    repo.get_facility_details = lambda facility_id=None: pd.DataFrame()
    repo.get_quota_registrations = lambda **kwargs: pd.DataFrame()
    with pytest.raises(RepositoryError, match="Hatch Date is required"):
        repo.upsert_flock({
            "FLOCK_NUMBER": "DEV-FLOCK-2",
            "ACCOUNT_ID": "account-1",
            "FACILITY_ID": "facility-1",
            "PERMIT_NUMBER": "DEV-PERMIT-2",
            "HATCH_DATE": "None",
            "BIRD_COUNT": 100,
        })
    assert not any(call[0] == "execute" for call in executor.calls)


def test_mock_repository_accepts_typed_and_unset_flock_dates():
    repo = MockRepository(seed=17)
    account = repo.get_accounts().iloc[0]
    facility = repo.get_facilities(account_id=account["ACCOUNT_ID"]).iloc[0]
    result = repo.upsert_flock({
        "FLOCK_NUMBER": "MOCK-DATE-COMPAT",
        "ACCOUNT_ID": account["ACCOUNT_ID"],
        "FACILITY_ID": facility["FACILITY_ID"],
        "PERMIT_NUMBER": "MOCK-PERMIT",
        "HATCH_DATE": dt.date(2026, 9, 14),
        "EST_DISPOSAL": None,
        "BIRD_COUNT": 25,
    })
    saved = repo.get_flock(result)
    assert saved["HATCH_DATE"] == dt.date(2026, 9, 14)
    assert saved["EST_DISPOSAL"] is None

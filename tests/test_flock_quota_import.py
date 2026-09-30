"""Focused coverage for routine Flock and Quota workbook imports."""

from __future__ import annotations

from contextlib import contextmanager
import datetime as dt
from io import BytesIO

import pandas as pd
import pytest
from openpyxl import Workbook

from app.security import Role, User
from app.services.authorized_repository import AuthorizedRepository
from data.flock_quota_import import (
    EXPECTED_HEADERS,
    WorkbookImportError,
    parse_flock_quota_workbook,
    validate_flock_quota_batch,
)
from data.repositories.base import RepositoryError
from data.repositories.mock import MockRepository
from data.repositories.snowflake import SnowflakeRepository
from data.validation import normalize_flock_dates


def _workbook_bytes(rows, headers=EXPECTED_HEADERS, sheet_name="Batch Import"):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = sheet_name
    worksheet.append(list(headers))
    for row in rows:
        worksheet.append([row.get(header) for header in headers])
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _context(repo):
    account = repo.get_accounts().iloc[0]
    facility = repo.get_facilities(account_id=account["ACCOUNT_ID"]).iloc[0]
    return account, facility


def _quota_row(repo, suffix="001"):
    account, _ = _context(repo)
    return {
        "BATCH_ID": "DEV_DEMO_BATCH_001",
        "RECORD_TYPE": "QUOTA_REGISTRATION",
        "ACTION": "CREATE",
        "ACCOUNT": account["ORGANIZATION_NAME"],
        "REGISTRATION_NUMBER": f"DEV_DEMO_QUOTA_{suffix}",
        "QUOTA_NAME": f"Demo Quota {suffix}",
        "QUOTA_TYPE": "Egg Production",
        "EFFECTIVE_DATE": dt.date.today(),
    }


def _flock_row(repo, quota_suffix="001", flock_suffix="001"):
    account, facility = _context(repo)
    return {
        "BATCH_ID": "DEV_DEMO_BATCH_001",
        "RECORD_TYPE": "FLOCK",
        "ACTION": "CREATE",
        "ACCOUNT": account["ORGANIZATION_NAME"],
        "FACILITY": facility["FACILITY_NAME"],
        "FACILITY_DETAIL": "Unassigned",
        "QUOTA_REGISTRATION": f"DEV_DEMO_QUOTA_{quota_suffix}",
        "FLOCK_QUOTA_TYPE": "Egg Production",
        "FLOCK_NUMBER": f"DEV_DEMO_FLOCK_{flock_suffix}",
        "FLOCK_STATUS": "Planned",
        "CREATE_DELIVERY_TRANSACTION": False,
        "PERMIT_NUMBER": f"DEV_DEMO_PERMIT_{flock_suffix}",
        "HATCH_DATE": dt.date.today(),
        "BIRD_COUNT": 100,
        "EGG_COLOUR": "White",
        "BIRDS_DISPOSED": 0,
    }


def _report(repo, rows, headers=EXPECTED_HEADERS):
    parsed = parse_flock_quota_workbook(_workbook_bytes(rows, headers), "batch.xlsx")
    return validate_flock_quota_batch(parsed, repo)


def test_valid_mixed_workbook_resolves_same_batch_quota_first():
    repo = MockRepository(seed=2)
    report = _report(repo, [_flock_row(repo), _quota_row(repo)])
    assert report.can_import
    assert len(report.quota_records) == 1
    assert len(report.flock_records) == 1
    assert report.flock_records[0]["QUOTA_ID"] == report.quota_records[0]["QUOTA_ID"]


def test_identifier_text_is_preserved():
    repo = MockRepository(seed=2)
    row = _flock_row(repo)
    row["FLOCK_NUMBER"] = "DEV_DEMO_FLOCK_0007"
    row["PERMIT_NUMBER"] = "DEV_DEMO_PERMIT_0007"
    report = _report(repo, [_quota_row(repo), row])
    assert report.flock_records[0]["FLOCK_NUMBER"].endswith("0007")
    assert report.flock_records[0]["PERMIT_NUMBER"].endswith("0007")


def test_missing_batch_import_sheet_is_rejected():
    with pytest.raises(WorkbookImportError, match="Batch Import"):
        parse_flock_quota_workbook(_workbook_bytes([], sheet_name="Wrong"), "wrong.xlsx")


def test_missing_and_duplicate_headers_are_reported():
    repo = MockRepository(seed=2)
    missing = tuple(header for header in EXPECTED_HEADERS if header != "ACTION")
    report = _report(repo, [_quota_row(repo)], missing)
    assert any("Missing required headers: ACTION" in message for message in report.global_errors)

    duplicate = (*EXPECTED_HEADERS, "BATCH_ID")
    parsed = parse_flock_quota_workbook(_workbook_bytes([_quota_row(repo)], duplicate), "duplicate.xlsx")
    assert any("Duplicate headers: BATCH_ID" in message for message in parsed.global_errors)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("RECORD_TYPE", "OTHER", "RECORD_TYPE"),
        ("ACTION", "DELETE", "ACTION"),
        ("HATCH_DATE", "not-a-date", "Hatch Date"),
        ("BIRD_COUNT", "12.5", "Bird Count"),
        ("BIRD_COUNT", -1, "cannot be negative"),
    ],
)
def test_row_level_validation_errors(field, value, message):
    repo = MockRepository(seed=2)
    row = _flock_row(repo)
    row[field] = value
    report = _report(repo, [_quota_row(repo), row])
    assert not report.can_import
    assert any(message in item.message for item in report.rows)


def test_missing_hatch_date_is_rejected():
    repo = MockRepository(seed=2)
    row = _flock_row(repo)
    row["HATCH_DATE"] = None
    report = _report(repo, [_quota_row(repo), row])
    assert any("Hatch Date is required" in item.message for item in report.rows)


@pytest.mark.parametrize("field", ["REGISTRATION_NUMBER", "FLOCK_NUMBER", "PERMIT_NUMBER"])
def test_duplicate_business_identifiers_inside_workbook(field):
    repo = MockRepository(seed=2)
    if field == "REGISTRATION_NUMBER":
        rows = [_quota_row(repo), _quota_row(repo)]
    else:
        first = _flock_row(repo)
        second = _flock_row(repo, flock_suffix="002")
        second[field] = first[field]
        rows = [_quota_row(repo), first, second]
    report = _report(repo, rows)
    assert any("duplicated inside this workbook" in item.message for item in report.rows)


def test_account_and_facility_relationship_failures_are_rejected():
    repo = MockRepository(seed=2)
    row = _flock_row(repo)
    row["ACCOUNT"] = "missing account"
    report = _report(repo, [_quota_row(repo), row])
    assert any("Account was not found" in item.message for item in report.rows)

    accounts = repo.get_accounts().head(2)
    foreign_facility = repo.get_facilities(account_id=accounts.iloc[1]["ACCOUNT_ID"]).iloc[0]
    row = _flock_row(repo)
    row["FACILITY"] = foreign_facility["FACILITY_NAME"]
    report = _report(repo, [_quota_row(repo), row])
    assert any("Facility was not found" in item.message for item in report.rows)


def test_missing_quota_relationship_is_rejected():
    repo = MockRepository(seed=2)
    row = _flock_row(repo)
    row["QUOTA_REGISTRATION"] = "DEV_DEMO_QUOTA_MISSING"
    report = _report(repo, [row])
    assert any("Quota Registration was not found" in item.message for item in report.rows)


def test_duplicate_file_hash_is_rejected():
    repo = MockRepository(seed=2)
    batch = {"FILENAME": "batch.xlsx", "FILE_HASH": "same", "BATCH_ID": "DEV_DEMO_BATCH_001"}
    repo.import_flock_quota_batch(batch, [], [])
    with pytest.raises(ValueError, match="already been imported"):
        repo.import_flock_quota_batch(batch, [], [])


class _RecordingRepository(MockRepository):
    def __init__(self, *args, fail_flock=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.order = []
        self.fail_flock = fail_flock

    def upsert_quota_registration(self, record):
        self.order.append("quota")
        return super().upsert_quota_registration(record)

    def upsert_flock(self, record):
        self.order.append("flock")
        if self.fail_flock:
            raise ValueError("injected flock failure")
        return super().upsert_flock(record)


def test_quota_writes_precede_flocks_and_failure_rolls_back_all_rows():
    repo = _RecordingRepository(seed=2)
    report = _report(repo, [_flock_row(repo), _quota_row(repo)])
    result = repo.import_flock_quota_batch(
        {"FILENAME": "batch.xlsx", "FILE_HASH": "one", "BATCH_ID": report.batch_id},
        report.quota_records,
        report.flock_records,
    )
    assert repo.order == ["quota", "flock"]
    assert result["total_count"] == 2

    failing = _RecordingRepository(seed=2, fail_flock=True)
    report = _report(failing, [_quota_row(failing), _flock_row(failing)])
    before_quotas = len(failing.get_quota_registrations())
    before_flocks = len(failing.get_flocks())
    with pytest.raises(ValueError, match="injected flock failure"):
        failing.import_flock_quota_batch(
            {"FILENAME": "batch.xlsx", "FILE_HASH": "two", "BATCH_ID": report.batch_id},
            report.quota_records,
            report.flock_records,
        )
    assert len(failing.get_quota_registrations()) == before_quotas
    assert len(failing.get_flocks()) == before_flocks
    assert failing.find_import_by_hash("two") is None


class _AuditStore:
    def __init__(self):
        self.events = []

    def record_action(self, *args):
        self.events.append(args)


class _FailingAuditStore(_AuditStore):
    def record_action(self, *args):
        raise RuntimeError("audit unavailable")


def _user(role):
    return User("u1", "user@nsegg.ca", "User", role, True, False, "now", "now", None)


def test_reporting_viewer_cannot_call_batch_write_and_success_is_audited():
    repo = MockRepository(seed=2)
    batch = {"FILENAME": "batch.xlsx", "FILE_HASH": "permission", "BATCH_ID": "DEV_DEMO_BATCH_001"}
    store = _AuditStore()
    viewer = AuthorizedRepository(repo, store, _user(Role.REPORTING_VIEWER))
    with pytest.raises(RepositoryError, match="permission"):
        viewer.import_flock_quota_batch(batch, [], [])
    assert not store.events

    editor = AuthorizedRepository(repo, store, _user(Role.DATA_EDITOR))
    editor.import_flock_quota_batch(batch, [], [])
    assert len(store.events) == 1
    assert store.events[0][1:3] == ("IMPORT", "FLOCK_QUOTA_IMPORT")


def test_audit_failure_does_not_misreport_successful_core_commit():
    repo = MockRepository(seed=2)
    wrapped = AuthorizedRepository(repo, _FailingAuditStore(), _user(Role.DATA_EDITOR))
    result = wrapped.import_flock_quota_batch(
        {"FILENAME": "batch.xlsx", "FILE_HASH": "audit-failure", "BATCH_ID": "DEV_DEMO_BATCH_001"},
        [],
        [],
    )
    assert result["status"] == "Committed"
    assert result["audit_recorded"] is False
    assert repo.find_import_by_hash("audit-failure") is not None


def test_empty_optional_flock_dates_normalize_to_python_none():
    record = normalize_flock_dates(
        {
            "PERMIT_DATE": "None",
            "HATCH_DATE": dt.date(2026, 9, 1),
            "DATE_ORDERED": "",
            "PLACEMENT_DATE": "NULL",
            "EST_DISPOSAL": pd.NaT,
            "DISPOSAL_DATE": None,
        }
    )
    assert record["HATCH_DATE"] == dt.date(2026, 9, 1)
    assert all(
        record[field] is None
        for field in ("PERMIT_DATE", "DATE_ORDERED", "PLACEMENT_DATE", "EST_DISPOSAL", "DISPOSAL_DATE")
    )


class _CaptureExecutor:
    runtime_name = "Test"

    def __init__(self):
        self.calls = []

    @contextmanager
    def transaction(self):
        yield self

    def execute(self, sql, params=None):
        self.calls.append((sql, tuple(params or ())))
        return 0 if sql.startswith("UPDATE") else 1

    def query(self, sql, params=None):
        self.calls.append((sql, tuple(params or ())))
        return pd.DataFrame()


class _BatchExecutor(_CaptureExecutor):
    def __init__(self, account_id, facility_id, fail_flock=False):
        super().__init__()
        self.account_id = account_id
        self.facility_id = facility_id
        self.fail_flock = fail_flock
        self.transactions = 0
        self.rollbacks = 0

    @contextmanager
    def transaction(self):
        self.transactions += 1
        try:
            yield self
        except Exception:
            self.rollbacks += 1
            raise

    def execute(self, sql, params=None):
        values = tuple(params or ())
        self.calls.append((sql, values))
        if self.fail_flock and "INSERT INTO EFNS_DEV.CORE.FLOCK " in sql:
            raise RepositoryError("injected flock failure")
        return 0 if sql.startswith("UPDATE") else 1

    def query(self, sql, params=None):
        values = tuple(params or ())
        self.calls.append((sql, values))
        if sql.startswith("SELECT UPDATED_AT"):
            return pd.DataFrame()
        if "FROM EFNS_DEV.CORE.ACCOUNT WHERE ACCOUNT_ID" in sql:
            return pd.DataFrame({"ACCOUNT_ID": [self.account_id]})
        if "FROM EFNS_DEV.CORE.FACILITY WHERE FACILITY_ID" in sql:
            return pd.DataFrame({"ACCOUNT_ID": [self.account_id]})
        if sql.startswith(
            "SELECT ACCOUNT_ID FROM EFNS_DEV.CORE.QUOTA_REGISTRATION WHERE QUOTA_ID"
        ):
            return pd.DataFrame({"ACCOUNT_ID": [self.account_id]})
        return pd.DataFrame()


def test_manual_flock_insert_keeps_21_bound_parameters_in_model_order(monkeypatch):
    executor = _CaptureExecutor()
    repo = SnowflakeRepository(executor=executor)
    monkeypatch.setattr("data.repositories.snowflake.validate_flock", lambda repository, record: [])
    hatch = dt.date(2026, 9, 1)
    repo.upsert_flock(
        {
            "FLOCK_ID": "flock-id",
            "FLOCK_NUMBER": "DEV_DEMO_FLOCK_001",
            "ACCOUNT_ID": "account-id",
            "FACILITY_ID": "facility-id",
            "FACILITY_DETAIL_ID": None,
            "QUOTA_ID": None,
            "FLOCK_QUOTA_TYPE": "Egg Production",
            "STATUS": "Planned",
            "CREATE_DELIVERY_TRANSACTION": False,
            "PERMIT_NUMBER": "DEV_DEMO_PERMIT_001",
            "PERMIT_DATE": "None",
            "HATCH_DATE": hatch,
            "DATE_ORDERED": "",
            "BIRD_COUNT": 100,
            "EGG_COLOUR": "White",
            "BIRD_STRAIN": None,
            "PLACEMENT_DATE": "NULL",
            "EST_DISPOSAL": pd.NaT,
            "DISPOSAL_DATE": None,
            "BIRDS_DISPOSED": 0,
            "COMMENTS": None,
        }
    )
    insert_sql, params = next(call for call in executor.calls if call[0].startswith("INSERT"))
    assert insert_sql.count("%s") == 21
    assert len(params) == 21
    assert params[0] == "flock-id"
    assert params[9] == "DEV_DEMO_PERMIT_001"
    assert params[10] is None
    assert params[11] == hatch
    assert params[12] is None
    assert params[16] is None
    assert params[17] is None
    assert params[18] is None


def test_snowflake_batch_uses_one_transaction_orders_writes_and_rolls_back():
    source = MockRepository(seed=2)
    report = _report(source, [_flock_row(source), _quota_row(source)])
    account_id = report.quota_records[0]["ACCOUNT_ID"]
    facility_id = report.flock_records[0]["FACILITY_ID"]
    batch = {
        "FILENAME": "batch.xlsx",
        "FILE_HASH": "snowflake-batch",
        "BATCH_ID": report.batch_id,
    }

    executor = _BatchExecutor(account_id, facility_id)
    repo = SnowflakeRepository(executor=executor)
    result = repo.import_flock_quota_batch(batch, report.quota_records, report.flock_records)
    inserts = [sql for sql, _ in executor.calls if sql.startswith("INSERT INTO")]
    quota_index = next(index for index, sql in enumerate(inserts) if "CORE.QUOTA_REGISTRATION" in sql)
    flock_index = next(index for index, sql in enumerate(inserts) if "CORE.FLOCK " in sql)
    batch_index = next(index for index, sql in enumerate(inserts) if "RAW.IMPORT_BATCH" in sql)
    assert executor.transactions == 1
    assert quota_index < flock_index < batch_index
    assert result["total_count"] == 2

    failing = _BatchExecutor(account_id, facility_id, fail_flock=True)
    repo = SnowflakeRepository(executor=failing)
    with pytest.raises(RepositoryError, match="injected flock failure"):
        repo.import_flock_quota_batch(
            {**batch, "FILE_HASH": "snowflake-failure"},
            report.quota_records,
            report.flock_records,
        )
    assert failing.transactions == 1
    assert failing.rollbacks == 1

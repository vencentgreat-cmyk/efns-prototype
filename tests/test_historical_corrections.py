"""Focused coverage for confirmed historical EIMS correction rules."""

from __future__ import annotations

from pathlib import Path
from copy import deepcopy

import pandas as pd
import pytest

from data.historical_corrections import (
    PENDING_CONFIRMATION,
    ALREADY_COMMITTED,
    READY_CORE,
    build_historical_correction_preview,
)
from data.migration import load_mapping
from data.repositories.mock import MockRepository
from data.validation import validate_quota_registration


BATCH_ID = "DEV_MIGRATION_SYNTHETIC_CORRECTION"


def _raw(entity: str, row_id: str, source_row: int, values: dict) -> dict:
    spec = load_mapping()["entities"][entity]
    payload = {}
    for target, value in values.items():
        source = spec.get("field_map", {}).get(target)
        if source:
            payload[source.upper()] = value
    return {
        "MIGRATION_RAW_ROW_ID": row_id,
        "MIGRATION_BATCH_ID": BATCH_ID,
        "SOURCE_FILENAME": spec["filename"],
        "SOURCE_ENTITY": entity,
        "SOURCE_ROW_NUMBER": source_row,
        "SOURCE_ID": values.get(spec["id_field"]),
        "TARGET_ID": None,
        "RAW_DATA": payload,
        "NORMALIZED_DATA": None,
        "VALIDATION_STATUS": "REJECTED",
        "MATCH_STATUS": "NO_CANDIDATE",
        "VALIDATION_MESSAGES": ["Synthetic historical rejection."],
    }


def _rows() -> list[dict]:
    return [
        _raw("QUOTA_REGISTRATION", "raw-quota", 2, {
            "QUOTA_ID": "quota-new", "REGISTRATION_NUMBER": None,
            "ACCOUNT_ID": "account-a", "QUOTA_NAME": "Historical quota", "QUOTA_TYPE": "Layer",
        }),
        _raw("SALMONELLA_TEST", "raw-test", 3, {
            "SALMONELLA_TEST_ID": "test-new", "FLOCK_ID": "flock-existing",
            "ACCOUNT_ID": "account-b", "PERMIT_NUMBER": "P-1", "TESTING_DATE": "2025-01-03",
        }),
        _raw("FLOCK", "raw-flock", 4, {
            "FLOCK_ID": "flock-conflict", "FLOCK_NUMBER": "F-2", "ACCOUNT_ID": "account-b",
            "FACILITY_ID": "facility-a", "PERMIT_NUMBER": "P-2", "HATCH_DATE": "2025-01-01",
            "BIRD_COUNT": "10",
        }),
        _raw("FLOCK_TRANSACTION", "raw-flock-tx", 5, {
            "FLOCK_TRANSACTION_ID": "flock-tx-pending", "FLOCK_ID": "flock-conflict",
            "TRANSACTION_TYPE": "Placement", "QUANTITY": "10", "TRANSACTION_DATE": "2025-01-04",
        }),
        _raw("QUOTA_TRANSACTION", "raw-quota-tx-ready", 6, {
            "QUOTA_TRANSACTION_ID": "quota-tx-ready", "TRANSACTION_TYPE": "Allocation",
            "QUOTA_ID": "quota-new", "EFFECTIVE_DATE": "2025-01-05", "QUOTA_COUNT": "5",
        }),
        _raw("QUOTA_TRANSACTION", "raw-quota-tx-parent", 7, {
            "QUOTA_TRANSACTION_ID": "quota-tx-pending", "TRANSACTION_TYPE": "Allocation",
            "QUOTA_ID": None, "EFFECTIVE_DATE": "2025-01-06", "QUOTA_COUNT": "2",
        }),
        _raw("QUOTA_TRANSACTION", "raw-quota-tx-child", 8, {
            "QUOTA_TRANSACTION_ID": "quota-tx-child", "TRANSACTION_TYPE": "Transfer",
            "QUOTA_ID": "quota-new", "EFFECTIVE_DATE": "2025-01-07", "QUOTA_COUNT": "1",
            "RELATED_TRANSACTION_ID": "quota-tx-pending",
        }),
    ]


def _context():
    return {
        "ACCOUNT": {"account-a", "account-b"},
        "FLOCK": {"flock-existing"},
        "QUOTA_REGISTRATION": {"quota-existing"},
        "QUOTA_TRANSACTION": {"quota-tx-existing"},
        "SALMONELLA_TEST": set(),
    }, {"quota-existing": "account-a"}


def test_confirmed_historical_rules_recover_only_safe_core_rows():
    existing, owners = _context()
    preview = build_historical_correction_preview(
        BATCH_ID, _rows(), existing, quota_accounts=owners,
    )

    ready = {row["SOURCE_ID"] for row in preview.rows if row["DISPOSITION"] == READY_CORE}
    pending = {row["SOURCE_ID"] for row in preview.rows if row["DISPOSITION"] == PENDING_CONFIRMATION}
    assert ready == {"quota-new", "test-new", "quota-tx-ready"}
    assert pending == {"flock-conflict", "flock-tx-pending", "quota-tx-pending", "quota-tx-child"}
    assert all(row["RELATION_STATUS"] == "UNVERIFIED" for row in preview.pending_rows)
    quota = next(row for row in preview.core_rows if row["SOURCE_ENTITY"] == "QUOTA_REGISTRATION")
    assert quota["CORRECTED_DATA"]["REGISTRATION_NUMBER"] is None
    assert quota["TARGET_ID"] == "quota-new"
    pending_review = preview.review_frame[
        preview.review_frame["DISPOSITION"] == PENDING_CONFIRMATION
    ]
    assert set(pending_review) >= {
        "SOURCE_FILENAME", "SOURCE_ROW_NUMBER", "MIGRATION_RAW_ROW_ID",
        "ORIGINAL_VALIDATION_MESSAGES", "FLOCK_ID", "QUOTA_ID",
        "RELATED_TRANSACTION_ID",
    }
    assert pending_review["ORIGINAL_VALIDATION_MESSAGES"].map(bool).all()


def _repository() -> MockRepository:
    repo = MockRepository(seed=123)
    repo._accounts = pd.DataFrame([
        {"ACCOUNT_ID": "account-a", "ORGANIZATION_NAME": "Synthetic A"},
        {"ACCOUNT_ID": "account-b", "ORGANIZATION_NAME": "Synthetic B"},
    ])
    repo._flocks = pd.DataFrame([{"FLOCK_ID": "flock-existing", "ACCOUNT_ID": "account-a"}])
    repo._quota_registrations = pd.DataFrame([
        {"QUOTA_ID": "quota-existing", "ACCOUNT_ID": "account-a", "REGISTRATION_NUMBER": "Q-1"}
    ])
    repo._quota_transactions = pd.DataFrame(columns=["QUOTA_TRANSACTION_ID"])
    repo._salmonella_tests = pd.DataFrame(columns=["SALMONELLA_TEST_ID"])
    repo._flock_transactions = pd.DataFrame(columns=["FLOCK_TRANSACTION_ID"])
    repo._migration_batches = [{"MIGRATION_BATCH_ID": BATCH_ID, "STATUS": "COMMITTED"}]
    repo._migration_raw_rows = _rows()
    return repo


def test_correction_commit_is_separate_idempotent_and_keeps_pending_rows():
    repo = _repository()

    result = repo.commit_historical_corrections(BATCH_ID)
    repeated = repo.commit_historical_corrections(BATCH_ID)
    status = repo.get_historical_correction_status(BATCH_ID)

    assert sum(result["counts"].values()) == 3
    assert result["pending_count"] == 4
    assert repeated["idempotent"] is True
    assert status["STATUS"] == "COMMITTED_WITH_PENDING"
    assert status["READY_ROW_COUNT"] == 3
    assert status["PENDING_ROW_COUNT"] == 4
    assert status["COMMITTED_AT"] is not None
    assert len(repo._migration_raw_rows) == 7
    assert repo._migration_batches[0]["STATUS"] == "COMMITTED"
    assert set(repo._migration_correction_rows[0]) >= {
        "ORIGINAL_MIGRATION_BATCH_ID", "MIGRATION_RAW_ROW_ID", "RELATION_STATUS",
    }


def test_correction_commit_rolls_back_core_and_tracking_on_failure(monkeypatch):
    repo = _repository()
    original = repo._upsert_frame

    def fail_on_salmonella(attribute, key, record):
        if attribute == "_salmonella_tests":
            raise RuntimeError("synthetic write failure")
        return original(attribute, key, record)

    monkeypatch.setattr(repo, "_upsert_frame", fail_on_salmonella)

    with pytest.raises(RuntimeError, match="synthetic write failure"):
        repo.commit_historical_corrections(BATCH_ID)

    assert "quota-new" not in set(repo._quota_registrations["QUOTA_ID"].astype(str))
    assert repo._migration_correction_batches == []
    assert repo._migration_correction_rows == []


def test_daily_quota_validation_remains_strict_while_v3_history_is_nullable():
    mapping = load_mapping()
    assert "REGISTRATION_NUMBER" not in mapping["entities"]["QUOTA_REGISTRATION"]["required"]
    assert mapping["entities"]["SALMONELLA_TEST"]["allow_account_mismatch"] is True
    repo = _repository()
    errors = validate_quota_registration(repo, {
        "ACCOUNT_ID": "account-a", "REGISTRATION_NUMBER": None,
        "QUOTA_TYPE": "Layer", "EFFECTIVE_DATE": pd.Timestamp("2025-01-01").date(),
    })
    assert "Registration Number is required." in errors


def test_committed_page_labels_old_errors_as_history_and_hides_repeat_commit():
    source = (
        Path(__file__).resolve().parents[1] / "app" / "pages" / "17_Migration_Import.py"
    ).read_text(encoding="utf-8")

    assert "Historical failed attempts retained for audit." in source
    assert 'if batch_status == "COMMITTED"' in source
    assert 'if correction_preview.core_rows:' in source
    assert 'len(correction_preview.committed_rows)' in source


def test_committed_targets_are_separate_from_eligible_and_pending_rows():
    repo = _repository()
    repo.commit_historical_corrections(BATCH_ID)
    preview = repo.preview_historical_corrections(BATCH_ID)
    assert len(preview.committed_rows) == 3
    assert len(preview.core_rows) == 0
    assert len(preview.pending_rows) == 4
    assert {row["DISPOSITION"] for row in preview.committed_rows} == {ALREADY_COMMITTED}


def test_followup_correction_is_separate_retry_safe_and_preserves_original_history():
    repo = _repository()
    repo.commit_historical_corrections(BATCH_ID)
    initial_batch = deepcopy(repo._migration_correction_batches[0])
    initial_tracking = deepcopy(repo._migration_correction_rows)
    initial_raw = deepcopy(repo._migration_raw_rows)
    repo._flocks = pd.concat([
        repo._flocks, pd.DataFrame([{"FLOCK_ID": "flock-conflict", "ACCOUNT_ID": "account-b"}]),
    ], ignore_index=True)
    preview = repo.preview_historical_corrections(BATCH_ID)
    assert len(preview.core_rows) == 1
    assert preview.core_rows[0]["SOURCE_ID"] == "flock-tx-pending"
    assert preview.correction_batch_id != initial_batch["MIGRATION_CORRECTION_BATCH_ID"]
    assert repo.preview_historical_corrections(BATCH_ID).correction_batch_id == preview.correction_batch_id
    result = repo.commit_historical_corrections(BATCH_ID)
    repeated = repo.commit_historical_corrections(BATCH_ID)
    assert sum(result["counts"].values()) == 1
    assert result["pending_count"] == 3
    assert repeated["idempotent"] is True and repeated["counts"] == {}
    assert repo._migration_correction_batches[0] == initial_batch
    assert repo._migration_correction_rows[:len(initial_tracking)] == initial_tracking
    assert repo._migration_raw_rows == initial_raw
    assert repo._flock_transactions["FLOCK_TRANSACTION_ID"].tolist() == ["flock-tx-pending"]
    all_tracking_ids = [row["MIGRATION_CORRECTION_ROW_ID"] for row in repo._migration_correction_rows]
    assert len(all_tracking_ids) == len(set(all_tracking_ids))
    latest = repo.preview_historical_corrections(BATCH_ID)
    assert len(latest.committed_rows) == 4 and not latest.core_rows


def test_followup_write_failure_rolls_back_without_changing_committed_round(monkeypatch):
    repo = _repository()
    repo.commit_historical_corrections(BATCH_ID)
    before_batches = deepcopy(repo._migration_correction_batches)
    before_rows = deepcopy(repo._migration_correction_rows)
    repo._flocks = pd.concat([
        repo._flocks, pd.DataFrame([{"FLOCK_ID": "flock-conflict", "ACCOUNT_ID": "account-b"}]),
    ], ignore_index=True)
    original = repo._upsert_frame

    def fail(attribute, key, record):
        if attribute == "_flock_transactions":
            raise RuntimeError("synthetic followup failure")
        return original(attribute, key, record)

    monkeypatch.setattr(repo, "_upsert_frame", fail)
    with pytest.raises(RuntimeError, match="synthetic followup failure"):
        repo.commit_historical_corrections(BATCH_ID)
    assert repo._migration_correction_batches == before_batches
    assert repo._migration_correction_rows == before_rows
    assert repo._flock_transactions.empty


def test_missing_committed_target_is_an_integrity_issue_not_a_repeat_insert():
    repo = _repository()
    repo.commit_historical_corrections(BATCH_ID)
    repo._quota_registrations = repo._quota_registrations[
        repo._quota_registrations["QUOTA_ID"] != "quota-new"
    ].copy()
    preview = repo.preview_historical_corrections(BATCH_ID)
    row = next(row for row in preview.rows if row["SOURCE_ID"] == "quota-new")
    assert row["DISPOSITION"] == PENDING_CONFIRMATION
    assert "missing from CORE" in row["REASON"]
    assert not preview.core_rows


def test_existing_guid_without_correction_trace_is_not_silently_reused():
    repo = _repository()
    repo._salmonella_tests = pd.DataFrame([{"SALMONELLA_TEST_ID": "test-new"}])
    row = next(row for row in repo.preview_historical_corrections(BATCH_ID).rows if row["SOURCE_ID"] == "test-new")
    assert row["DISPOSITION"] == PENDING_CONFIRMATION
    assert "without a committed correction trace" in row["REASON"]


def test_committed_trace_pointing_to_a_different_source_is_not_counted_as_resolved():
    repo = _repository()
    repo.commit_historical_corrections(BATCH_ID)
    saved = next(row for row in repo._migration_correction_rows if row["SOURCE_ID"] == "test-new")
    saved["TARGET_ID"] = "flock-existing"
    row = next(row for row in repo.preview_historical_corrections(BATCH_ID).rows if row["SOURCE_ID"] == "test-new")
    assert row["DISPOSITION"] == PENDING_CONFIRMATION
    assert "identifiers do not match" in row["REASON"]


def test_snowflake_followup_failure_rolls_back_core_and_tracking(monkeypatch):
    from data.connection import SnowparkExecutor
    from data.repositories.snowflake import SnowflakeRepository
    from tests.test_connection import FakeSession, FakeStatement
    repo = _repository()
    repo.commit_historical_corrections(BATCH_ID)
    repo._flocks = pd.concat([
        repo._flocks, pd.DataFrame([{"FLOCK_ID": "flock-conflict", "ACCOUNT_ID": "account-b"}]),
    ], ignore_index=True)
    preview = repo.preview_historical_corrections(BATCH_ID)
    raw_frame = repo.get_migration_raw_rows(BATCH_ID)
    session = FakeSession(lambda sql, params: FakeStatement(
        raw_frame.to_dict("records"), list(raw_frame.columns)
    ) if "FROM EFNS_DEV.RAW.MIGRATION_RAW_ROW" in sql else FakeStatement([], []))
    snowflake_repo = SnowflakeRepository(SnowparkExecutor(session))
    monkeypatch.setattr(snowflake_repo, "preview_historical_corrections", lambda batch_id: preview)

    def fail(tx, entity, records):
        if records:
            raise RuntimeError("synthetic CORE insert failure")
        return 0

    monkeypatch.setattr(snowflake_repo, "_insert_migration_core", fail)
    with pytest.raises(RuntimeError, match="synthetic CORE insert failure"):
        snowflake_repo.commit_historical_corrections(BATCH_ID)
    statements = [sql for sql, _params in session.calls]
    assert statements.count("BEGIN") == 1 and statements.count("ROLLBACK") == 1
    assert "COMMIT" not in statements
    assert any("INSERT INTO EFNS_DEV.RAW.MIGRATION_CORRECTION_ROW" in sql for sql in statements)
    assert not any(sql.startswith("UPDATE") for sql in statements)


@pytest.mark.parametrize("quantity", ["-5", "0"])
def test_correction_preserves_signed_quota_and_revalidates_all_foreign_keys(quantity):
    repo = _repository()
    row = next(row for row in repo._migration_raw_rows if row["MIGRATION_RAW_ROW_ID"] == "raw-quota-tx-ready")
    row["RAW_DATA"]["NEW_QUOTACOUNT"] = quantity
    preview = repo.preview_historical_corrections(BATCH_ID)
    corrected = next(row for row in preview.core_rows if row["SOURCE_ID"] == "quota-tx-ready")
    assert float(corrected["CORRECTED_DATA"]["QUOTA_COUNT"]) == float(quantity)
    row["RAW_DATA"]["NEW_RELATEDACCOUNT"] = "missing-account"
    rejected = next(row for row in repo.preview_historical_corrections(BATCH_ID).rows if row["SOURCE_ID"] == "quota-tx-ready")
    assert rejected["DISPOSITION"] == PENDING_CONFIRMATION
    assert "RELATED_ACCOUNT_ID references a missing ACCOUNT." in rejected["CURRENT_VALIDATION_MESSAGES"]

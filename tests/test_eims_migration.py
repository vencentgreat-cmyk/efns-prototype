from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import pandas as pd
import pytest

from data.migration import (
    MigrationSourceFile,
    V3_MAPPING_PATH,
    analyze_migration_files,
    load_mapping,
    migration_stage_path,
    migration_stage_prefix,
)
from data.repositories.mock import MockRepository
from data.connection import ConnectorExecutor
from scripts.generate_fake_eims_export import generate


EXPECTED_COUNTS = {
    "ACCOUNT": 50, "FARM_LOCATION": 125, "FACILITY": 100, "FACILITY_DETAIL": 150,
    "QUOTA_REGISTRATION": 100, "FLOCK": 500, "FLOCK_TRANSACTION": 2000,
    "QUOTA_TRANSACTION": 300, "SALMONELLA_TEST": 250, "PRODUCTION_RECORD": 5000,
}

HISTORICAL_V1_TOTAL = 8450


def _v3_sources():
    mapping = load_mapping(V3_MAPPING_PATH)
    ids = {name: f"00000000-0000-0000-0000-{index:012d}" for index, name in enumerate(mapping["entity_order"], 1)}
    target_rows = {
        "ACCOUNT": {"ACCOUNT_ID": ids["ACCOUNT"], "ORGANIZATION_NAME": "Synthetic Account", "DEFAULT_ON_REPORTS": "1"},
        "CONTACT": {"CONTACT_ID": ids["CONTACT"], "ACCOUNT_ID": ids["ACCOUNT"], "FULL_NAME": "Synthetic Contact"},
        "FARM_LOCATION": {"FARM_LOCATION_ID": ids["FARM_LOCATION"], "ACCOUNT_ID": ids["ACCOUNT"], "LOCATION_NAME": "Synthetic Location"},
        "FACILITY": {"FACILITY_ID": ids["FACILITY"], "ACCOUNT_ID": ids["ACCOUNT"], "FARM_LOCATION_ID": ids["FARM_LOCATION"], "FACILITY_NAME": "Synthetic Facility"},
        "FACILITY_DETAIL": {"FACILITY_DETAIL_ID": ids["FACILITY_DETAIL"], "FACILITY_ID": ids["FACILITY"]},
        "QUOTA_REGISTRATION": {"QUOTA_ID": ids["QUOTA_REGISTRATION"], "REGISTRATION_NUMBER": "SYN-Q-1", "ACCOUNT_ID": ids["ACCOUNT"], "QUOTA_TYPE": "Layer", "EFFECTIVE_DATE": "2026-01-01T00:00:00Z"},
        "FLOCK": {"FLOCK_ID": ids["FLOCK"], "FLOCK_NUMBER": "SYN-F-1", "ACCOUNT_ID": ids["ACCOUNT"], "FACILITY_ID": ids["FACILITY"], "PERMIT_NUMBER": "SYN-P-1", "HATCH_DATE": "2026-01-02T13:14:15Z", "BIRD_COUNT": "10", "CREATE_DELIVERY_TRANSACTION": "0.0"},
        "FLOCK_TRANSACTION": {"FLOCK_TRANSACTION_ID": ids["FLOCK_TRANSACTION"], "FLOCK_ID": ids["FLOCK"], "TRANSACTION_TYPE": "Placement", "QUANTITY": "10", "TRANSACTION_DATE": "2026-01-03"},
        "QUOTA_TRANSACTION": {"QUOTA_TRANSACTION_ID": ids["QUOTA_TRANSACTION"], "TRANSACTION_TYPE": "Adjustment", "QUOTA_ID": ids["QUOTA_REGISTRATION"], "EFFECTIVE_DATE": "2026-01-04", "QUOTA_COUNT": "-12.5"},
        "SALMONELLA_TEST": {"SALMONELLA_TEST_ID": ids["SALMONELLA_TEST"], "FLOCK_ID": ids["FLOCK"], "ACCOUNT_ID": ids["ACCOUNT"], "PERMIT_NUMBER": "SYN-P-1", "TESTING_DATE": "2026-01-05"},
        "SALMONELLA_TEST_SAMPLE": {"SALMONELLA_TEST_SAMPLE_ID": ids["SALMONELLA_TEST_SAMPLE"], "SALMONELLA_TEST_ID": ids["SALMONELLA_TEST"]},
        "PRODUCTION_RECORD": {"PRODUCTION_ID": ids["PRODUCTION_RECORD"], "PRODUCER_ACCOUNT_ID": ids["ACCOUNT"], "SOURCE_WEEK_CODE": "202601", "TOTAL": "-1.25"},
        "QUOTA_ALLOCATION": {"QUOTA_ALLOCATION_ID": ids["QUOTA_ALLOCATION"], "ALLOCATION_COUNT": "0", "EFFECTIVE_DATE": "2026-01-01", "QUOTA_TYPE": "Layer"},
        "DIM_EFC_DATE": {"DAY": "2026-01-01T00:00:00Z", "ELEMENT_CODE": "A", "DATE_VALUE": "2026-01-01"},
    }
    sources = []
    for entity in mapping["entity_order"]:
        spec = mapping["entities"][entity]
        rows = []
        for target in ([target_rows[entity], {**target_rows[entity], "ELEMENT_CODE": "B"}]
                       if entity == "DIM_EFC_DATE" else [target_rows[entity]]):
            source = {}
            for field, value in target.items():
                source_field = spec.get("field_map", {}).get(field)
                if source_field:
                    source[source_field] = value
                elif field == "FLOCK_NUMBER":
                    source[spec["fallbacks"][field][0]] = value
            rows.append(source)
        content = pd.DataFrame(rows).to_csv(index=False).encode("utf-8-sig")
        sources.append(MigrationSourceFile(spec["filename"], content))
    return sources, mapping, ids


def test_v3_named_column_package_preserves_types_relationships_and_date_deduplication():
    sources, mapping, ids = _v3_sources()
    analysis = analyze_migration_files(sources, mapping)
    assert analysis.schema_version == "EFNS-EIMS-DATAVERSE-3"
    assert analysis.ready_count == 15
    assert analysis.rejected_count == 0
    assert analysis.records["ACCOUNT"][0]["ACCOUNT_ID"] == ids["ACCOUNT"]
    assert analysis.records["ACCOUNT"][0]["DEFAULT_ON_REPORTS"] is True
    assert analysis.records["FLOCK"][0]["CREATE_DELIVERY_TRANSACTION"] is False
    assert analysis.records["FLOCK"][0]["HATCH_DATE"].isoformat() == "2026-01-02"
    assert str(analysis.records["QUOTA_TRANSACTION"][0]["QUOTA_COUNT"]) == "-12.5"
    assert analysis.records["QUOTA_TRANSACTION"][0]["OWNER_ACCOUNT_ID"] == ids["ACCOUNT"]
    assert len(analysis.records["DIM_EFC_DATE"]) == 1
    assert analysis.records["DIM_EFC_DATE"][0]["ELEMENT_CODES"] == "A,B"


def test_v3_reconciliation_is_persisted_and_commit_rolls_back_atomically(monkeypatch):
    sources, mapping, _ids = _v3_sources()
    analysis = analyze_migration_files(sources, mapping)
    repository = MockRepository()
    repository.prepare_migration_batch(
        {"MIGRATION_BATCH_ID": analysis.batch_id, "PACKAGE_HASH": analysis.package_hash,
         "SCHEMA_VERSION": analysis.schema_version},
        analysis.files,
        analysis.raw_rows,
    )
    reconciliation = repository.get_migration_reconciliation(analysis.batch_id)
    assert reconciliation["SOURCE_ROWS"].sum() == analysis.ready_count + analysis.rejected_count
    baseline = len(repository.get_accounts())
    monkeypatch.setattr(repository, "insert_production_records", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("rollback")))
    with pytest.raises(RuntimeError, match="rollback"):
        repository.commit_migration_batch(analysis.batch_id)
    assert len(repository.get_accounts()) == baseline


def test_real_additive_sql_is_core_scoped_and_non_destructive():
    sql = Path("sql/12_real_eims_additive_migration.sql").read_text(encoding="utf-8").upper()
    for table in ("CONTACT", "QUOTA_ALLOCATION", "DIM_EFC_DATE"):
        assert f"CREATE TABLE IF NOT EXISTS EFNS_DEV.CORE.{table}" in sql
    assert "CREATE TABLE IF NOT EXISTS EFNS_DEV.RAW.MIGRATION_ERROR" in sql
    assert "CREATE TABLE IF NOT EXISTS EFNS_DEV.RAW.MIGRATION_RECONCILIATION" in sql
    assert "EFNS_DEV.REPORTING.DIM_EFC_DATE" not in sql
    assert "TRUNCATE" not in sql
    assert "DROP TABLE" not in sql


def _sources(directory: Path):
    return [MigrationSourceFile(path.name, path.read_bytes()) for path in sorted(directory.iterdir())]


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    root = tmp_path_factory.mktemp("eims_package")
    manifest = generate(root)
    return root, manifest


def test_generator_is_deterministic_and_manifest_hashes_match(generated, tmp_path):
    root, manifest = generated
    second = generate(tmp_path / "second")
    assert (root / "manifest.json").read_bytes() == (tmp_path / "second" / "manifest.json").read_bytes()
    assert manifest == second
    for dataset in ("clean", "edge_cases"):
        for filename, metadata in manifest["datasets"][dataset]["files"].items():
            content = (root / dataset / filename).read_bytes()
            assert hashlib.sha256(content).hexdigest() == metadata["sha256"]


def test_clean_package_counts_and_relationships(generated):
    root, manifest = generated
    analysis = analyze_migration_files(_sources(root / "clean"))
    counts = {row["SOURCE_ENTITY"]: row["SOURCE_ROWS"] for row in analysis.reconciliation.to_dict("records")}
    assert counts == EXPECTED_COUNTS
    assert analysis.ready_count == sum(EXPECTED_COUNTS.values())
    assert analysis.rejected_count == 0
    assert analysis.errors.empty
    assert manifest["datasets"]["clean"]["package_hash"] == analysis.package_hash


def test_v1_nine_file_package_remains_explicitly_supported(tmp_path):
    from data.migration import load_mapping
    from scripts.generate_fake_eims_export import clean_frames, package_bytes

    mapping = load_mapping(Path("config/eims_migration_mapping_v1.json"))
    files = package_bytes(clean_frames(), mapping)
    analysis = analyze_migration_files([MigrationSourceFile(name, content) for name, content in files.items()])
    assert analysis.schema_version == "EFNS-EIMS-PROVISIONAL-1"
    assert analysis.ready_count == HISTORICAL_V1_TOTAL
    assert analysis.rejected_count == 0


def test_edge_package_quarantines_bad_rows_with_traceable_messages(generated):
    root, _ = generated
    analysis = analyze_migration_files(_sources(root / "edge_cases"))
    assert analysis.rejected_count > 0
    assert {"SOURCE_FILE", "SOURCE_ENTITY", "SOURCE_ROW_NUMBER", "FIELD_MESSAGE"} == set(analysis.errors.columns)
    messages = " ".join(analysis.errors["FIELD_MESSAGE"].tolist())
    for expected in ("Duplicate", "required", "missing or rejected", "valid number", "ISO date", "unknown choice", "at least"):
        assert expected in messages
    assert all(row["NORMALIZED_DATA"] is None for row in analysis.raw_rows if row["VALIDATION_STATUS"] == "REJECTED")


def test_stage_paths_are_scoped_and_reject_traversal():
    assert migration_stage_path("DEV_MIGRATION_abc", "accounts.csv") == "@EFNS_DEV.RAW.EIMS_MIGRATION_FILES/DEV_MIGRATION_abc/accounts.csv"
    assert migration_stage_prefix("DEV_MIGRATION_abc") == "@EFNS_DEV.RAW.EIMS_MIGRATION_FILES/DEV_MIGRATION_abc/"
    with pytest.raises(ValueError): migration_stage_path("REAL_BATCH", "accounts.csv")
    with pytest.raises(ValueError): migration_stage_path("DEV_MIGRATION_abc", "../accounts.csv")


def test_connector_stage_upload_preserves_the_reviewed_filename():
    calls = []

    class Cursor:
        def execute(self, sql, params=()): calls.append((sql, params))
        def close(self): pass

    class Connection:
        def cursor(self): return Cursor()

    ConnectorExecutor(lambda: Connection()).put_stream(
        io.BytesIO(b"synthetic"),
        migration_stage_path("DEV_MIGRATION_abc", "accounts.csv"),
    )
    sql = calls[0][0].replace("\\", "/")
    assert "/accounts.csv' @EFNS_DEV.RAW.EIMS_MIGRATION_FILES/DEV_MIGRATION_abc/" in sql
    assert "OVERWRITE=FALSE" in sql


def test_connector_batches_insert_select_without_native_executemany_rewrite():
    calls = []

    class Cursor:
        rowcount = -1
        def execute(self, sql, params=()): calls.append((sql, params))
        def executemany(self, *_args): raise AssertionError("native rewrite must not be used")
        def close(self): pass

    class Connection:
        def cursor(self): return Cursor()

    executor = ConnectorExecutor(lambda: Connection())
    count = executor.executemany(
        "INSERT INTO EFNS_DEV.RAW.MIGRATION_RAW_ROW (A, B) SELECT %s, PARSE_JSON(%s)",
        [(1, '{}'), (2, '{}')],
        batch_size=10,
    )
    assert count == 2
    assert " UNION ALL SELECT " in calls[0][0]
    assert calls[0][1] == (1, '{}', 2, '{}')


def test_mock_migration_preserves_raw_commits_in_order_and_retries_idempotently(generated):
    root, _ = generated
    analysis = analyze_migration_files(_sources(root / "clean"))
    repository = MockRepository()
    repository.prepare_migration_batch(
        {"MIGRATION_BATCH_ID": analysis.batch_id, "PACKAGE_HASH": analysis.package_hash, "SCHEMA_VERSION": analysis.schema_version},
        analysis.files, analysis.raw_rows,
    )
    assert len(repository.get_migration_raw_rows(analysis.batch_id)) == sum(EXPECTED_COUNTS.values())
    result = repository.commit_migration_batch(analysis.batch_id)
    assert result["counts"] == EXPECTED_COUNTS
    retry = repository.commit_migration_batch(analysis.batch_id)
    assert retry["idempotent"] is True
    assert repository.cleanup_synthetic_migration(analysis.batch_id) is True
    assert repository.get_migration_batches().empty


def test_mock_core_commit_rolls_back_and_marks_batch_failed(generated, monkeypatch):
    root, _ = generated
    analysis = analyze_migration_files(_sources(root / "clean"))
    repository = MockRepository()
    repository.prepare_migration_batch(
        {"MIGRATION_BATCH_ID": analysis.batch_id, "PACKAGE_HASH": analysis.package_hash, "SCHEMA_VERSION": analysis.schema_version},
        analysis.files, analysis.raw_rows,
    )
    initial_accounts = len(repository.get_accounts())

    def fail_production(*_args, **_kwargs):
        raise RuntimeError("synthetic rollback probe")

    monkeypatch.setattr(repository, "insert_production_records", fail_production)
    with pytest.raises(RuntimeError, match="rollback probe"):
        repository.commit_migration_batch(analysis.batch_id)
    assert len(repository.get_accounts()) == initial_accounts
    assert repository.get_migration_batches().iloc[0]["STATUS"] == "FAILED"
    assert len(repository.get_migration_raw_rows(analysis.batch_id)) == sum(EXPECTED_COUNTS.values())


def test_migration_sql_keeps_stage_and_tables_behind_app_owner():
    sql = Path("sql/11_eims_migration_foundation.sql").read_text(encoding="utf-8").upper()
    assert "ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE')" in sql
    assert "GRANT READ, WRITE ON STAGE EFNS_DEV.RAW.EIMS_MIGRATION_FILES TO ROLE EFNS_DEV_APP_OWNER" in sql
    assert "USE ROLE SYSADMIN" in sql
    assert "USE ROLE SECURITYADMIN" in sql
    assert "USE ROLE ACCOUNTADMIN" in sql
    assert "CREATE OR REPLACE PROCEDURE EFNS_DEV.RAW.CLEANUP_SYNTHETIC_MIGRATION" in sql
    assert "SOURCE_ENTITY = 'FARM_LOCATION'" in sql
    assert "GRANT USAGE ON PROCEDURE EFNS_DEV.RAW.CLEANUP_SYNTHETIC_MIGRATION(VARCHAR)" in sql
    assert "GRANT DELETE ON TABLE EFNS_DEV.CORE.PRODUCTION_RECORD TO ROLE EFNS_DEV_APP_OWNER" not in sql
    assert "GRANT DELETE ON TABLE EFNS_DEV.RAW.IMPORT_BATCH TO ROLE EFNS_DEV_APP_OWNER" not in sql
    assert "FUTURE" not in sql
    assert "ALL TABLES" not in sql
    for role in ("EFNS_DEV_VIEWER", "EFNS_DEV_EDITOR", "EFNS_DEV_ADMIN", "EFNS_DEV_DEVELOPER"):
        assert f"TO ROLE {role};" not in sql


def test_migration_page_is_permission_guarded_and_navigation_is_internal():
    page = Path("app/pages/17_Migration_Import.py").read_text(encoding="utf-8")
    home = Path("app/Home.py").read_text(encoding="utf-8")
    navigation = Path("app/navigation.py").read_text(encoding="utf-8")
    assert "require_page_permission(Permission.IMPORT_DATA)" in page
    assert "17_Migration_Import.py" in home
    assert 'st.caption("Select a record to view its details.")' in navigation
    combined = page + navigation
    assert "LinkColumn" not in combined
    assert "href=" not in combined
    assert "query_params" not in combined

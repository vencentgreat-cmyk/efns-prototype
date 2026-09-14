"""Offline structural checks for the DEV-only Snowflake fixture scripts."""

from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SEED = (ROOT / "sql" / "09_dev_synthetic_seed.sql").read_text(encoding="utf-8")
CLEANUP = (ROOT / "sql" / "10_dev_synthetic_cleanup.sql").read_text(encoding="utf-8")
CORE_DDL = (ROOT / "sql" / "02_core_tables.sql").read_text(encoding="utf-8")
PRODUCTION_DDL = (ROOT / "sql" / "03_production_tables.sql").read_text(encoding="utf-8")


EXPECTED_GENERATED_ROWS = {
    "EFNS_DEV.CORE.ACCOUNT": 5,
    "EFNS_DEV.CORE.FACILITY": 8,
    "EFNS_DEV.CORE.QUOTA_REGISTRATION": 6,
    "EFNS_DEV.CORE.FLOCK": 12,
    "EFNS_DEV.CORE.FLOCK_TRANSACTION": 20,
    "EFNS_DEV.CORE.QUOTA_TRANSACTION": 10,
    "EFNS_DEV.CORE.SALMONELLA_TEST": 10,
    "EFNS_DEV.CORE.PRODUCTION_RECORD": 100,
}


def _ddl_columns(sql: str) -> dict[str, set[str]]:
    tables: dict[str, set[str]] = {}
    pattern = re.compile(
        r"CREATE TABLE IF NOT EXISTS\s+(EFNS_DEV\.(?:CORE|RAW)\.\w+)\s*\("
        r"(.*?)\n\)\s*(?:COMMENT\s*=.*?;|;)",
        re.IGNORECASE | re.DOTALL,
    )
    for table, body in pattern.findall(sql):
        columns = set()
        for line in body.splitlines():
            candidate = line.strip().rstrip(",")
            if not candidate or candidate.upper().startswith("CONSTRAINT "):
                continue
            columns.add(candidate.split()[0].upper())
        tables[table.upper()] = columns
    return tables


def _merge_section(table: str) -> str:
    match = re.search(
        rf"MERGE INTO\s+{re.escape(table)}\s+AS target(.*?)(?=\n\s*MERGE INTO|\n\s*COMMIT;)",
        SEED,
        re.IGNORECASE | re.DOTALL,
    )
    assert match, f"Missing MERGE for {table}"
    return match.group(1)


def test_seed_counts_order_and_idempotent_merges_are_explicit():
    for table, expected in EXPECTED_GENERATED_ROWS.items():
        section = _merge_section(table)
        assert f"ROWCOUNT => {expected}" in section
        assert "WHEN NOT MATCHED THEN INSERT" in section

    assert "MERGE INTO EFNS_DEV.RAW.IMPORT_BATCH" in SEED
    assert SEED.count("WHEN NOT MATCHED THEN INSERT") == 9

    parent_order = (
        "EFNS_DEV.CORE.ACCOUNT",
        "EFNS_DEV.CORE.FACILITY",
        "EFNS_DEV.CORE.QUOTA_REGISTRATION",
        "EFNS_DEV.CORE.FLOCK",
        "EFNS_DEV.CORE.FLOCK_TRANSACTION",
        "EFNS_DEV.CORE.QUOTA_TRANSACTION",
        "EFNS_DEV.CORE.SALMONELLA_TEST",
        "EFNS_DEV.RAW.IMPORT_BATCH",
        "EFNS_DEV.CORE.PRODUCTION_RECORD",
    )
    positions = [SEED.index(f"MERGE INTO {table}") for table in parent_order]
    assert positions == sorted(positions)


def test_seed_insert_columns_exist_in_current_snowflake_ddl():
    ddl = _ddl_columns(CORE_DDL + "\n" + PRODUCTION_DDL)
    insert_pattern = re.compile(
        r"MERGE INTO\s+(EFNS_DEV\.(?:CORE|RAW)\.\w+)\s+AS target.*?"
        r"WHEN NOT MATCHED THEN INSERT\s*\((.*?)\)\s*VALUES",
        re.IGNORECASE | re.DOTALL,
    )
    merges = insert_pattern.findall(SEED)
    assert len(merges) == 9
    for table, raw_columns in merges:
        columns = {column.strip().upper() for column in raw_columns.split(",")}
        assert table.upper() in ddl
        assert columns <= ddl[table.upper()], f"Unknown columns for {table}: {columns - ddl[table.upper()]}"


def test_seed_and_cleanup_are_transactional_scoped_and_security_free():
    for script in (SEED, CLEANUP):
        upper = script.upper()
        assert "BEGIN TRANSACTION;" in upper
        assert "COMMIT;" in upper
        assert "WHEN OTHER THEN" in upper
        assert "ROLLBACK;" in upper
        assert "RAISE;" in upper
        assert "DROP " not in upper
        assert "TRUNCATE " not in upper
        assert "CREATE " not in upper
        assert not re.search(
            r"(?:INSERT\s+INTO|MERGE\s+INTO|UPDATE|DELETE\s+FROM)\s+"
            r"EFNS_DEV\.(?:SECURITY|APP)\.",
            upper,
        )

    assert "DEV_SYNTH" in SEED
    assert "DEV_SYNTH" in CLEANUP
    assert "APP_USER" not in SEED.upper()
    assert "AUDIT_EVENT" not in SEED.upper()


def test_cleanup_uses_dependency_safe_dev_synth_filters_only():
    delete_pattern = re.compile(
        r"DELETE FROM\s+(EFNS_DEV\.(?:CORE|RAW)\.\w+)\s+WHERE\s+"
        r"STARTSWITH\((\w+),\s*'DEV_SYNTH_'\);",
        re.IGNORECASE,
    )
    deletes = delete_pattern.findall(CLEANUP)
    assert len(deletes) == 13
    assert "LIKE 'DEV_SYNTH_%'" not in CLEANUP.upper()

    ordered_tables = [table.upper() for table, _ in deletes]
    assert ordered_tables.index("EFNS_DEV.CORE.PRODUCTION_RECORD") < ordered_tables.index(
        "EFNS_DEV.RAW.IMPORT_BATCH"
    )
    assert ordered_tables.index("EFNS_DEV.CORE.SALMONELLA_TEST") < ordered_tables.index(
        "EFNS_DEV.CORE.FLOCK"
    )
    assert ordered_tables.index("EFNS_DEV.CORE.FLOCK_TRANSACTION") < ordered_tables.index(
        "EFNS_DEV.CORE.FLOCK"
    )
    assert ordered_tables.index("EFNS_DEV.CORE.QUOTA_TRANSACTION") < ordered_tables.index(
        "EFNS_DEV.CORE.QUOTA_REGISTRATION"
    )
    assert ordered_tables.index("EFNS_DEV.CORE.FLOCK") < ordered_tables.index(
        "EFNS_DEV.CORE.FACILITY"
    )
    assert ordered_tables[-1] == "EFNS_DEV.CORE.ACCOUNT"


def test_seed_includes_count_relationship_and_repository_semantic_checks():
    upper = SEED.upper()
    for expected in (5, 8, 12, 20, 6, 10, 100):
        assert f"{expected} AS EXPECTED_COUNT" in upper or f", {expected}, COUNT(*)" in upper
    assert "BROKEN_RELATIONSHIP_COUNT" in upper
    assert "FLOCK_FACILITY_ACCOUNT_MISMATCH_COUNT" in upper
    assert "FLOCK_QUOTA_ACCOUNT_MISMATCH_COUNT" in upper
    assert "QUOTA_OWNER_MISMATCH_COUNT" in upper
    assert "SALMONELLA_ACCOUNT_MISMATCH_COUNT" in upper
    assert "SALMONELLA_PERMIT_MISMATCH_COUNT" in upper
    assert "PRODUCTION_FLOCK_CONTEXT_MISMATCH_COUNT" in upper
    assert "REPORTING.VW_PRODUCTION_SUMMARY" in upper

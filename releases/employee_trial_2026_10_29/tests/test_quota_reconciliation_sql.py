"""Offline contract checks only, NOT Snowflake syntax/engine verification."""
from pathlib import Path
import re


SQL = Path(__file__).resolve().parents[1] / 'sql/review/quota_flock_reconciliation_20261029.sql'


def test_review_script_is_select_only_and_mapping_has_complete_identity():
    source = SQL.read_text(encoding='utf-8')
    code = re.sub(r'--[^\n]*', '', source)
    statements = [s.strip() for s in code.split(';') if s.strip()]
    # Semicolons in quoted messages must not be interpreted as commands.
    # Strip string content before splitting for command/forbidden-token checks.
    lexical = re.sub(r"'(?:''|[^'])*'", "''", code)
    statements = [s.strip() for s in lexical.split(';') if s.strip()]
    assert len(statements) >= 12
    assert all(s.startswith(('SELECT ', 'WITH ')) for s in statements)
    assert not re.search(r'\b(INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|TRUNCATE|MERGE|CALL|GRANT|REVOKE|SET|USE)\b', lexical, re.I)
    assert 'm.MIGRATION_BATCH_ID=r.MIGRATION_BATCH_ID' in source
    assert 'm.MIGRATION_RAW_ROW_ID=r.MIGRATION_RAW_ROW_ID' in source
    assert 'core_rows=0' in source and 'VALIDATION_MESSAGES' in source
    assert 'unresolved_owner_gaps' in source and 'latest_counts_by_source' in source
    assert 'COUNT(DISTINCT COALESCE(count_source' in source
    assert 'COUNT_IF(' in source and 'COALESCE(COUNT_IF(' in source


def test_sql_has_all_requested_sections_and_no_add_removal_direction():
    source = SQL.read_text(encoding='utf-8')
    for section in ('T1a', 'T1b', 'T1c', 'T1d', 'T1e', 'T1f'):
        assert '-- ' + section in source
    assert 'EFC_ADDREMOVALBOOLEAN' not in source
    assert "'National Allocation','Provincial Allocation'" in source
    assert "IN ('inactive','1')" in source
    assert 'NULL::NUMBER(38,6) AS net_position' in source

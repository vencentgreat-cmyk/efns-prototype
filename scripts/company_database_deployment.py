"""Guarded fresh-company initialization and read-only structural verification.

Used by company_connection_check.py with a user-authenticated live connection.
Never receives or persists credentials; does not invoke Snowflake CLI.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
from io import StringIO
from pathlib import Path
import re

from snowflake.connector.util_text import split_statements

try:
    from scripts.prepare_company_deployment import ROOT, build_sql, saved_tables, deployment_tables
except ModuleNotFoundError:
    from prepare_company_deployment import ROOT, build_sql, saved_tables, deployment_tables

IDENTITY_SQL = ('SELECT CURRENT_ORGANIZATION_NAME(), CURRENT_ACCOUNT_NAME(), '
                'CURRENT_ACCOUNT(), CURRENT_REGION(), CURRENT_ROLE(), CURRENT_USER()')
EXPECTED = ('QDCTNKN', 'UW19058', 'CB12755', 'AWS_CA_CENTRAL_1')


def query(cursor, sql, evidence):
    entry = {'sql': sql, 'started_at_utc': datetime.now(timezone.utc).isoformat()}
    evidence.setdefault('deployment_queries', []).append(entry)
    try:
        cursor.execute(sql)
        entry['query_id'] = cursor.sfqid
        columns = [column[0] for column in cursor.description] if cursor.description else []
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()] if columns else []
        entry['rows'] = rows
        entry['status'] = 'SUCCESS'
        return rows
    except Exception as error:
        entry.update(status='FAILED', query_id=getattr(cursor, 'sfqid', None),
                     error_code=getattr(error, 'errno', None), error_type=type(error).__name__)
        raise


def initialize(cursor, evidence, bundle):
    identity = query(cursor, IDENTITY_SQL, evidence)[0]
    if tuple(identity.values())[:4] != EXPECTED or list(identity.values())[4:] != ['ACCOUNTADMIN', 'EFNSDATABASE']:
        raise ValueError('Fresh initialization requires the verified company identity and EFNSDATABASE/ACCOUNTADMIN')
    databases = query(cursor, 'SHOW DATABASES', evidence)
    if any(row['name'].upper() == 'EFNS_DEV' for row in databases):
        raise ValueError('EFNS_DEV already exists: no initialization attempted; inspect and use --verify-schema')
    expected_sql = build_sql(saved_tables())
    actual_sql = (bundle / '01_fresh_company.sql').read_text(encoding='utf-8-sig')
    if actual_sql != expected_sql:
        raise ValueError('Prepared SQL differs from the current reviewed builder; regenerate/review, do not execute')
    evidence['initialization_plan'] = {
        'database': 'EFNS_DEV', 'warehouse': 'EFNS_DEV_WH', 'size': 'XSMALL',
        'auto_suspend_seconds': 60, 'tables': len(deployment_tables()), 'views': 4, 'roles': 6,
        'stages': 2, 'business_rows': 0, 'infrastructure_lock_rows': 1,
        'initial_admin_created': False,
        'sql_sha256': hashlib.sha256(actual_sql.encode('utf-8')).hexdigest(),
    }
    print(f'Verified company target: QDCTNKN/UW19058/CB12755; creating EFNS_DEV, XSMALL/60s warehouse, {len(deployment_tables())} tables, 4 views, 6 roles and 2 stages. No business rows or app administrator will be created.', flush=True)
    evidence['initialization_started_at_utc'] = datetime.now(timezone.utc).isoformat()
    # The generated DDL is a single guarded block. DDL auto-commits; never retry
    # initialization after a failure without inspecting the partial environment.
    for sql, _ in split_statements(StringIO(actual_sql)):
        query(cursor, sql, evidence)
    evidence['initialization_ddl_completed_at_utc'] = datetime.now(timezone.utc).isoformat()


def _columns(text):
    return tuple(value.strip().strip('"').upper() for value in text.split(','))


def key_groups(ddl):
    primary = {_columns(columns) for columns in re.findall(r'primary\s+key\s*\(([^)]+)\)', ddl, re.I)}
    unique = {_columns(columns) for columns in re.findall(r'\bunique\s*\(([^)]+)\)', ddl, re.I)}
    foreign = set()
    for child, parent, columns in re.findall(r'foreign\s+key\s*\(([^)]+)\)\s+references\s+([\w."]+)\s*\(([^)]+)\)', ddl, re.I):
        parent = parent.replace('"', '').upper()
        foreign.add((_columns(child), parent, _columns(columns)))
    return {'primary': primary, 'unique': unique, 'foreign': foreign}


def compare_columns(expected, actual):
    def key(row):
        return tuple(row[field] for field in ('TABLE_SCHEMA', 'TABLE_NAME', 'COLUMN_NAME'))
    by_key = {key(row): row for row in actual}
    expected_keys = {key(row) for row in expected}
    differences = []
    for wanted in expected:
        found = by_key.get(key(wanted))
        if found is None:
            differences.append({'column': key(wanted), 'problem': 'missing'})
            continue
        for field in ('DATA_TYPE', 'CHARACTER_MAXIMUM_LENGTH', 'NUMERIC_PRECISION', 'NUMERIC_SCALE', 'IS_NULLABLE', 'COLUMN_DEFAULT'):
            observed = '' if found[field] is None else str(found[field])
            if observed != wanted[field]:
                differences.append({'column': key(wanted), 'attribute': field,
                                    'expected': wanted[field], 'actual': observed})
    differences += [{'column': extra, 'problem': 'unexpected'} for extra in by_key.keys() - expected_keys]
    return differences


def server_side_stage_encryption(stage, settings):
    # DESCRIBE STAGE need not expose an encryption property. SHOW STAGES uses
    # INTERNAL NO CSE for internal storage without client-side encryption;
    # internal storage remains server-encrypted (SNOWFLAKE_SSE).
    return (str(stage.get('type', '')).upper() == 'INTERNAL NO CSE'
            or any(str(row.get('property_value', '')).upper() == 'SNOWFLAKE_SSE' for row in settings))


def supplement_columns():
    return [dict(TABLE_SCHEMA='CORE',TABLE_NAME='FLOCK_TRANSACTION',
        COLUMN_NAME='COUNT_SOURCE_LABEL',DATA_TYPE='TEXT',CHARACTER_MAXIMUM_LENGTH='255',
        NUMERIC_PRECISION='',NUMERIC_SCALE='',IS_NULLABLE='YES',COLUMN_DEFAULT='')]


def manual_decision_columns():
    """Expected upgrade columns derived from the same reviewed table DDL."""
    ddl = deployment_tables()['RAW.MIGRATION_CORRECTION_DECISION']
    result = []
    for name, kind, size, rest in re.findall(
        r'^\s+([A-Z_]+)\s+(VARCHAR|NUMBER|VARIANT|TIMESTAMP_NTZ)(?:\(([^)]+)\))?([^\n]*)', ddl, re.M
    ):
        precision = size.split(',') if kind == 'NUMBER' else []
        default = rest.split(' DEFAULT ', 1)[1].strip().rstrip(',') if ' DEFAULT ' in rest else ''
        result.append(dict(TABLE_SCHEMA='RAW', TABLE_NAME='MIGRATION_CORRECTION_DECISION',
            COLUMN_NAME=name, DATA_TYPE='TEXT' if kind == 'VARCHAR' else kind,
            CHARACTER_MAXIMUM_LENGTH=size if kind == 'VARCHAR' else '',
            NUMERIC_PRECISION=precision[0] if precision else '',
            NUMERIC_SCALE=precision[1] if len(precision)>1 else '',
            IS_NULLABLE='NO' if 'NOT NULL' in rest else 'YES', COLUMN_DEFAULT=default))
    for name, kind, length, precision, scale in [
        ('DECISION_ID', 'TEXT', '36', '', ''), ('DECISION_VERSION', 'NUMBER', '', '18', '0')
    ]:
        result.append(dict(TABLE_SCHEMA='RAW', TABLE_NAME='MIGRATION_CORRECTION_ROW', COLUMN_NAME=name,
            DATA_TYPE=kind, CHARACTER_MAXIMUM_LENGTH=length, NUMERIC_PRECISION=precision,
            NUMERIC_SCALE=scale, IS_NULLABLE='YES', COLUMN_DEFAULT=''))
    return result


def verify(cursor, evidence, *, expect_empty=False):
    identity = query(cursor, IDENTITY_SQL, evidence)[0]
    if tuple(identity.values())[:4] != EXPECTED:
        raise ValueError('Company identity mismatch: verification stopped')
    query(cursor, 'USE ROLE ACCOUNTADMIN', evidence)
    query(cursor, 'USE WAREHOUSE EFNS_DEV_WH', evidence)
    query(cursor, 'USE DATABASE EFNS_DEV', evidence)
    with (ROOT / 'docs/identity_history_2026-10-14/Column_Inventory.csv').open(encoding='utf-8-sig', newline='') as handle:
        expected_columns = list(csv.DictReader(handle))
    actual_columns = query(cursor, "SELECT TABLE_SCHEMA,TABLE_NAME,COLUMN_NAME,DATA_TYPE,CHARACTER_MAXIMUM_LENGTH,NUMERIC_PRECISION,NUMERIC_SCALE,IS_NULLABLE,COLUMN_DEFAULT FROM EFNS_DEV.INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA <> 'INFORMATION_SCHEMA'", evidence)
    expected_columns += manual_decision_columns()
    expected_columns += supplement_columns()
    differences = compare_columns(expected_columns, actual_columns)
    tables = deployment_tables()
    objects = query(cursor, "SELECT TABLE_SCHEMA,TABLE_NAME,TABLE_TYPE FROM EFNS_DEV.INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA <> 'INFORMATION_SCHEMA'", evidence)
    found_tables = {row['TABLE_SCHEMA'] + '.' + row['TABLE_NAME'] for row in objects if row['TABLE_TYPE'] == 'BASE TABLE'}
    found_views = {row['TABLE_SCHEMA'] + '.' + row['TABLE_NAME'] for row in objects if row['TABLE_TYPE'] == 'VIEW'}
    wanted_views = {'REPORTING.' + name for name in ('VW_ACCOUNT_FACILITY', 'VW_FLOCK_DETAIL', 'VW_PRODUCTION_SIZE_DETAIL', 'VW_PRODUCTION_SUMMARY')}
    for label, wanted, found in (('tables', set(tables), found_tables), ('views', wanted_views, found_views)):
        if wanted != found:
            differences.append({'object_group': label, 'missing': sorted(wanted - found), 'unexpected': sorted(found - wanted)})
    key_counts = {'primary': 0, 'foreign': 0, 'unique': 0}
    for name, ddl in sorted(tables.items()):
        rows = query(cursor, f"SELECT GET_DDL('TABLE','EFNS_DEV.{name}') AS DDL", evidence)
        expected_keys, actual_keys = key_groups(ddl), key_groups(rows[0]['DDL'])
        for kind in key_counts:
            key_counts[kind] += len(actual_keys[kind])
            if expected_keys[kind] != actual_keys[kind]:
                differences.append({'table': name, 'key_kind': kind, 'expected': sorted(expected_keys[kind]), 'actual': sorted(actual_keys[kind])})
    counts = {}
    for name in sorted(tables):
        rows = query(cursor, f'SELECT COUNT(*) AS N FROM EFNS_DEV.{name}', evidence)
        counts[name] = int(rows[0]['N'])
        if expect_empty and counts[name] != (1 if name == 'RAW.INTAKE_LOCK' else 0):
            differences.append({'table': name, 'problem': 'Unexpected fresh-install row count', 'actual': counts[name]})
    warehouses = query(cursor, "SHOW WAREHOUSES LIKE 'EFNS_DEV_WH'", evidence)
    if len(warehouses) != 1 or str(warehouses[0]['size']).upper().replace('-', '') != 'XSMALL' or int(warehouses[0]['auto_suspend']) != 60 or str(warehouses[0]['auto_resume']).lower() != 'true':
        differences.append({'problem': 'Warehouse configuration mismatch'})
    grants = query(cursor, 'SHOW GRANTS TO ROLE EFNS_DEV_APP_OWNER', evidence)
    query(cursor, 'SHOW GRANTS TO ROLE EFNS_DEV_DEPLOYER', evidence)
    stages = query(cursor, 'SHOW STAGES IN DATABASE EFNS_DEV', evidence)
    for row in grants:
        if str(row.get('name', '')).upper() in {'EFNS_DEV.APP.AUDIT_EVENT', 'EFNS_DEV.APP.RECORD_REVISION', 'EFNS_DEV.CORE.FLOCK_EVENT', 'EFNS_DEV.RAW.PRODUCTION_MATCH_DECISION', 'EFNS_DEV.RAW.MIGRATION_CORRECTION_DECISION'} and str(row.get('privilege', '')).upper() in {'UPDATE', 'DELETE', 'OWNERSHIP'}:
            differences.append({'problem': 'Append-only runtime table has mutation privilege', 'object': row['name'], 'privilege': row['privilege']})
    expected_stages = {'RAW.EIMS_MIGRATION_FILES', 'APP.EFNS_STREAMLIT_STAGE'}
    actual_stages = {str(row['schema_name']) + '.' + str(row['name']) for row in stages}
    if actual_stages != expected_stages:
        differences.append({'problem': 'Stage set mismatch', 'expected': sorted(expected_stages), 'actual': sorted(actual_stages)})
    for stage in ('RAW.EIMS_MIGRATION_FILES', 'APP.EFNS_STREAMLIT_STAGE'):
        settings = query(cursor, f'DESCRIBE STAGE EFNS_DEV.{stage}', evidence)
        stage_metadata = next((row for row in stages if str(row['schema_name']) + '.' + str(row['name']) == stage), {})
        if not server_side_stage_encryption(stage_metadata, settings):
            differences.append({'problem': 'Stage encryption is not confirmed as SNOWFLAKE_SSE', 'stage': stage})
    # Test every runtime read with the intended owner hierarchy and no elevated
    # secondary roles. No INSERT/UPDATE/DELETE is used as a privilege test.
    try:
        query(cursor, 'USE ROLE EFNS_DEV_DEPLOYER', evidence)
        query(cursor, 'USE SECONDARY ROLES NONE', evidence)
        runtime_identity = query(cursor, 'SELECT CURRENT_ROLE() AS ROLE, CURRENT_SECONDARY_ROLES() AS SECONDARY_ROLES, CURRENT_DATABASE() AS DB', evidence)[0]
        if runtime_identity['ROLE'] != 'EFNS_DEV_DEPLOYER' or runtime_identity['DB'] != 'EFNS_DEV':
            differences.append({'problem': 'Runtime role/database mismatch'})
        for name in sorted(set(tables) | wanted_views):
            query(cursor, f'SELECT * FROM EFNS_DEV.{name} LIMIT 0', evidence)
    finally:
        query(cursor, 'USE ROLE ACCOUNTADMIN', evidence)
    evidence['verification'] = {'verified_at_utc': datetime.now(timezone.utc).isoformat(),
                                'table_count': len(found_tables), 'view_count': len(found_views),
                                'column_count': len(actual_columns), 'key_counts': key_counts,
                                'row_counts': counts, 'runtime_identity': runtime_identity,
                                'differences': differences, 'passed': not differences,
                                'business_write_tests_executed': False,
                                'browser_acceptance_executed': False}
    if differences:
        raise ValueError('Company structure verification found differences; see saved evidence. Do not deploy the application.')
    print(f'Company structure verified: {len(found_tables)} tables, {len(found_views)} views, {len(actual_columns)} columns; keys and runtime reads checked. No business data written.', flush=True)

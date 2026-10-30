"""Build an isolated, fresh-company install from the saved deployed DDL.

No network calls and no source data are included in the application package.
The output is deliberately not an upgrade script for an existing database.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
from io import StringIO

import yaml
from snowflake.connector.util_text import split_statements

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / '.local/company-20261019'
SNAPSHOT = ROOT / 'docs/identity_history_2026-10-14'
IDENTITY = ('QDCTNKN', 'UW19058', 'CB12755', 'AWS_CA_CENTRAL_1')


def saved_tables():
    text = (SNAPSHOT / 'Actual_Get_DDL.sql').read_text(encoding='utf-8-sig')
    result = {}
    for match in re.finditer(r'^-- ([A-Z_]+\.[A-Z_]+)\s*\n(.*?)(?=^-- [A-Z_]+\.[A-Z_]+\s*$|\Z)', text, re.M | re.S):
        name, ddl = match.groups()
        if not re.match(r'create or replace TABLE\b', ddl, re.I):
            continue
        result[name] = re.sub(r'create or replace TABLE\s+\w+',
                             'CREATE TABLE IF NOT EXISTS EFNS_DEV.' + name,
                             ddl.strip(), count=1, flags=re.I)
    if len(result) != 32:
        raise ValueError(f'Expected the reviewed 32-table snapshot, found {len(result)}')
    return result


def ordered_tables(tables):
    pending = dict(tables)
    emitted = []
    while pending:
        ready = [name for name, ddl in pending.items()
                 if not (set(re.findall(r'references EFNS_DEV\.([A-Z_]+\.[A-Z_]+)', ddl, re.I))
                         - {name}).intersection(pending)]
        if not ready:
            raise ValueError('Unresolved foreign-key dependency cycle')
        for name in sorted(ready):
            emitted.append((name, pending.pop(name)))
    return emitted


def deployment_tables(tables=None):
    """Extend, never rewrite, the dated evidence snapshot for new installations."""
    result = dict(saved_tables() if tables is None else tables)
    sql = (ROOT / 'sql/17_Historical_Manual_Corrections.sql').read_text(encoding='utf-8')
    match = re.search(r'CREATE TABLE IF NOT EXISTS EFNS_DEV\.RAW\.MIGRATION_CORRECTION_DECISION\s*\(.*?\n \);', sql, re.S)
    if not match:
        raise ValueError('Manual decision DDL is missing or incomplete')
    result['RAW.MIGRATION_CORRECTION_DECISION'] = match[0]
    name = 'RAW.MIGRATION_CORRECTION_ROW'
    if 'DECISION_ID VARCHAR' not in result[name]:
        result[name] = re.sub(r'\(\s*\n', '(\n DECISION_ID VARCHAR(36),\n DECISION_VERSION NUMBER(18,0),\n', result[name], count=1)
    name = 'CORE.FLOCK_TRANSACTION'
    if 'COUNT_SOURCE_LABEL' not in result[name]:
        result[name] = re.sub(r'\(\s*\n', '(\n COUNT_SOURCE_LABEL VARCHAR(255),\n', result[name], count=1)
    return result


def guard():
    expressions = ('CURRENT_ORGANIZATION_NAME()', 'CURRENT_ACCOUNT_NAME()',
                   'CURRENT_ACCOUNT()', 'CURRENT_REGION()')
    return ' OR '.join(f"{expr} <> '{value}'" for expr, value in zip(expressions, IDENTITY))


def grant_statements(tables):
    operational = {'ACCOUNT', 'FARM_LOCATION', 'FACILITY', 'FACILITY_DETAIL', 'FLOCK',
                   'FLOCK_TRANSACTION', 'QUOTA_REGISTRATION', 'QUOTA_TRANSACTION', 'SALMONELLA_TEST'}
    append_only = {'CONTACT', 'QUOTA_ALLOCATION', 'DIM_EFC_DATE', 'FLOCK_EVENT',
                   'RECORD_REVISION', 'PRODUCTION_MATCH_DECISION', 'AUDIT_EVENT',
                   'IMPORT_RAW_ROW', 'MIGRATION_FILE', 'MIGRATION_RAW_ROW', 'MIGRATION_ERROR',
                   'MIGRATION_CORRECTION_DECISION'}
    for name in sorted(tables):
        short = name.split('.')[1]
        if short in operational or short == 'APP_USER':
            privileges = 'SELECT, INSERT, UPDATE, DELETE'
        elif short == 'SALMONELLA_TEST_SAMPLE':
            privileges = 'SELECT, INSERT, DELETE'
        elif short == 'PRODUCTION_SIZE_BREAKDOWN':
            privileges = 'SELECT'
        elif short == 'INTAKE_LOCK':
            privileges = 'SELECT, UPDATE'
        elif short in append_only:
            privileges = 'SELECT, INSERT'
        else:
            privileges = 'SELECT, INSERT, UPDATE'
        yield f'GRANT {privileges} ON TABLE EFNS_DEV.{name} TO ROLE EFNS_DEV_APP_OWNER;'


def build_sql(tables):
    tables = deployment_tables(tables)
    foundation = (ROOT / 'sql/00_dev_foundation.sql').read_text(encoding='utf-8-sig')
    # The optional budget monitor is a separate company policy decision.
    foundation = foundation.split('CREATE RESOURCE MONITOR')[0]
    statements = [foundation, 'USE ROLE ACCOUNTADMIN; USE WAREHOUSE EFNS_DEV_WH; USE DATABASE EFNS_DEV;']
    statements += [ddl for _, ddl in ordered_tables(tables)]
    views = (ROOT / 'sql/04_reporting_views.sql').read_text(encoding='utf-8-sig')
    views = re.sub(r'CREATE OR REPLACE VIEW', 'CREATE VIEW IF NOT EXISTS', views, flags=re.I)
    views = re.sub(r'\bCOPY GRANTS\b', '', views, flags=re.I)
    statements.append(views)
    for stage in ('RAW.EIMS_MIGRATION_FILES', 'APP.EFNS_STREAMLIT_STAGE'):
        statements.append(f"CREATE STAGE IF NOT EXISTS EFNS_DEV.{stage} ENCRYPTION=(TYPE='SNOWFLAKE_SSE') DIRECTORY=(ENABLE=TRUE);")
    statements += [
        "INSERT INTO EFNS_DEV.RAW.INTAKE_LOCK (LOCK_ID, VERSION) SELECT 'continuity', 0 WHERE NOT EXISTS (SELECT 1 FROM EFNS_DEV.RAW.INTAKE_LOCK WHERE LOCK_ID='continuity');",
        'GRANT USAGE ON DATABASE EFNS_DEV TO ROLE EFNS_DEV_APP_OWNER;',
        'GRANT USAGE ON WAREHOUSE EFNS_DEV_WH TO ROLE EFNS_DEV_APP_OWNER;',
    ]
    statements += [f'GRANT USAGE ON SCHEMA EFNS_DEV.{schema} TO ROLE EFNS_DEV_APP_OWNER;'
                   for schema in ('RAW', 'CORE', 'REPORTING', 'SECURITY', 'APP')]
    statements += list(grant_statements(tables))
    statements += [f'GRANT READ, WRITE ON STAGE EFNS_DEV.{stage} TO ROLE EFNS_DEV_APP_OWNER;'
                   for stage in ('RAW.EIMS_MIGRATION_FILES', 'APP.EFNS_STREAMLIT_STAGE')]
    statements += ['GRANT SELECT ON ALL VIEWS IN SCHEMA EFNS_DEV.REPORTING TO ROLE EFNS_DEV_APP_OWNER;',
                   'GRANT CREATE STREAMLIT ON SCHEMA EFNS_DEV.APP TO ROLE EFNS_DEV_DEPLOYER;',
                   'GRANT ROLE EFNS_DEV_DEPLOYER TO USER EFNSDATABASE;',
                   'USE ROLE ACCOUNTADMIN;']
    statements.append("""CREATE PROCEDURE EFNS_DEV.RAW.CLEANUP_SYNTHETIC_MIGRATION(BATCH_ID VARCHAR)
RETURNS VARCHAR LANGUAGE SQL EXECUTE AS OWNER
AS 'BEGIN RETURN ''REJECTED_MANUAL_PROVENANCE_REVIEW_REQUIRED''; END;';""")
    statements.append('GRANT USAGE ON PROCEDURE EFNS_DEV.RAW.CLEANUP_SYNTHETIC_MIGRATION(VARCHAR) TO ROLE EFNS_DEV_APP_OWNER;')
    # Execute inside one guarded scripting block. DDL is still auto-committing;
    # a failure requires inspection rather than an automatic rollback/retry.
    body = '\n'.join(" EXECUTE IMMEDIATE '" + statement.replace("'", "''") + "';"
                     for statement, _ in split_statements(StringIO('\n'.join(statements))))
    return ("-- Fresh company install only. No historical or synthetic business rows.\n"
            "-- Source: actual DDL snapshot 2026-10-14 plus current reporting views.\n"
            "USE ROLE ACCOUNTADMIN;\n"
            "SELECT CURRENT_ORGANIZATION_NAME(), CURRENT_ACCOUNT_NAME(), CURRENT_ACCOUNT(), CURRENT_REGION(), CURRENT_ROLE();\n"
            "EXECUTE IMMEDIATE $$\nDECLARE\n"
            " wrong_account EXCEPTION (-20001, 'Company account identity mismatch');\n"
            " existing_database EXCEPTION (-20002, 'EFNS_DEV already exists: inspect before resuming');\n"
            " n NUMBER;\nBEGIN\n"
            f" IF ({guard()}) THEN RAISE wrong_account; END IF;\n"
            " SHOW DATABASES LIKE 'EFNS_DEV';\n"
            " SELECT COUNT(*) INTO :n FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));\n"
            " IF (n <> 0) THEN RAISE existing_database; END IF;\n"
            + body + '\nEND;\n$$;\n')


ENTRYPOINT = '''"""Company-only entrypoint; never fall back to seeded mock data."""
import os
import runpy
from pathlib import Path
import streamlit as st
from snowflake.snowpark.context import get_active_session

os.environ['EFNS_RUNTIME_MODE'] = 'snowflake'
os.environ['REPOSITORY_MODE'] = 'snowflake'
os.environ['SNOWFLAKE_DATABASE'] = 'EFNS_DEV'
os.environ['SNOWFLAKE_WAREHOUSE'] = 'EFNS_DEV_WH'
os.environ['EFNS_PAGE_PREFIX'] = 'app/pages'
os.environ['EFNS_ENTRYPOINT'] = 'streamlit_app.py'
try:
    identity = tuple(get_active_session().sql("SELECT CURRENT_ORGANIZATION_NAME(), CURRENT_ACCOUNT_NAME(), CURRENT_ACCOUNT(), CURRENT_REGION(), CURRENT_DATABASE()").collect()[0])
    if identity != ('QDCTNKN', 'UW19058', 'CB12755', 'AWS_CA_CENTRAL_1', 'EFNS_DEV'):
        raise RuntimeError('Wrong company database context')
except Exception:
    st.error('The company database connection is not ready. Contact the application administrator.')
    st.stop()
runpy.run_path(str(Path(__file__).parent / 'app' / 'Home.py'), run_name='__main__')
'''


def prepare(destination=DEST):
    destination = Path(destination)
    if destination.exists():
        raise ValueError('Destination exists; choose a new output directory to preserve the prior package')
    tables = deployment_tables()
    destination.mkdir(parents=True)
    (destination / '01_fresh_company.sql').write_text(build_sql(tables), encoding='utf-8')
    app = destination / 'app'
    app.mkdir()
    project = yaml.safe_load((ROOT / 'snowflake.yml').read_text(encoding='utf-8'))
    entity = project['entities'].pop('efns_dev')
    project['entities']['efns_company'] = entity
    manifest = []
    for artifact in entity['artifacts']:
        pattern = artifact if isinstance(artifact, str) else artifact['src']
        matches = sorted(ROOT.glob(pattern))
        if not matches:
            raise ValueError(f'Empty application artifact: {pattern}')
        for source in matches:
            relative = source.relative_to(ROOT)
            target = app / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    (app / 'streamlit_app.py').write_text(ENTRYPOINT, encoding='utf-8')
    (app / 'config/source_provenance.json').write_text(json.dumps({
        'evidence_date': '2026-10-19',
        'evidence': 'New company installation: classify batches only after reconciliation in this account.',
        'batches': {}, 'legacy_file_imports': {},
    }, indent=2), encoding='utf-8')
    (app / 'snowflake.yml').write_text(yaml.safe_dump(project, sort_keys=False), encoding='utf-8')
    for path in sorted(app.rglob('*')):
        if path.is_file():
            manifest.append({'path': str(path.relative_to(app)).replace('\\', '/'),
                             'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    (destination / 'application_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    shutil.copyfile(SNAPSHOT / 'Column_Inventory.csv', destination / 'expected_columns.csv')
    (destination / 'expected_tables.json').write_text(json.dumps(sorted(tables), indent=2), encoding='utf-8')
    counts = '\nUNION ALL\n'.join(f"SELECT '{name}' AS OBJECT_NAME, COUNT(*) AS ROW_COUNT FROM EFNS_DEV.{name}" for name in sorted(tables))
    verification = f"""-- Read-only: run only after successful company initialization.
USE ROLE ACCOUNTADMIN;
USE WAREHOUSE EFNS_DEV_WH;
USE DATABASE EFNS_DEV;
SELECT CURRENT_ORGANIZATION_NAME(), CURRENT_ACCOUNT_NAME(), CURRENT_ACCOUNT(), CURRENT_REGION(), CURRENT_ROLE();
SELECT TABLE_SCHEMA, TABLE_TYPE, COUNT(*) AS OBJECT_COUNT FROM EFNS_DEV.INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA IN ('APP','CORE','RAW','REPORTING','SECURITY') GROUP BY 1,2 ORDER BY 1,2;
SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
FROM EFNS_DEV.INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA <> 'INFORMATION_SCHEMA' ORDER BY 1,2,ORDINAL_POSITION;
SHOW PRIMARY KEYS IN DATABASE EFNS_DEV;
SHOW IMPORTED KEYS IN DATABASE EFNS_DEV;
SELECT TABLE_SCHEMA,TABLE_NAME,CONSTRAINT_NAME,CONSTRAINT_TYPE FROM EFNS_DEV.INFORMATION_SCHEMA.TABLE_CONSTRAINTS
WHERE CONSTRAINT_TYPE='UNIQUE' ORDER BY 1,2,3;
SHOW GRANTS TO ROLE EFNS_DEV_APP_OWNER;
SHOW GRANTS TO ROLE EFNS_DEV_DEPLOYER;
SHOW WAREHOUSES LIKE 'EFNS_DEV_WH';
{counts};
-- Switch off secondary roles to verify runtime access, not ACCOUNTADMIN access.
USE ROLE EFNS_DEV_DEPLOYER;
USE SECONDARY ROLES NONE;
SELECT COUNT(*) FROM EFNS_DEV.CORE.ACCOUNT;
SELECT COUNT(*) FROM EFNS_DEV.REPORTING.VW_PRODUCTION_SUMMARY;
SELECT COUNT(*) FROM EFNS_DEV.RAW.SOURCE_FILE;
SELECT COUNT(*) FROM EFNS_DEV.APP.RECORD_REVISION;
SELECT COUNT(*) FROM EFNS_DEV.CORE.FLOCK_EVENT;
"""
    (destination / '02_verify_company.sql').write_text(verification, encoding='utf-8')
    print(json.dumps({'directory': str(destination), 'tables': len(tables),
                      'views': 4, 'application_files': len(manifest), 'remote_executed': False}))
    return destination


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, default=DEST)
    prepare(parser.parse_args().destination)

"""Offline safety checks for the separate fresh-company deployment package."""
import json
import re

import pytest

from scripts.company_connection_check import verify_identity
from scripts.prepare_company_deployment import ROOT, build_sql, ordered_tables, prepare, saved_tables
from scripts import company_database_deployment as deployment


def test_company_identity_is_exact_and_old_account_is_rejected():
    verify_identity(('QDCTNKN', 'UW19058', 'CB12755', 'AWS_CA_CENTRAL_1', 'ACCOUNTADMIN'))
    with pytest.raises(RuntimeError):
        verify_identity(('QDCTNKN', 'RC34234', 'CB12755', 'AWS_CA_CENTRAL_1'))


def test_final_snapshot_dependencies_and_non_destructive_sql():
    tables = saved_tables()
    assert len(tables) == 32
    ddl = '\n'.join(tables.values())
    assert len(re.findall(r'primary key\s*\(', ddl, re.I)) == 32
    assert len(re.findall(r'foreign key\s*\(', ddl, re.I)) == 46
    assert len(re.findall(r'\bunique\s*\(', ddl, re.I)) == 6
    positions = {name: i for i, (name, _) in enumerate(ordered_tables(tables))}
    for name, ddl in tables.items():
        for parent in re.findall(r'references EFNS_DEV\.([A-Z_]+\.[A-Z_]+)', ddl, re.I):
            assert parent == name or positions[parent] < positions[name]
    sql = build_sql(tables)
    assert not re.search(r'\b(DROP|TRUNCATE)\b|\bDELETE\s+FROM\b|CREATE\s+OR\s+REPLACE', sql, re.I)
    assert 'existing_database' in sql and 'CB12755' in sql
    assert 'RC34234' not in sql
    assert len(re.findall(r'CREATE TABLE IF NOT EXISTS', sql)) == 33
    assert len(re.findall(r'CREATE VIEW IF NOT EXISTS', sql)) == 4
    assert 'MIGRATION_BATCH_ID, MIGRATION_RAW_ROW_ID' in tables['RAW.MIGRATION_RAW_ROW']
    assert 'ENTITY_ID VARCHAR(1000)' in tables['APP.AUDIT_EVENT']


def test_package_excludes_credentials_and_old_source_certification(tmp_path):
    destination = prepare(tmp_path / 'company')
    app = destination / 'app'
    names = [p.relative_to(app).as_posix() for p in app.rglob('*') if p.is_file()]
    assert all(not name.endswith(('.csv', '.xlsx', '.xlsm', '.toml')) for name in names)
    assert not any('.env' in name or '__pycache__' in name for name in names)
    policy = json.loads((app / 'config/source_provenance.json').read_text())
    assert policy['batches'] == {} and policy['legacy_file_imports'] == {}
    entry = (app / 'streamlit_app.py').read_text()
    assert "os.environ['EFNS_RUNTIME_MODE'] = 'snowflake'" in entry
    assert 'st.stop()' in entry and 'CB12755' in entry
    assert (app / 'data/repositories/continuity.py').is_file()
    assert (app / 'data/connection.py').read_bytes() == (ROOT / 'data/connection.py').read_bytes()
    with pytest.raises(ValueError, match='Destination exists'):
        prepare(destination)


def test_declared_keys_compare_field_groups_not_generated_constraint_names():
    old = 'constraint OLD primary key (A,B), constraint C foreign key (A,B) references EFNS_DEV.RAW.X(A,B), unique(C)'
    new = 'constraint NEW primary key (A, B), constraint D foreign key (A, B) references "EFNS_DEV"."RAW"."X"(A, B), unique (C)'
    assert deployment.key_groups(old) == deployment.key_groups(new)


def test_column_comparison_keeps_null_default_distinct_from_text():
    row = {'TABLE_SCHEMA': 'CORE', 'TABLE_NAME': 'ACCOUNT', 'COLUMN_NAME': 'LATITUDE',
           'DATA_TYPE': 'NUMBER', 'CHARACTER_MAXIMUM_LENGTH': '', 'NUMERIC_PRECISION': '10',
           'NUMERIC_SCALE': '7', 'IS_NULLABLE': 'YES', 'COLUMN_DEFAULT': ''}
    actual = {**row, 'CHARACTER_MAXIMUM_LENGTH': None, 'NUMERIC_PRECISION': 10,
              'NUMERIC_SCALE': 7, 'COLUMN_DEFAULT': None}
    assert deployment.compare_columns([row], [actual]) == []
    assert deployment.compare_columns([row], [{**actual, 'COLUMN_DEFAULT': 'None'}])


def test_stage_encryption_accepts_real_show_stage_without_describe_encryption_field():
    assert deployment.server_side_stage_encryption({'type':'INTERNAL NO CSE'},[{'property':'FIELD_DELIMITER','property_value':','}])
    assert not deployment.server_side_stage_encryption({'type':'EXTERNAL'},[])
    assert not deployment.server_side_stage_encryption({'type':'INTERNAL'},[])


@pytest.mark.parametrize('identity,existing', [
    (('QDCTNKN', 'UW19058', 'CB12755', 'AWS_CA_CENTRAL_1', 'ACCOUNTADMIN', 'EFNSDATABASE'), True),
    (('QDCTNKN', 'RC34234', 'CB12755', 'AWS_CA_CENTRAL_1', 'ACCOUNTADMIN', 'EFNSDATABASE'), False),
])
def test_initialization_stops_before_any_ddl_on_wrong_account_or_existing_database(monkeypatch,tmp_path,identity,existing):
    statements = []
    def query(_cursor, sql, _evidence):
        statements.append(sql)
        if sql == deployment.IDENTITY_SQL:
            return [dict(zip(('ORG','ACCOUNT','LOCATOR','REGION','ROLE','USER'), identity))]
        if sql == 'SHOW DATABASES':
            return [{'name': 'EFNS_DEV'}] if existing else []
        raise AssertionError('DDL must not run')
    monkeypatch.setattr(deployment, 'query', query)
    with pytest.raises(ValueError):
        deployment.initialize(None, {}, tmp_path)
    assert not any('CREATE' in sql for sql in statements)


def test_initialization_checks_prepared_sql_and_does_not_retry_a_ddl_failure(monkeypatch,tmp_path):
    (tmp_path/'01_fresh_company.sql').write_text(build_sql(saved_tables()), encoding='utf-8')
    executed = []
    def query(_cursor, sql, _evidence):
        executed.append(sql)
        if sql == deployment.IDENTITY_SQL:
            return [dict(zip(('ORG','ACCOUNT','LOCATOR','REGION','ROLE','USER'),
                             ('QDCTNKN','UW19058','CB12755','AWS_CA_CENTRAL_1','ACCOUNTADMIN','EFNSDATABASE')))]
        if sql == 'SHOW DATABASES':
            return []
        if sql.lstrip().startswith('EXECUTE IMMEDIATE'):
            raise RuntimeError('Synthetic DDL failure')
        return []
    monkeypatch.setattr(deployment, 'query', query)
    evidence = {}
    with pytest.raises(RuntimeError, match='Synthetic DDL failure'):
        deployment.initialize(None, evidence, tmp_path)
    assert sum(sql.lstrip().startswith('EXECUTE IMMEDIATE') for sql in executed) == 1
    assert 'initialization_ddl_completed_at_utc' not in evidence
    assert evidence['initialization_plan']['business_rows'] == 0


@pytest.mark.parametrize('inspect_profile',[False,True])
def test_password_only_probe_does_not_claim_mfa_or_save_password(monkeypatch,tmp_path,inspect_profile):
    import snowflake.connector
    from scripts import company_connection_check as probe
    captured = {}
    class Cursor:
        sfqid = 'synthetic-query-id'
        description = []
        def __enter__(self): return self
        def __exit__(self,*_args): pass
        def execute(self,sql):
            self.sql=sql
            self.description = [('property',),('value',)] if sql=='DESCRIBE USER EFNSDATABASE' else []
        def fetchone(self):
            return ('QDCTNKN','UW19058','CB12755','AWS_CA_CENTRAL_1','ACCOUNTADMIN','EFNSDATABASE')
        def fetchall(self):
            if self.sql=='DESCRIBE USER EFNSDATABASE':
                return [('EMAIL','database@nsegg.ca'),('DISPLAY_NAME','EFNS Database'),('DISABLED','false'),('PASSWORD','synthetic-private-property'),('RSA_PUBLIC_KEY','synthetic-private-key')]
            return []
    class Connection:
        def __enter__(self): return self
        def __exit__(self,*_args): pass
        def cursor(self): return Cursor()
    def connect(**kwargs):
        captured.update(kwargs)
        return Connection()
    evidence = tmp_path/'probe.json'
    monkeypatch.setattr(snowflake.connector, 'connect', connect)
    monkeypatch.setattr(probe, 'getpass', lambda _prompt: 'synthetic-secret')
    monkeypatch.setattr('sys.argv', ['probe','--password','--evidence',str(evidence)]+(['--inspect-user-profile'] if inspect_profile else []))
    probe.main()
    assert captured['authenticator'] == 'snowflake' and 'passcode' not in captured
    assert 'synthetic-secret' not in evidence.read_text()
    assert json.loads(evidence.read_text())['authentication']['mfa_enrollment_verified'] is False
    if inspect_profile:
        profile=json.loads(evidence.read_text())['user_profile']
        assert profile['email_matches_confirmed_admin'] and not profile['admin_created']
        assert not profile['viewer_email_verified_in_app']
        assert 'synthetic-private' not in evidence.read_text()


@pytest.mark.parametrize('bad_column',[False,True])
def test_read_only_full_verification_and_schema_difference_gate(monkeypatch,bad_column):
    import csv
    with (ROOT/'docs/identity_history_2026-10-14/Column_Inventory.csv').open(encoding='utf-8-sig',newline='') as handle:
        columns = list(csv.DictReader(handle))
    columns += deployment.manual_decision_columns() + deployment.supplement_columns()
    if bad_column:
        columns[0] = {**columns[0], 'IS_NULLABLE': 'YES'}
    tables = deployment.deployment_tables()
    objects = sorted({(row['TABLE_SCHEMA'],row['TABLE_NAME']) for row in columns})
    statements = []
    def query(_cursor,sql,_evidence):
        statements.append(sql)
        if sql == deployment.IDENTITY_SQL:
            return [dict(zip(('ORG','ACCOUNT','LOCATOR','REGION','ROLE','USER'),('QDCTNKN','UW19058','CB12755','AWS_CA_CENTRAL_1','ACCOUNTADMIN','EFNSDATABASE')))]
        if 'INFORMATION_SCHEMA.COLUMNS' in sql: return columns
        if 'INFORMATION_SCHEMA.TABLES' in sql:
            return [{'TABLE_SCHEMA':s,'TABLE_NAME':n,'TABLE_TYPE':'BASE TABLE' if s+'.'+n in tables else 'VIEW'} for s,n in objects]
        if 'GET_DDL' in sql:
            name = sql.split("'EFNS_DEV.")[1].split("'")[0]
            return [{'DDL':tables[name]}]
        if sql.startswith('SELECT COUNT(*)'):
            return [{'N':1 if sql.endswith('RAW.INTAKE_LOCK') else 0}]
        if sql.startswith('SHOW WAREHOUSES'):
            return [{'size':'X-Small','auto_suspend':60,'auto_resume':'true'}]
        if sql.startswith('SHOW STAGES'):
            return [{'schema_name':'RAW','name':'EIMS_MIGRATION_FILES'},{'schema_name':'APP','name':'EFNS_STREAMLIT_STAGE'}]
        if sql.startswith('DESCRIBE STAGE'):
            return [{'property_value':'SNOWFLAKE_SSE'}]
        if sql.startswith('SELECT CURRENT_ROLE()'):
            return [{'ROLE':'EFNS_DEV_DEPLOYER','SECONDARY_ROLES':'NONE','DB':'EFNS_DEV'}]
        return []
    monkeypatch.setattr(deployment,'query',query)
    evidence = {}
    if bad_column:
        with pytest.raises(ValueError,match='verification found differences'):
            deployment.verify(None,evidence,expect_empty=True)
    else:
        deployment.verify(None,evidence,expect_empty=True)
    assert evidence['verification']['passed'] is not bad_column
    assert evidence['verification']['key_counts']=={'primary':33,'foreign':47,'unique':7}
    assert all(not re.match(r'\s*(CREATE|INSERT|UPDATE|DELETE|ALTER|DROP|TRUNCATE|GRANT)\b',sql,re.I) for sql in statements)
    assert 'USE SECONDARY ROLES NONE' in statements


def test_snowsight_package_preserves_paths_and_only_prepares_app_creation(tmp_path):
    from scripts.prepare_company_snowsight import prepare as prepare_web
    bundle=prepare(tmp_path/'company')
    destination=prepare_web(bundle)
    files=json.loads((destination/'File_Manifest.json').read_text())
    assert len(files)==75 and len({row['path'] for row in files})==75
    assert {'data/flock_transaction_supplement.py','data/repositories/flock_supplement.py',
            'app/services/flock_supplement_workspace.py'} <= {row['path'] for row in files}
    assert {'data/repositories/flock_date_repair.py','app/services/flock_date_repair_workspace.py',
            'config/eims_migration_mapping_v3_disposal_r1.json'} <= {row['path'] for row in files}
    assert any(row['path']=='data/connection.py' for row in files)
    assert any(row['path']=='app/pages/17_Migration_Import.py' for row in files)
    sql=(destination/'03_Create_Application_After_Web_Upload.sql').read_text()
    assert 'FULL OUTER JOIN' in sql and 'RAISE wrong_files' in sql
    assert 'RAISE existing_app' in sql and 'CB12755' in sql
    assert 'CREATE STREAMLIT EFNS_DEV.APP.EFNS_INTERNAL_APP' in sql
    assert 'ADD LIVE VERSION FROM LAST' in sql
    assert not re.search(r'CREATE\s+(?:OR\s+REPLACE\s+)?(?:DATABASE|SCHEMA|TABLE|STAGE)\b|\bDROP\b|\bTRUNCATE\b|\bINSERT\s+INTO\b',sql,re.I)

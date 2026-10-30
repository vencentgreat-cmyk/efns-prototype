"""Verify staged company source, then explicitly create/publish a fresh app.

Uses the already-authorized connector, never launches Snowflake CLI and never
initializes a database. Existing applications are inspected, not overwritten.
"""
from __future__ import annotations

from collections import Counter
from io import StringIO
import json
from pathlib import Path

from snowflake.connector.util_text import split_statements

try:
    from scripts.company_database_deployment import EXPECTED, IDENTITY_SQL, ROOT, query
except ModuleNotFoundError:
    from company_database_deployment import EXPECTED, IDENTITY_SQL, ROOT, query

RELEASE = 'release_20261019_adac0b97b630'
STAGE = 'EFNS_DEV.APP.EFNS_STREAMLIT_STAGE'
APP = 'EFNS_DEV.APP.EFNS_INTERNAL_APP'
BUNDLE = ROOT / '.local/company-20261019'


def executable_statements(sql):
    for statement,_ in split_statements(StringIO(sql),remove_comments=True):
        if statement.strip():
            yield statement


def validate_application(description):
    if not description or not description[0].get('live_version_location_uri'):
        raise ValueError('A live application version is not confirmed; stop before grants')
    if str(description[0].get('main_file','')).lstrip('/') != 'streamlit_app.py' or str(description[0].get('query_warehouse','')).upper() != 'EFNS_DEV_WH':
        raise ValueError('Application entrypoint/warehouse differs from expected; stop before grants')
    if str(description[0].get('runtime_name','')).upper() != 'SYSTEM$WAREHOUSE_RUNTIME':
        raise ValueError('Application runtime differs from expected; stop before grants')


def complete_grants(cursor,evidence):
    for statement in executable_statements((ROOT/'sql/08_post_deploy_grants.sql').read_text(encoding='utf-8-sig')):
        query(cursor,statement,evidence)
    query(cursor,'USE ROLE EFNS_DEV_DEPLOYER',evidence)
    query(cursor,'USE SECONDARY ROLES NONE',evidence)
    grants=query(cursor,f'SHOW GRANTS ON STREAMLIT {APP}',evidence)
    app_rows=query(cursor,"SHOW STREAMLITS LIKE 'EFNS_INTERNAL_APP' IN SCHEMA EFNS_DEV.APP",evidence)
    description=query(cursor,f'DESCRIBE STREAMLIT {APP}',evidence)
    wanted={'EFNS_DEV_ADMIN','EFNS_DEV_EDITOR','EFNS_DEV_DEVELOPER','EFNS_DEV_VIEWER'}
    actual={str(row.get('grantee_name','')).upper() for row in grants if str(row.get('privilege','')).upper()=='USAGE'}
    if not wanted.issubset(actual):
        raise ValueError('Required application USAGE grants missing; inspect saved evidence')
    validate_application(description)
    evidence['application'].update(status='PUBLISHED_GRANTS_VERIFIED',show=app_rows,describe=description,
                                   usage_roles=sorted(wanted),browser_verified=False,viewer_email_verified=False,admin_initialized=False)
    record_url(cursor,evidence)
    print('Live application and USAGE grants verified; browser identity/admin are not yet verified.',flush=True)


def record_url(cursor, evidence):
    # Public Snowsight route used by the official CLI. Do not rely on its
    # internal host-discovery function, which this company account lacks.
    evidence['application']['url'] = 'https://app.snowflake.com/qdctnkn/uw19058/#/streamlit-apps/' + APP
    evidence['application']['url_basis'] = 'Public Snowsight object route and verified company/object metadata'
    evidence['application']['url_browser_verified'] = False
    print('Application URL (browser not yet verified): '+evidence['application']['url'],flush=True)


def compare_upload(files, remote):
    expected = {row['path']: int(row['bytes']) for row in files}
    actual = {}
    wrong_paths, compressed = [], []
    counts = Counter()
    for row in remote:
        name = str(row['name'])
        marker = RELEASE + '/'
        if name.count(marker) != 1:
            wrong_paths.append(name)
            continue
        path = name.split(marker, 1)[1]
        prefix = name.split(marker,1)[0]
        if prefix and not prefix.endswith('/'):
            wrong_paths.append(name)
            continue
        counts[path] += 1
        actual[path] = int(row['size'])
        if path.lower().endswith('.gz'):
            compressed.append(path)
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    sizes = [{'path': path, 'expected': expected[path], 'actual': actual[path]}
             for path in sorted(set(expected) & set(actual)) if expected[path] != actual[path]]
    duplicates = sorted(path for path, n in counts.items() if n != 1)
    return {'expected_count': len(expected), 'remote_count': len(remote),
            'missing': missing, 'extra': extra, 'size_differences': sizes,
            'compressed': compressed, 'wrong_paths': wrong_paths, 'duplicates': duplicates,
            'passed': bool(files) and len(remote) == len(expected) == len(files) and not any((missing, extra, sizes, compressed, wrong_paths, duplicates)),
            'remote_sha256_verified': False}


def run(cursor, evidence, *, deploy=False, complete_existing_grants=False, bundle=BUNDLE):
    bundle = Path(bundle)
    identity = query(cursor, IDENTITY_SQL, evidence)[0]
    if tuple(identity.values())[:4] != EXPECTED:
        raise ValueError('Company identity mismatch; application operation stopped')
    # Inspect with the authenticated administrative role first, so an app owned
    # by another role cannot be hidden from the deployer's SHOW visibility.
    apps = query(cursor, "SHOW STREAMLITS LIKE 'EFNS_INTERNAL_APP' IN SCHEMA EFNS_DEV.APP", evidence)
    existing = [row for row in apps if str(row['name']).upper() == 'EFNS_INTERNAL_APP']
    existing_description = query(cursor,f'DESCRIBE STREAMLIT {APP}',evidence) if existing else None
    query(cursor, 'USE ROLE EFNS_DEV_DEPLOYER', evidence)
    query(cursor, 'USE SECONDARY ROLES NONE', evidence)
    query(cursor, 'USE WAREHOUSE EFNS_DEV_WH', evidence)
    query(cursor, 'USE DATABASE EFNS_DEV', evidence)
    query(cursor, 'USE SCHEMA APP', evidence)
    files = json.loads((bundle/'snowsight/File_Manifest.json').read_text(encoding='utf-8'))
    all_remote = query(cursor, f'LIST @{STAGE}/', evidence)
    remote = query(cursor, f'LIST @{STAGE}/{RELEASE}/', evidence)
    comparison = compare_upload(files, remote)
    comparison['outside_release_files'] = [row['name'] for row in all_remote if RELEASE+'/' not in str(row['name'])]
    evidence['upload_comparison'] = comparison
    print(json.dumps({'upload_verified':comparison['passed'], 'expected':len(files), 'remote':len(remote),
                      'missing':len(comparison['missing']), 'extra':len(comparison['extra']),
                      'size_differences':len(comparison['size_differences']), 'gz_files':len(comparison['compressed'])}),flush=True)
    if existing:
        evidence['application'] = {'status':'EXISTING_INSPECTED_NOT_MODIFIED', 'show':existing, 'describe':existing_description}
        if complete_existing_grants:
            if not comparison['passed']:
                raise ValueError('Remote upload mismatch; no grant recovery executed')
            if any(str(row.get('owner','')).upper()!='EFNS_DEV_DEPLOYER' for row in existing):
                raise ValueError('Existing application has a different owner; no grant recovery executed')
            validate_application(existing_description)
            evidence['application']['recovery_mode']='GRANTS_ONLY_NO_CREATE_OR_PUBLISH'
            complete_grants(cursor,evidence)
            return
        record_url(cursor,evidence)
        print('Existing application inspected; no CREATE, replacement, publish or grants executed.',flush=True)
        return
    if not comparison['passed']:
        raise ValueError('Remote source differs from the release manifest; no application changes made')
    if complete_existing_grants:
        raise ValueError('No existing application found: grant-only recovery will not create one')
    if not deploy:
        evidence['application'] = {'status':'NOT_PRESENT_UPLOAD_VERIFIED', 'created':False}
        return
    path = bundle/'snowsight/03_Create_Application_After_Web_Upload.sql'
    sql = path.read_text(encoding='utf-8-sig')
    if any(token in sql.upper() for token in ('CREATE OR REPLACE','CREATE DATABASE','DROP TABLE','TRUNCATE','INSERT INTO')):
        raise ValueError('Unexpected destructive/business SQL in application creation script')
    print('Remote files verified and no application exists; executing prepared application-only creation and publish SQL.',flush=True)
    for statement in executable_statements(sql):
        query(cursor,statement,evidence)
    # Recheck context and a live version before executing the existing grants.
    description = query(cursor,f'DESCRIBE STREAMLIT {APP}',evidence)
    validate_application(description)
    evidence['application'] = {'status':'CREATED_AND_PUBLISHED', 'describe':description}
    evidence['application']['created_in_this_run']=True
    complete_grants(cursor,evidence)

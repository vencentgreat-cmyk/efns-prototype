import json

import pytest

from scripts import company_application_deployment as app


def files_and_remote():
    files=[{'path':f'app/file_{i}.py','bytes':i+1} for i in range(66)]
    remote=[{'name':f'efns_streamlit_stage/{app.RELEASE}/'+row['path'],'size':row['bytes']} for row in files]
    return files,remote


@pytest.mark.parametrize('problem',['none','missing','extra','size','gz','nested','duplicate'])
def test_remote_inventory_all_66_paths_and_sizes(problem):
    files,remote=files_and_remote()
    if problem=='missing':remote.pop()
    if problem=='extra':remote.append({'name':f'stage/{app.RELEASE}/extra.py','size':5})
    if problem=='size':remote[0]['size']=900
    if problem=='gz':remote[0]['name']+='.gz'
    if problem=='nested':remote[0]['name']=f'stage/{app.RELEASE}/unexpected/app/file_0.py'
    if problem=='duplicate':remote[-1]=dict(remote[0])
    result=app.compare_upload(files,remote)
    assert result['passed'] is (problem=='none')
    assert result['remote_sha256_verified'] is False


@pytest.mark.parametrize('existing,bad_files',[(False,False),(True,False),(False,True)])
def test_read_only_preflight_or_existing_app_never_executes_ddl(tmp_path,monkeypatch,existing,bad_files):
    files,remote=files_and_remote()
    if bad_files:remote.pop()
    (tmp_path/'snowsight').mkdir()
    (tmp_path/'snowsight/File_Manifest.json').write_text(json.dumps(files))
    statements=[]
    def query(_cursor,sql,_evidence):
        statements.append(sql)
        if sql==app.IDENTITY_SQL:
            return [dict(zip(('ORG','ACCOUNT','LOCATOR','REGION','ROLE','USER'),('QDCTNKN','UW19058','CB12755','AWS_CA_CENTRAL_1','ACCOUNTADMIN','EFNSDATABASE')))]
        if sql.startswith('LIST '):return remote
        if sql.startswith('SHOW STREAMLITS'):return [{'name':'EFNS_INTERNAL_APP'}] if existing else []
        if sql.startswith('DESCRIBE STREAMLIT'):return [{'live_version_location_uri':'snow://existing'}]
        return []
    monkeypatch.setattr(app,'query',query)
    evidence={}
    if bad_files:
        with pytest.raises(ValueError,match='Remote source differs'):
            app.run(None,evidence,deploy=True,bundle=tmp_path)
    else:
        app.run(None,evidence,deploy=existing,bundle=tmp_path)
    assert not any(sql.startswith(('CREATE','ALTER','GRANT','INSERT','DROP','EXECUTE')) for sql in statements)
    if existing:assert evidence['application']['status']=='EXISTING_INSPECTED_NOT_MODIFIED'


@pytest.mark.parametrize('recovery',[False,True])
def test_fresh_creation_or_grants_only_recovery_without_initialization(tmp_path,monkeypatch,recovery):
    from scripts.prepare_company_deployment import prepare
    from scripts.prepare_company_snowsight import prepare as prepare_web
    bundle=prepare(tmp_path/'company');prepare_web(bundle)
    files=json.loads((bundle/'snowsight/File_Manifest.json').read_text())
    remote=[{'name':f'stage/{app.RELEASE}/'+row['path'],'size':row['bytes']} for row in files]
    statements=[];created=recovery
    def query(_cursor,sql,_evidence):
        nonlocal created
        statements.append(sql)
        if sql==app.IDENTITY_SQL:
            return [dict(zip(('ORG','ACCOUNT','LOCATOR','REGION','ROLE','USER'),('QDCTNKN','UW19058','CB12755','AWS_CA_CENTRAL_1','ACCOUNTADMIN','EFNSDATABASE')))]
        if sql.startswith('LIST '):return remote
        if sql.startswith('SHOW STREAMLITS'):return [{'name':'EFNS_INTERNAL_APP','owner':'EFNS_DEV_DEPLOYER'}] if created else []
        if 'CREATE STREAMLIT' in sql:created=True
        if sql.startswith('DESCRIBE STREAMLIT'):
            return [{'main_file':'streamlit_app.py','query_warehouse':'EFNS_DEV_WH','runtime_name':'SYSTEM$WAREHOUSE_RUNTIME','live_version_location_uri':'snow://synthetic/live'}]
        if sql.startswith('SHOW GRANTS ON STREAMLIT'):
            return [{'privilege':'USAGE','grantee_name':role} for role in ('EFNS_DEV_ADMIN','EFNS_DEV_EDITOR','EFNS_DEV_DEVELOPER','EFNS_DEV_VIEWER')]
        if sql.startswith('SELECT SYSTEM$GET_SNOWSIGHT_HOST'):
            return [{'HOST':'https://app.snowflake.com'}]
        return []
    monkeypatch.setattr(app,'query',query)
    evidence={};app.run(None,evidence,deploy=not recovery,complete_existing_grants=recovery,bundle=bundle)
    assert evidence['application']['status']=='PUBLISHED_GRANTS_VERIFIED'
    assert evidence['application']['url'].endswith('/#/streamlit-apps/EFNS_DEV.APP.EFNS_INTERNAL_APP')
    assert evidence['application']['browser_verified'] is False and evidence['application']['admin_initialized'] is False
    assert sum('CREATE STREAMLIT' in sql for sql in statements)==(0 if recovery else 1)
    assert not any('CREATE DATABASE' in sql or 'INSERT INTO' in sql for sql in statements)
    assert not any(sql.strip().startswith('--') for sql in statements)
    if recovery:
        assert not any('ADD LIVE VERSION' in sql for sql in statements)
        assert evidence['application']['recovery_mode']=='GRANTS_ONLY_NO_CREATE_OR_PUBLISH'


def test_sql_splitter_never_sends_comment_only_tail_but_preserves_literal_comments():
    assert list(app.executable_statements('-- notes only\n-- second line'))==[]
    statements=list(app.executable_statements("SELECT '-- value';\n-- trailing notes"))
    assert len(statements)==1 and "'-- value'" in statements[0]

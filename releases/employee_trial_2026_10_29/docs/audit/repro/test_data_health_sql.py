"""Static SQL boundary checks; not Snowflake syntax or engine validation."""
from pathlib import Path
import re
import pytest
SQL=Path(__file__).resolve().parents[3]/'sql/review/data_health_20261030.sql'

def code_only(sql):
    # SQL emitted here uses ordinary single quoted strings and line comments.
    return re.sub(r"--[^\n]*|'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"",lambda m:' ' if m[0].startswith('--') else ' LITERAL ',sql)

def check_read_only(sql):
    code=code_only(sql)
    statements=[x.strip() for x in code.split(';') if x.strip()]
    assert statements and all(re.match(r'^(SELECT|WITH)\b',s,re.I) for s in statements)
    forbidden=r'\b(INSERT|UPDATE|DELETE|MERGE|CREATE|ALTER|DROP|TRUNCATE|COPY|PUT|GET|CALL|EXECUTE|GRANT|REVOKE|USE|SET|UNSET|BEGIN|COMMIT|ROLLBACK|REMOVE|SHOW|DESCRIBE|UNDROP)\b'
    assert not re.search(forbidden,code,re.I)
    return statements

def test_data_health_contains_only_select_with():
    text=SQL.read_text(encoding='utf-8')
    assert len(check_read_only(text))==11
    assert 'EFNS_DEV.CORE.' in text
    assert 'COUNT_SOURCE_LABEL' not in text or 'UPDATE' not in code_only(text)

@pytest.mark.parametrize('sql',['SELECT 1; DELETE FROM x;','WITH a AS (SELECT 1) DELETE FROM x;',
    'SELECT 1; ALTER SESSION SET x=1;','CALL x();','SELECT 1; COMMIT;'])
def test_guard_rejects_writes_or_session_commands(sql):
    with pytest.raises(AssertionError):check_read_only(sql)

def test_guard_ignores_comments_and_strings():
    assert len(check_read_only("-- UPDATE is forbidden\nSELECT 'DELETE; DROP' AS harmless;"))==1

def test_every_declared_core_identity_is_covered():
    text=SQL.read_text(encoding='utf-8')
    duplicate_section=text.split('-- Q01 duplicate',1)[1].split('-- Q01b',1)[0]
    tables=set(re.findall(r'FROM EFNS_DEV.CORE.(\w+)',duplicate_section))
    assert tables=={'ACCOUNT','CONTACT','FARM_LOCATION','FACILITY','FACILITY_DETAIL','FLOCK',
        'FLOCK_TRANSACTION','QUOTA_REGISTRATION','QUOTA_TRANSACTION','QUOTA_ALLOCATION',
        'SALMONELLA_TEST','SALMONELLA_TEST_SAMPLE','DIM_EFC_DATE','PRODUCTION_RECORD',
        'PRODUCTION_SIZE_BREAKDOWN','FLOCK_EVENT'}

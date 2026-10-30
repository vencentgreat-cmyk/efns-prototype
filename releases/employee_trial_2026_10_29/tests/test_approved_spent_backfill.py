"""Synthetic stateful Snowpark doubles; NOT real-engine rollback evidence."""
import copy,json,re,sys,uuid
from pathlib import Path
from types import SimpleNamespace
import pandas as pd
import pytest
OPS=Path(__file__).resolve().parent/'support/approved_spent_backfill'
sys.path.insert(0,str(OPS))
from core import checked_plan,digest,run_atomic,FIELD,reason_for,identities
from engine import RestrictedExecutor,read_snapshot,check_before,check_after
from app.security import User,Role
from app.services.authorized_repository import AuthorizedRepository
from data.repositories.snowflake import SnowflakeRepository
from data.repositories.base import RepositoryError


def fixture_plan():
    target=str(uuid.uuid5(uuid.NAMESPACE_URL,'synthetic-target')).upper()
    version='2026-01-01T00:00:00.123456789';rows=[];accounts=[];raw=[];mapping=[]
    def account(aid,name):return dict(ACCOUNT_ID=aid,ORGANIZATION_NAME=name,STATUS='Inactive',DESCRIPTION='Keep this',LATITUDE=0,SPENT_FOWL_PLANS='Legacy evidence',SPENT_FOWL_PLANS_ACCOUNT_ID=None,CREATED_AT='2020-01-01T00:00:00.000000000',UPDATED_AT=version)
    accounts.append(account(target,'Synthetic target'))
    for i in range(26):
        aid=str(uuid.uuid5(uuid.NAMESPACE_URL,'synthetic-source-'+str(i))).upper();rid='ACCOUNT:'+str(i+2)
        payload={'ACCOUNTID':aid,'EFNS_SPENTFOWLPLANS':target};normalized={'ACCOUNT_ID':aid}
        proposal=dict(original_batch='SYNTHETIC',raw_row_id=rid,source_account_guid=aid,source_guid=target,expected_old_link=None,expected_updated_at_ff9=version,proposed_lookup_id=target,target_updated_at_ff9=version,raw_payload_sha256=digest(payload),supplement_version='EFNS-ACCOUNT-RELATIONSHIPS-1',normalized_payload_sha256=digest(normalized),expected_mapping_status='COMMITTED',source_row_number=i+2,source_filename='account.csv')
        rows.append(dict(proposal=proposal,review_token=digest(proposal),original_batch='SYNTHETIC',raw_row_id=rid,source_account_guid=aid,proposed_lookup_id=target,expected_updated_at_ff9=version,raw_payload_sha256=digest(payload),normalized_payload_sha256=digest(normalized),target_expected_updated_at_ff9=version,current_database_lookup_id=None,proposed_request_id=str(uuid.uuid5(uuid.NAMESPACE_URL,'synthetic-request-'+str(i))),disposition='READY_FOR_USER_REVIEW'))
        accounts.append(account(aid,'Synthetic '+str(i)))
        raw.append(dict(MIGRATION_BATCH_ID='SYNTHETIC',MIGRATION_RAW_ROW_ID=rid,SOURCE_ID=aid,TARGET_ID=aid,SOURCE_ENTITY='ACCOUNT',SOURCE_FILENAME='account.csv',SOURCE_ROW_NUMBER=i+2,VALIDATION_STATUS='READY',RAW_DATA=payload,NORMALIZED_DATA=normalized))
        mapping.append(dict(MIGRATION_BATCH_ID='SYNTHETIC',MIGRATION_RAW_ROW_ID=rid,SOURCE_ID=aid,TARGET_ID=aid,STATUS='COMMITTED'))
    key=digest([{'request_id':r['proposed_request_id'],'review_token':r['review_token']} for r in rows])
    for r in rows:r['review_set']=key
    return dict(records=rows,review_set_sha256=key),dict(accounts=accounts,raw=raw,mappings=mapping,batch=[{'MIGRATION_BATCH_ID':'SYNTHETIC','STATUS':'COMMITTED'}],revisions=[],audits=[])


class FakeSession:
    def __init__(self,state,fail=None):self.state=copy.deepcopy(state);self.calls=[];self.saved=None;self.fail=fail;self.counts={}
    def sql(self,sql,params=None):
        def collect(statement_params=None):
            self.calls.append((sql,params,statement_params))
            if sql=='BEGIN':
                assert self.saved is None,'Nested BEGIN';self.saved=copy.deepcopy(self.state);return []
            if sql=='COMMIT':self.saved=None;return []
            if sql=='ROLLBACK':self.state=self.saved;self.saved=None;return []
            assert not sql.startswith(('SHOW','ALTER','CREATE','DROP','DELETE'))
            if sql.startswith('UPDATE EFNS_DEV.RAW.INTAKE_LOCK'):
                assert statement_params=={'STATEMENT_TIMEOUT_IN_SECONDS':'30'};return [{'number of rows updated':1}]
            if sql.startswith('UPDATE EFNS_DEV.CORE.ACCOUNT'):
                target,aid,version=params;row=next(r for r in self.state['accounts'] if r['ACCOUNT_ID']==aid)
                if pd.Timestamp(version)!=pd.Timestamp(row['UPDATED_AT']):return [{'number of rows updated':0}]
                row[FIELD]=target;row['UPDATED_AT']=(pd.Timestamp(row['UPDATED_AT'])+pd.Timedelta(1,unit='ns')).isoformat()
                if self.fail=='unexpected_attribute':row['DESCRIPTION']='Wrong'
                return [{'number of rows updated':1}]
            if sql.startswith('INSERT INTO'):
                table='revisions' if '.RECORD_REVISION ' in sql else 'audits'
                self.counts[table]=self.counts.get(table,0)+1
                if self.fail==table and self.counts[table]==13:raise RuntimeError('synthetic mid-batch failure')
                columns=sql.split('(',1)[1].split(')',1)[0].replace(' ','').split(',');expressions=sql.split(' SELECT ',1)[1].split(',');bound=iter(params);record={}
                for col,expr in zip(columns,expressions):
                    value=None if expr.strip()=='NULL' else next(bound)
                    record[col]=json.loads(value) if 'PARSE_JSON' in expr else value
                self.state[table].append(record)
                if self.fail=='duplicate_receipt' and table=='audits' and len(self.state[table])==26:self.state['revisions'].append(copy.deepcopy(self.state['revisions'][0]))
                return [{'number of rows inserted':1}]
            if 'FROM EFNS_DEV.CORE.ACCOUNT' in sql:
                return copy.deepcopy([r for r in self.state['accounts'] if not params or r['ACCOUNT_ID']==params[0]])
            for fragment,key in [('RAW.MIGRATION_RAW_ROW','raw'),('RAW.MIGRATION_ID_MAP','mappings'),('RAW.MIGRATION_BATCH','batch'),('APP.RECORD_REVISION','revisions'),('APP.AUDIT_EVENT','audits')]:
                if 'FROM EFNS_DEV.'+fragment in sql:
                    values=self.state[key]
                    if key=='revisions' and re.search(r'WHERE REVISION_ID\s*=\s*\?',sql):values=[r for r in values if r['REVISION_ID']==params[0]]
                    return copy.deepcopy(values)
            raise AssertionError(sql)
        statement=SimpleNamespace()
        def collect_with_schema(statement_params=None):
            result=collect(statement_params)
            statement.schema=SimpleNamespace(fields=[SimpleNamespace(name=k) for k in (result[0] if result else {})])
            return result
        statement.collect=collect_with_schema
        return statement


def setup(fail=None):
    plan,state=fixture_plan();rows=checked_plan(plan,plan['review_set_sha256'],'SYNTHETIC')
    actor=User('synthetic-admin','synthetic.admin@nsegg.ca','Synthetic Admin',Role.ADMIN,True,False,'now','now',None)
    session=FakeSession(state,fail);ex=RestrictedExecutor(session,rows,plan['review_set_sha256'],actor);repo=SnowflakeRepository(ex)
    authorized=AuthorizedRepository(repo,None,actor)
    return plan,rows,state,actor,session,ex,repo,authorized


def callbacks(rows,actor,review_hash,ex):
    holder={}
    def prepare(tx):
        assert tx is ex
        holder['before']=read_snapshot(ex,rows,'SYNTHETIC')
        return check_before(holder['before'],rows,'SYNTHETIC')
    def verify(tx,before):return check_after(before,read_snapshot(ex,rows,'SYNTHETIC'),rows,review_hash,actor)
    return prepare,verify


def test_26_real_repository_revisions_join_one_snowpark_transaction():
    plan,rows,state,actor,session,ex,repo,authorized=setup();prepare,verify=callbacks(rows,actor,plan['review_set_sha256'],ex)
    result=run_atomic(repo,authorized,rows,plan['review_set_sha256'],prepare,verify)
    assert result['status']=='COMMIT_CONFIRMED'
    assert [r['sql'] for r in ex.control]==['BEGIN','COMMIT']
    assert len(session.state['revisions'])==len(session.state['audits'])==26
    assert {k:sum(x['kind']==k for x in ex.calls) for k in ['LOCK','ACCOUNT','REVISION','AUDIT']}=={'LOCK':1,'ACCOUNT':26,'REVISION':26,'AUDIT':26}
    assert all(params is None for sql,_,params in session.calls if 'UPDATE EFNS_DEV.RAW.INTAKE_LOCK' not in sql)


def test_repeated_same_revision_requests_reuse_receipts_without_new_business_writes():
    plan,rows,state,actor,session,ex,repo,authorized=setup();prepare,verify=callbacks(rows,actor,plan['review_set_sha256'],ex)
    run_atomic(repo,authorized,rows,plan['review_set_sha256'],prepare,verify)
    original=copy.deepcopy(session.state);start=len(ex.calls)
    with repo._continuity_transaction():
        for row in rows:
            result=authorized.revise_record('ACCOUNT',row['source_account_guid'],{FIELD:row['proposed_lookup_id']},reason_for(row,plan['review_set_sha256']),row['proposed_request_id'],expected_updated_at=row['expected_updated_at_ff9'])
            assert result==row['source_account_guid']
    assert session.state==original
    assert [x['kind'] for x in ex.calls[start:]]==['LOCK']


def test_request_identity_cannot_be_reused_with_different_reviewed_content():
    plan,rows,state,actor,session,ex,repo,authorized=setup();prepare,verify=callbacks(rows,actor,plan['review_set_sha256'],ex)
    run_atomic(repo,authorized,rows,plan['review_set_sha256'],prepare,verify)
    original=copy.deepcopy(session.state);row=rows[0]
    with pytest.raises(RepositoryError):
        authorized.revise_record('ACCOUNT',row['source_account_guid'],{FIELD:row['proposed_lookup_id']},'changed reason',row['proposed_request_id'],expected_updated_at=row['expected_updated_at_ff9'])
    assert session.state==original


@pytest.mark.parametrize('failure',['revisions','audits','duplicate_receipt','unexpected_attribute'])
def test_any_partial_failure_or_bad_verification_rolls_back_whole_batch(failure):
    plan,rows,state,actor,session,ex,repo,authorized=setup(failure);prepare,verify=callbacks(rows,actor,plan['review_set_sha256'],ex)
    with pytest.raises(RepositoryError):run_atomic(repo,authorized,rows,plan['review_set_sha256'],prepare,verify)
    assert session.state==state
    assert [r['sql'] for r in ex.control]==['BEGIN','ROLLBACK']


@pytest.mark.parametrize('change',['source_version','parent_version','raw','mapping'])
def test_review_conflict_stops_all_updates_without_rebasing(change):
    plan,rows,state,actor,session,ex,repo,authorized=setup()
    if change=='source_version':session.state['accounts'][1]['UPDATED_AT']='2026-01-01T00:00:00.123456790'
    if change=='parent_version':session.state['accounts'][0]['UPDATED_AT']='2026-01-01T00:00:00.123456790'
    if change=='raw':session.state['raw'][0]['RAW_DATA']['EFNS_SPENTFOWLPLANS']='changed'
    if change=='mapping':session.state['mappings'][0]['TARGET_ID']='wrong'
    outside=copy.deepcopy(session.state);prepare,verify=callbacks(rows,actor,plan['review_set_sha256'],ex)
    with pytest.raises(RepositoryError):run_atomic(repo,authorized,rows,plan['review_set_sha256'],prepare,verify)
    assert session.state==outside and not any(x['kind']=='ACCOUNT' for x in ex.calls)


def test_plan_tampering_is_rejected_before_transaction():
    plan,_=fixture_plan();expected=plan['review_set_sha256'];plan['records'][0]['proposed_lookup_id']='wrong'
    with pytest.raises(RepositoryError):checked_plan(plan,expected,'SYNTHETIC')


def test_unapproved_sql_is_rejected_before_engine():
    *_,session,ex,repo,authorized=setup()
    with pytest.raises(RepositoryError):ex.execute('UPDATE EFNS_DEV.CORE.ACCOUNT SET DESCRIPTION=%s',('wrong',))
    assert session.calls==[]


def test_viewer_cannot_start_batch():
    plan,rows,state,actor,session,ex,repo,authorized=setup()
    authorized.actor=User('viewer','viewer@nsegg.ca','Viewer',Role.REPORTING_VIEWER,True,False,'now','now',None)
    with pytest.raises(Exception):run_atomic(repo,authorized,rows,plan['review_set_sha256'],lambda tx:None,lambda tx,s:None)
    assert session.calls==[]

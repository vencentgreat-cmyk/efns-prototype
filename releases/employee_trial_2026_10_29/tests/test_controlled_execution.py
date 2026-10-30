"""Synthetic only. Fake engine tests count actual SnowparkExecutor submissions, not engine evidence."""
import copy,json,uuid,datetime as dt,io,re
from contextlib import contextmanager
from types import SimpleNamespace
from urllib.parse import urlencode
from zipfile import ZipFile
import pandas as pd
import pytest
from openpyxl import Workbook
from data.controlled_case import build_case,batches,bytehash,digest
from data.count_source_supplement import preview as count_preview
from data.repositories.mock import MockRepository
from data.repositories.snowflake import SnowflakeRepository
from data.repositories.continuity import stable_id
from data.repositories.base import RepositoryError,ConcurrencyError
from data.connection import SnowparkExecutor
from app.services.authorized_repository import AuthorizedRepository
from app.security import Role,User
from tests.test_source_field_fixes import fixture as count_fixture

def uid(text):return str(uuid.uuid5(uuid.NAMESPACE_URL,'controlled-synthetic:'+text)).upper()
ACTOR={'user_id':'synthetic-admin','email':'synthetic.admin@nsegg.ca'}
def authorized(r,role=Role.ADMIN):return AuthorizedRepository(r,None,User(ACTOR['user_id'],ACTOR['email'],'Synthetic operator',role,True,False,'now','now',None))

def count_repo(size=3):
    r=MockRepository();a=count_fixture(size)
    r._migration_raw_rows=a['raw_rows'];r._migration_id_map=a['mappings'];r._migration_files=a['files'];r._migration_batches=a['batches'];r._flock_transactions=pd.DataFrame(a['current_rows'])
    # A source-independent old tag must never be overwritten.
    r._flock_transactions=pd.concat([r._flock_transactions,pd.DataFrame([dict(FLOCK_TRANSACTION_ID=uid('protected'),COUNT_SOURCE_LABEL='Producer',QUANTITY=0,UPDATED_AT='2026-01-01T00:00:00.123456789')])],ignore_index=True)
    return r,count_preview(**a)

def workbook(entity,records):
    w=Workbook();s=w.active;s.title='Source';hidden=w.create_sheet('hidden');hidden.sheet_state='veryHidden'
    pk='new_flocksid' if entity=='FLOCK' else 'new_flocktransactionid'
    fields=[pk,'checksumLogicalName','modifiedon']+(['new_name','new_hatchdate','new_birdcount','new_placementdate','new_account','new_facilityidid'] if entity=='FLOCK' else ['new_date','new_birdcount','new_flocktransactiontype','efc_flockcounttype','new_comments'])
    headers=['(Do Not Modify) ID','(Do Not Modify) Row Checksum','(Do Not Modify) Modified On']+fields[3:]
    hidden['A1']=('new_flocks' if entity=='FLOCK' else 'new_flocktransaction')+':non-executable:'+urlencode(list(zip(fields,headers)))
    s.append(headers)
    for r in records:s.append([r.get(f) for f in fields])
    out=io.BytesIO();w.save(out);return out.getvalue()

def incremental_case():
    a,f,existing,new,tx1,tx2,hold,excluded=[uid(x) for x in ['account','facility','existing','new','tx1','tx2','hold','inactive']]
    stamp='2026-01-01T00:00:00Z';clock='2026-01-01 00:00:00'
    blobs={}
    blobs['flocks.xlsx']=workbook('FLOCK',[dict(new_flocksid=new,checksumLogicalName='original-checksum',modifiedon=clock,new_name='SYNTHETIC NEW',new_hatchdate=dt.date(2025,1,1),new_birdcount=10,new_placementdate=dt.date(2025,2,1),new_account='Synthetic Account',new_facilityidid='Synthetic Facility')])
    records=[dict(new_flocktransactionid=id,checksumLogicalName='c',modifiedon=clock,new_date=dt.date(2025,3,1),new_birdcount=10,new_flocktransactiontype='Count',efc_flockcounttype='Producer',new_comments='Synthetic only') for id in [tx1,tx2,hold]]
    records[-1]['new_date']=None;records[-1]['new_birdcount']=None
    blobs['transactions.xlsx']=workbook('FLOCK_TRANSACTION',records)
    def doc(values):return {'@odata.context':'https://eggfarmersofns.crm.dynamics.com/api/data/v9.2/$metadata#synthetic','value':values}
    fa=doc([dict(new_flocksid=new,_new_account_value=a,_new_facilityidid_value=f,modifiedon=stamp,**{'@odata.etag':'W/"1"'})])
    blobs['flocks.txt']=json.dumps(fa).encode()
    ta=[dict(new_flocktransactionid=id,_new_flockidid_value=parent,modifiedon=stamp,**{'@odata.etag':'W/"2"'}) for id,parent in [(tx1,existing),(tx2,new),(hold,existing),(excluded,existing)]]
    zipped=io.BytesIO()
    with ZipFile(zipped,'w') as z:
        for i,row in enumerate(ta):
            d=doc([row])
            if i<3:d['@odata.nextLink']='https://eggfarmersofns.crm.dynamics.com/api/data/v9.2/new_flocktransactions?$skiptoken='+str(i+2)
            z.writestr(f'page{i}.json',json.dumps(d))
    blobs['links.zip']=zipped.getvalue()
    blobs['status.json']=json.dumps(doc([dict(ta[-1],statecode=1,statuscode=2)])).encode()
    blobs['nulls.json']=json.dumps(doc([dict(ta[-2],new_date=None,new_birdcount=None)])).encode()
    kinds=dict(FLOCK_XLSX='flocks.xlsx',TRANSACTION_XLSX='transactions.xlsx',FLOCK_API='flocks.txt',TRANSACTION_API='links.zip',STATUS_API='status.json',NULL_API='nulls.json')
    policy=dict(original_batch='b',files=[dict(kind=k,name=n,sha256=bytehash(blobs[n]),size=len(blobs[n]),origin='Synthetic fixture only') for k,n in kinds.items()],phase_a_ids=[new],phase_b_ids=[tx1,tx2],hold_ids={hold:'Confirmed source date/quantity NULL'},excluded_ids=[excluded])
    plan=build_case(blobs,policy);r=MockRepository();r._accounts=pd.DataFrame([dict(ACCOUNT_ID=a,UPDATED_AT='2026-01-01T00:00:00.123456789')]);r._facilities=pd.DataFrame([dict(FACILITY_ID=f,ACCOUNT_ID=a,UPDATED_AT='2026-01-01T00:00:00.123456789')]);r._flocks=pd.DataFrame([dict(FLOCK_ID=existing,ACCOUNT_ID=a,FACILITY_ID=f,BIRD_COUNT=20,STATUS='Active',UPDATED_AT='2026-01-01T00:00:00.123456789')]);r._flock_transactions=pd.DataFrame(columns=['FLOCK_TRANSACTION_ID','FLOCK_ID','QUANTITY']);r._migration_batches=[dict(MIGRATION_BATCH_ID='b',STATUS='COMMITTED')];r._import_batches=[];r._raw_rows=[]
    return r,plan,blobs

def independent_memory(repo):
    @contextmanager
    def factory():
        reader=MockRepository()
        for field in ['_flocks','_migration_review_audit','_continuity_rows','_raw_rows','_import_batches']:
            setattr(reader,field,copy.deepcopy(getattr(repo,field)))
        yield reader
    return factory

def prepare_case():
    r,p,blobs=incremental_case();auth=authorized(r);auth.archive_controlled_case(p,blobs,confirmed=True);auth.stage_controlled_case(p,confirmed=True)
    return r,p,auth

def test_count_commit_one_scope_history_atomic_and_retry_has_no_duplicates():
    r,p=count_repo();auth=authorized(r);before=r._flock_transactions.copy(deep=True);raw=copy.deepcopy(r._migration_raw_rows)
    result=auth.commit_count_source_supplement(p,confirmed=True,actor={'user_id':'forged','email':'forged@nsegg.ca'})
    assert result['updated']==3 and r._migration_raw_rows==raw
    assert r._flock_transactions.iloc[-1].COUNT_SOURCE_LABEL=='Producer'
    pd.testing.assert_series_equal(r._flock_transactions.QUANTITY,before.QUANTITY)
    assert len(r._continuity_rows['RECORD_REVISION'])==3 and len(r._migration_review_audit)==4
    assert {x['RECORDED_BY'] for x in r._continuity_rows['RECORD_REVISION']}=={ACTOR['user_id']}
    again=auth.commit_count_source_supplement(p,confirmed=True)
    assert again['already_committed'] and len(r._migration_review_audit)==4

@pytest.mark.parametrize('table',['RECORD_REVISION','AUDIT_EVENT'])
def test_count_history_failure_rolls_back_every_target_and_history(table):
    r,p=count_repo();before=r._flock_transactions.copy(deep=True);original=r._cs_insert
    def fail(tx,t,rows):
        if t==table:raise RepositoryError('Synthetic mandatory history failure')
        return original(tx,t,rows)
    r._cs_insert=fail
    with pytest.raises(RepositoryError):authorized(r).commit_count_source_supplement(p,confirmed=True)
    pd.testing.assert_frame_equal(before,r._flock_transactions)
    assert not r._continuity_rows['RECORD_REVISION'] and not getattr(r,'_migration_review_audit',[])

def test_count_stale_version_source_duplicate_and_existing_label_never_rebase():
    for change in ['version','source','duplicate','existing']:
        r,p=count_repo()
        if change=='version':r._flock_transactions.at[0,'UPDATED_AT']='2026-01-01T00:00:00.123456790'
        if change=='source':r._migration_raw_rows[0]['RAW_DATA']['EFC_FLOCKCOUNTTYPE_DISPLAYNAME']='Changed'
        if change=='duplicate':r._flock_transactions=pd.concat([r._flock_transactions,r._flock_transactions.iloc[:1]],ignore_index=True)
        if change=='existing':r._flock_transactions.at[0,'COUNT_SOURCE_LABEL']='Existing'
        state=r._flock_transactions.copy(deep=True)
        with pytest.raises(RepositoryError):authorized(r).commit_count_source_supplement(p,confirmed=True)
        pd.testing.assert_frame_equal(state,r._flock_transactions)

def test_13556_mock_metadata_repairs_do_not_touch_flocks_and_receipt_is_bounded():
    r,p=count_repo(13556);flocks=r._flocks.copy(deep=True);progress=[]
    result=authorized(r).commit_count_source_supplement(p,confirmed=True,progress_callback=lambda event:progress.append(event))
    assert result['updated']==13556
    assert len(r._continuity_rows['RECORD_REVISION'])==13556 and len(r._migration_review_audit)==13557
    assert len(json.dumps(r._migration_review_audit[-1]['DETAILS']).encode())<4096
    assert len([x for x in progress if not x['committed']])==28 and progress[-1]['committed']
    pd.testing.assert_frame_equal(flocks,r._flocks)

def test_incremental_archives_all_original_bytes_and_only_stages_before_commit():
    r,p,blobs=incremental_case();before=r._flocks.copy(deep=True);auth=authorized(r)
    metas=auth.archive_controlled_case(p,blobs,confirmed=True)
    for meta in metas:assert r.get_source_file_bytes(meta['SOURCE_FILE_ID'])==blobs[meta['ORIGINAL_FILENAME']]
    auth.stage_controlled_case(p,confirmed=True);auth.stage_controlled_case(p,confirmed=True)
    assert len(r._raw_rows)==4 and len(r._import_batches)==1 and len(r._flock_transactions)==0
    pd.testing.assert_frame_equal(before,r._flocks)

def test_phases_require_independent_verification_and_leave_holds_and_existing_flock_unchanged():
    r,p,auth=prepare_case();existing=r._flocks.copy(deep=True)
    with pytest.raises(RepositoryError):auth.preview_controlled_incremental(p,'B')
    a=auth.preview_controlled_incremental(p,'A');auth.commit_controlled_incremental(p,'A',a['review_token'],confirmed=True)
    assert len(r._flocks)==2 and len(r._flock_transactions)==0 and len(r._continuity_rows['FLOCK_EVENT'])==0
    with pytest.raises(RepositoryError,match='independent'):auth.preview_controlled_incremental(p,'B')
    r._controlled_independent_reader=independent_memory(r);b=auth.preview_controlled_incremental(p,'B')
    assert b['count']==2
    auth.commit_controlled_incremental(p,'B',b['review_token'],confirmed=True)
    assert len(r._flock_transactions)==2 and len(r._flocks)==2
    for key,value in existing.iloc[0].to_dict().items():assert str(r._flocks.iloc[0][key])==str(value)
    assert sum(x['VALIDATION_STATUS']=='HOLD' for x in r._raw_rows)==1
    assert r._import_batches[0]['ROW_COUNT']==3 and r._import_batches[0]['STATUS']=='Committed'
    before=(len(r._flock_transactions),len(r._migration_review_audit),len(r._continuity_rows['RECORD_REVISION']))
    assert auth.commit_controlled_incremental(p,'B',b['review_token'],confirmed=True)['already_committed']
    assert before==(len(r._flock_transactions),len(r._migration_review_audit),len(r._continuity_rows['RECORD_REVISION']))

def test_source_tamper_and_same_session_verifier_cannot_pass():
    r,p,blobs=incremental_case();bad=dict(blobs);bad['flocks.xlsx']+=b'changed'
    with pytest.raises(RepositoryError):authorized(r).archive_controlled_case(p,bad,confirmed=True)
    assert not r._continuity_rows['SOURCE_FILE']
    r,p,auth=prepare_case();a=auth.preview_controlled_incremental(p,'A');auth.commit_controlled_incremental(p,'A',a['review_token'],confirmed=True)
    @contextmanager
    def same():yield r
    r._controlled_independent_reader=same
    with pytest.raises(RepositoryError,match='reused'):auth.preview_controlled_incremental(p,'B')

def test_incremental_conflict_stale_parent_and_audit_failure_are_atomic():
    for change in ['parent','existing','audit']:
        r,p,auth=prepare_case();a=auth.preview_controlled_incremental(p,'A')
        if change=='parent':r._facilities.at[0,'UPDATED_AT']='2026-01-01T00:00:00.123456790'
        if change=='existing':r._flocks=pd.concat([r._flocks,pd.DataFrame([p['records'][0]['core']])],ignore_index=True)
        if change=='audit':
            original=r._cs_insert
            def fail(tx,table,rows):
                if table=='AUDIT_EVENT':raise RepositoryError('Synthetic audit failure')
                return original(tx,table,rows)
            r._cs_insert=fail
        snapshot=r._flocks.copy(deep=True);tracking=copy.deepcopy(r._raw_rows)
        with pytest.raises(RepositoryError):auth.commit_controlled_incremental(p,'A',a['review_token'],confirmed=True)
        pd.testing.assert_frame_equal(snapshot,r._flocks);assert r._raw_rows==tracking
        assert not r._continuity_rows['RECORD_REVISION']

@pytest.mark.parametrize('method,args',[('commit_count_source_supplement',(None,)),('archive_controlled_case',(None,None)),('stage_controlled_case',(None,)),('commit_controlled_incremental',(None,'A','token'))])
def test_readonly_role_cannot_execute_any_controlled_action(method,args):
    r=MockRepository()
    with pytest.raises(RepositoryError,match='permission'):getattr(authorized(r,Role.REPORTING_VIEWER),method)(*args,confirmed=True)

# Stateful Snowpark test double. Parses only our fixed SQL shapes; not engine syntax/concurrency proof.
class Engine:
    def __init__(self,r,fail=None):
        self.data={}
        from data.repositories.controlled_supplements import TABLES
        for table,(_,_,attribute) in TABLES.items():
            values=r._continuity_rows[table] if attribute is None else getattr(r,attribute,[])
            self.data[table]=copy.deepcopy(values.to_dict('records') if isinstance(values,pd.DataFrame) else values)
        for table,attribute in [('MIGRATION_RAW_ROW','_migration_raw_rows'),('MIGRATION_ID_MAP','_migration_id_map'),('MIGRATION_FILE','_migration_files'),('MIGRATION_BATCH','_migration_batches')]:self.data[table]=copy.deepcopy(getattr(r,attribute,[]))
        self.calls=[];self.saved=None;self.fail=fail;self.locked=0
    def sql(self,sql,params=None):
        statement=SimpleNamespace()
        def collect(statement_params=None):
            self.calls.append((sql,params,statement_params));values=self.run(sql,params or [],statement_params)
            statement.schema=SimpleNamespace(fields=[SimpleNamespace(name=k) for k in (values[0] if values else {})]);return values
        statement.collect=collect;return statement
    def run(self,sql,params,statement_params):
        if sql=='BEGIN':assert self.saved is None;self.saved=copy.deepcopy(self.data);return []
        if sql=='COMMIT':self.saved=None;return []
        if sql=='ROLLBACK':
            if self.saved is not None:self.data=self.saved;self.saved=None
            return []
        if sql.startswith('UPDATE EFNS_DEV.RAW.INTAKE_LOCK'):
            assert statement_params=={'STATEMENT_TIMEOUT_IN_SECONDS':'30'};self.locked+=1;return [{'number of rows updated':1}]
        if 'CURRENT_ORGANIZATION_NAME()' in sql:return [dict(ORG='QDCTNKN',ACCOUNT_NAME='UW19058',LOCATOR='CB12755',REGION='AWS_CA_CENTRAL_1',DB='EFNS_DEV',SESSION_ID='synthetic-snowpark')]
        if sql.startswith('/*cs:insert:'):
            table=sql.split(':')[2].split('*/')[0];part=json.loads(params[0]);assert 'IFF(IS_NULL_VALUE' in sql and len(params[0].encode())<=1024*1024
            if self.fail==table:raise RuntimeError('Synthetic mandatory engine failure')
            for row in part:
                times={'CREATED_AT','UPDATED_AT'} if table in {'FLOCK','FLOCK_TRANSACTION','IMPORT_RAW_ROW'} else {'RECORDED_AT'} if table=='RECORD_REVISION' else {'OCCURRED_AT'} if table=='AUDIT_EVENT' else {'UPLOADED_AT'} if table=='SOURCE_FILE' else {'CREATED_AT','UPDATED_AT','UPLOAD_TIMESTAMP'}
                self.data[table].append(dict(row,**{f:'2026-10-29T00:00:00.123456789' for f in times}))
            return [{'number of rows inserted':len(part)}]
        if sql.startswith('/*cs:label-cas*/'):
            part=json.loads(params[0]);count=0
            for item in part:
                found=[r for r in self.data['FLOCK_TRANSACTION'] if r['FLOCK_TRANSACTION_ID'].upper()==item['ID']]
                for r in found:
                    if pd.Timestamp(r['UPDATED_AT'])==pd.Timestamp(item['VERSION']) and not r['COUNT_SOURCE_LABEL']:
                        r['COUNT_SOURCE_LABEL']=item['LABEL'];r['UPDATED_AT']=(pd.Timestamp(r['UPDATED_AT'])+pd.Timedelta(1,unit='ns')).isoformat();count+=1
            return [{'number of rows updated':count}]
        if sql.startswith('/*cs:mark-raw*/'):
            ids=set(json.loads(params[1]));count=0
            for row in self.data['IMPORT_RAW_ROW']:
                if row['IMPORT_ID']==params[0] and row['RAW_ROW_ID'] in ids and row['VALIDATION_STATUS']=='NEW':row['VALIDATION_STATUS']='COMMITTED';count+=1
            return [{'number of rows updated':count}]
        if sql.startswith('/*cs:mark-batch*/'):
            count=0
            for row in self.data['IMPORT_BATCH']:
                if row['IMPORT_ID']==params[2] and row['FILE_HASH']==params[3]:row['STATUS']=params[0];row['ROW_COUNT']=params[1];count+=1
            return [{'number of rows updated':count}]
        match=re.search(r'FROM EFNS_DEV\.(?:CORE|RAW|APP)\.(\w+)',sql)
        if not match:raise AssertionError(sql)
        table=match[1];records=copy.deepcopy(self.data[table])
        if table in {'MIGRATION_RAW_ROW','MIGRATION_ID_MAP'}:
            ids=set(json.loads(params[1]));return [r for r in records if r['MIGRATION_BATCH_ID']==params[0] and r['SOURCE_ENTITY']=='FLOCK_TRANSACTION' and r['SOURCE_ID'].upper() in ids]
        if table in {'MIGRATION_FILE','MIGRATION_BATCH'}:return [r for r in records if r['MIGRATION_BATCH_ID']==params[0]]
        from data.repositories.controlled_supplements import TABLES
        key=TABLES[table][1]
        if 'PARSE_JSON' in sql:
            ids={str(x).upper() for x in json.loads(params[0])};records=[r for r in records if str(r[key]).upper() in ids]
        elif params:records=[r for r in records if r.get('IMPORT_ID')==params[0] or r.get(key)==params[0]]
        return records

def test_snowpark_batched_13556_count_service_has_bounded_real_executor_requests(tmp_path):
    import time
    from pathlib import Path
    memory,p=count_repo(13556);engine=Engine(memory);repo=SnowflakeRepository(SnowparkExecutor(engine));started=time.perf_counter();result=authorized(repo).commit_count_source_supplement(p,confirmed=True);elapsed=time.perf_counter()-started
    assert result['updated']==13556
    statements=[sql for sql,_,_ in engine.calls]
    assert statements.count('BEGIN')==statements.count('COMMIT')==1 and 'ROLLBACK' not in statements
    assert sum(sql.startswith('/*cs:label-cas*/') for sql in statements)==28
    assert len(engine.calls)<160
    metrics=dict(source='Stateful fake session + actual SnowparkExecutor, NOT real engine benchmark',rows=13556,SQL_submissions=len(engine.calls),label_update_submissions=28,elapsed_local_fake_seconds=elapsed,statement_param_timeout_only_on_lock=all(params is None for sql,_,params in engine.calls if 'UPDATE EFNS_DEV.RAW.INTAKE_LOCK' not in sql),max_bind_bytes=max(len(p[0].encode()) for sql,p,_ in engine.calls if p and isinstance(p[0],str) and sql.startswith('/*cs:')))
    (tmp_path/'controlled_fake_metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
    assert all(not sql.startswith(('ALTER','SHOW','CREATE')) for sql in statements)
    before=len(engine.calls);assert authorized(repo).commit_count_source_supplement(p,confirmed=True)['already_committed']
    assert not any(s.startswith(('/*cs:insert','/*cs:label','BEGIN')) for s,_,_ in engine.calls[before:])

def test_actual_snowpark_executor_failure_rolls_back_all_rows_in_double():
    memory,p=count_repo(501);engine=Engine(memory,'AUDIT_EVENT');before=copy.deepcopy(engine.data);repo=SnowflakeRepository(SnowparkExecutor(engine))
    with pytest.raises(RepositoryError):authorized(repo).commit_count_source_supplement(p,confirmed=True)
    assert engine.data==before
    assert [s for s,_,_ in engine.calls if s in {'BEGIN','COMMIT','ROLLBACK'}]==['BEGIN','ROLLBACK']


def test_snowpark_incremental_both_phases_use_one_transaction_and_never_update_flock():
    memory,p,_=incremental_case();auth=authorized(memory)
    # Source archive/parser behavior is tested separately; seed their preserved results.
    r,p,auth=prepare_case();engine=Engine(r);repo=SnowflakeRepository(SnowparkExecutor(engine));repo._cs_restore_case=lambda _:p
    a=authorized(repo).preview_controlled_incremental(p,'A');authorized(repo).commit_controlled_incremental(p,'A',a['review_token'],confirmed=True)
    # Independent proof is a separate fake session sharing committed data, not native evidence.
    @contextmanager
    def reader():
        other_engine=Engine(r);other_engine.data=engine.data
        base=other_engine.run
        def run(sql,params,statement_params):
            if 'CURRENT_ORGANIZATION_NAME()' in sql:return [dict(ORG='QDCTNKN',ACCOUNT_NAME='UW19058',LOCATOR='CB12755',REGION='AWS_CA_CENTRAL_1',DB='EFNS_DEV',SESSION_ID='independent-synthetic')]
            return base(sql,params,statement_params)
        other_engine.run=run
        yield SnowflakeRepository(SnowparkExecutor(other_engine))
    repo._controlled_independent_reader=reader
    b=authorized(repo).preview_controlled_incremental(p,'B');before=copy.deepcopy(engine.data['FLOCK'])
    authorized(repo).commit_controlled_incremental(p,'B',b['review_token'],confirmed=True)
    assert engine.data['FLOCK']==before
    assert len(engine.data['FLOCK_TRANSACTION'])==2
    statements=[s for s,_,_ in engine.calls]
    assert statements.count('BEGIN')==statements.count('COMMIT')==2
    assert not any('UPDATE EFNS_DEV.CORE.FLOCK ' in s for s in statements)
    assert len(engine.data['RECORD_REVISION'])==3
    assert sum(x['VALIDATION_STATUS']=='HOLD' for x in engine.data['IMPORT_RAW_ROW'])==1


def test_phase_b_failure_rolls_back_transactions_history_and_tracking():
    r,p,auth=prepare_case();a=auth.preview_controlled_incremental(p,'A');auth.commit_controlled_incremental(p,'A',a['review_token'],confirmed=True)
    r._controlled_independent_reader=independent_memory(r);b=auth.preview_controlled_incremental(p,'B')
    rows=copy.deepcopy(r._raw_rows);batches=copy.deepcopy(r._import_batches);audits=copy.deepcopy(r._migration_review_audit);revs=copy.deepcopy(r._continuity_rows['RECORD_REVISION']);flocks=r._flocks.copy(deep=True)
    original=r._cs_insert
    def fail(tx,table,values):
        if table=='AUDIT_EVENT':raise RepositoryError('Synthetic mandatory audit failure')
        return original(tx,table,values)
    r._cs_insert=fail
    with pytest.raises(RepositoryError):auth.commit_controlled_incremental(p,'B',b['review_token'],confirmed=True)
    assert len(r._flock_transactions)==0 and r._raw_rows==rows and r._import_batches==batches and r._migration_review_audit==audits and r._continuity_rows['RECORD_REVISION']==revs
    pd.testing.assert_frame_equal(flocks,r._flocks)


def test_committed_history_tamper_cannot_be_replayed():
    r,p=count_repo();auth=authorized(r);auth.commit_count_source_supplement(p,confirmed=True)
    r._continuity_rows['RECORD_REVISION'][0]['REASON']='tampered'
    with pytest.raises(RepositoryError,match='digest'):auth.commit_count_source_supplement(p,confirmed=True)
    assert len(r._migration_review_audit)==4


def test_archive_metadata_failure_retains_original_bytes_and_retry_registers_once():
    r,p,blobs=incremental_case();original=r._cs_insert
    def fail(tx,t,rows):
        if t=='SOURCE_FILE':raise RepositoryError('Synthetic registration failure')
        return original(tx,t,rows)
    r._cs_insert=fail
    with pytest.raises(RepositoryError):authorized(r).archive_controlled_case(p,blobs,confirmed=True)
    assert r._original_bytes and not r._continuity_rows['SOURCE_FILE']
    r._cs_insert=original;authorized(r).archive_controlled_case(p,blobs,confirmed=True);authorized(r).archive_controlled_case(p,blobs,confirmed=True)
    assert len(r._continuity_rows['SOURCE_FILE'])==6


def test_staged_tracking_corruption_blocks_independent_verification():
    r,p,auth=prepare_case();a=auth.preview_controlled_incremental(p,'A');auth.commit_controlled_incremental(p,'A',a['review_token'],confirmed=True)
    r._raw_rows[0]['VALIDATION_STATUS']='NEW';r._controlled_independent_reader=independent_memory(r)
    with pytest.raises(RepositoryError,match='tracking'):auth.preview_controlled_incremental(p,'B')


def test_cli_write_switch_is_required_before_any_connection(monkeypatch):
    from scripts import controlled_historical_supplement as cli
    monkeypatch.setattr(cli,'inputs',lambda *a:(None,None,None))
    monkeypatch.setattr(cli,'company',lambda *a:pytest.fail('No connection permitted'))
    with pytest.raises(SystemExit) as info:cli.main(['--manifest','synthetic.json','--action','commit-a'])
    assert info.value.code==2


def test_case_plan_survives_canonical_json_save_and_source_reparse():
    from data.controlled_case import validate_case
    from data.source_evidence import evidence_json
    _,p,blobs=incremental_case();saved=json.loads(evidence_json(p));validate_case(saved)
    assert build_case(blobs,saved['policy'])['case_hash']==saved['case_hash']


def test_incremental_failed_confirmation_never_begins_writing():
    r,p,auth=prepare_case();a=auth.preview_controlled_incremental(p,'A');before=r._flocks.copy(deep=True)
    with pytest.raises(RepositoryError,match='confirmation'):auth.commit_controlled_incremental(p,'A',a['review_token'])
    pd.testing.assert_frame_equal(before,r._flocks)
    assert not r._continuity_rows['RECORD_REVISION']


def test_release_manifest_includes_new_mapping_and_all_runtime_modules():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1];spec=(root/'snowflake.yml').read_text()
    assert 'src: config/eims_migration_mapping_v3_count_source_r1.json' in spec
    assert 'dest: config/eims_migration_mapping_v3_count_source_r1.json' in spec
    for relative in ['data/controlled_case.py','data/controlled_primitives.py','data/repositories/controlled_supplements.py','app/services/facility_source_description.py']:
        assert (root/relative).is_file()
    assert 'src: data/*.py' in spec and 'src: data/repositories/*.py' in spec
    assert '.local' not in spec and 'tests/' not in spec


def two_phase_a_case():
    from data.controlled_case import workbook_rows
    r,p,blobs=incremental_case();policy=copy.deepcopy(p['policy']);new=uid('second-new-flock')
    rows=[copy.deepcopy(v['logical']) for v in workbook_rows(blobs['flocks.xlsx'],'FLOCK').values()]
    extra=dict(rows[0],new_flocksid=new,new_name='SECOND SYNTHETIC FLOCK');rows.append(extra)
    blobs['flocks.xlsx']=workbook('FLOCK',rows)
    api=json.loads(blobs['flocks.txt']);api['value'].append(dict(api['value'][0],new_flocksid=new));blobs['flocks.txt']=json.dumps(api).encode()
    policy['phase_a_ids'].append(new)
    for spec in policy['files']:spec.update(sha256=bytehash(blobs[spec['name']]),size=len(blobs[spec['name']]))
    p=build_case(blobs,policy);auth=authorized(r);auth.archive_controlled_case(p,blobs,confirmed=True);auth.stage_controlled_case(p,confirmed=True)
    a=auth.preview_controlled_incremental(p,'A');auth.commit_controlled_incremental(p,'A',a['review_token'],confirmed=True)
    return r,p,auth


def test_phase_a_verifier_and_b_ignore_only_query_row_order():
    r,p,auth=two_phase_a_case();original=r._cs_read;flip=[False]
    def unordered(table,*args,**kwargs):
        rows=original(table,*args,**kwargs)
        if table=='FLOCK':flip[0]=not flip[0];return list(reversed(rows)) if flip[0] else rows
        return rows
    r._cs_read=unordered;r._controlled_independent_reader=independent_memory(r)
    first=r._cs_independent_a(p);second=r._cs_independent_a(p)
    assert first['targets_sha256']==second['targets_sha256']
    a_ids=p['policy']['phase_a_ids'];assert r._cs_flock_targets_digest(a_ids)==first['targets_sha256']
    b=auth.preview_controlled_incremental(p,'B');auth.commit_controlled_incremental(p,'B',b['review_token'],confirmed=True)
    assert len(r._flock_transactions)==2


@pytest.mark.parametrize('field,value',[('BIRD_COUNT',11),('UPDATED_AT','2099-01-01T00:00:00.123456789')])
def test_phase_a_actual_field_or_ff9_change_is_not_order_noise(field,value):
    r,p,auth=two_phase_a_case();ids=p['policy']['phase_a_ids'];before=r._cs_flock_targets_digest(ids)
    index=r._flocks.index[r._flocks.FLOCK_ID==ids[0]][0]
    if field=='UPDATED_AT':value=(pd.Timestamp(r._flocks.at[index,field])+pd.Timedelta(1,unit='ns')).isoformat()
    r._flocks.at[index,field]=value
    assert r._cs_flock_targets_digest(ids)!=before
    r._controlled_independent_reader=independent_memory(r)
    with pytest.raises(RepositoryError):auth.preview_controlled_incremental(p,'B')
    assert len(r._flock_transactions)==0


def phase_b_ready():
    r,p,auth=prepare_case();a=auth.preview_controlled_incremental(p,'A');auth.commit_controlled_incremental(p,'A',a['review_token'],confirmed=True)
    r._controlled_independent_reader=independent_memory(r)
    return r,p,auth


def break_parent_relationship(r,kind):
    existing=r._flocks.index[0]
    if kind=='ownership':r._facilities.at[0,'ACCOUNT_ID']=uid('wrong-owner')
    elif kind=='facility-missing':r._facilities=r._facilities.iloc[0:0].copy()
    elif kind=='facility-duplicate':r._facilities=pd.concat([r._facilities,r._facilities.iloc[[0]]],ignore_index=True)
    elif kind=='parent-missing':r._flocks=r._flocks.drop(index=existing).reset_index(drop=True)
    elif kind=='parent-duplicate':r._flocks=pd.concat([r._flocks,r._flocks.iloc[[existing]]],ignore_index=True)
    elif kind=='facility-null':r._flocks.at[existing,'FACILITY_ID']=None
    else:raise AssertionError(kind)


@pytest.mark.parametrize('when',['before-preview','after-preview'])
@pytest.mark.parametrize('kind',['ownership','facility-missing','facility-duplicate','parent-missing','parent-duplicate'])
def test_phase_b_rechecks_all_parent_facilities_before_preview_and_in_submit(when,kind):
    r,p,auth=phase_b_ready()
    token=auth.preview_controlled_incremental(p,'B')['review_token'] if when=='after-preview' else None
    before=(copy.deepcopy(r._raw_rows),copy.deepcopy(r._migration_review_audit),copy.deepcopy(r._continuity_rows['RECORD_REVISION']))
    break_parent_relationship(r,kind)
    with pytest.raises(RepositoryError):
        if when=='before-preview':auth.preview_controlled_incremental(p,'B')
        else:auth.commit_controlled_incremental(p,'B',token,confirmed=True)
    assert len(r._flock_transactions)==0
    assert before==(r._raw_rows,r._migration_review_audit,r._continuity_rows['RECORD_REVISION'])


def test_facility_same_owner_but_ff9_changes_after_preview_rejects_stale_token():
    r,p,auth=phase_b_ready();b=auth.preview_controlled_incremental(p,'B')
    r._facilities.at[0,'UPDATED_AT']=(pd.Timestamp(r._facilities.at[0,'UPDATED_AT'])+pd.Timedelta(1,unit='ns')).isoformat()
    with pytest.raises(ConcurrencyError,match='versions changed'):auth.commit_controlled_incremental(p,'B',b['review_token'],confirmed=True)
    assert len(r._flock_transactions)==0


def test_historical_null_facility_is_explicit_preserved_and_does_not_block_b():
    r,p,auth=phase_b_ready();r._flocks.at[0,'FACILITY_ID']=None
    b=auth.preview_controlled_incremental(p,'B')
    assert b['parent_facility_null_ids']==[r._flocks.iloc[0].FLOCK_ID]
    auth.commit_controlled_incremental(p,'B',b['review_token'],confirmed=True)
    assert r._flocks.iloc[0].FACILITY_ID is None and len(r._flock_transactions)==2
    history=r._continuity_rows['RECORD_REVISION']
    assert any(x['AFTER_DATA']['_CONTROLLED_SUPPLEMENT']['source'].get('parent_facility_state')=='NOT_PROVIDED_HISTORICAL' for x in history)


@pytest.mark.parametrize('initial_null',[False,True])
def test_parent_facility_null_to_known_or_known_to_null_after_preview_needs_new_review(initial_null):
    r,p,auth=phase_b_ready();known=r._flocks.at[0,'FACILITY_ID']
    if initial_null:r._flocks.at[0,'FACILITY_ID']=None
    b=auth.preview_controlled_incremental(p,'B');r._flocks.at[0,'FACILITY_ID']=known if initial_null else None
    with pytest.raises(ConcurrencyError):auth.commit_controlled_incremental(p,'B',b['review_token'],confirmed=True)
    assert len(r._flock_transactions)==0


def test_create_history_retains_json_null_for_required_variant_before_snapshot():
    r,p,auth=prepare_case();engine=Engine(r);repo=SnowflakeRepository(SnowparkExecutor(engine));repo._cs_restore_case=lambda _:p
    a=authorized(repo).preview_controlled_incremental(p,'A');authorized(repo).commit_controlled_incremental(p,'A',a['review_token'],confirmed=True)
    sqls=[sql for sql,_,_ in engine.calls if sql.startswith('/*cs:insert:RECORD_REVISION*/')]
    assert sqls and all('v.VALUE:BEFORE_DATA' in sql and 'IS_NULL_VALUE(v.VALUE:BEFORE_DATA)' not in sql for sql in sqls)
    assert engine.data['RECORD_REVISION'][0]['BEFORE_DATA'] is None

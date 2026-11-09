"""Apply only saved exact matches; verify/copy existing original bytes, never RAW rows."""
import hashlib
import json
from pathlib import Path
import sys

import snowflake.connector

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from data.connection import ConnectorExecutor
from data.repositories.snowflake import SnowflakeRepository
from data.producer_identity import resolve_producer,text

out=Path('.local/continuity-20261014')
preview=json.loads((out/'producer_preview.json').read_text(encoding='utf-8'))
conn=snowflake.connector.connect(connection_name='efns-dev',role='EFNS_DEV_DEPLOYER',warehouse='EFNS_DEV_WH',database='EFNS_DEV',autocommit=False)
ex=ConnectorExecutor(lambda:conn);result={'archives':[],'original_gaps':[],'matches':[]}
projection="OBJECT_DELETE(OBJECT_CONSTRUCT_KEEP_NULL(*),'PRODUCER_ACCOUNT_ID','MATCH_STATUS','MATCH_METHOD','MATCH_BASIS','UPDATED_AT','SOURCE_FILE_ID','RAW_ROW_ID')"
try:
 ex.execute('USE SECONDARY ROLES NONE')
 context=ex.query('SELECT CURRENT_ACCOUNT_NAME() ACCOUNT_NAME,CURRENT_DATABASE() DB,CURRENT_ROLE() ROLE').iloc[0].to_dict()
 if context['ACCOUNT_NAME']!='RC34234' or context['DB']!='EFNS_DEV':raise ValueError('DEV guard failed')
 repo=SnowflakeRepository(ex)
 result['context']=context
 result['before_nonmatch_hash']=ex.query(f'SELECT COUNT(*) N,HASH_AGG({projection}) H FROM EFNS_DEV.CORE.PRODUCTION_RECORD').iloc[0].to_dict()
 with ex.transaction():
  accounts=repo.get_accounts()
  for proposed in preview['rows']:
   frame=ex.query('SELECT * FROM EFNS_DEV.CORE.PRODUCTION_RECORD WHERE PRODUCTION_ID=%s',(proposed['PRODUCTION_ID'],))
   if len(frame)!=1:raise ValueError('Saved preview row is missing/ambiguous')
   current=frame.iloc[0].to_dict()
   if text(current.get('PRODUCER_ACCOUNT_ID')):
    if current['PRODUCER_ACCOUNT_ID']!=proposed['account_id']:raise ValueError('Producer attribution changed since preview; no overwrite permitted')
    result['matches'].append({'production_id':proposed['PRODUCTION_ID'],'handling':'ALREADY_LINKED'})
    continue
   decision=resolve_producer(current,accounts)
   if decision['status']!=proposed['status'] or decision['account_id']!=proposed['account_id']:raise ValueError('Exact candidate set changed since preview')
   applied=repo.match_production_producer(proposed['PRODUCTION_ID'],actor='SYSTEM_EXACT_MATCH_20261014')
   result['matches'].append({'production_id':proposed['PRODUCTION_ID'],'status':applied['status'],'handling':'AUTO'})
 result['after_nonmatch_hash']=ex.query(f'SELECT COUNT(*) N,HASH_AGG({projection}) H FROM EFNS_DEV.CORE.PRODUCTION_RECORD').iloc[0].to_dict()
 if result['before_nonmatch_hash']!=result['after_nonmatch_hash']:raise ValueError('Non-matching production values changed; inspect evidence')
 originals=ex.query("SELECT SOURCE_FILENAME,FILE_HASH,FILE_SIZE_BYTES,STAGE_PATH FROM EFNS_DEV.RAW.MIGRATION_FILE WHERE MIGRATION_BATCH_ID=%s",('DEV_MIGRATION_255ef9b50a52e766a7dff9',))
 for original in originals.to_dict('records'):
  try:
   with ex.get_stream(original['STAGE_PATH']) as stream:content=stream.read()
   if len(content)!=original['FILE_SIZE_BYTES'] or hashlib.sha256(content).hexdigest()!=original['FILE_HASH']:raise ValueError('Original checksum/size mismatch')
   archived=repo.archive_source_file(original['SOURCE_FILENAME'],content,'HISTORICAL_EIMS_ARCHIVE',actor='SYSTEM_ARCHIVE_20261014')
   result['archives'].append({'batch_id':'DEV_MIGRATION_255ef9b50a52e766a7dff9','filename':original['SOURCE_FILENAME'],'source_file_id':archived['SOURCE_FILE_ID'],'byte_exact':True,'original_stage_unchanged':True})
  except Exception as exc:
   result['original_gaps'].append({'filename':original['SOURCE_FILENAME'],'error_type':type(exc).__name__,'original_stage_retained':True})
 workbook_batches=ex.query("SELECT IMPORT_ID,FILENAME,FILE_HASH,FILE_SIZE_BYTES FROM EFNS_DEV.RAW.IMPORT_BATCH WHERE SOURCE NOT ILIKE '%migration%'")
 downloads=Path.home()/'Downloads'
 for batch in workbook_batches.to_dict('records'):
  filename=Path(str(batch['FILENAME'])).name
  candidates=[path for path in downloads.glob(filename) if path.is_file()] if filename and '*' not in filename else []
  found=None
  for path in candidates:
   content=path.read_bytes()
   if hashlib.sha256(content).hexdigest()==batch['FILE_HASH']:found=(path,content);break
  if found:
   archived=repo.archive_source_file(filename,found[1],'LEGACY_PRODUCTION_ARCHIVE',actor='SYSTEM_ARCHIVE_20261014')
   result['archives'].append({'import_id':batch['IMPORT_ID'],'filename':filename,'source_file_id':archived['SOURCE_FILE_ID'],'byte_exact':True,'proof':'Original saved hash verified against local file'})
  else:result['original_gaps'].append({'import_id':batch['IMPORT_ID'],'filename':filename,'reason':'No matching original bytes verified in Downloads; RAW is not an original file'})
finally:
 conn.close()
 destination=out/'applied_evidence.json'
 if destination.exists() and json.loads(destination.read_text(encoding='utf-8')).get('archives'):
  destination=out/'applied_evidence_archive_retry.json'
 destination.write_text(json.dumps(result,default=str,indent=2),encoding='utf-8')
print(json.dumps({'matches':{status:sum(row.get('status')==status for row in result['matches']) for status in ['UNIQUE_MATCHED','MULTIPLE_CANDIDATES','MISSING_SOURCE_ID']},'verified_originals':len(result['archives']),'original_gaps':len(result['original_gaps']),'nonmatch_values_unchanged':result['before_nonmatch_hash']==result['after_nonmatch_hash']}))

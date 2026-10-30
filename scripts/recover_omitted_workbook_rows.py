"""Append RAW-only evidence for verified omitted worksheet rows; no CORE writes."""
import json
from io import BytesIO
from pathlib import Path
import sys

import snowflake.connector
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from data.connection import ConnectorExecutor
from data.repositories.snowflake import SnowflakeRepository
from data.repositories.continuity import stable_id
from data.importing import read_eims_workbook
from data.production_intake import prepare_workbook

root=Path('.local/continuity-20261014')
checks=json.loads((root/'recovered_workbook_check.json').read_text(encoding='utf-8'))
conn=snowflake.connector.connect(connection_name='efns-dev',role='EFNS_DEV_DEPLOYER',warehouse='EFNS_DEV_WH',database='EFNS_DEV',autocommit=False)
ex=ConnectorExecutor(lambda:conn);results=[]
try:
 ex.execute('USE SECONDARY ROLES NONE')
 context=ex.query('SELECT CURRENT_ACCOUNT_NAME() ACCOUNT_NAME,CURRENT_DATABASE() DB').iloc[0]
 if context.ACCOUNT_NAME!='RC34234' or context.DB!='EFNS_DEV':raise ValueError('DEV guard failed')
 repo=SnowflakeRepository(ex)
 for check in checks:
  missing=check['not_previously_saved_row_numbers']
  if not missing:continue
  raw=read_eims_workbook(BytesIO(repo.get_source_file_bytes(check['archived_file_id'])))
  omitted=raw[raw.SOURCE_ROW_NUMBER.isin(missing)]
  records,rows,errors,_=prepare_workbook(omitted,check['archived_file_id'],repo.get_accounts())
  # This recovery deliberately cannot write any normalized record.
  for row in rows:
   row['TARGET_ENTITY']=None;row['TARGET_ID']=None
   row['VALIDATION_STATUS']='PENDING_REVIEW'
   row['VALIDATION_MESSAGES'].append('Recovered nonempty worksheet row omitted by the previous reader; review its source role before any business import.')
  supplement=stable_id('raw-omission-review',check['import_id'],check['archived_file_id'])
  with repo._continuity_transaction() as tx:
   found=tx.query('SELECT IMPORT_ID FROM EFNS_DEV.RAW.IMPORT_BATCH WHERE IMPORT_ID=%s',(supplement,))
   if found.empty:
    repo._insert_batch(tx,supplement,dict(FILENAME='Recovered worksheet RAW review',SOURCE='RAW-only supplemental review',SOURCE_FILE_ID=check['archived_file_id'],SOURCE_RECORD_COUNT=len(rows),ROW_COUNT=0,ERROR_COUNT=len(errors),STATUS='ReviewOnly',NOTES=json.dumps({'original_import_id':check['import_id'],'row_numbers':missing,'basis':'Verified original bytes; physical worksheet rows absent from old RAW; not claimed business observations'})))
    repo._insert_raw(tx,supplement,rows)
   saved=repo.get_raw_rows(supplement)
   if len(saved)!=len(rows) or set(saved.SOURCE_ROW_NUMBER)!=set(missing):raise ValueError('Supplement source rows do not reconcile')
  results.append(dict(original_import_id=check['import_id'],supplement_import_id=supplement,source_file_id=check['archived_file_id'],raw_rows=len(rows),source_rows=missing,core_rows_written=0,status='ReviewOnly',technical_errors=len(errors),business_role_not_inferred=True))
finally:conn.close()
(root/'omitted_rows_recovery.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print(json.dumps(results))

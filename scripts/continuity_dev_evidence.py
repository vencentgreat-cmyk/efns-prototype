"""Confirm the existing DEV account and save aggregate evidence without PII."""
import json
from pathlib import Path
import snowflake.connector

out=Path('.local/continuity-20261014');out.mkdir(parents=True,exist_ok=True)
conn=snowflake.connector.connect(connection_name='efns-dev',role='ACCOUNTADMIN',warehouse='EFNS_DEV_WH',database='EFNS_DEV')
e={'queries':[]}
try:
 with conn.cursor() as c:
  def q(name,sql):
   c.execute(sql); rows=[dict(zip([x[0] for x in c.description],r)) for r in c.fetchall()]
   e[name]=rows;e['queries'].append({'name':name,'sql':sql,'query_id':c.sfqid});return rows
  context=q('context','SELECT CURRENT_ACCOUNT_NAME() ACCOUNT_NAME,CURRENT_ORGANIZATION_NAME() ORGANIZATION,CURRENT_DATABASE() DB,CURRENT_WAREHOUSE() WH,CURRENT_ROLE() ROLE')[0]
  if context['ACCOUNT_NAME'].upper()!='RC34234' or context['DB']!='EFNS_DEV':raise ValueError('Existing project DEV account/database guard failed')
  q('production_identity',"SELECT SOURCE_TYPE,COUNT(*) RECORD_COUNT,COUNT(PRODUCER_ACCOUNT_ID) ACCOUNT_LINKS,COUNT(PRODUCER_NUMBER) SOURCE_NUMBERS,COUNT(MATCH_CONFIRMED_AT) STAFF_TIMES FROM EFNS_DEV.CORE.PRODUCTION_RECORD GROUP BY 1")
  q('duplicate_registration',"SELECT COUNT(*) GROUPS FROM (SELECT UPPER(TRIM(REGISTRATION_NUMBER)) K FROM EFNS_DEV.CORE.ACCOUNT WHERE REGISTRATION_NUMBER IS NOT NULL GROUP BY 1 HAVING COUNT(*)>1)")
  q('preservation',"SELECT 'RAW' T,COUNT(*) N,HASH_AGG(*) H FROM EFNS_DEV.RAW.MIGRATION_RAW_ROW UNION ALL SELECT 'ERROR',COUNT(*),HASH_AGG(*) FROM EFNS_DEV.RAW.MIGRATION_ERROR UNION ALL SELECT 'CORRECTION',COUNT(*),HASH_AGG(*) FROM EFNS_DEV.RAW.MIGRATION_CORRECTION_ROW")
  q('stage_files','LIST @EFNS_DEV.RAW.EIMS_MIGRATION_FILES')
  q('historical_files',"SELECT SOURCE_FILENAME,FILE_HASH,FILE_SIZE_BYTES,STAGE_PATH FROM EFNS_DEV.RAW.MIGRATION_FILE WHERE MIGRATION_BATCH_ID='DEV_MIGRATION_255ef9b50a52e766a7dff9'")
finally:conn.close();(out/'before.json').write_text(json.dumps(e,default=str,indent=2),encoding='utf-8')
print(json.dumps({'context':context,'production_identity':e['production_identity'],'staged_file_count':len(e['stage_files'])}))

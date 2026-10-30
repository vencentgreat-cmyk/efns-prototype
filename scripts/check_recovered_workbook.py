"""Read-only completeness check on the checksum-verified recovered workbook."""
import json
from pathlib import Path
from io import BytesIO
import sys
import snowflake.connector
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from data.connection import ConnectorExecutor
from data.repositories.snowflake import SnowflakeRepository
from data.importing import read_eims_workbook

conn=snowflake.connector.connect(connection_name='efns-dev',role='EFNS_DEV_DEPLOYER',warehouse='EFNS_DEV_WH',database='EFNS_DEV')
ex=ConnectorExecutor(lambda:conn);result=[]
try:
 ex.execute('USE SECONDARY ROLES NONE')
 context=ex.query('SELECT CURRENT_ACCOUNT_NAME() ACCOUNT_NAME,CURRENT_DATABASE() DB').iloc[0]
 if context.ACCOUNT_NAME!='RC34234' or context.DB!='EFNS_DEV':raise ValueError('DEV guard failed')
 repo=SnowflakeRepository(ex)
 manifest=json.loads(Path('.local/continuity-20261014/applied_evidence_archive_retry.json').read_text(encoding='utf-8'))
 for row in manifest['archives']:
  if not row.get('import_id') or not row['filename'].lower().endswith(('.xlsx','.xlsm')):continue
  raw=read_eims_workbook(BytesIO(repo.get_source_file_bytes(row['source_file_id'])))
  saved=repo.get_raw_rows(row['import_id'])
  missing=sorted(set(raw.SOURCE_ROW_NUMBER)-set(saved.SOURCE_ROW_NUMBER))
  result.append(dict(import_id=row['import_id'],archived_file_id=row['source_file_id'],parsed_source_rows=len(raw),saved_raw_rows=len(saved),not_previously_saved_row_numbers=missing))
finally:conn.close()
Path('.local/continuity-20261014/recovered_workbook_check.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))

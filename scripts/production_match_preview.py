"""Read-only exact matching preview; IDs are saved locally, no business names logged."""
import json
from pathlib import Path
import sys

import snowflake.connector

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from data.connection import ConnectorExecutor
from data.repositories.snowflake import SnowflakeRepository
from data.producer_identity import resolve_producer

connection=snowflake.connector.connect(connection_name='efns-dev',role='EFNS_DEV_DEPLOYER',warehouse='EFNS_DEV_WH',database='EFNS_DEV')
executor=ConnectorExecutor(lambda:connection)
try:
 executor.execute('USE SECONDARY ROLES NONE')
 context=executor.query('SELECT CURRENT_ACCOUNT_NAME() ACCOUNT_NAME,CURRENT_DATABASE() DB,CURRENT_ROLE() ROLE').iloc[0].to_dict()
 if context['ACCOUNT_NAME']!='RC34234' or context['DB']!='EFNS_DEV':raise ValueError('DEV guard failed')
 repo=SnowflakeRepository(executor)
 accounts=repo.get_accounts()
 pending=executor.query('SELECT PRODUCTION_ID,IMPORT_ID,SOURCE_ROW_NUMBER,PRODUCER_NUMBER,PRODUCER_ACCOUNT_ID,SOURCE_TYPE,UPDATED_AT FROM EFNS_DEV.CORE.PRODUCTION_RECORD WHERE PRODUCER_ACCOUNT_ID IS NULL')
 preview=[dict(PRODUCTION_ID=row['PRODUCTION_ID'],IMPORT_ID=row['IMPORT_ID'],SOURCE_ROW_NUMBER=row['SOURCE_ROW_NUMBER'],SOURCE_TYPE=row['SOURCE_TYPE'],**resolve_producer(row,accounts)) for row in pending.to_dict('records')]
 counts={status:sum(row['status']==status for row in preview) for status in sorted({row['status'] for row in preview})}
 path=Path('.local/continuity-20261014/producer_preview.json')
 path.write_text(json.dumps({'context':context,'counts':counts,'rows':preview},default=str,indent=2),encoding='utf-8')
 print(json.dumps({'context':context,'counts':counts,'path':str(path)}))
finally:connection.close()

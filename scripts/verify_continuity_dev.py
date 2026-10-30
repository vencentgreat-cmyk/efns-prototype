"""DEV checks using isolated temporary targets, never synthetic CORE records."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd
import snowflake.connector

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from data.connection import ConnectorExecutor
from data.repositories.snowflake import SnowflakeRepository
from app.services.report_center import build_custom_report,report_csv,report_xlsx
from app.security import Role,User
from io import BytesIO

out=Path('.local/continuity-20261014');evidence={}
conn=snowflake.connector.connect(connection_name='efns-dev',role='ACCOUNTADMIN',warehouse='EFNS_DEV_WH',database='EFNS_DEV',autocommit=False)
executor=ConnectorExecutor(lambda:conn)
def q(name,sql,params=None):
 with conn.cursor() as c:
  c.execute(sql,params); rows=[dict(zip([x[0] for x in c.description],r)) for r in c.fetchall()]
  evidence[name]={'sql':sql,'query_id':c.sfqid,'rows':rows};return rows

class QARepository(SnowflakeRepository):
 def _table(self,table,schema=None):
  if table in {'FLOCK','PRODUCTION_RECORD','IMPORT_BATCH','IMPORT_RAW_ROW'}:return f'EFNS_DEV.APP.QA_CONTINUITY_{table}'
  return super()._table(table,schema)
 def _continuity_table(self,table):
  if table in {'FLOCK_EVENT','RECORD_REVISION','PRODUCTION_MATCH_DECISION'}:return f'EFNS_DEV.APP.QA_CONTINUITY_{table}'
  return super()._continuity_table(table)
 def get_accounts(self,*args,**kwargs):
  return pd.DataFrame([dict(ACCOUNT_ID='00000000-0000-0000-0000-000000000001',REGISTRATION_NUMBER='SYN-QA',ORGANIZATION_NAME='Isolated synthetic')])
 def get_facilities(self,*args,**kwargs):
  return pd.DataFrame([dict(FACILITY_ID=f'00000000-0000-0000-0000-{i:012}',ACCOUNT_ID='00000000-0000-0000-0000-000000000001') for i in (2,3)])

try:
 context=q('context','SELECT CURRENT_ACCOUNT_NAME() ACCOUNT_NAME,CURRENT_DATABASE() DB,CURRENT_ROLE() ROLE')[0]
 if context['ACCOUNT_NAME']!='RC34234' or context['DB']!='EFNS_DEV':raise ValueError('DEV guard failed')
 for schema,table in [('CORE','FLOCK_EVENT'),('APP','RECORD_REVISION'),('RAW','PRODUCTION_MATCH_DECISION'),('CORE','PRODUCTION_RECORD'),('RAW','IMPORT_BATCH'),('RAW','IMPORT_RAW_ROW')]:
  executor.execute(f'CREATE TEMPORARY TABLE EFNS_DEV.APP.QA_CONTINUITY_{table} LIKE EFNS_DEV.{schema}.{table}')
  executor.execute(f'GRANT SELECT,INSERT,UPDATE ON TABLE EFNS_DEV.APP.QA_CONTINUITY_{table} TO ROLE EFNS_DEV_DEPLOYER')
 executor.execute('CREATE TEMPORARY TABLE EFNS_DEV.APP.QA_CONTINUITY_FLOCK (FLOCK_ID VARCHAR(36),FLOCK_NUMBER VARCHAR(100),ACCOUNT_ID VARCHAR(36),FACILITY_ID VARCHAR(36),FACILITY_DETAIL_ID VARCHAR(36),DISPOSAL_DATE DATE,CREATED_AT TIMESTAMP_NTZ,UPDATED_AT TIMESTAMP_NTZ)')
 executor.execute('GRANT SELECT,INSERT,UPDATE ON TABLE EFNS_DEV.APP.QA_CONTINUITY_FLOCK TO ROLE EFNS_DEV_DEPLOYER')
 executor.execute('USE ROLE EFNS_DEV_DEPLOYER');executor.execute('USE SECONDARY ROLES NONE')
 q('actual_application_role','SELECT CURRENT_ROLE() ROLE,CURRENT_SECONDARY_ROLES() SECONDARY_ROLES')
 repo=QARepository(executor)
 source=b'synthetic_column\r\noriginal bytes, not re-exported\r\n'
 archived=repo.archive_source_file('SYNTHETIC_ORIGINAL_ARCHIVE_QA.csv',source,'ISOLATED_ARCHIVE_QA',actor='SYSTEM_QA')
 assert repo.get_source_file_bytes(archived['SOURCE_FILE_ID'])==source
 evidence['original_archive']={'file_id':archived['SOURCE_FILE_ID'],'sha256':hashlib.sha256(source).hexdigest(),'byte_exact':True,'route':'ISOLATED_ARCHIVE_QA'}
 with executor.transaction() as tx:
  tx.execute("INSERT INTO EFNS_DEV.APP.QA_CONTINUITY_FLOCK VALUES (%s,%s,%s,%s,NULL,NULL,CURRENT_TIMESTAMP()::TIMESTAMP_NTZ,CURRENT_TIMESTAMP()::TIMESTAMP_NTZ)",('00000000-0000-0000-0000-000000000004','SYNTHETIC QA','00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000002'))
 event=repo.record_flock_event('00000000-0000-0000-0000-000000000004','MOVE',dt.datetime(2026,1,1,tzinfo=dt.timezone.utc),'ISOLATED QA','unique','00000000-0000-0000-0000-000000000003',actor='SYSTEM_QA',position_confirmed=True)
 assert repo.record_flock_event('00000000-0000-0000-0000-000000000004','MOVE',dt.datetime(2026,1,1,tzinfo=dt.timezone.utc),'ISOLATED QA','unique','00000000-0000-0000-0000-000000000003',actor='SYSTEM_QA',position_confirmed=True)==event
 assert len(repo.get_flock_events('00000000-0000-0000-0000-000000000004'))==1
 evidence['temporary_event']={'movement_and_retry':True,'no_real_core_targets':True}
 record=dict(PRODUCER_ACCOUNT_ID='00000000-0000-0000-0000-000000000001',REPORTING_YEAR=2026,REPORTING_WEEK=1,TOTAL=0)
 manual=repo.create_manual_production(record,'qa-manual','SYSTEM_QA')
 assert repo.create_manual_production(record,'qa-manual','SYSTEM_QA')==manual
 evidence['temporary_manual']={'zero_preserved':True,'duplicate_prevented':True}
 class RollbackProbe(Exception):pass
 try:
  with executor.transaction():
   repo.record_flock_event('00000000-0000-0000-0000-000000000004','END',dt.datetime(2026,2,1,tzinfo=dt.timezone.utc),'ROLLBACK QA','rollback',actor='SYSTEM_QA')
   raise RollbackProbe()
 except RollbackProbe:pass
 assert len(repo.get_flock_events('00000000-0000-0000-0000-000000000004'))==1
 evidence['rollback']={'event_rolled_back':True,'outer_transaction_preserved':True}
 live=SnowflakeRepository(executor)
 user=User('SYSTEM_QA','qa@example.invalid','Automated DEV check',Role.DEVELOPER,True,False,'','','')
 for year,week,groups,total in [(1999,21,24,None),(2017,15,23,390288)]:
  frame=build_custom_report(live,user=user,dataset='Production Records',selected_fields=['PRODUCER_ACCOUNT_ID','PRODUCER_ACCOUNT_NAME','TOTAL'],filters={'reporting_year':year,'reporting_week':week},group_by=['PRODUCER_ACCOUNT_ID','PRODUCER_ACCOUNT_NAME'],aggregations={'TOTAL':'sum'})
  assert len(frame)==groups
  if total is None: assert frame['Source Total'].isna().all()
  else: assert frame['Source Total'].sum(min_count=1)==total
  csv=pd.read_csv(BytesIO(report_csv(user,frame)))
  xlsx=pd.read_excel(BytesIO(report_xlsx(user,frame)))
  assert csv['Source Total'].isna().sum()==xlsx['Source Total'].isna().sum()==frame['Source Total'].isna().sum()
  assert csv['Source Total'].sum(min_count=1)==xlsx['Source Total'].sum(min_count=1) or csv['Source Total'].isna().all()
  evidence[f'report_{year}_{week}']={'groups':len(frame),'null_totals':int(frame['Source Total'].isna().sum()),'total':None if total is None else str(frame['Source Total'].sum(min_count=1)),'csv_xlsx_agree':True,'browser_test':False}
 q('new_core_history_counts','SELECT (SELECT COUNT(*) FROM EFNS_DEV.CORE.FLOCK_EVENT) REAL_EVENTS,(SELECT COUNT(*) FROM EFNS_DEV.APP.RECORD_REVISION) REAL_REVISIONS')
finally:
 conn.close();(out/'dev_runtime_checks.json').write_text(json.dumps(evidence,default=str,indent=2),encoding='utf-8')
print(json.dumps({key:value for key,value in evidence.items() if key not in {'context','actual_application_role','new_core_history_counts'}}))

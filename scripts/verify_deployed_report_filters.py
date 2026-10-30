"""Real DEV automated filters/exports, without browser or write impersonation."""

import io
import json
from pathlib import Path
import sys

import pandas as pd
from openpyxl import load_workbook
import snowflake.connector


def main():
    sys.dont_write_bytecode=True
    sys.path.insert(0,str(Path('.local/design-repairs-20261012/deployed_source/old_app').resolve()))
    from data.repositories.snowflake import SnowflakeRepository
    from app.services.report_center import build_custom_report,report_csv,report_xlsx
    from app.security import User,Role
    connection=snowflake.connector.connect(connection_name='efns-dev',role='EFNS_DEV_DEPLOYER',warehouse='EFNS_DEV_WH',database='EFNS_DEV')
    queries=[]
    class ReadOnly:
        def query(self,sql,params=None):
            assert sql.lstrip().upper().startswith('SELECT')
            cursor=connection.cursor()
            try:
                cursor.execute(sql,params)
                result=pd.DataFrame(cursor.fetchall(),columns=[c[0] for c in cursor.description])
                queries.append({'sql':sql,'parameters':params,'query_id':cursor.sfqid,'rows':len(result)})
                return result
            finally:
                cursor.close()
        def execute(self,*args,**kwargs): raise AssertionError('No writes')
    reader=ReadOnly()
    results=[]
    try:
        connection.cursor().execute('USE SECONDARY ROLES NONE')
        sample=reader.query('''SELECT p.REPORTING_YEAR,p.REPORTING_WEEK,p.PRODUCER_ACCOUNT_ID,p.FACILITY_ID,p.FLOCK_ID,
            fl.ACCOUNT_ID FLOCK_ACCOUNT_ID,fac.ACCOUNT_ID FACILITY_ACCOUNT_ID
            FROM EFNS_DEV.CORE.PRODUCTION_RECORD p LEFT JOIN EFNS_DEV.CORE.FLOCK fl ON fl.FLOCK_ID=p.FLOCK_ID
            LEFT JOIN EFNS_DEV.CORE.FACILITY fac ON fac.FACILITY_ID=p.FACILITY_ID
            WHERE p.FACILITY_ID IS NOT NULL AND p.PRODUCER_ACCOUNT_ID IS NOT NULL AND fl.ACCOUNT_ID IS NOT NULL
            ORDER BY p.PRODUCTION_ID LIMIT 1''')
        if sample.empty:
            results.append({'scene':'three-role filter','status':'No suitable real DEV sample; synthetic tests only'})
        else:
            row=sample.iloc[0]
            filters={
                'reporting_year':int(row.REPORTING_YEAR),'reporting_week':int(row.REPORTING_WEEK),
                'account_id':row.PRODUCER_ACCOUNT_ID,'flock_account_id':row.FLOCK_ACCOUNT_ID,
                'facility_account_id':row.FACILITY_ACCOUNT_ID,'facility_id':row.FACILITY_ID,
            }
            expected=reader.query('''SELECT p.PRODUCTION_ID FROM EFNS_DEV.CORE.PRODUCTION_RECORD p
                LEFT JOIN EFNS_DEV.CORE.FLOCK fl ON fl.FLOCK_ID=p.FLOCK_ID LEFT JOIN EFNS_DEV.CORE.FACILITY fac ON fac.FACILITY_ID=COALESCE(p.FACILITY_ID,fl.FACILITY_ID)
                WHERE p.REPORTING_YEAR=%s AND p.REPORTING_WEEK=%s AND p.PRODUCER_ACCOUNT_ID=%s
                AND fl.ACCOUNT_ID=%s AND fac.ACCOUNT_ID=%s AND COALESCE(p.FACILITY_ID,fl.FACILITY_ID)=%s''',tuple(filters.values()))
            user=User('read-only-test','verification@nsegg.ca','Verification',Role.REPORTING_VIEWER,True,False,'','',None)
            fields=['PRODUCTION_ID','PRODUCER_ACCOUNT_ID','FLOCK_ACCOUNT_ID','FACILITY_ACCOUNT_ID','REPORT_FACILITY_ID','REPORT_FACILITY_SOURCE','FACILITY_REFERENCE_DIFFERENCE','TOTAL']
            report=build_custom_report(SnowflakeRepository(reader),user=user,dataset='Production Records',selected_fields=fields,filters=filters)
            assert set(report['Production ID'])==set(expected.PRODUCTION_ID) and report['Production ID'].is_unique
            assert report['Facility Source'].eq('Production record').all()
            csv=pd.read_csv(io.BytesIO(report_csv(user,report)))
            rows=list(load_workbook(io.BytesIO(report_xlsx(user,report)),data_only=True).active.values)
            xlsx=pd.DataFrame(rows[1:],columns=rows[0])
            for export in (csv,xlsx):
                assert export['Production ID'].tolist()==report['Production ID'].tolist()
                assert export['Facility Source'].tolist()==report['Facility Source'].tolist()
                assert export['Facility Reference Comparison'].tolist()==report['Facility Reference Comparison'].tolist()
                assert export['Source Total'].isna().tolist()==report['Source Total'].isna().tolist()
            results.append({'scene':'three-role / Facility filter with direct reference','rows':len(report),'ids_match_independent_core_query':True,'no_duplicates':True,'csv_xlsx_match':True,'filters':filters})
        no_reference=reader.query('''SELECT COUNT(*) ROW_COUNT FROM EFNS_DEV.CORE.PRODUCTION_RECORD p
            LEFT JOIN EFNS_DEV.CORE.FLOCK f ON p.FLOCK_ID=f.FLOCK_ID
            WHERE p.REPORTING_YEAR=1999 AND p.REPORTING_WEEK=21 AND p.FACILITY_ID IS NULL AND f.FACILITY_ID IS NULL''')
        results.append({'scene':'1999/21 no available Facility reference','rows':int(no_reference.iloc[0,0])})
    finally:
        connection.close()
    evidence={'verification':'Automated downloaded deployed code / actual runtime role / secondary roles NONE; not authenticated browser acceptance','scenes':results,'queries':queries,'real_dev_missing_scenes':['Linked-Flock fallback','different Facility references'],'synthetic_evidence':'tests/test_report_facility_provenance.py and tests/test_report_account_roles.py'}
    root=Path('.local/design-repairs-20261012')
    for folder in ('verification','claude_handoff'):
        (root/folder/'report_filter_verification.json').write_text(json.dumps(evidence,default=str,indent=2),encoding='utf-8')
    print(json.dumps(results,default=str))


if __name__=='__main__':
    main()

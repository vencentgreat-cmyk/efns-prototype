"""Execute downloaded deployed code against DEV with read-only data access."""

import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import sys

import pandas as pd
from openpyxl import load_workbook
import snowflake.connector


def main(source, package, output):
    output.mkdir(parents=True,exist_ok=True)
    file_checks=[]
    for file in source.rglob('*'):
        if not file.is_file() or file.name=='snowflake.yml' or '__pycache__' in file.parts:
            continue
        relative=file.relative_to(source)
        expected=package/relative
        if not expected.is_file() or expected.read_bytes()!=file.read_bytes():
            raise ValueError('Deployed source mismatch: '+str(relative))
        file_checks.append({'path':str(relative),'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
    sys.dont_write_bytecode=True
    sys.path.insert(0,str(source.resolve()))
    from data.repositories.snowflake import SnowflakeRepository
    from app.services.report_center import build_custom_report,report_csv,report_xlsx
    from app.security import User,Role
    from data.migration import load_mapping

    evidence={'deployed_files':file_checks,'queries':[]}
    connection=snowflake.connector.connect(connection_name='efns-dev',role='EFNS_DEV_DEPLOYER',warehouse='EFNS_DEV_WH',database='EFNS_DEV',autocommit=False)
    class ReadOnly:
        def query(self,sql,params=None):
            if not sql.lstrip().upper().startswith('SELECT'):
                raise AssertionError('Non-read query blocked')
            with connection.cursor() as cursor:
                cursor.execute(sql,params)
                frame=pd.DataFrame(cursor.fetchall(),columns=[c[0] for c in cursor.description])
                evidence['queries'].append({'query_id':cursor.sfqid,'sql':sql,'parameters':params,'rows':len(frame)})
                return frame
        def execute(self,*args,**kwargs): raise AssertionError('Writes prohibited')
        def executemany(self,*args,**kwargs): raise AssertionError('Writes prohibited')
        def transaction(self): raise AssertionError('Writes prohibited')
    reader=ReadOnly()
    try:
        with connection.cursor() as cursor:
            cursor.execute('USE SECONDARY ROLES NONE')
        evidence['context']=reader.query('SELECT CURRENT_ROLE() ROLE,CURRENT_DATABASE() DB,CURRENT_WAREHOUSE() WH,CURRENT_SECONDARY_ROLES() SECONDARY_ROLES').to_dict('records')
        repo=SnowflakeRepository(reader)
        batch='DEV_MIGRATION_255ef9b50a52e766a7dff9'
        preview=repo.preview_historical_corrections(batch)
        evidence['correction_preview']=preview.summary.to_dict('records')
        assert len(preview.committed_rows)==112 and len(preview.core_rows)==0 and len(preview.pending_rows)==159
        evidence['pending_reasons']=[{'entity':entity,'reason':reason,'rows':count} for (entity,reason),count in Counter((r['SOURCE_ENTITY'],r['REASON']) for r in preview.pending_rows).items()]
        # One-to-one source identity join, not the old unscoped 271->314 join.
        evidence['correction_source_join']=reader.query('''SELECT COUNT(*) JOIN_ROWS,
            COUNT_IF(r.MIGRATION_RAW_ROW_ID IS NULL) MISSING_RAW
            FROM EFNS_DEV.RAW.MIGRATION_CORRECTION_ROW c LEFT JOIN EFNS_DEV.RAW.MIGRATION_RAW_ROW r
            ON c.ORIGINAL_MIGRATION_BATCH_ID=r.MIGRATION_BATCH_ID AND c.MIGRATION_RAW_ROW_ID=r.MIGRATION_RAW_ROW_ID
            WHERE c.ORIGINAL_MIGRATION_BATCH_ID=%s''',(batch,)).to_dict('records')
        assert evidence['correction_source_join'][0]=={'JOIN_ROWS':271,'MISSING_RAW':0}
        results=[]
        mapping=load_mapping()
        for entity,spec in mapping['entities'].items():
            frame=reader.query(f'''SELECT COUNT(*) LINEAGES, COUNT(DISTINCT m.TARGET_ID) TARGETS,
                COUNT_IF(t.{spec['id_field']} IS NULL) MISSING_TARGETS
                FROM EFNS_DEV.RAW.MIGRATION_ID_MAP m LEFT JOIN EFNS_DEV.CORE.{entity} t
                ON TO_VARCHAR(t.{spec['id_field']})=m.TARGET_ID
                WHERE m.MIGRATION_BATCH_ID=%s AND m.SOURCE_ENTITY=%s''',(batch,entity))
            assert int(frame.iloc[0]['MISSING_TARGETS'])==0
            results.append({'entity':entity,**frame.iloc[0].to_dict()})
        evidence['original_target_reconciliation']=results
        corrected=[]
        for entity in sorted({r['SOURCE_ENTITY'] for r in preview.committed_rows}):
            key=mapping['entities'][entity]['id_field']
            row=reader.query(f'''SELECT COUNT(*) TRACKED,COUNT(DISTINCT c.TARGET_ID) TARGETS,
                COUNT_IF(t.{key} IS NULL) MISSING_TARGETS
                FROM EFNS_DEV.RAW.MIGRATION_CORRECTION_ROW c
                JOIN EFNS_DEV.RAW.MIGRATION_CORRECTION_BATCH b ON b.MIGRATION_CORRECTION_BATCH_ID=c.MIGRATION_CORRECTION_BATCH_ID
                LEFT JOIN EFNS_DEV.CORE.{entity} t ON TO_VARCHAR(t.{key})=c.TARGET_ID
                WHERE c.ORIGINAL_MIGRATION_BATCH_ID=%s AND c.SOURCE_ENTITY=%s
                AND c.DISPOSITION='READY_CORE' AND b.COMMITTED_AT IS NOT NULL''',(batch,entity)).iloc[0].to_dict()
            assert row['MISSING_TARGETS']==0 and row['TRACKED']==row['TARGETS']
            corrected.append({'entity':entity,**row})
        evidence['correction_targets']=corrected
        original=sum(r['TARGETS'] for r in results)
        added=sum(r['TARGETS'] for r in corrected)
        extra=sum(r['LINEAGES']-r['TARGETS'] for r in results)
        source_count=int(reader.query('SELECT SOURCE_ROW_COUNT FROM EFNS_DEV.RAW.MIGRATION_BATCH WHERE MIGRATION_BATCH_ID=%s',(batch,)).iloc[0,0])
        assert original+added+extra+len(preview.pending_rows)==source_count
        evidence['reconciliation']={'source_rows':source_count,'original_targets':original,'correction_targets':added,'extra_lineages':extra,'pending':len(preview.pending_rows),'final_targets':original+added}
        user=User('read-only-verification','verification@nsegg.ca','Verification',Role.REPORTING_VIEWER,True,False,'','',None)
        reports=[]
        for year,week in ((1999,21),(2017,15)):
            result=build_custom_report(repo,user=user,dataset='Production Records',selected_fields=['PRODUCER_ACCOUNT_ID','PRODUCER_ACCOUNT_NAME','TOTAL'],filters={'reporting_year':year,'reporting_week':week},group_by=['PRODUCER_ACCOUNT_ID','PRODUCER_ACCOUNT_NAME'],aggregations={'TOTAL':'sum'})
            csv=pd.read_csv(io.BytesIO(report_csv(user,result)))
            sheet=load_workbook(io.BytesIO(report_xlsx(user,result)),data_only=True).active
            rows=list(sheet.values)
            xlsx=pd.DataFrame(rows[1:],columns=rows[0])
            for exported in (csv,xlsx):
                assert result['Source Total'].isna().tolist()==exported['Source Total'].isna().tolist()
                pd.testing.assert_series_equal(pd.to_numeric(result['Source Total']),pd.to_numeric(exported['Source Total']),check_dtype=False,check_names=False)
            if year==1999:
                assert len(result)==24 and result['Source Total'].isna().all()
            else:
                assert len(result)==23 and result['Source Total'].sum(min_count=1)==390288
                assert result.loc[result['Producer Account ID']=='C248413D-CDE6-E511-80E1-C4346BAC339C','Source Total'].iloc[0]==1483
            reports.append({'year':year,'week':week,'groups':len(result),'null_groups':int(result['Source Total'].isna().sum()),'sum':None if result['Source Total'].isna().all() else str(result['Source Total'].sum(min_count=1)),'csv_xlsx_match':True,'verification':'Downloaded deployed code; automated, not browser acceptance'})
        evidence['reports']=reports
        # List queries use independent children, not a multiplying child-to-child JOIN.
        account=reader.query('SELECT ACCOUNT_ID FROM EFNS_DEV.CORE.FACILITY GROUP BY ACCOUNT_ID ORDER BY COUNT(*) DESC LIMIT 1').iloc[0,0]
        facility=reader.query('SELECT FACILITY_ID FROM EFNS_DEV.CORE.FLOCK WHERE FACILITY_ID IS NOT NULL GROUP BY FACILITY_ID ORDER BY COUNT(*) DESC LIMIT 1').iloc[0,0]
        quota=reader.query('SELECT QUOTA_ID FROM EFNS_DEV.CORE.QUOTA_TRANSACTION GROUP BY QUOTA_ID ORDER BY COUNT(*) DESC LIMIT 1').iloc[0,0]
        sample_queries=[
            ('SQL-1 contacts','SELECT CONTACT_ID,ACCOUNT_ID FROM EFNS_DEV.CORE.CONTACT WHERE ACCOUNT_ID=%s',(account,)),
            ('SQL-1 locations','SELECT FARM_LOCATION_ID,ACCOUNT_ID FROM EFNS_DEV.CORE.FARM_LOCATION WHERE ACCOUNT_ID=%s',(account,)),
            ('SQL-1 facilities','SELECT FACILITY_ID,ACCOUNT_ID FROM EFNS_DEV.CORE.FACILITY WHERE ACCOUNT_ID=%s',(account,)),
            ('SQL-2 facility flocks','SELECT FLOCK_ID,ACCOUNT_ID,FACILITY_ID,PLACEMENT_DATE,DISPOSAL_DATE,EST_DISPOSAL FROM EFNS_DEV.CORE.FLOCK WHERE FACILITY_ID=%s',(facility,)),
            ('SQL-3 quota history','SELECT QUOTA_TRANSACTION_ID,QUOTA_ID,QUOTA_COUNT FROM EFNS_DEV.CORE.QUOTA_TRANSACTION WHERE QUOTA_ID=%s',(quota,)),
            ('SQL-4 Source Total','SELECT PRODUCER_ACCOUNT_ID,COUNT(*) ROW_COUNT,COUNT(TOTAL) KNOWN,SUM(TOTAL) TOTAL FROM EFNS_DEV.CORE.PRODUCTION_RECORD WHERE REPORTING_YEAR=%s AND REPORTING_WEEK=%s GROUP BY PRODUCER_ACCOUNT_ID',(2017,15)),
            ('SQL-5 lineage','SELECT SOURCE_ENTITY,COUNT(*) LINEAGES,COUNT(DISTINCT TARGET_ID) TARGETS FROM EFNS_DEV.RAW.MIGRATION_ID_MAP WHERE MIGRATION_BATCH_ID=%s GROUP BY SOURCE_ENTITY',(batch,)),
            ('PVQ-03a transactions','SELECT FLOCK_TRANSACTION_ID,FLOCK_ID,QUANTITY FROM EFNS_DEV.CORE.FLOCK_TRANSACTION WHERE FLOCK_ID IN (SELECT FLOCK_ID FROM EFNS_DEV.CORE.FLOCK WHERE FACILITY_ID=%s)',(facility,)),
            ('PVQ-04 test/sample list','SELECT t.SALMONELLA_TEST_ID,t.FLOCK_ID,t.ACCOUNT_ID,s.SALMONELLA_TEST_SAMPLE_ID FROM EFNS_DEV.CORE.SALMONELLA_TEST t LEFT JOIN EFNS_DEV.CORE.SALMONELLA_TEST_SAMPLE s ON t.SALMONELLA_TEST_ID=s.SALMONELLA_TEST_ID WHERE t.FLOCK_ID IN (SELECT FLOCK_ID FROM EFNS_DEV.CORE.FLOCK WHERE FACILITY_ID=%s)',(facility,)),
        ]
        evidence['sample_queries']=[]
        for label,sql,params in sample_queries:
            frame=reader.query(sql,params)
            evidence['sample_queries'].append({'label':label,'row_count':len(frame),'query_id':evidence['queries'][-1]['query_id'],'parameters':params,'status':'Executed list query; not a confirmed inventory/quota formula'})
        evidence['summary_metrics']=repo.get_production_summary_metrics()
        evidence['code_values']={}
        for table,field in (('FLOCK','STATUS'),('FLOCK_TRANSACTION','TRANSACTION_TYPE'),('QUOTA_TRANSACTION','TRANSACTION_TYPE'),('SALMONELLA_TEST','TEST_RESULT')):
            evidence['code_values'][table+'.'+field]=reader.query(f'SELECT {field} CODE,COUNT(*) ROW_COUNT FROM EFNS_DEV.CORE.{table} GROUP BY {field}').to_dict('records')
    finally:
        connection.close()
        (output/'deployed_verification.json').write_text(json.dumps(evidence,default=str,indent=2),encoding='utf-8')
    print(json.dumps({'deployed_files':len(file_checks),'reconciliation':evidence['reconciliation'],'reports':reports,'correction_preview':evidence['correction_preview']}))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--package',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    main(args.source,args.package,args.output)

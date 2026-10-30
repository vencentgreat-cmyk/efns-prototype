"""Supplement actual metadata and copy only non-payload review evidence."""

import json
from pathlib import Path
import shutil

import snowflake.connector


def main():
    root=Path('.local/design-repairs-20261012')
    connection=snowflake.connector.connect(connection_name='efns-dev',role='EFNS_DEV_DEPLOYER',warehouse='EFNS_DEV_WH',database='EFNS_DEV')
    evidence={}
    active_role='EFNS_DEV_DEPLOYER'
    cursor=connection.cursor()
    def query(name,sql,params=None):
        cursor.execute(sql,params)
        rows=[dict(zip([c[0] for c in cursor.description],row)) for row in cursor.fetchall()]
        evidence[name]={'role':active_role,'query_id':cursor.sfqid,'sql':sql,'rows':rows}
        return rows
    try:
        cursor.execute('USE SECONDARY ROLES NONE')
        query('session_timezone',"SHOW PARAMETERS LIKE 'TIMEZONE' IN SESSION")
        # Runtime reads the size VIEW, not the unused child table directly.
        # Metadata/independent child counts are an explicitly separate admin read.
        cursor.execute('USE ROLE ACCOUNTADMIN')
        active_role='ACCOUNTADMIN'
        precision=query('timestamp_precision',"SELECT TABLE_SCHEMA,TABLE_NAME,COLUMN_NAME,DATETIME_PRECISION FROM EFNS_DEV.INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA IN ('CORE','RAW','APP','SECURITY','REPORTING')")
        child_count=query('size_child_admin_count','SELECT COUNT(*) SIZE_CHILD_ROWS FROM EFNS_DEV.CORE.PRODUCTION_SIZE_BREAKDOWN')[0]['SIZE_CHILD_ROWS']
        cursor.execute('USE ROLE EFNS_DEV_DEPLOYER')
        active_role='EFNS_DEV_DEPLOYER'
        batch='DEV_MIGRATION_255ef9b50a52e766a7dff9'
        query('pending_groups','''SELECT SOURCE_ENTITY,
            CASE WHEN SOURCE_ENTITY='FLOCK' THEN 'Account conflict'
                 WHEN SOURCE_ENTITY='FLOCK_TRANSACTION' AND (CORRECTED_DATA:FLOCK_ID IS NULL OR IS_NULL_VALUE(CORRECTED_DATA:FLOCK_ID)) THEN 'Missing Flock'
                 WHEN SOURCE_ENTITY='FLOCK_TRANSACTION' THEN 'Dependent Flock'
                 WHEN SOURCE_ENTITY='QUOTA_TRANSACTION' AND (CORRECTED_DATA:QUOTA_ID IS NULL OR IS_NULL_VALUE(CORRECTED_DATA:QUOTA_ID)) THEN 'Missing Quota'
                 ELSE 'Dependent transaction' END REASON_GROUP,COUNT(*) ROW_COUNT
            FROM EFNS_DEV.RAW.MIGRATION_CORRECTION_ROW
            WHERE ORIGINAL_MIGRATION_BATCH_ID=%s AND DISPOSITION='PENDING_CONFIRMATION'
            GROUP BY 1,2 ORDER BY 1,2''',(batch,))
        query('production_grains','''SELECT
            (SELECT COUNT(*) FROM EFNS_DEV.CORE.PRODUCTION_RECORD) CORE_ROWS,
            (SELECT COUNT(*) FROM EFNS_DEV.REPORTING.VW_PRODUCTION_SUMMARY) SUMMARY_ROWS,
            (SELECT COUNT(DISTINCT PRODUCTION_ID) FROM EFNS_DEV.REPORTING.VW_PRODUCTION_SUMMARY) SUMMARY_IDS,
            (SELECT COUNT(*) FROM EFNS_DEV.REPORTING.VW_PRODUCTION_SIZE_DETAIL WHERE SIZE_BREAKDOWN_ID IS NOT NULL) REAL_SIZE_VIEW_ROWS,
            (SELECT COUNT(*) FROM EFNS_DEV.REPORTING.VW_PRODUCTION_SIZE_DETAIL WHERE SIZE_BREAKDOWN_ID IS NULL) NO_SIZE_PLACEHOLDERS''')
        evidence['production_grains']['independent_size_child_rows']=child_count
        query('facility_sources','''SELECT CASE WHEN p.FACILITY_ID IS NOT NULL THEN 'Production record'
            WHEN f.FACILITY_ID IS NOT NULL THEN 'Linked Flock' ELSE 'No available reference' END FACILITY_SOURCE,
            COUNT(*) ROW_COUNT,COUNT_IF(p.FACILITY_ID IS NOT NULL AND f.FACILITY_ID IS NOT NULL AND UPPER(p.FACILITY_ID)<>UPPER(f.FACILITY_ID)) CONFLICT_ROWS
            FROM EFNS_DEV.CORE.PRODUCTION_RECORD p LEFT JOIN EFNS_DEV.CORE.FLOCK f ON p.FLOCK_ID=f.FLOCK_ID
            GROUP BY 1''')
        # The repaired Account IDs are used only as private parameters, not published.
        saved=json.loads((root/'execution/repair_backup.json').read_text())
        ids=[r['ACCOUNT_ID'] for r in saved['account_before']]
        query('repaired_account_original_batch_membership',f'''SELECT COUNT(*) ORIGINAL_BATCH_MAPS
            FROM EFNS_DEV.RAW.MIGRATION_ID_MAP WHERE MIGRATION_BATCH_ID=%s AND SOURCE_ENTITY='ACCOUNT'
            AND TARGET_ID IN ({','.join(['%s']*len(ids))})''',(batch,*ids))
        meta_path=root/'final/dev_evidence.json'
        metadata=json.loads(meta_path.read_text())
        index={(r['TABLE_SCHEMA'],r['TABLE_NAME'],r['COLUMN_NAME']):r['DATETIME_PRECISION'] for r in precision}
        for name in ('columns','field_usage'):
            for row in metadata[name]:
                row['DATETIME_PRECISION']=index.get((row['TABLE_SCHEMA'],row['TABLE_NAME'],row['COLUMN_NAME']))
        meta_path.write_text(json.dumps(metadata,default=str,indent=2),encoding='utf-8')
    finally:
        connection.close()
    (root/'verification/final_supplement.json').write_text(json.dumps(evidence,default=str,indent=2),encoding='utf-8')
    handoff=root/'claude_handoff'
    for name in ('deployed_verification.json','permissions.json','preserved_values.json','final_supplement.json'):
        shutil.copy2(root/'verification'/name,handoff/name)
    shutil.copy2(root/'final/dev_evidence.json',handoff/'final_dev_metadata.json')
    shutil.copy2(Path('docs/EFNS_Design_Repair_Status_2026-10-12.md'),handoff/'README_Claude_Handoff.md')
    print(json.dumps({name:value['rows'] for name,value in evidence.items() if name not in {'timestamp_precision','session_timezone'}},default=str))


if __name__=='__main__':
    main()

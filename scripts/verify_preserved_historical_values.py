"""Read-only batch-scoped comparison of signed values and period conversion."""

import json
from pathlib import Path
import sys

import snowflake.connector


def main():
    root=Path('.local/design-repairs-20261012/deployed_source/old_app').resolve()
    sys.dont_write_bytecode=True
    sys.path.insert(0,str(root))
    from data.migration import parse_reporting_period
    connection=snowflake.connector.connect(connection_name='efns-dev',role='EFNS_DEV_DEPLOYER',warehouse='EFNS_DEV_WH',database='EFNS_DEV')
    evidence={}
    batch='DEV_MIGRATION_255ef9b50a52e766a7dff9'
    try:
        cursor=connection.cursor()
        cursor.execute('USE SECONDARY ROLES NONE')
        for entity,key,field in (('FLOCK','FLOCK_ID','BIRDS_DISPOSED'),('QUOTA_TRANSACTION','QUOTA_TRANSACTION_ID','QUOTA_COUNT')):
            cursor.execute(f'''SELECT COUNT_IF(t.{field}<0) NEGATIVE_TARGETS,
                COUNT_IF(t.{field}=0) ZERO_TARGETS,
                COUNT_IF(TRY_TO_DECIMAL(r.NORMALIZED_DATA:{field}::STRING,38,8) IS DISTINCT FROM t.{field}) VALUE_DIFFERENCES
                FROM EFNS_DEV.RAW.MIGRATION_ID_MAP m
                JOIN EFNS_DEV.RAW.MIGRATION_RAW_ROW r ON m.MIGRATION_BATCH_ID=r.MIGRATION_BATCH_ID AND m.MIGRATION_RAW_ROW_ID=r.MIGRATION_RAW_ROW_ID
                JOIN EFNS_DEV.CORE.{entity} t ON m.TARGET_ID=t.{key}
                WHERE m.MIGRATION_BATCH_ID=%s AND m.SOURCE_ENTITY=%s''',(batch,entity))
            row=dict(zip([c[0] for c in cursor.description],cursor.fetchone()))
            assert row['VALUE_DIFFERENCES']==0
            evidence[field]={**row,'query_id':cursor.sfqid}
        cursor.execute('''SELECT p.SOURCE_WEEK_CODE,p.REPORTING_YEAR,p.REPORTING_WEEK
            FROM EFNS_DEV.CORE.PRODUCTION_RECORD p JOIN EFNS_DEV.RAW.MIGRATION_ID_MAP m
            ON m.TARGET_ID=p.PRODUCTION_ID WHERE m.MIGRATION_BATCH_ID=%s AND m.SOURCE_ENTITY='PRODUCTION_RECORD' ''',(batch,))
        rows=cursor.fetchall()
        mismatches=0
        known=0
        for code,year,week in rows:
            parsed=parse_reporting_period(code)
            if parsed is not None:
                known+=1
                mismatches+=parsed!=(int(year),int(week))
        assert mismatches==0
        evidence['production_period']={'rows':len(rows),'parsed_codes':known,'differences':mismatches,'query_id':cursor.sfqid,'limitation':'Tests recorded year/week conversion, not an unconfirmed EFC-period JOIN.'}
    finally:
        connection.close()
    output=Path('.local/design-repairs-20261012/verification/preserved_values.json')
    output.write_text(json.dumps(evidence,default=str,indent=2),encoding='utf-8')
    print(json.dumps(evidence,default=str))


if __name__=='__main__':
    main()

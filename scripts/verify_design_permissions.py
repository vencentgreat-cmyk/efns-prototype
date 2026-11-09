"""Permission probes use zero-row DML and rollback; no business data changes."""

import json
from pathlib import Path
import snowflake.connector


def main():
    output=Path('.local/design-repairs-20261012/verification/permissions.json')
    results=[]
    for role in ('EFNS_DEV_DEPLOYER','EFNS_DEV_VIEWER'):
        connection=snowflake.connector.connect(connection_name='efns-dev',role=role,warehouse='EFNS_DEV_WH',database='EFNS_DEV',autocommit=False)
        try:
            cursor=connection.cursor()
            cursor.execute('USE SECONDARY ROLES NONE')
            cursor.execute('SELECT CURRENT_ROLE(),CURRENT_SECONDARY_ROLES()')
            context=cursor.fetchone()
            probes=(
                ('read_core','SELECT COUNT(*) FROM EFNS_DEV.CORE.ACCOUNT'),
                ('update_core_zero_rows','UPDATE EFNS_DEV.CORE.ACCOUNT SET ACCOUNT_ID=ACCOUNT_ID WHERE 1=0'),
                ('delete_audit_zero_rows','DELETE FROM EFNS_DEV.APP.AUDIT_EVENT WHERE 1=0'),
            )
            for name,sql in probes:
                result={'role':role,'context':context,'probe':name,'sql':sql}
                try:
                    cursor.execute(sql)
                    if sql.startswith('SELECT'):
                        cursor.fetchall()
                    else:
                        assert cursor.rowcount==0
                    result.update({'allowed':True,'query_id':cursor.sfqid,'changed_rows':0})
                except snowflake.connector.Error as exc:
                    result.update({'allowed':False,'query_id':getattr(exc,'sfqid',None),'error_code':exc.errno})
                finally:
                    connection.rollback()
                results.append(result)
        finally:
            connection.close()
    assert next(r for r in results if r['role']=='EFNS_DEV_DEPLOYER' and r['probe']=='read_core')['allowed']
    assert next(r for r in results if r['role']=='EFNS_DEV_DEPLOYER' and r['probe']=='update_core_zero_rows')['allowed']
    assert not next(r for r in results if r['role']=='EFNS_DEV_DEPLOYER' and r['probe']=='delete_audit_zero_rows')['allowed']
    assert not any(r['allowed'] for r in results if r['role']=='EFNS_DEV_VIEWER')
    output.write_text(json.dumps(results,default=str,indent=2),encoding='utf-8')
    print(json.dumps(results,default=str))


if __name__=='__main__':
    main()

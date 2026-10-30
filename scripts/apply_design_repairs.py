"""Explicitly authorized DEV identity DDL and confirmed null-placeholder repair."""

import argparse
import datetime as dt
import json
from pathlib import Path

import snowflake.connector


def main(output):
    output.mkdir(parents=True, exist_ok=True)
    evidence = {"started_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "queries": []}
    connection = snowflake.connector.connect(
        connection_name="efns-dev", role="ACCOUNTADMIN", warehouse="EFNS_DEV_WH",
        database="EFNS_DEV", autocommit=False,
    )
    cursor = connection.cursor()

    def query(sql, params=None):
        cursor.execute(sql, params)
        rows = [dict(zip([c[0] for c in cursor.description], row)) for row in cursor.fetchall()]
        evidence["queries"].append({"query_id":cursor.sfqid,"sql":sql,"row_count":len(rows)})
        return rows

    try:
        cursor.execute("USE SECONDARY ROLES NONE")
        context = query("SELECT CURRENT_DATABASE() DB, CURRENT_ROLE() ROLE")
        if context[0]["DB"] != "EFNS_DEV":
            raise ValueError("DEV guard failed.")
        active = query("SELECT COUNT(*) N FROM TABLE(EFNS_DEV.INFORMATION_SCHEMA.QUERY_HISTORY(RESULT_LIMIT=>1000)) WHERE EXECUTION_STATUS='RUNNING' AND QUERY_TYPE IN ('INSERT','UPDATE','DELETE','MERGE') AND (QUERY_TEXT ILIKE '%MIGRATION_%' OR QUERY_TEXT ILIKE '%CORE.%')")[0]["N"]
        if active:
            raise ValueError("Active migration or CORE writer detected; repair stopped.")
        evidence["old_ddl"] = {
            name: query("SELECT GET_DDL('TABLE',%s) DDL",("EFNS_DEV.RAW."+name,))[0]["DDL"]
            for name in ("MIGRATION_RAW_ROW","MIGRATION_ID_MAP","MIGRATION_CORRECTION_ROW")
        }
        evidence["old_id_maps"] = query("SELECT * FROM EFNS_DEV.RAW.MIGRATION_ID_MAP ORDER BY MIGRATION_ID_MAP_ID")
        fields = ("PARENT_ACCOUNT_ID","GRADING_STATION_ACCOUNT_ID","PULLET_GROWER_ACCOUNT_ID")
        affected = query("SELECT ACCOUNT_ID,"+",".join(fields)+",CREATED_AT,UPDATED_AT FROM EFNS_DEV.CORE.ACCOUNT WHERE "+" OR ".join(f"LOWER(TRIM({f})) IN ('','none','null')" for f in fields))
        evidence["account_before"] = affected
        # Persist recovery material before the first DDL or DML.
        backup = output / "repair_backup.json"
        if not backup.exists():
            backup.write_text(json.dumps(evidence,default=str,indent=2),encoding="utf-8")
        source = Path(__file__).resolve().parents[1] / "sql/14_EIMS_Source_Identity.sql"
        for result in connection.execute_stream(__import__('io').StringIO(source.read_text(encoding="utf-8"))):
            evidence["queries"].append({"query_id":result.sfqid,"operation":"identity_sql"})
        # All old UUIDs and original map content except the newly added column must survive.
        new_maps = query("SELECT * EXCLUDE MIGRATION_RAW_ROW_ID FROM EFNS_DEV.RAW.MIGRATION_ID_MAP ORDER BY MIGRATION_ID_MAP_ID")
        old_maps = [{k:v for k,v in r.items() if k!="MIGRATION_RAW_ROW_ID"} for r in evidence["old_id_maps"]]
        if new_maps != old_maps:
            raise ValueError("Original ID map content changed unexpectedly.")
        cursor.execute("BEGIN")
        changed = 0
        try:
            for row in affected:
                for field in fields:
                    old = row[field]
                    if not isinstance(old,str) or old.strip().lower() not in {"","none","null"}:
                        continue
                    cursor.execute(f"UPDATE EFNS_DEV.CORE.ACCOUNT SET {field}=NULL WHERE ACCOUNT_ID=%s AND {field}=%s",(row["ACCOUNT_ID"],old))
                    if cursor.rowcount != 1:
                        raise ValueError("Scoped Account correction did not update exactly one row.")
                    changed += 1
                    evidence["queries"].append({"query_id":cursor.sfqid,"operation":"scoped_account_null_repair"})
            cursor.execute("COMMIT")
        except Exception:
            cursor.execute("ROLLBACK")
            raise
        evidence["account_after"] = query("SELECT ACCOUNT_ID,"+",".join(fields)+",CREATED_AT,UPDATED_AT FROM EFNS_DEV.CORE.ACCOUNT WHERE ACCOUNT_ID IN ("+",".join(["%s"]*len(affected))+")",tuple(r["ACCOUNT_ID"] for r in affected)) if affected else []
        evidence["affected_accounts"] = len(affected)
        evidence["changed_fields"] = changed
        evidence["finished_at_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
        print(json.dumps({"identity_sql":"applied","affected_accounts":len(affected),"changed_fields":changed}))
    except Exception as exc:
        try:
            connection.rollback()
        except Exception:
            pass
        evidence["error"] = {"type":type(exc).__name__,"message":str(exc),"query_id":getattr(exc,"sfqid",None)}
        raise
    finally:
        connection.close()
        (output/"repair_execution.json").write_text(json.dumps(evidence,default=str,indent=2),encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    main(args.output)

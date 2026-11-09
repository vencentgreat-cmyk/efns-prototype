"""Read-only DEV metadata, declared-key checks and source identity evidence."""

from __future__ import annotations

import argparse
from collections import defaultdict
import datetime as dt
import json
from pathlib import Path
import re

import snowflake.connector


def quoted(value):
    if not re.fullmatch(r"[A-Z][A-Z0-9_]*", value):
        raise ValueError("Unexpected metadata identifier.")
    return '"' + value + '"'


def export(output, role):
    output.mkdir(parents=True, exist_ok=True)
    connection = snowflake.connector.connect(
        connection_name="efns-dev", role=role, warehouse="EFNS_DEV_WH",
        database="EFNS_DEV", autocommit=False,
    )
    cursor = connection.cursor()
    evidence = {"captured_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "queries": []}

    def query(sql, params=None):
        cursor.execute(sql, params)
        rows = [dict(zip([c[0] for c in cursor.description], row)) for row in cursor.fetchall()]
        evidence["queries"].append({"sql": sql, "query_id": cursor.sfqid, "row_count": len(rows)})
        return rows

    try:
        cursor.execute("USE SECONDARY ROLES NONE")
        evidence["context"] = query("SELECT CURRENT_DATABASE() DB, CURRENT_ROLE() ROLE, CURRENT_WAREHOUSE() WH, CURRENT_SECONDARY_ROLES() SECONDARY_ROLES")
        if evidence["context"][0]["DB"] != "EFNS_DEV":
            raise ValueError("DEV database guard failed.")
        evidence["tables"] = query("SELECT TABLE_SCHEMA,TABLE_NAME,TABLE_TYPE,COMMENT FROM EFNS_DEV.INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA IN ('CORE','RAW','APP','SECURITY','REPORTING') ORDER BY 1,2")
        evidence["columns"] = query("SELECT TABLE_SCHEMA,TABLE_NAME,ORDINAL_POSITION,COLUMN_NAME,DATA_TYPE,CHARACTER_MAXIMUM_LENGTH,NUMERIC_PRECISION,NUMERIC_SCALE,IS_NULLABLE,COLUMN_DEFAULT,COMMENT FROM EFNS_DEV.INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA IN ('CORE','RAW','APP','SECURITY','REPORTING') ORDER BY 1,2,3")
        evidence["constraints"] = query("SELECT TABLE_SCHEMA,TABLE_NAME,CONSTRAINT_NAME,CONSTRAINT_TYPE,ENFORCED,RELY FROM EFNS_DEV.INFORMATION_SCHEMA.TABLE_CONSTRAINTS WHERE TABLE_SCHEMA IN ('CORE','RAW','APP','SECURITY') ORDER BY 1,2,3")
        for key, sql in (("pks", "SHOW PRIMARY KEYS IN DATABASE EFNS_DEV"), ("uks", "SHOW UNIQUE KEYS IN DATABASE EFNS_DEV"), ("fks", "SHOW IMPORTED KEYS IN DATABASE EFNS_DEV")):
            evidence[key] = query(sql)
        evidence["ddl"] = {}
        evidence["field_usage"] = []
        for table in evidence["tables"]:
            schema, name = table["TABLE_SCHEMA"], table["TABLE_NAME"]
            full = f"EFNS_DEV.{quoted(schema)}.{quoted(name)}"
            kind = "VIEW" if table["TABLE_TYPE"] == "VIEW" else "TABLE"
            evidence["ddl"][f"{schema}.{name}"] = query("SELECT GET_DDL(%s,%s) DDL", (kind, full))[0]["DDL"]
            cols = [c for c in evidence["columns"] if c["TABLE_SCHEMA"] == schema and c["TABLE_NAME"] == name]
            expressions = ["COUNT(*) ROW_COUNT"]
            for index, col in enumerate(cols):
                field = quoted(col["COLUMN_NAME"])
                expressions.append(f"COUNT({field}) N{index}")
                if col["DATA_TYPE"] in {"NUMBER", "FLOAT", "DOUBLE", "REAL", "DECIMAL"}:
                    expressions.append(f"COUNT(CASE WHEN {field}=0 THEN 1 END) Z{index}")
            counts = query("SELECT " + ",".join(expressions) + " FROM " + full)[0]
            for index, col in enumerate(cols):
                evidence["field_usage"].append({
                    **col, "ROW_COUNT": counts["ROW_COUNT"], "NON_NULL_COUNT": counts[f"N{index}"],
                    "ZERO_COUNT": counts.get(f"Z{index}"),
                })
        checks = []
        for category in ("pks", "uks"):
            groups = defaultdict(list)
            for key in evidence[category]:
                groups[(key["schema_name"], key["table_name"], key["constraint_name"])].append(key)
            for (schema, table, constraint), members in groups.items():
                columns = [quoted(k["column_name"]) for k in sorted(members, key=lambda k:k["key_sequence"])]
                full = f"EFNS_DEV.{quoted(schema)}.{quoted(table)}"
                where = " AND ".join(c + " IS NOT NULL" for c in columns) if category == "uks" else "TRUE"
                result = query(f"SELECT COUNT(*) DUPLICATE_GROUPS FROM (SELECT {','.join(columns)} FROM {full} WHERE {where} GROUP BY {','.join(columns)} HAVING COUNT(*)>1)")[0]
                checks.append({"constraint": constraint, "table": f"{schema}.{table}", "kind": category, **result})
        groups = defaultdict(list)
        for key in evidence["fks"]:
            groups[(key["fk_schema_name"],key["fk_table_name"],key["fk_name"])].append(key)
        for (schema, table, constraint), members in groups.items():
            members.sort(key=lambda k:k["key_sequence"])
            parent = members[0]
            join = " AND ".join(f'c.{quoted(k["fk_column_name"])}=p.{quoted(k["pk_column_name"])}' for k in members)
            non_null = " AND ".join(f'c.{quoted(k["fk_column_name"])} IS NOT NULL' for k in members)
            result = query(f'SELECT COUNT(*) ORPHAN_ROWS FROM EFNS_DEV.{quoted(schema)}.{quoted(table)} c WHERE {non_null} AND NOT EXISTS (SELECT 1 FROM EFNS_DEV.{quoted(parent["pk_schema_name"])}.{quoted(parent["pk_table_name"])} p WHERE {join})')[0]
            checks.append({"constraint": constraint, "table":f"{schema}.{table}", "kind":"fk", **result})
        evidence["integrity"] = checks
        evidence["preservation"] = {}
        for table in ("MIGRATION_BATCH", "MIGRATION_RAW_ROW", "MIGRATION_ERROR", "MIGRATION_CORRECTION_BATCH", "MIGRATION_CORRECTION_ROW"):
            evidence["preservation"][table] = query(f"SELECT COUNT(*) ROW_COUNT,HASH_AGG(*) CONTENT_HASH FROM EFNS_DEV.RAW.{table}")[0]
        evidence["lineages"] = query("SELECT MIGRATION_BATCH_ID,SOURCE_ENTITY,COUNT(*) SOURCE_LINEAGES,COUNT(DISTINCT TARGET_ID) DISTINCT_TARGETS FROM EFNS_DEV.RAW.MIGRATION_ID_MAP GROUP BY 1,2 ORDER BY 1,2")
        evidence["corrections"] = query("SELECT ORIGINAL_MIGRATION_BATCH_ID,MIGRATION_CORRECTION_BATCH_ID,DISPOSITION,RELATION_STATUS,SOURCE_ENTITY,COUNT(*) ROW_COUNT FROM EFNS_DEV.RAW.MIGRATION_CORRECTION_ROW GROUP BY 1,2,3,4,5 ORDER BY 1,2,3,5")
        evidence["batch_status"] = query("SELECT MIGRATION_BATCH_ID,STATUS,SOURCE_ROW_COUNT,READY_ROW_COUNT,REJECTED_ROW_COUNT,COMMITTED_AT FROM EFNS_DEV.RAW.MIGRATION_BATCH ORDER BY MIGRATION_BATCH_ID")
    finally:
        connection.close()
        (output / "dev_evidence.json").write_text(json.dumps(evidence, default=str, indent=2), encoding="utf-8")
    print(json.dumps({"objects":len(evidence["tables"]),"columns":len(evidence["columns"]),"key_issues":[c for c in checks if c.get("DUPLICATE_GROUPS",0) or c.get("ORPHAN_ROWS",0)]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--role", default="ACCOUNTADMIN")
    args = parser.parse_args()
    export(args.output, args.role)

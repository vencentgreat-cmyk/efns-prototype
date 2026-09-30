# EIMS v3 DEV Database Deployment

Open [`sql/10_EIMS_V3_DEV_Deployment.sql`](../sql/10_EIMS_V3_DEV_Deployment.sql)
in a Snowflake Snowsight Worksheet connected to the EFNS development account.

## Running the script

Run the whole file as a script. It explicitly selects `ACCOUNTADMIN`,
`EFNS_DEV_WH`, and `EFNS_DEV`, then stops before DDL if the active database is
not `EFNS_DEV`.

The file has five sections:

1. **Preflight and guard** displays the current role, warehouse, database, and
   schema, then enforces the DEV database boundary.
2. **Business tables** creates missing EIMS v3 target tables in dependency
   order without replacing existing tables.
3. **Migration infrastructure** creates the encrypted stage and RAW batch,
   file, payload, ID-map, error, and reconciliation tables.
4. **Additive upgrades** adds missing columns, conditionally relaxes historical
   constraints, adds v3 relationships, and grants exact app privileges.
5. **Verification** reports object/column/constraint presence, row counts,
   orphan lineage counts, and a final readiness status. It does not select
   business columns or PII.

Normal completion ends with `MISSING_REQUIRED_OBJECTS = 0` and
`FINAL_STATUS = READY_FOR_EIMS_V3_VALIDATION`. The disallowed-check and duplicate
Day counts should also be zero, and the four historical nullable columns should
report `YES`. Existing table counts may be zero or nonzero; the deployment does
not alter business rows.

If execution fails, correct the reported privilege, warehouse, or DDL issue and
rerun the entire script. Every DDL operation is additive or metadata-guarded,
so a full rerun is preferred over starting midway. If organizational policy
requires section-by-section execution, rerun from the heading containing the
failed statement and always run section 5 afterward.

Snowflake is ready for a migration dry-run when all required objects, columns,
and constraints report `PRESENT`, orphan lineage checks report zero, and the
final status is `READY_FOR_EIMS_V3_VALIDATION`.

This database deployment does **not** upload, stage, validate, or commit the
86,908 real EIMS source rows.


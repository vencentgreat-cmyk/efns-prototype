# EIMS source identity repair

## Scope

`sql/14_EIMS_Source_Identity.sql` changes DEV informational key declarations and
adds the ID map's source RAW row reference. RAW IDs, payloads, validation errors,
committed batches, correction rows, target records and date lineage are retained.
The source identity is `(MIGRATION_BATCH_ID, MIGRATION_RAW_ROW_ID)`; a date target
is still `DIM_EFC_DATE.DAY`. Multiple source rows may reference the same DAY.

Old ID maps stored only batch/entity/source/target, not the specific RAW row.
Equivalent duplicate-date groups are paired deterministically by map UUID and
source file/row/RAW ID. This is a compatible reconstruction, not evidence of the
original UUID-to-source-row assignment. Group counts must match before repair.
Subsequent inserts and retries store and compare the full source identity.

## Execution and recovery

First verify writers are idle, save GET_DDL for the three tables and export ID
map records including UUIDs. Run the SQL before deploying the updated application.
It is repeatable: existing non-null references are not overwritten, all preflight
checks run again, and key declarations are recreated with the same definitions.
Snowflake DDL auto-commits, so this is not an atomic schema transaction. If a DDL
statement fails, keep writers idle, investigate metadata, and resume the guarded
key section. Do not delete lineage or RAW to make a constraint fit.

Application rollback requires the saved full application package. A schema
rollback uses saved constraint definitions, after verifying compatibility. Before
running a legacy writer that omits the new map column, explicitly execute
`ALTER TABLE EFNS_DEV.RAW.MIGRATION_ID_MAP ALTER COLUMN MIGRATION_RAW_ROW_ID DROP NOT NULL`
and keep migration writers paused until the rollback package is verified. The
added column/references can remain; null references from any legacy writes must
be backfilled before redeploying the new writer. Backfill pairs only unassigned
maps and not-yet-referenced RAW rows, preserving established references.
Do not restore the old single-column RAW PK
or source-ID UNIQUE as an integrity claim: existing data violates those keys.

## Integrity responsibility

Standard-table PK/FK/UNIQUE declarations are informational. Repository checks
reject mixed batches, duplicate source rows and correction metadata mismatches.
Connection locks serialize calls on the same connection, not independent
Snowflake sessions. Cross-session check-then-insert races remain a limitation;
this repair does not claim database-enforced uniqueness or scheduled monitoring.

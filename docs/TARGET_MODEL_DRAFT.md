# Target Model Draft

> Provisional addition: `ACCOUNT 1:N FARM_LOCATION`. A Farm Location represents
> an Account-owned postal, physical, or operational address and is distinct
> from `FACILITY` and `FACILITY_DETAIL`. Dynamics metadata and stakeholder
> confirmation may rename or reshape this entity.

**Status: provisional.** Executable definitions are in `sql/02_core_tables.sql`, `sql/03_production_tables.sql` and `sql/04_reporting_views.sql`; field details are in `docs/DATA_DICTIONARY.md`.

The model separates `RAW` ingestion, normalized `CORE` operational tables and derived `REPORTING` views. RAW rows retain source JSON, source row number, validation messages and match audit fields. Normalized EIMS production records keep nullable Account, Facility and Flock links and begin as `UNMATCHED`.

Operational relationships are Account → Facility → Facility Detail/Flock, Account → Quota Registration → Quota Transaction, Flock → Flock Transaction/Salmonella Test, and Import Batch → RAW Row/Production Record. All names, requiredness and cardinalities remain subject to Dataverse metadata.

Snowflake standard tables are used for RAW, history, operational and reporting storage. Hybrid Tables may be evaluated later using measured workloads and verified constraints; the current design does not depend on them.

All table scripts use `CREATE TABLE IF NOT EXISTS` and are DEV/provisional. They have not been executed against a real Snowflake environment.

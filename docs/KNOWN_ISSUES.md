# Known Issues

- Dataverse logical names, choices, required fields, keys and relationship cardinalities remain unknown.
- Imported EIMS rows remain `UNMATCHED`; candidate generation and manual confirmation UI remain future work.
- Mock data resets with each Streamlit session.
- Snowflake SQL and repository writes require integration testing against a DEV account, warehouse and privileges.
- Snowflake mode trusts `st.user.email` and persists application access in Snowflake;
  actual account email population, MFA, identity lifecycle, and role assignment
  still require validation and policy in the EFNS Snowflake account.
- Deletion blocks referenced records. Final soft-delete and retention rules require business/Dataverse decisions.
- Sample-level Salmonella fields and final quota rules require authoritative metadata.
- Optimistic locking is implemented for current editable business entities, including the dedicated Facility Detail workspace. Real multi-session behavior still requires Snowflake DEV validation.
- Snowflake create/update/delete now handles known and unknown Snowpark affected-row results without treating an unconfirmed insert as successful. Query ID, operation, object, error code and SQLSTATE are exposed as sanitized correlation fields. Exact result shapes and multi-session optimistic locking still require validation in the real DEV account.
- Streamlit named-connection, active warehouse session, connector SSO and key-pair paths are implemented but still require deployment-specific validation.
- Snowpark bulk writes use bounded multi-row `VALUES` statements. Real DEV testing must establish safe batch sizes for actual row widths and warehouse limits.
- Production NUMBER bindings now convert pandas missing values and textual null
  sentinels to SQL `NULL`, preserve integer/decimal DDL semantics, accept valid
  comma-grouped numbers, and reject invalid text before writing. Connector and
  Snowpark behavior still requires a DEV import verification. Snowpark expanded
  bulk writes now literalize only Python `None` as SQL `NULL`; all non-NULL
  values remain qmark-bound to avoid the warehouse runtime's observed textual
  `"None"` conversion.
- Operational detail navigation now uses registered Streamlit pages and
  page-local session state. Snowsight selection, Back, cross-module switching,
  and stale-record recovery still require a deployed UI smoke test.
- Quota and Facility Detail fields, choices and requiredness remain provisional pending EIMS metadata, although their list/new/detail/edit workflows are implemented.
- Source profiling is advisory and processes all selected worksheets in application memory; authoritative types, keys and relationships require EIMS metadata confirmation.
- Local audit events remain SQLite-only. Snowflake audit events use the actual viewer
  email and UTC database timestamp, but retention, event-table correlation, client
  address, and Snowflake query-history correlation remain to be defined.
- Existing DEV rows are not backfilled by these changes. Old fixed-timestamp
  `DEV_SYNTH` rows must be removed with the targeted cleanup and reseeded before
  timestamp verification. `CREATE TABLE IF NOT EXISTS` also does not change a
  default on an already-created table; application writes remain safe because
  every current repository path supplies the server-side UTC expression.
- Warehouse runtime limits individual frontend messages to 32 MB and uploads to
  200 MB. Current pages are not paginated for very large result sets.

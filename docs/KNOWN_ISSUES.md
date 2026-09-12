# Known Issues

- Dataverse logical names, choices, required fields, keys and relationship cardinalities remain unknown.
- Imported EIMS rows remain `UNMATCHED`; candidate generation and manual confirmation UI remain future work.
- Mock data resets with each Streamlit session.
- Snowflake SQL and repository writes require integration testing against a DEV account, warehouse and privileges.
- Authentication, role authorization and durable user identity are deployment work.
- Deletion blocks referenced records. Final soft-delete and retention rules require business/Dataverse decisions.
- Sample-level Salmonella fields and final quota rules require authoritative metadata.
- Optimistic locking is implemented for current editable business entities, including the dedicated Facility Detail workspace. Real multi-session behavior still requires Snowflake DEV validation.
- Snowflake optimistic locking and Snowpark affected-row parsing require validation against a real DEV account with populated `UPDATED_AT` columns.
- Streamlit named-connection, active warehouse session, connector SSO and key-pair paths are implemented but still require deployment-specific validation.
- Snowpark bulk writes use bounded multi-row `VALUES` statements. Real DEV testing must establish safe batch sizes for actual row widths and warehouse limits.
- Quota and Facility Detail fields, choices and requiredness remain provisional pending EIMS metadata, although their list/new/detail/edit workflows are implemented.
- Source profiling is advisory and processes all selected worksheets in application memory; authoritative types, keys and relationships require EIMS metadata confirmation.

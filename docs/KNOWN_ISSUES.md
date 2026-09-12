# Known Issues

- Dataverse logical names, choices, required fields, keys and relationship cardinalities remain unknown.
- Imported EIMS rows remain `UNMATCHED`; candidate generation and manual confirmation UI remain future work.
- Mock data resets with each Streamlit session.
- Snowflake SQL and repository writes require integration testing against a DEV account, warehouse and privileges.
- Authentication, role authorization and durable user identity are deployment work.
- Deletion blocks referenced records. Final soft-delete and retention rules require business/Dataverse decisions.
- Sample-level Salmonella fields and final quota rules require authoritative metadata.
- Optimistic locking currently covers only Account edits. Facilities, Flocks, Quotas and Salmonella upserts still last-write-wins; extend the `EXPECTED_UPDATED_AT` pattern to them next.
- The Snowflake optimistic-lock clause is verified only by SQL-shape unit tests with a stubbed cursor; it needs validation against a real DEV account (`UPDATED_AT` column present and populated on every CORE table).

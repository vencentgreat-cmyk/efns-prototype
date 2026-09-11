# Known Issues

- Dataverse logical names, choices, required fields, keys and relationship cardinalities remain unknown.
- Imported EIMS rows remain `UNMATCHED`; candidate generation and manual confirmation UI remain future work.
- Mock data resets with each Streamlit session.
- Snowflake SQL and repository writes require integration testing against a DEV account, warehouse and privileges.
- Authentication, role authorization and durable user identity are deployment work.
- Deletion blocks referenced records. Final soft-delete and retention rules require business/Dataverse decisions.
- Sample-level Salmonella fields and final quota rules require authoritative metadata.

# Known Issues

- Dataverse table names, choices, required fields, keys, and relationship
  cardinalities are still unknown.
- Production-to-flock links in synthetic records are fabricated for the demo.
  Imported EIMS records remain `UNMATCHED`; no relationship IDs are inferred.
- Mock data is in-memory and resets with each Streamlit session.
- Snowflake write operations, including RAW row persistence, are not implemented.
- The transitional production union accepts new columns intentionally. It must be
  replaced by an approved schema and migration in the Snowflake implementation.
- Authentication, authorization, durable audit identity, duplicate-file handling,
  and transactional import rollback remain future deployment requirements.
- Quota and disease-testing modules remain placeholders; their business rules are
  not implemented.

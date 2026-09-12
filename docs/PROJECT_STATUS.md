# Project Status

## Implemented

- Streamlit workspaces for Accounts, Facilities, Facility Details, Flocks, Flock Transactions, Quota Registrations, Quota Transactions, Salmonella Tests and reporting. Operational entity pages use record-based list/new/detail/edit navigation; Quota related records support cross-module links and new-transaction prefill.
- Full Flock validation at the repository boundary; the dedicated Flocks page is the only Flock editor.
- EIMS validation, SHA-256 duplicate detection, RAW preservation and atomic RAW/normalized import.
- Mock persistence and a parameterized Snowflake adapter for CRUD, import writes, filtered reads, commit and rollback.
- A shared, lazy `SqlExecutor` boundary with Streamlit connection, active Snowpark session and connector runtimes. Snowpark uses public session APIs and bounded multi-row inserts.
- Optimistic locking for Account, Facility, Facility Detail, Flock, Flock Transaction, Quota Registration, Quota Transaction and Salmonella Test upserts. Both repositories consume `EXPECTED_UPDATED_AT`; stale edits raise `ConcurrencyError`.
- A System Status page with repository/runtime/configuration state and an explicit read-only connection check.
- Provisional DEV SQL for RAW, CORE and REPORTING standard tables/views.
- Automated pytest workflow for pushes and pull requests.

Mock mode remains the default. Connection/executor behavior is available for offline verification but has not been run against an EFNS Snowflake account. Dataverse logical names, choices and relationships remain provisional.

## Validation boundaries

- **Completed in code:** executor abstraction, lazy runtime choice, parameter binding, transaction boundary, bulk insert strategy, sanitized errors, configuration templates and optimistic locking.
- **Offline verification:** syntax/import checks and executor/repository tests with fake connector and Snowpark sessions.
- **Needs Snowflake DEV:** authentication, grants, DML affected-row shapes, transaction behavior, query result casing and bulk statement limits.
- **Needs EIMS metadata:** final identifiers, types, required fields, relationships, choice values and business rules.

Run: `.\.venv\Scripts\python.exe -m streamlit run app/Home.py`.

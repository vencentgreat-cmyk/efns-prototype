# Project Status

## Implemented

- Streamlit workspaces for Accounts, Facilities, Facility Details, Flocks, Flock Transactions, Quota Registrations, Quota Transactions, Salmonella Tests and reporting. Operational entity pages use record-based list/new/detail/edit navigation; Quota related records support cross-module links and new-transaction prefill.
- Full Flock validation at the repository boundary; the dedicated Flocks page is the only Flock editor.
- EIMS validation, SHA-256 duplicate detection, RAW preservation and atomic RAW/normalized import.
- Mock persistence and a parameterized Snowflake adapter for CRUD, import writes, filtered reads, commit and rollback.
- A shared, lazy `SqlExecutor` boundary with Streamlit connection, active Snowpark session and connector runtimes. Snowpark uses public session APIs and bounded multi-row inserts.
- Optimistic locking for Account, Facility, Facility Detail, Flock, Flock Transaction, Quota Registration, Quota Transaction and Salmonella Test upserts. Both repositories consume `EXPECTED_UPDATED_AT`; stale edits raise `ConcurrencyError`.
- A System Status page with repository/runtime/configuration state and an explicit read-only connection check.
- A schema-agnostic Source Data Profiler for in-memory CSV/XLSX/XLSM inspection, heuristic key/relationship suggestions, and profile-only CSV/Excel exports.
- Offline executor coverage for runtime selection, settings, transactions, affected-row parsing and validated Connector/Snowpark bulk writes.
- Replaceable application authentication contract with local SQLite password
  sessions and Snowflake viewer identity, both enforcing `@nsegg.ca` access.
- Role-aware navigation, direct page guards, repository-level mutation authorization, Admin user management and an Admin/Developer audit log.
- Provisional DEV SQL for RAW, CORE and REPORTING plus SECURITY/APP persistence,
  role/grant scripts, X-Small warehouse and a reviewed resource-monitor default.
- Automated pytest workflow for pushes and pull requests.
- Dual local/Snowflake identity handling: SQLite sessions locally and trusted
  `st.user.email` in Snowflake, backed by Snowflake application-user and audit tables.
- Snowflake-default Python 3.11/Streamlit 1.52.2 warehouse deployment bundle,
  credential-free Snowflake CLI project definition with an explicit warehouse
  runtime, table-specific DEV grants, and a 10-credit monthly cost control.

Mock mode remains the default. Connection/executor behavior is available for offline verification but has not been run against an EFNS Snowflake account. Dataverse logical names, choices and relationships remain provisional.

## Validation boundaries

- **Completed in code:** executor abstraction, lazy runtime choice, parameter binding, transaction boundary, bulk insert strategy, sanitized errors, configuration templates, optimistic locking, prototype authentication and application authorization.
- **Offline verification:** syntax/import checks and executor/repository tests with fake connector and Snowpark sessions.
- **Needs Snowflake DEV:** `st.user` email population, package resolution, grants,
  DML affected-row shapes, transaction behavior, query result casing and bulk limits.
- **Needs EIMS metadata:** final identifiers, types, required fields, relationships, choice values and business rules.

Run: `.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py`.

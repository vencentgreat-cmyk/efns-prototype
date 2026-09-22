# Project Status

## Implemented

- Streamlit workspaces for Accounts, Farm Locations, Facilities, Facility Details, Flocks, Flock Transactions, Quota Registrations, Quota Transactions, Salmonella Tests and reporting. Farm Location is a provisional Account child kept separate from Facility. Operational entity pages use record-based list/new/detail/edit navigation through page-local session state and registered-page actions without generated browser URLs.
- Reusable Active/Inactive/All saved views for Accounts, Farm Locations, Facilities, Facility Details, Flocks and Quota Registrations. Account role views are generated from shared role constants; repository queries apply status and role predicates where practical.
- Full Flock validation at the repository boundary; the dedicated Flocks page is the only Flock editor.
- EIMS validation, SHA-256 duplicate detection, RAW preservation and atomic RAW/normalized import.
- A separate historical EIMS migration workspace with deterministic synthetic export generation, cross-file validation, encrypted-stage paths, RAW traceability, source-to-target IDs, dependency-ordered atomic CORE writes, reconciliation, idempotent retries, and batch-scoped synthetic cleanup.
- Mock persistence and a parameterized Snowflake adapter for CRUD, import writes, filtered reads, commit and rollback.
- A shared, lazy `SqlExecutor` boundary with Streamlit connection, active Snowpark session and connector runtimes. Snowpark uses public session APIs and bounded multi-row inserts.
- Optimistic locking for Account, Facility, Facility Detail, Flock, Flock Transaction, Quota Registration, Quota Transaction and Salmonella Test upserts. Both repositories consume `EXPECTED_UPDATED_AT`; stale edits raise `ConcurrencyError`.
- A System Status page with repository/runtime/configuration state and an explicit read-only connection check.
- A schema-agnostic Source Data Profiler for in-memory CSV/XLSX/XLSM inspection, heuristic key/relationship suggestions, and profile-only CSV/Excel exports.
- Offline executor coverage for runtime selection, settings, transactions, affected-row parsing and validated Connector/Snowpark bulk writes.
- Replaceable application authentication contract with local SQLite password
  sessions and Snowflake viewer identity, both enforcing `@nsegg.ca` access.
- Role-aware navigation, direct page guards, repository-level mutation authorization, Admin user management and an Admin/Developer audit log.
- Internal Report Center with a code-maintained catalog, service-level report permissions, parameter-bound Quota Summary query, ten allowlisted custom datasets, exact-result CSV/XLSX exports, session-only saved configurations and report audit events. Screenshot-supported Flock reports and official forms/letters remain catalog contracts pending rules/templates.
- Provisional DEV SQL for RAW, CORE and REPORTING plus SECURITY/APP persistence,
  role/grant scripts, X-Small warehouse and a reviewed resource-monitor default.
- Automated pytest workflow for pushes and pull requests.
- Dual local/Snowflake identity handling: SQLite sessions locally and trusted
  `st.user.email` in Snowflake, backed by Snowflake application-user and audit tables.
- Snowflake-default Python 3.11/Streamlit 1.52.2 warehouse deployment bundle,
  credential-free Snowflake CLI project definition with an explicit warehouse
  runtime, table-specific DEV grants, and a 10-credit monthly cost control.

Mock mode remains the default. The V1 migration package was manually verified in EFNS DEV at 8,450 RAW rows with all nine CORE counts matched and restricted cleanup completed. Farm Location and the 8,575-row V2 package are offline-validated only. Dataverse logical names, choices and relationships remain provisional.

## Validation boundaries

- **Completed in code:** executor abstraction, lazy runtime choice, parameter binding, transaction boundary, bulk insert strategy, sanitized errors, configuration templates, optimistic locking, prototype authentication and application authorization.
- **Offline verification:** syntax/import checks and executor/repository tests with fake connector and Snowpark sessions.
- **Needs Snowflake DEV:** migration stage upload, `st.user` email population, package resolution, grants,
  DML affected-row shapes, transaction behavior, query result casing and bulk limits.
- **Needs EIMS metadata:** final identifiers, types, required fields, relationships, choice values and business rules.

Run: `.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py`.

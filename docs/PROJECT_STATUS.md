# Project Status

## Implemented

- Streamlit workspaces for Accounts, Facilities, Facility Details, Flocks, Flock Transactions, Quota Registrations, Quota Transactions, Salmonella Tests and reporting.
- Full Flock validation at the repository boundary; the dedicated Flocks page is the only Flock editor.
- EIMS validation, SHA-256 duplicate detection, RAW preservation and atomic RAW/normalized import.
- Mock persistence and a parameterized Snowflake adapter for CRUD, import writes, filtered reads, commit and rollback.
- Provisional DEV SQL for RAW, CORE and REPORTING standard tables/views.
- Automated pytest workflow for pushes and pull requests.

Mock mode remains the default. Snowflake code is covered with fake-connection tests but has not been run against an EFNS Snowflake account. Dataverse logical names, choices and relationships remain provisional.

Run: `.\.venv\Scripts\python.exe -m streamlit run app/Home.py`.

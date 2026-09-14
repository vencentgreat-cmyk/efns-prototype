# Streamlit in Snowflake Compatibility Audit

Audit target: Snowflake warehouse runtime, its default Python 3.11 runtime, and
Streamlit 1.52.2. This combination has deployed and started successfully in DEV.

## Compatible now

- Runtime Python files parse with the Python 3.11 grammar. The code uses
  `StrEnum`, type unions, dataclasses, and standard-library APIs available in 3.11.
- `streamlit_app.py` is at the deployment source root. It runs the existing
  application shell without copying business logic. `st.navigation` remains the
  only multipage mechanism, and the page directory is included explicitly.
- Imports are rooted at `app` and `data`; both packages and their `__init__.py`
  files are included in `snowflake.yml`.
- The used Streamlit APIs are available in 1.52.2, including `st.navigation`,
  `st.Page`, `st.user`, `st.query_params`, `st.context`, dataframe selection,
  link columns, Material icons, width parameters, and horizontal containers.
- Uploaded CSV/Excel data is processed in memory. Exports use in-memory buffers.
  Snowflake mode does not persist application state to the local filesystem.
- SQLite is optional at import time and instantiated for the local authentication
  backend only. Snowflake mode instantiates `SnowflakeAuthStore`; `.local` is
  absent from deployment artifacts.
- Deployment dependencies use only the Snowflake Anaconda channel: Streamlit,
  pandas, NumPy, Snowpark, and openpyxl. `environment.yml` deliberately omits a
  Python dependency so the warehouse runtime supplies its default Python 3.11.

## Snowflake-specific behavior

- `snowflake.yml` requests `SYSTEM$WAREHOUSE_RUNTIME`, and the mandatory
  post-deployment SQL sets it again after every deploy or replacement.
- `page_title` and `page_icon` arguments to `st.set_page_config` are ignored by
  Snowflake; layout remains supported.
- Snowflake adds `streamlit-` to browser query parameter names while the
  `st.query_params` API continues to expose unprefixed keys.
- Warehouse runtime caches are session-scoped. This application relies on
  session state for Mock data and does not assume cross-viewer cache sharing.
- A single frontend message is limited to 32 MB and a file upload to 200 MB.
  Large production datasets need pagination/bounded result policies before PROD.
- Snowflake CSP permits the current inline visual styling. The application does
  not load external scripts or custom components.

## Must be checked in the real DEV account

- Confirm that the account package channel resolves every version in
  `environment.yml`, particularly pandas, NumPy, openpyxl, and Streamlit 1.52.2.
  Python should be the warehouse runtime default (currently Python 3.11), not an
  explicit Conda dependency.
- Confirm `st.user.email` is populated for every EFNS viewer and normalized to
  the expected corporate email.
- Validate cross-page record links in the Snowsight `/!/` URL shell.
- Validate owner-rights grants, Snowpark DML affected-row results, explicit
  transaction rollback, upload size expectations, and 32 MB display boundaries.

Run `python scripts/check_snowflake_readiness.py` for offline structure and
Python 3.11 grammar checks.

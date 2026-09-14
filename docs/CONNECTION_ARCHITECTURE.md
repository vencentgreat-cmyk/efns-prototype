# Snowflake Connection Architecture

This implementation is infrastructure for a provisional DEV model. It does not certify the current SQL as the final EFNS schema.

## Execution boundary

`SnowflakeRepository` depends on `SqlExecutor` from `data/connection.py`. It does not select authentication methods, open cursors, or access Snowpark private connection attributes.

The repository emits fixed application-controlled identifiers and `%s` data placeholders. `ConnectorExecutor` uses connector binding directly. `SnowparkExecutor` converts placeholders to `?` and passes values through `Session.sql(..., params=...)`.

Supported operations are:

- query returning a pandas DataFrame
- DML with affected-row count
- connector `executemany` and Snowpark multi-row VALUES batches
- explicit commit and rollback
- a transaction context used by CRUD and production imports

Snowpark bulk inserts are converted into bounded multi-row statements. There is no silent row-by-row fallback.

## Lazy runtime selection

The executor is selected on the first SQL operation in this order:

1. named `st.connection("snowflake").session()` for local Streamlit or supported Streamlit deployments
2. Snowpark `get_active_session()` for warehouse runtime compatibility
3. `snowflake.connector` for local scripts, services, and offline test doubles

Only errors that mean a runtime is absent allow the next option. Authentication, network, permission, and SQL errors are surfaced as sanitized repository errors and do not trigger a different credential path.

## Configuration

Preferred authentication is a named connection, SSO/external browser, or a private key stored outside the repository. Password authentication is optional for isolated development. `.env`, `secrets.toml`, tokens, and private keys must remain untracked.

`REPOSITORY_MODE=mock` requires no Snowflake configuration. `REPOSITORY_MODE=snowflake` validates identifiers immediately and opens a connection only when data is requested or the user selects **Check connection**.

## Deployment modes

- **Local Streamlit:** use a Streamlit Snowflake connection or connector settings. Start with `python -m streamlit run streamlit_app.py`.
- **Streamlit in Snowflake warehouse runtime:** the named Streamlit connection is attempted first; an active Snowpark session is the compatibility path.
- **Container runtime:** use connector configuration supplied by the platform secret manager. Do not bake credentials or keys into the image.

Run all schema scripts manually against a dedicated DEV database only after reviewing provisional identifiers. Real account validation, grants, affected-row response shapes, SSO/key-pair setup, and Streamlit deployment packaging remain pending.

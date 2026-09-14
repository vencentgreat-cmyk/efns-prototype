# EFNS Snowflake DEV Deployment

This runbook prepares a warehouse-runtime Streamlit in Snowflake application.
All object names and the 10-credit monthly DEV monitor are reviewable defaults.
The operational model remains provisional until EIMS metadata is available.

## Information to collect

Collect these values before running setup:

- Snowflake organization name, account name, full account identifier
  (`organization-account`), cloud/region, account locator, and Snowsight URL.
- Named Snowflake CLI connection name and approved authentication method. Prefer
  SSO with `EXTERNALBROWSER` for a human deployer or key-pair/workload identity
  for later automation. Keep credentials in the user-level CLI config only.
- Snowflake usernames for the account setup operator, EFNS deployer, and every
  DEV viewer; confirm each user profile has its real `@nsegg.ca` email populated.
- Real initial EFNS Admin email and display name for `07_initial_admin.sql`.
- People approved to receive `EFNS_DEV_ADMIN`, `EFNS_DEV_EDITOR`,
  `EFNS_DEV_DEVELOPER`, `EFNS_DEV_VIEWER`, and `EFNS_DEV_DEPLOYER` account roles.
- Approval for `EFNS_DEV`, `EFNS_DEV_WH`, schema, stage, and Streamlit object
  names, plus the X-Small size, 60-second auto-suspend, and 10-credit monthly cap.
- Network policy/MFA requirements, data residency, account edition, retention,
  Time Travel, audit retention, and incident contacts.
- Confirmation that the Snowflake Anaconda channel offers the exact packages in
  `environment.yml` for this account and region.

No password, token, private key, `config.toml`, `.env`, or `secrets.toml` belongs
in this repository.

## First-time setup order

1. Review all SQL, replace the two placeholders in `sql/07_initial_admin.sql`,
   and adjust the resource-monitor quota if EFNS Finance/IT requires it.
2. Install current Snowflake CLI on the administrator workstation. Add a named
   connection interactively and test it:

   ```powershell
   snow connection add --connection-name efns-dev --authenticator EXTERNALBROWSER
   snow connection test --connection efns-dev
   ```

3. As an operator able to use USERADMIN, SYSADMIN, SECURITYADMIN, and
   ACCOUNTADMIN, run the account foundation and schema/table files in order:

   ```powershell
   snow sql --connection efns-dev --filename sql/00_dev_foundation.sql
   snow sql --connection efns-dev --filename sql/01_setup.sql
   snow sql --connection efns-dev --filename sql/02_core_tables.sql
   snow sql --connection efns-dev --filename sql/03_production_tables.sql
   snow sql --connection efns-dev --filename sql/04_reporting_views.sql
   snow sql --connection efns-dev --filename sql/05_security_tables.sql
   snow sql --connection efns-dev --filename sql/06_least_privilege_grants.sql
   ```

4. Grant `EFNS_DEV_DEPLOYER` directly to the approved deployment user, then use
   a CLI connection whose primary role is `EFNS_DEV_DEPLOYER`. Run the reviewed
   initial-admin script:

   ```powershell
   snow sql --connection efns-dev --filename sql/07_initial_admin.sql
   ```

5. Run offline checks and tests before upload:

   ```powershell
   .\.venv\Scripts\python.exe scripts/check_snowflake_readiness.py
   .\.venv\Scripts\python.exe -m pytest -v
   git diff --check
   ```

6. From the repository root, deploy through the current Snowflake CLI path. Do
   not pass `--legacy`; current CLI uses `CREATE STREAMLIT ... FROM`:

   ```powershell
   snow streamlit deploy efns_dev --connection efns-dev --replace --prune
   ```

7. After **every** deployment, run the mandatory post-deployment script using an
   operator that can use `EFNS_DEV_DEPLOYER` and `SECURITYADMIN`:

   ```powershell
   snow sql --connection efns-dev --filename sql/08_post_deploy_grants.sql
   ```

   The script first runs the following as `EFNS_DEV_DEPLOYER`, then switches to
   `SECURITYADMIN` for the viewer grants:

   ```sql
   ALTER STREAMLIT EFNS_DEV.APP.EFNS_INTERNAL_APP
       SET RUNTIME_NAME = 'SYSTEM$WAREHOUSE_RUNTIME';
   ```

   Treat the deploy and this script as one release procedure. Do not open the
   application to viewers until both steps succeed.

8. Grant one of the four viewer account roles to each approved Snowflake user.
   Add each real email to `SECURITY.APP_USER` through the EFNS User Management
   page (the initial Admin is already seeded). Account-role access and the table
   role must both be present.
9. Complete every item in `SNOWFLAKE_SMOKE_TEST.md` with synthetic data before
   allowing operational use.

## Authentication behavior

Local development sets `EFNS_RUNTIME_MODE=local` and defaults to Mock plus the
ignored `.local/efns_auth.db`. Snowflake deployment uses automatic runtime
detection: `st.user.email` is validated against `@nsegg.ca`, then an active user
and role are loaded from `EFNS_DEV.SECURITY.APP_USER`. Password login, reset, and
local sessions are not shown in Snowflake. Operations audit the viewer email and
Snowflake `CURRENT_TIMESTAMP()` in UTC-capable `TIMESTAMP_TZ` columns.

The Streamlit object runs with owner rights. `EFNS_DEV_APP_OWNER` has only the
warehouse, database/schema usage, operational table DML, reporting SELECT, stage,
and Streamlit creation privileges required by the current application. The audit
table grants only `SELECT` and `INSERT`; no future-object grant can restore
`UPDATE` or `DELETE`. Viewer
roles receive database/schema/Streamlit USAGE and no direct table DML.

`06_least_privilege_grants.sql` first revokes the earlier database-wide current
and future table/view grants, then grants only the objects queried by the current
repositories. This cleanup matters when upgrading a DEV environment created from
an earlier draft of the script.

The deployment definition selects `SYSTEM$WAREHOUSE_RUNTIME`, and the mandatory
post-deployment SQL enforces it again. Snowflake supplies the warehouse runtime's
default Python 3.11; `environment.yml` intentionally omits Python while pinning
Streamlit 1.52.2 and the remaining reviewed packages. The DEV monitor notifies
at 75% of 10 credits and suspends the warehouse at 100%.

## Rollback

For a bad application release, redeploy the last reviewed Git revision using
the same `snow streamlit deploy ... --replace --prune` command, then rerun
`sql/08_post_deploy_grants.sql`. Preserve data tables and audit events. If access
must stop immediately, revoke USAGE on the Streamlit object from the four viewer
roles; re-grant after remediation.

For a bad schema migration, stop application access, restore affected DEV tables
with the account's available Time Travel/clone procedure, validate counts and
relationships, then redeploy. The current setup scripts are creation-oriented;
they do not drop tables or use `CREATE OR REPLACE TABLE`.

## Troubleshooting

- **No viewer email:** verify the Snowflake user's EMAIL property and sign-in
  identity. Do not fall back to `CURRENT_USER()`, which can identify the app owner.
- **Access not provisioned:** confirm exact normalized email, `ACTIVE=TRUE`, one
  supported role value, and an account-role grant allowing Streamlit USAGE.
- **Package resolution:** confirm the application uses the warehouse runtime's
  default Python 3.11 and check the Snowsight package picker for the pinned
  package versions. Do not add Python to `environment.yml`; change package pins
  only after review and tests.
- **Unexpected container runtime:** rerun `sql/08_post_deploy_grants.sql`, then
  confirm the Streamlit object's `RUNTIME_NAME` is `SYSTEM$WAREHOUSE_RUNTIME`.
- **SQL permission error:** verify the Streamlit owner/deployer role inheritance
  and grants from `06_least_privilege_grants.sql`; do not add broad account grants.
- **Import failure:** verify the transaction rollback across IMPORT_BATCH, RAW,
  and PRODUCTION_RECORD, then correlate sanitized UI time with query history.
- **Unexpected cost:** suspend `EFNS_DEV_WH`, inspect warehouse history and the
  resource monitor, then adjust access or queries before resuming.

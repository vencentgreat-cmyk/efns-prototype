# Snowflake DEV Smoke Test

Use synthetic data only. Record the Snowflake query ID and UTC time for failures.

1. **Deployment runtime:** immediately after deployment, run
   `sql/08_post_deploy_grants.sql`. Inspect the Streamlit object and confirm
   `RUNTIME_NAME` is `SYSTEM$WAREHOUSE_RUNTIME`, the application starts, the
   runtime supplies Python 3.11, and Streamlit reports version 1.52.2.
2. **Connection and viewer identity:** open System Status as each test user,
   confirm the repository is Snowflake, authentication is Snowflake viewer, the
   displayed viewer email is correct, and `Check connection` succeeds.
3. **Authorization:** verify Admin, Data Editor, Reporting Viewer, and Developer
   navigation and direct-page guards against the documented permission matrix.
   Confirm an inactive `APP_USER` cannot enter the application.
4. **Reads:** open Accounts, Facilities, Flocks, Quota, Salmonella, Production,
   and Reports. Apply filters and confirm bounded result sets and links.
5. **Creates/updates:** as Data Editor create and update one synthetic Account,
   Facility, Flock, Quota, and Salmonella record. Verify IDs, timestamps, and
   relationships in Snowflake. Attempt a stale edit from a second browser and
   confirm the first saved value is not overwritten.
6. **Permission enforcement:** as Reporting Viewer attempt direct new/edit URLs
   and service mutations. Confirm the repository rejects writes. Confirm only an
   Admin can manage users and only Admin/Developer can read audit events.
7. **Production import:** upload a small synthetic workbook, verify one import
   batch, source rows, normalized rows, source hash, and `UNMATCHED` status.
   Re-upload it and confirm duplicate detection blocks it unless override is used.
8. **Rollback:** use a deliberately invalid normalized row in DEV. Confirm the
   batch, RAW rows, and normalized rows all roll back and an error is safely shown.
9. **Audit:** verify create, update, delete, import, and user-management events
   contain the actual `st.user.email` and a UTC `OCCURRED_AT` timestamp.
10. **Cost/operations:** confirm X-Small size, 60-second auto-suspend, resource
   monitor assignment, query warehouse, event logging, and no plaintext secrets
   in the stage or Streamlit source.

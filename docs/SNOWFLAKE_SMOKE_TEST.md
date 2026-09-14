# Snowflake DEV Smoke Test

Use synthetic data only. Record the Snowflake query ID and UTC time for failures.

1. **Connection and viewer identity:** open System Status as each test user,
   confirm the repository is Snowflake, authentication is Snowflake viewer, the
   displayed viewer email is correct, and `Check connection` succeeds.
2. **Authorization:** verify Admin, Data Editor, Reporting Viewer, and Developer
   navigation and direct-page guards against the documented permission matrix.
   Confirm an inactive `APP_USER` cannot enter the application.
3. **Reads:** open Accounts, Facilities, Flocks, Quota, Salmonella, Production,
   and Reports. Apply filters and confirm bounded result sets and links.
4. **Creates/updates:** as Data Editor create and update one synthetic Account,
   Facility, Flock, Quota, and Salmonella record. Verify IDs, timestamps, and
   relationships in Snowflake. Attempt a stale edit from a second browser and
   confirm the first saved value is not overwritten.
5. **Permission enforcement:** as Reporting Viewer attempt direct new/edit URLs
   and service mutations. Confirm the repository rejects writes. Confirm only an
   Admin can manage users and only Admin/Developer can read audit events.
6. **Production import:** upload a small synthetic workbook, verify one import
   batch, source rows, normalized rows, source hash, and `UNMATCHED` status.
   Re-upload it and confirm duplicate detection blocks it unless override is used.
7. **Rollback:** use a deliberately invalid normalized row in DEV. Confirm the
   batch, RAW rows, and normalized rows all roll back and an error is safely shown.
8. **Audit:** verify create, update, delete, import, and user-management events
   contain the actual `st.user.email` and a UTC `OCCURRED_AT` timestamp.
9. **Cost/operations:** confirm X-Small size, 60-second auto-suspend, resource
   monitor assignment, query warehouse, event logging, and no plaintext secrets
   in the stage or Streamlit source.
